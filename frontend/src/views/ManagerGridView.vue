<script setup lang="ts">
/**
 * Manager Charts 3 - 7: Parents Complaint, Discontinued Students, KPI Points,
 * Staff's Count and Work List Mistakes -- the month-wise sheet with its detail.
 */
import { computed, ref, watch } from "vue"

import { getManagerDetail, getReport } from "@/api/reports"
import type { DetailResult, ManagerGridReport, ManagerQuery } from "@/api/types"
import ChartSheet from "@/components/ChartSheet.vue"
import DetailDialog from "@/components/DetailDialog.vue"
import ManagerInsights from "@/components/ManagerInsights.vue"
import { type Cell, downloadCsv, slug } from "@/lib/csv"
import { date } from "@/lib/format"
import type { ReportDef } from "@/lib/reports"
import { options, useFilters } from "@/lib/store"

const props = defineProps<{ report: ReportDef }>()

const { filters, apiFilters, summary } = useFilters()
const data = ref<ManagerGridReport | null>(null)
const error = ref("")
const loading = ref(false)
let controller: AbortController | null = null

const sent = computed(() => apiFilters(props.report))

async function load() {
	controller?.abort()
	controller = new AbortController()
	loading.value = true
	error.value = ""
	try {
		data.value = await getReport<ManagerGridReport>(props.report.key, sent.value, controller.signal)
	} catch (e) {
		if ((e as Error).name === "AbortError") return
		data.value = null
		error.value = (e as Error).message
	} finally {
		loading.value = false
	}
}

watch(() => JSON.stringify(sent.value), load, { immediate: true })

/** What a number on each sheet opens. */
const KIND: Record<string, string> = {
	parent_complaint: "complaint",
	discontinued: "discontinued",
	kpi_points: "kpi",
	staff_count: "staff",
	work_mistakes: "worklist",
}
const kind = computed(() => KIND[props.report.key] ?? "")
const linkBase = computed(() => (props.report.student ? options.data?.tuition_site_url ?? "" : ""))

// ---------------------------------------------------------------- drill-down

const detail = ref<{ q: ManagerQuery; title: string } | null>(null)

function openSheet(q: { kind: string; row?: string | null; month?: string | null }) {
	const d = data.value
	if (!d) return
	const row = d.rows.find((r) => r.key === q.row)
	const col = d.columns.find((c) => c.key === q.month)
	const title = [props.report.nav, row?.label ?? "All rows", col ? `${col.month} ${col.year}` : "Whole period"].join(" · ")
	detail.value = { q: { kind: kind.value, row: q.row ?? null, month: q.month ?? null, batch: (q as { batch?: string }).batch ?? null }, title }
}

function openInsight(q: ManagerQuery, label: string) {
	detail.value = { q: { ...q, kind: q.kind || kind.value }, title: `${props.report.nav} · ${label}` }
}

const loadDetail = computed(() => {
	const d = detail.value
	if (!d) return null
	const f = sent.value
	return (): Promise<DetailResult> => getManagerDetail(props.report.key, f, d.q)
})

// ---------------------------------------------------------------- export

function exportCsv() {
	const d = data.value
	if (!d) return
	const cols = d.columns
	const rows: Cell[][] = [
		[d.title],
		[`ACADEMIC YEAR : ${d.academic_year_label}`],
		[summary(props.report)],
		[],
		["S.No.", d.row_head || "STD", "TOTAL", ...cols.map((c) => c.label)],
		...d.rows.map((r) => [r.idx, r.label, r.total, ...cols.map((c) => r.values[c.key])]),
		["", "TOTAL", d.totals.total, ...cols.map((c) => d.totals.values[c.key])],
	]
	downloadCsv(`${slug(props.report.nav)}_${slug(filters.value.academic_year)}`, rows)
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
		<ChartSheet :report="report" :data="data" @open="openSheet" />
		<ManagerInsights :data="data.insights" :kind="kind" :link-base="linkBase" @open="openInsight" />

		<p v-if="error" class="bbr-state error">{{ error }}</p>
		<p class="bbr-footnote">
			Generated {{ date(data.generated_on) }} · {{ summary(report) }}.<br />
			<template v-if="report.key === 'parent_complaint'">
				Counted from Parent Complaint records, in the month each was received, under the student's STD and gender.
			</template>
			<template v-else-if="report.key === 'discontinued'">
				Students who left during the month (a student who left and rejoined counts in the month they left). TOTAL = leavers
				across the months.
			</template>
			<template v-else-if="report.key === 'kpi_points'">
				<b>Penalty points</b> from BB Performance Manager — the points of every counted staff mistake in the month (Active,
				not withdrawn). <b>Lower is better</b>; 0 is a clean month. Each row adds up the staff holding that posting role,
				matched on their designation; a blank cell means nobody held the role that month. Past months turn Final once
				rankings are saved.
			</template>
			<template v-else-if="report.key === 'staff_count'">
				Staff employed on any day of the month (joined by its end, not relieved before it started). Each person counts once:
				Posting and Internship by department, then Morning (morning department or a shift ending by 12:30), Subject (teaching
				designations), Evening (a shift starting after 2 PM), else Other. TOTAL = different people across the months.
			</template>
			<template v-else>
				A <b>work list mistake</b> is an Employee Worklist Entry marked Missed (or linked to a mistake), in the month of the
				period it was for. Hover a number for its Daily / Weekly / Monthly split.
			</template>
			Months not started yet are blank. Click any number to see the records behind it.
		</p>
	</div>

	<DetailDialog
		:load="loadDetail"
		:title="detail?.title ?? ''"
		:filter-summary="summary(report)"
		:tuition-url="options.data?.tuition_site_url ?? ''"
		@close="detail = null"
	/>
</template>
