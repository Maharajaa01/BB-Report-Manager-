<script setup lang="ts">
/** Report 1 -- ACTUAL STUDENTS COUNT, STD & MONTH WISE, with its detail sections. */
import { computed, ref, watch } from "vue"

import { getReport, getReportDetail } from "@/api/reports"
import type { DetailKind, DetailQuery, DetailResult, StudentCountReport } from "@/api/types"
import BatchTable from "@/components/BatchTable.vue"
import ChartSheet from "@/components/ChartSheet.vue"
import DetailDialog from "@/components/DetailDialog.vue"
import MovementTable from "@/components/MovementTable.vue"
import StackedChart from "@/components/StackedChart.vue"
import SummaryTiles from "@/components/SummaryTiles.vue"
import { downloadCsv, slug } from "@/lib/csv"
import { date, num } from "@/lib/format"
import type { ReportDef } from "@/lib/reports"
import { options, useFilters } from "@/lib/store"

const props = defineProps<{ report: ReportDef }>()

const { filters, apiFilters, summary } = useFilters()
const data = ref<StudentCountReport | null>(null)
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
		data.value = await getReport<StudentCountReport>(props.report.key, sent.value, controller.signal)
	} catch (e) {
		if ((e as Error).name === "AbortError") return
		data.value = null
		error.value = (e as Error).message
	} finally {
		loading.value = false
	}
}

watch(() => JSON.stringify(sent.value), load, { immediate: true })

// ---------------------------------------------------------------- drill-down

const DETAIL_TITLES: Record<DetailKind, string> = {
	present: "Students enrolled",
	opening: "Students at month start",
	joined: "New admissions",
	rejoined: "Rejoined students",
	discontinued: "Discontinued students",
	closing: "Students at month end",
}

const detail = ref<DetailQuery | null>(null)

const detailTitle = computed(() => {
	const q = detail.value
	const d = data.value
	if (!q || !d) return ""
	const row = d.rows.find((r) => r.key === q.row)
	const col = d.columns.find((c) => c.key === q.month)
	const [std, gender] = (q.row || "").split("|")
	const who = row ? row.label : std ? `${std}${gender ? ` - ${gender}` : ""}` : "All standards"
	const batch = q.batch ? (q.batch === "__none__" ? "No batch" : `Batch ${q.batch}`) : null
	return [DETAIL_TITLES[q.kind as DetailKind], who, batch, col ? `${col.month} ${col.year}` : "Whole period"].filter(Boolean).join(" · ")
})

const loadDetail = computed(() => {
	const q = detail.value
	if (!q) return null
	const filters = sent.value
	return async (): Promise<DetailResult> => ({
		type: "student",
		rows: await getReportDetail(props.report.key, filters, q),
	})
})

const strengthBars = computed(() =>
	(data.value?.movement ?? []).map((m) => ({
		key: m.key,
		label: m.label,
		short: m.short,
		running: m.running,
		lower: m.boys,
		upper: m.girls,
		extra: [
			{ label: "Joined", value: num(m.joined + m.rejoined) },
			{ label: "Left", value: num(m.discontinued) },
		],
	})),
)

const lastMonth = computed(() => {
	const m = data.value?.movement ?? []
	return m.length ? m[m.length - 1].key : null
})

// ---------------------------------------------------------------- export

function exportCsv() {
	const d = data.value
	if (!d) return
	const cols = d.columns
	const rows: (string | number | null)[][] = [
		[d.title],
		[`ACADEMIC YEAR : ${d.academic_year_label}`],
		[summary(props.report)],
		[],
		["S.No.", "STD", "TOTAL", ...cols.map((c) => c.label)],
		...d.rows.map((r) => [r.idx, r.label, r.total, ...cols.map((c) => r.values[c.key])]),
		["", "TOTAL", d.totals.total, ...cols.map((c) => d.totals.values[c.key])],
	]
	if (d.movement.length) {
		rows.push([], ["MONTH-WISE STUDENT MOVEMENT"],
			["Month", "Opening", "New", "Rejoined", "Left", "Closing", "Net", "Boys", "Girls"],
			...d.movement.map((m) => [m.label, m.opening, m.joined, m.rejoined, m.discontinued, m.closing, m.net, m.boys, m.girls]))
	}
	const b = d.batch_breakdown
	if (b) {
		rows.push([], [`STANDARD x BATCH STRENGTH - ${b.label}`],
			["Standard", ...b.batches.map((x) => `Batch ${x}`), "No batch", "Boys", "Girls", "Total"],
			...b.rows.map((r) => [r.standard, ...b.batches.map((x) => r.values[x]), r.no_batch, r.boys, r.girls, r.total]),
			["TOTAL", ...b.batches.map((x) => b.totals.values[x]), b.totals.no_batch, b.totals.boys, b.totals.girls, b.totals.total])
	}
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
	<!-- Refetch keeps the frame: the old render dims while new numbers load. -->
	<div v-else class="bbr-content" :class="{ 'is-loading': loading }">
		<ChartSheet :report="report" :data="data" @open="detail = $event" />
		<SummaryTiles v-if="data.summary" :summary="data.summary" :last-month="lastMonth" @open="detail = $event" />
		<div v-if="data.movement.length" class="bbr-grid-2">
			<StackedChart
				title="Month-end strength"
				:series="['Boys', 'Girls']"
				:bars="strengthBars"
				:note="data.movement.some((m) => m.running) ? '* running month, counted till today' : ''"
				@open="detail = { kind: 'closing', month: $event }"
			/>
			<MovementTable :movement="data.movement" @open="detail = $event" />
		</div>
		<BatchTable
			v-if="data.batch_breakdown && data.batch_breakdown.rows.length"
			:data="data.batch_breakdown"
			:gender="filters.gender"
			@open="detail = $event"
		/>
		<p v-if="error" class="bbr-state error">{{ error }}</p>
		<p class="bbr-footnote">
			Generated {{ date(data.generated_on) }} · {{ summary(report) }}.<br />
			<b>How students are counted:</b> a student counts in a month if they were enrolled on any day of it (admitted on or
			before the month end and not discontinued before it started; rejoined students count again from the rejoin date).
			Month-end strength counts only those still enrolled on the last day (or today, for the running month). TOTAL column =
			distinct students across the selected months. Batch is the student's current batch. Click any number to see the
			students.
		</p>
	</div>

	<DetailDialog
		:load="loadDetail"
		:title="detailTitle"
		:filter-summary="summary(report)"
		:tuition-url="options.data?.tuition_site_url ?? ''"
		@close="detail = null"
	/>
</template>
