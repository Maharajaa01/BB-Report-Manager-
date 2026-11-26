<script setup lang="ts">
/**
 * The Target Chart sheets: Asst. Manager (posting staff) and TL (6th - 12th STD students).
 * Weekly / Monthly "Last 2 Place" grids and the 10+ Mistake lists.
 */
import { computed, ref, watch } from "vue"

import { getReport } from "@/api/reports"
import type { TargetCell, TargetGridReport, TargetReport, TenPlusReport } from "@/api/types"
import RankDialog from "@/components/RankDialog.vue"
import TargetGrid from "@/components/TargetGrid.vue"
import TargetInsights from "@/components/TargetInsights.vue"
import TenPlusSheet from "@/components/TenPlusSheet.vue"
import { type Cell, downloadCsv, slug } from "@/lib/csv"
import { date } from "@/lib/format"
import type { ReportDef } from "@/lib/reports"
import { options, useFilters } from "@/lib/store"
import { gridCsv, tenPlusCsv } from "@/lib/targets"

const props = defineProps<{ report: ReportDef }>()

const { filters, setFilter, apiFilters, summary } = useFilters()
const data = ref<TargetReport | null>(null)
const error = ref("")
const loading = ref(false)
let controller: AbortController | null = null

const sent = computed(() => apiFilters(props.report))
const staff = computed(() => props.report.dashboard === "asst_manager")

async function load() {
	controller?.abort()
	controller = new AbortController()
	loading.value = true
	error.value = ""
	try {
		data.value = await getReport<TargetReport>(props.report.key, sent.value, controller.signal)
	} catch (e) {
		if ((e as Error).name === "AbortError") return
		data.value = null
		error.value = (e as Error).message
	} finally {
		loading.value = false
	}
}

watch(() => JSON.stringify(sent.value), load, { immediate: true })

const grid = computed(() => (data.value && "tables" in data.value ? (data.value as TargetGridReport) : null))
const tenPlus = computed(() => (data.value && "lists" in data.value ? (data.value as TenPlusReport) : null))
const weekly = computed(() => !!grid.value && grid.value.tables.length > 1)

// Staff live on this (ERP) site; students on the tuition site.
const link = (id: string) =>
	staff.value
		? `/app/employee/${encodeURIComponent(id)}`
		: `${options.data?.tuition_site_url ?? ""}/app/student/${encodeURIComponent(id)}`

/** A month clicked in the trend: show every sheet for that month. */
function pickMonth(key: string) {
	const t = data.value?.insights.trend.find((m) => m.key === key)
	if (t) setFilter("month", t.label.split(" ")[0])
}

// ---------------------------------------------------------------- drill-down

const cell = ref<TargetCell | null>(null)
const cellTitle = ref("")
function openCell(title: string, c: TargetCell) {
	cellTitle.value = title
	cell.value = c
}

// ---------------------------------------------------------------- export

function exportCsv() {
	const d = data.value
	if (!d) return
	const head: Cell[][] = [[d.subtitle], [d.title], [`${d.period} · ${summary(props.report)}`]]
	const body = grid.value ? gridCsv(grid.value) : tenPlus.value ? tenPlusCsv(tenPlus.value) : []
	downloadCsv(`${slug(props.report.nav)}_${slug(d.period)}`, [...head, ...body])
}

defineExpose({ refresh: load, exportCsv })
</script>

<template>
	<div v-if="error && !data" class="bbr-state error">
		{{ error }}
		<div><button type="button" class="bbr-btn secondary" @click="load">Try again</button></div>
	</div>
	<div v-else-if="!data" class="bbr-state">Loading…</div>
	<div v-else class="bbr-content" :class="{ 'is-loading': loading }">
		<section class="bbr-sheet bbr-target-sheet" :style="{ '--chart-bg': report.bg }">
			<p class="bbr-sheet-year">{{ data.subtitle }}</p>
			<h1 class="bbr-sheet-title">{{ data.title }}</h1>
			<p class="bbr-target-period">
				<span v-if="report.key === 'am_monthly' && !filters.month"></span>
				<span v-else>Month: <b>{{ data.period }}</b></span>
				<span>Academic Year {{ data.academic_year_label }}</span>
			</p>

			<div v-if="grid" :class="{ 'bbr-target-weeks': weekly }">
				<TargetGrid
					v-for="t in grid.tables"
					:key="t.key"
					:data="grid"
					:table="t"
					:heading="weekly ? t.label : undefined"
					@open="openCell"
				/>
			</div>
			<TenPlusSheet v-else-if="tenPlus" :data="tenPlus" :link="link" />

			<div class="bbr-target-signs">
				<span>{{ staff ? "HR Sign" : "TL Sign" }}</span>
				<span>{{ report.key === "am_weekly" || report.key === "tl_weekly" ? "Asst. Manager Sign" : "Manager Sign" }}</span>
			</div>
		</section>

		<TargetInsights
			:data="data.insights"
			:lower-key="staff ? 'attendance' : 'leave'"
			:staff="staff"
			:link="link"
			@month="pickMonth"
		/>

		<p v-if="error" class="bbr-state error">{{ error }}</p>

		<p class="bbr-footnote">
			Generated {{ date(data.generated_on) }} · {{ summary(report) }}.<br />
			<template v-if="grid">
				Each cell shows the <b>last 2 places</b>: the two {{ staff ? "staff" : "students" }} with the most mistakes in that
				category, with their count, and the cell's <b>Total</b>. Click a cell to see everyone in it.
				<template v-if="weekly || report.key === 'am_weekly'"> Weeks are 01–07, 08–14, 15–21 and 22 to the month end.</template>
				<template v-if="!filters.month && report.key !== 'am_monthly'"> No month picked, so this is the current month.</template>
			</template>
			<template v-else>
				Everyone with <b>10 or more</b> mistakes in the month in that category.
				<template v-if="!filters.month"> No month picked, so this is the current month.</template>
			</template>
			<template v-if="staff">
				Counted from Employee Mistake records that are Active and not withdrawn on review.
			</template>
			<template v-else>
				Discipline / Critical = Behaviour graded Discipline / Critical; Attendance (Leave) = marked Absent; Study =
				Incomplete; Test = Fail; Home Work = Not Done. The 10+ Discipline list counts Critical too, and Study &amp; Test
				are counted together. Mistakes count under the standard and batch the student was in that day.
			</template>
		</p>
	</div>

	<RankDialog
		:cell="cell"
		:title="cellTitle"
		:filter-summary="summary(report)"
		:detail-head="staff ? 'Designation - Department' : 'STD - Batch'"
		:link="link"
		@close="cell = null"
	/>
</template>
