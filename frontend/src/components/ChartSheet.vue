<script setup lang="ts">
/** The chart exactly as printed in the "Manager wiro" PDF: S.No | STD | TOTAL | months. */
import type { DetailKind, DetailQuery, FeeKind, MonthColumn, SheetRow } from "@/api/types"
import { num } from "@/lib/format"
import type { ReportDef } from "@/lib/reports"

/** Any "STD & MONTH WISE" grid: Report 1 (students), Report 2 (fees pending) ... */
interface SheetData {
	title: string
	academic_year_label: string
	columns: (MonthColumn & { state?: "ok" | "future" | "no_data" })[]
	rows: SheetRow[]
	/** First column heading: STD on student sheets, the row kind on staff sheets. */
	row_head?: string
	totals: { values: Record<string, number | null>; total: number }
}

const props = withDefaults(defineProps<{ report: ReportDef; data: SheetData; kind?: DetailKind | FeeKind }>(), {
	kind: "present",
})
const emit = defineEmits<{ open: [q: DetailQuery] }>()

function open(v: number | null | undefined, q: Omit<DetailQuery, "kind">) {
	if (v) emit("open", { kind: props.kind, ...q })
}
const cls = (v: number | null | undefined) => ["num", { zero: v === 0, clickable: !!v }]
const noData = (key: string) => props.data.columns.find((c) => c.key === key)?.state === "no_data"
const cell = (v: number | null | undefined, key: string) => (noData(key) ? "–" : num(v))
/** Work list sheet: "Daily 2 · Weekly 1" under each month's number. */
const splitTitle = (row: SheetRow, key: string) => {
	const s = row.split?.[key]
	return s ? Object.entries(s).map(([k, n]) => `${k} works: ${n}`).join("\n") : undefined
}
</script>

<template>
	<section class="bbr-sheet" :class="{ 'dark-bg': report.dark }" :style="{ '--chart-bg': report.bg }">
		<p class="bbr-sheet-year">ACADEMIC YEAR : {{ data.academic_year_label }}</p>
		<h1 class="bbr-sheet-title">{{ data.title || report.title }}</h1>
		<div v-if="data.rows.length" class="bbr-sheet-scroll">
			<table class="bbr-chart">
				<thead>
					<tr>
						<th class="col-sno">S.No.</th>
						<th class="col-std">{{ data.row_head || "STD" }}</th>
						<th class="col-total">TOTAL</th>
						<th v-for="c in data.columns" :key="c.key" :class="`m-${c.label}`" :title="`${c.month} ${c.year}`">
							{{ c.label }}
						</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="row in data.rows" :key="row.key">
						<td class="col-sno">{{ row.idx }}</td>
						<td class="col-std">{{ row.label }}</td>
						<td :class="cls(row.total)" @click="open(row.total, { row: row.key })">{{ num(row.total) }}</td>
						<td
							v-for="c in data.columns"
							:key="c.key"
							:class="[cls(row.values[c.key]), { nodata: noData(c.key) }]"
							:title="noData(c.key) ? 'No payment dates on record for this month' : splitTitle(row, c.key)"
							@click="open(row.values[c.key], { row: row.key, month: c.key })"
						>
							{{ cell(row.values[c.key], c.key) }}
						</td>
					</tr>
				</tbody>
				<tfoot>
					<tr>
						<td class="col-sno"></td>
						<td class="col-std">TOTAL</td>
						<td :class="cls(data.totals.total)" @click="open(data.totals.total, {})">{{ num(data.totals.total) }}</td>
						<td
							v-for="c in data.columns"
							:key="c.key"
							:class="[cls(data.totals.values[c.key]), { nodata: noData(c.key) }]"
							@click="open(data.totals.values[c.key], { month: c.key })"
						>
							{{ cell(data.totals.values[c.key], c.key) }}
						</td>
					</tr>
				</tfoot>
			</table>
		</div>
		<div v-else class="bbr-state">No rows match these filters.</div>
	</section>
</template>
