<script setup lang="ts">
/**
 * Manager Charts 8 and 9: CRITICAL PROBLEMS - MONTH WISE (a column of problems per
 * month) and the ASST. MANAGER & MANAGER - SINGLE SHEET PROBLEMS list for one month.
 */
import { computed, ref, watch } from "vue"

import { getManagerDetail, getReport } from "@/api/reports"
import type { CriticalProblemsReport, DetailResult, ManagerQuery, ProblemRow, SingleSheetReport } from "@/api/types"
import DetailDialog from "@/components/DetailDialog.vue"
import ManagerInsights from "@/components/ManagerInsights.vue"
import { dateTime } from "@/lib/cells"
import { type Cell, downloadCsv, slug } from "@/lib/csv"
import { date } from "@/lib/format"
import type { ReportDef } from "@/lib/reports"
import { options, useFilters } from "@/lib/store"

const props = defineProps<{ report: ReportDef }>()

const { filters, apiFilters, summary } = useFilters()
const data = ref<CriticalProblemsReport | SingleSheetReport | null>(null)
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
		data.value = await getReport<CriticalProblemsReport | SingleSheetReport>(props.report.key, sent.value, controller.signal)
	} catch (e) {
		if ((e as Error).name === "AbortError") return
		data.value = null
		error.value = (e as Error).message
	} finally {
		loading.value = false
	}
}

watch(() => JSON.stringify(sent.value), load, { immediate: true })

const critical = computed(() => (data.value?.report === "critical_problems" ? data.value : null))
const single = computed(() => (data.value?.report === "single_sheet_problems" ? data.value : null))
const solvedCount = (rows: ProblemRow[]) => rows.filter((r) => r.solved).length

// ---------------------------------------------------------------- drill-down

const detail = ref<{ q: ManagerQuery; title: string } | null>(null)
const openInsight = (q: ManagerQuery, label: string) => (detail.value = { q, title: `${props.report.nav} · ${label}` })
const openMonth = (key: string, label: string) => (detail.value = { q: { kind: "problem", month: key }, title: `${props.report.nav} · ${label}` })

const loadDetail = computed(() => {
	const d = detail.value
	if (!d) return null
	const f = sent.value
	return (): Promise<DetailResult> => getManagerDetail(props.report.key, f, d.q)
})

// ---------------------------------------------------------------- export

const line = (p: ProblemRow, i: number): Cell[] => [i + 1, date(p.date), p.title, p.who, p.kind, p.status, p.solved ? "Yes" : "No", dateTime(p.solved_at), p.assigned]
const HEAD = ["S.No", "Date", "Problem", "Posting Name", "Type", "Status", "Problem Solved", "Solved on", "Handled by"]

function exportCsv() {
	const d = data.value
	if (!d) return
	const rows: Cell[][] = [[d.title], [`ACADEMIC YEAR : ${d.academic_year_label}`], [summary(props.report)]]
	if (single.value) {
		rows.push([`Month : ${single.value.period}`], [], HEAD, ...single.value.rows.map(line))
	} else if (critical.value) {
		for (const c of critical.value.columns) {
			const items = critical.value.items[c.key] ?? []
			if (!items.length) continue
			rows.push([], [`${c.month} ${c.year} · Total ${items.length}`], HEAD, ...items.map(line))
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
		<!-- CRITICAL PROBLEMS: one column per month, like the paper sheet -->
		<section v-if="critical" class="bbr-sheet dark-bg" :style="{ '--chart-bg': report.bg }">
			<p class="bbr-sheet-year">ACADEMIC YEAR : {{ critical.academic_year_label }}</p>
			<h1 class="bbr-sheet-title">{{ critical.title }}</h1>
			<div class="bbr-sheet-scroll">
				<div class="bbr-problem-months">
					<div v-for="c in critical.columns" :key="c.key" class="bbr-problem-month" :class="{ future: critical.future.includes(c.key), has: !!critical.items[c.key]?.length }">
						<h3 :class="`m-${c.label}`">{{ c.label }}</h3>
						<ol>
							<li v-for="p in critical.items[c.key]" :key="p.link" :class="{ open: !p.solved }">
								<a :href="p.link" target="_blank" rel="noopener">{{ p.title }}</a>
								<small>{{ date(p.date).slice(0, 5) }} · {{ p.who }}</small>
								<small class="bbr-problem-state">{{ p.solved ? "✓ Solved" : `● ${p.status}` }}</small>
							</li>
						</ol>
						<button
							v-if="critical.items[c.key]?.length"
							type="button"
							class="bbr-problem-total"
							@click="openMonth(c.key, `${c.month} ${c.year}`)"
						>
							Total {{ critical.items[c.key].length }} · {{ solvedCount(critical.items[c.key]) }} solved
						</button>
						<div v-else class="bbr-problem-total empty">{{ critical.future.includes(c.key) ? "" : "0" }}</div>
					</div>
				</div>
			</div>
		</section>

		<!-- SINGLE SHEET PROBLEMS: the month's numbered list -->
		<section v-else-if="single" class="bbr-sheet dark-bg bbr-single-sheet" :style="{ '--chart-bg': report.bg }">
			<p class="bbr-sheet-year">Month : {{ single.period }}</p>
			<h1 class="bbr-sheet-title">Asst. Manager &amp; Manager - Single Sheet Problems</h1>
			<div class="bbr-sheet-scroll">
				<table class="bbr-chart bbr-single">
					<thead>
						<tr><th class="col-sno">S.No</th><th>Date</th><th>Problem</th><th>Posting Name</th><th>Problem Solved</th></tr>
					</thead>
					<tbody>
						<tr v-for="(p, i) in single.rows" :key="p.link" :class="{ open: !p.solved, overdue: p.overdue }">
							<td class="col-sno">{{ i + 1 }}</td>
							<td class="nowrap">{{ date(p.date) }}</td>
							<td class="problem">
								<a :href="p.link" target="_blank" rel="noopener">{{ p.title }}</a>
								<small>{{ p.kind }}{{ p.priority === "Urgent" ? " · Urgent" : "" }}{{ p.assigned ? ` · handled by ${p.assigned}` : "" }}</small>
							</td>
							<td>{{ p.who }}<small v-if="p.role">{{ p.role }}</small></td>
							<td class="solved">
								<span v-if="p.solved" class="bbr-check yes">✓</span>
								<span v-else class="bbr-check no">{{ p.status }}</span>
								<small v-if="p.solved_at">{{ dateTime(p.solved_at) }}</small>
							</td>
						</tr>
						<tr v-if="!single.rows.length"><td colspan="5" class="bbr-empty">No problems raised this month.</td></tr>
					</tbody>
				</table>
			</div>
		</section>

		<ManagerInsights :data="data.insights" kind="problem" link-base="" @open="openInsight" />

		<p v-if="error" class="bbr-state error">{{ error }}</p>
		<p class="bbr-footnote">
			Generated {{ date(data.generated_on) }} · {{ summary(report) }}.<br />
			<template v-if="critical">
				A <b>critical problem</b> is a Helpdesk Issue raised as <b>Urgent</b>, or a staff mistake recorded under the Critical
				category, listed under the month it arose.
			</template>
			<template v-else>
				Every Helpdesk Issue (complaints and struggles) raised in the month. <b>Problem Solved</b> = the issue is Resolved;
				anything else is still open. <template v-if="!filters.month">No month picked, so this is the current month.</template>
			</template>
			Issues marked “MD Only” are never shown. Click a problem to open it, or a number to list the problems behind it.
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
