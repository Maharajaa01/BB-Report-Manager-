<script setup lang="ts">
/** Manager Report 2 -- AFTER 15TH FEES PENDING COUNT, STD & MONTH WISE. */
import { computed, ref, watch } from "vue"

import { getFeeDetail, getReport } from "@/api/reports"
import type { DetailQuery, DetailResult, FeeKind, FeesPendingReport } from "@/api/types"
import BatchTable from "@/components/BatchTable.vue"
import ChartSheet from "@/components/ChartSheet.vue"
import DetailDialog from "@/components/DetailDialog.vue"
import FeeMonthTable from "@/components/FeeMonthTable.vue"
import StackedChart from "@/components/StackedChart.vue"
import { type Cell, downloadCsv, slug } from "@/lib/csv"
import { date, num, rupees, signed } from "@/lib/format"
import type { ReportDef } from "@/lib/reports"
import { options, useFilters } from "@/lib/store"

const props = defineProps<{ report: ReportDef }>()

const { filters, apiFilters, summary } = useFilters()
const data = ref<FeesPendingReport | null>(null)
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
		data.value = await getReport<FeesPendingReport>(props.report.key, sent.value, controller.signal)
	} catch (e) {
		if ((e as Error).name === "AbortError") return
		data.value = null
		error.value = (e as Error).message
	} finally {
		loading.value = false
	}
}

watch(() => JSON.stringify(sent.value), load, { immediate: true })

const s = computed(() => data.value?.summary ?? null)
const delta = computed(() => (s.value && s.value.pending_prev !== null ? s.value.pending - s.value.pending_prev : null))
const lastKey = computed(() => {
	const m = data.value?.monthly ?? []
	return m.length ? m[m.length - 1].key : null
})
const dataFromLabel = computed(() => {
	const from = data.value?.data_from
	if (!from) return ""
	const [y, m] = from.split("-").map(Number)
	return new Date(y, m - 1, 1).toLocaleString("en-IN", { month: "long", year: "numeric" })
})

const bars = computed(() =>
	(data.value?.monthly ?? []).map((m) => ({
		key: m.key,
		label: m.label,
		short: m.short,
		lower: m.paid_late,
		upper: m.still_pending,
		extra: [
			{ label: "Fee due", value: num(m.due) },
			{ label: "Pending %", value: m.pending_pct === null ? "–" : `${m.pending_pct}%` },
			{ label: "Owed on 15th", value: rupees(m.balance_on_cutoff) },
		],
	})),
)

// ---------------------------------------------------------------- drill-down

const TITLES: Record<FeeKind, string> = {
	pending: "Fees pending after 15th",
	due: "Fee due",
	on_time: "Paid by the 15th",
	paid_late: "Paid after the 15th",
	still_pending: "Still unpaid",
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
	return [TITLES[q.kind as FeeKind] ?? "Students", who, batch, col ? `${col.month} ${col.year}` : "All judged months"]
		.filter(Boolean)
		.join(" · ")
})

const loadDetail = computed(() => {
	const q = detail.value
	if (!q) return null
	const f = sent.value
	return async (): Promise<DetailResult> => ({ type: "fee", rows: await getFeeDetail(f, q) })
})

// ---------------------------------------------------------------- export

