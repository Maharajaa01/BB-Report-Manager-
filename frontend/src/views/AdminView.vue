<script setup lang="ts">
/** The Admin registers: Enquiry & Joiners, Total / Actual / Discontinued Students Count. */
import { computed, ref, watch } from "vue"

import { getAdminDetail, getReport } from "@/api/reports"
import type {
	AdminCountReport,
	AdminDetailQuery,
	AdminEnquiryReport,
	AdminReport,
	CountSectionKey,
} from "@/api/types"
import AdminCountSheet from "@/components/AdminCountSheet.vue"
import AdminInsights from "@/components/AdminInsights.vue"
import DetailDialog from "@/components/DetailDialog.vue"
import EnquiryMonths from "@/components/EnquiryMonths.vue"
import EnquirySheet from "@/components/EnquirySheet.vue"
import EnquirySummary from "@/components/EnquirySummary.vue"
import { type Cell, downloadCsv, slug } from "@/lib/csv"
import { date } from "@/lib/format"
import type { ReportDef } from "@/lib/reports"
import { options, useFilters } from "@/lib/store"

const props = defineProps<{ report: ReportDef }>()

const { filters, apiFilters, summary } = useFilters()
const data = ref<AdminReport | null>(null)
const error = ref("")
const loading = ref(false)
const tab = ref<CountSectionKey | "all">("all")
let controller: AbortController | null = null

const sent = computed(() => apiFilters(props.report))

async function load() {
	controller?.abort()
	controller = new AbortController()
	loading.value = true
	error.value = ""
	try {
		data.value = await getReport<AdminReport>(props.report.key, sent.value, controller.signal)
		if (tab.value !== "all" && !data.value.sections.some((s) => s.key === tab.value)) tab.value = "all"
	} catch (e) {
		if ((e as Error).name === "AbortError") return
		data.value = null
		error.value = (e as Error).message
	} finally {
		loading.value = false
	}
}

watch(() => JSON.stringify(sent.value), load, { immediate: true })

const enquiry = computed(() => (data.value?.report === "admin_enquiry" ? (data.value as AdminEnquiryReport) : null))
const counts = computed(() => (data.value && data.value.report !== "admin_enquiry" ? (data.value as AdminCountReport) : null))
const visible = (key: CountSectionKey) => tab.value === "all" || tab.value === key

// ---------------------------------------------------------------- drill-down

const detail = ref<AdminDetailQuery | null>(null)
const loadDetail = computed(() => {
	const q = detail.value
	if (!q) return null
	const filters = sent.value
	return () => getAdminDetail(props.report.key, filters, q)
})

// ---------------------------------------------------------------- export

function exportCsv() {
	const d = data.value
	if (!d) return
	const cols = d.columns
	const rows: Cell[][] = [[d.title], [`ACADEMIC YEAR : ${d.academic_year_label}`], [summary(props.report)]]
	if (enquiry.value) {
		for (const s of enquiry.value.sections) {
			rows.push([], [s.label], ["S.No", "STD", ...cols.flatMap((c) => [`${c.label} E`, `${c.label} J`]), "TOTAL E", "TOTAL J"])
			for (const r of s.rows) {
				rows.push([r.idx, r.label, ...cols.flatMap((c) => [r.values[c.key]?.e ?? "", r.values[c.key]?.j ?? ""]), r.total.e, r.total.j])
			}
			rows.push(["", "TOTAL", ...cols.flatMap((c) => [s.totals.values[c.key]?.e ?? "", s.totals.values[c.key]?.j ?? ""]), s.totals.total.e, s.totals.total.j])
		}
	} else if (counts.value) {
		const peak = (m: string | null) => cols.find((c) => c.key === m)?.label ?? ""
		for (const s of counts.value.sections) {
			rows.push([], [s.label], ["S.No.", "STD", ...cols.map((c) => c.label), "Highest Count", "Highest in"])
			for (const r of s.rows) rows.push([r.idx, r.label, ...cols.map((c) => r.values[c.key]), r.highest, peak(r.highest_month)])
			rows.push(["", "TOTAL", ...cols.map((c) => s.totals.values[c.key]), s.totals.highest, peak(s.totals.highest_month)])
		}
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
		<nav v-if="data.sections.length > 1" class="bbr-tabs" aria-label="Sections">
			<button type="button" :class="{ active: tab === 'all' }" @click="tab = 'all'">All sections</button>
			<button v-for="s in data.sections" :key="s.key" type="button" :class="{ active: tab === s.key }" @click="tab = s.key">
				{{ s.label }}
			</button>
		</nav>

		<template v-if="enquiry">
			<template v-for="s in enquiry.sections" :key="s.key">
				<EnquirySheet v-if="visible(s.key)" :data="enquiry" :section="s" :batch="filters.batch" @open="detail = $event" />
			</template>
			<div class="bbr-summary-block">
				<EnquirySummary :summary="enquiry.summary" />
			</div>
			<EnquiryMonths :data="enquiry" @open="detail = $event" />
		</template>
		<template v-else-if="counts">
			<template v-for="s in counts.sections" :key="s.key">
				<AdminCountSheet v-if="visible(s.key)" :report="report" :data="counts" :section="s" @open="detail = $event" />
			</template>
			<AdminInsights :data="counts" :gender="filters.gender" @open="detail = $event" />
		</template>

		<div v-if="!data.sections.length" class="bbr-state">No rows match these filters.</div>
		<p v-if="error" class="bbr-state error">{{ error }}</p>

		<p class="bbr-footnote">
			Generated {{ date(data.generated_on) }} · {{ summary(report) }}.<br />
			<template v-if="enquiry">
				<b>E</b> = enquiries entered that month (Student Enquiry Form date). <b>J</b> = students admitted that month.
				Joiners are counted from admissions, so a student who joined without an enquiry still counts. 11th/12th rows
				follow the subject group on the enquiry or student; “Group not set” collects enquiries without one. The Batch
				filter applies to joined students only (enquiries have no batch).
			</template>
			<template v-else-if="data.report === 'admin_total'">
				<b>TOTAL</b> = every student admitted on or before the month end, including students who later left.
				<b>Highest Count</b> = the row's peak month (hover to see which).
			</template>
			<template v-else-if="data.report === 'admin_actual'">
				<b>ACTUAL</b> = students enrolled on any day of the month (the same rule as the Manager chart): admitted by the
				month end and not discontinued before it started. <b>Highest Count</b> = the row's peak month.
			</template>
			<template v-else>
				<b>DISCONTINUED</b> = students who left during the month (a student who left and rejoined counts in the month
				they left). <b>Highest Count</b> = the row's worst month.
			</template>
			Months not started yet are blank. Click any number to see the {{ enquiry ? "enquiries or students" : "students" }}.
		</p>
	</div>

	<DetailDialog
		:load="loadDetail"
		:title="detail?.label ?? ''"
		:filter-summary="summary(report)"
		:tuition-url="options.data?.tuition_site_url ?? ''"
		@close="detail = null"
	/>
</template>