function exportCsv() {
	const d = data.value
	if (!d) return
	const cols = d.columns
	const cell = (v: number | null, key: string) => (cols.find((c) => c.key === key)?.state === "no_data" ? "-" : v)
	const rows: Cell[][] = [
		[d.title],
		[`ACADEMIC YEAR : ${d.academic_year_label}`],
		[summary(props.report)],
		[],
		["S.No.", "STD", "TOTAL", ...cols.map((c) => c.label)],
		...d.rows.map((r) => [r.idx, r.label, r.total, ...cols.map((c) => cell(r.values[c.key], c.key))]),
		["", "TOTAL", d.totals.total, ...cols.map((c) => cell(d.totals.values[c.key], c.key))],
		[],
		["MONTH-WISE FEE COLLECTION AGAINST THE 15TH"],
		["Month", "Fee due", "Paid by 15th", "Pending after 15th", "Pending %", "Owed on 15th", "Paid later", "Still unpaid", "Still unpaid Rs"],
		...d.monthly.map((m) => [m.label, m.due, m.on_time, m.pending, m.pending_pct, m.balance_on_cutoff, m.paid_late, m.still_pending, m.still_pending_amount]),
	]
	const b = d.batch_breakdown
	if (b) {
		rows.push([], [`PENDING AFTER 15TH BY STANDARD x BATCH - ${b.label}`],
			["Standard", ...b.batches.map((x) => `Batch ${x}`), "No batch", "Boys", "Girls", "Total"],
			...b.rows.map((r) => [r.standard, ...b.batches.map((x) => r.values[x]), r.no_batch, r.boys, r.girls, r.total]))
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
	<div v-else class="bbr-content" :class="{ 'is-loading': loading }">
		<ChartSheet :report="report" :data="data" kind="pending" @open="detail = $event" />

		<section v-if="s" class="bbr-tiles" aria-label="Summary">
			<button type="button" class="bbr-tile" @click="detail = { kind: 'pending', month: lastKey }">
				<span class="bbr-tile-label">Pending after 15th · {{ s.month }}</span>
				<span class="bbr-tile-value">{{ num(s.pending) }}</span>
				<span class="bbr-tile-sub">
					<!-- more pending is worse: an increase reads red -->
					<span v-if="delta !== null" class="bbr-delta" :class="{ down: delta > 0, up: delta < 0 }">
						{{ delta > 0 ? "▲" : delta < 0 ? "▼" : "■" }} {{ signed(delta) }} vs {{ s.prev_label }}
					</span>
					<span>of {{ num(s.due) }} students due ({{ s.pending_pct ?? "–" }}%)</span>
				</span>
			</button>
			<div class="bbr-tile static">
				<span class="bbr-tile-label">Owed on the 15th</span>
				<span class="bbr-tile-value">{{ rupees(s.balance_on_cutoff) }}</span>
				<span class="bbr-tile-sub">unpaid fee for {{ s.month }} at the cutoff</span>
			</div>
			<button type="button" class="bbr-tile" @click="detail = { kind: 'paid_late', month: lastKey }">
				<span class="bbr-tile-label">Paid after the 15th</span>
				<span class="bbr-tile-value">{{ num(s.paid_late) }}</span>
				<span class="bbr-tile-sub">late, but settled since</span>
			</button>
			<button type="button" class="bbr-tile" @click="detail = { kind: 'still_pending', month: lastKey }">
				<span class="bbr-tile-label">Still unpaid today</span>
				<span class="bbr-tile-value">{{ num(s.still_pending) }}</span>
				<span class="bbr-tile-sub">{{ rupees(s.still_pending_amount) }} to collect for {{ s.month }}</span>
			</button>
			<div class="bbr-tile static">
				<span class="bbr-tile-label">Yearly-fee students</span>
				<span class="bbr-tile-value">{{ num(data.yearly_students) }}</span>
				<span class="bbr-tile-sub">pay once a year · not counted here</span>
			</div>
		</section>

		<!-- full width: the collection table has nine columns -->
		<div v-if="data.monthly.length" class="bbr-stack">
			<StackedChart
				title="Pending after the 15th"
				:series="['Paid later', 'Still unpaid']"
				:bars="bars"
				total-label="Pending after 15th"
				@open="detail = { kind: 'pending', month: $event }"
			/>
			<FeeMonthTable :monthly="data.monthly" @open="detail = $event" />
		</div>

		<BatchTable
			v-if="data.batch_breakdown && data.batch_breakdown.totals.total"
			:data="data.batch_breakdown"
			:gender="filters.gender"
			kind="pending"
			title="Pending after 15th by standard × batch"
			@open="detail = $event"
		/>

		<p v-if="error" class="bbr-state error">{{ error }}</p>
		<p class="bbr-footnote">
			Generated {{ date(data.generated_on) }} · {{ summary(report) }}.<br />
			<b>How it is counted:</b> a student is <b>pending after 15th</b> for a month when they were enrolled on the 15th and
			that month's fee was not fully paid by the end of the 15th — paid later, or still unpaid. The cutoff is the
			<b>15th of every month for every student</b>. Months marked No Fees, waived, or covered by the starting payment are
			not counted; yearly-fee students are left out. A month is judged once its 15th has passed (blank until then).
			<template v-if="dataFromLabel">
				Payment dates come from Fee Invoices, which start in {{ dataFromLabel }} — earlier months show “–”.
			</template>
			TOTAL = pending cases across the months. Click any number to see the students and what they owed.
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
