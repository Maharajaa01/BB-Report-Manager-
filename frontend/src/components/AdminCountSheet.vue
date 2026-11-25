<script setup lang="ts">
/**
 * One page of the Admin "Students Count List" register (Total / Actual / Discontinued):
 * S.No | STD | months | Highest Count, with the TOTAL row and the Highest column shaded.
 */
import type { AdminCountReport, AdminCountSection, AdminDetailQuery, AdminKind, MonthColumn } from "@/api/types"
import { num } from "@/lib/format"
import type { ReportDef } from "@/lib/reports"

const props = defineProps<{ report: ReportDef; data: AdminCountReport; section: AdminCountSection }>()
const emit = defineEmits<{ open: [q: AdminDetailQuery] }>()

const kind = props.data.report.replace("admin_", "") as AdminKind
const colOf = (key: string | null) => props.data.columns.find((c) => c.key === key)
const monthName = (c: MonthColumn | undefined) => (c ? `${c.month} ${c.year}` : "")

function open(v: number | null, label: string, month: string | null, row: string | null) {
	if (!v) return
	emit("open", { kind, row, month, section: row ? null : props.section.key, label: [label, monthName(colOf(month))].filter(Boolean).join(" · ") })
}
const cls = (v: number | null) => ["num", { zero: v === 0, clickable: !!v }]
const peakTitle = (month: string | null) => (month ? `Peak: ${monthName(colOf(month))}` : "No students in any month")
</script>

<template>
	<section class="bbr-sheet bbr-admin-sheet" :style="{ '--chart-bg': report.bg }">
		<p class="bbr-sheet-year">ACADEMIC YEAR : {{ data.academic_year_label }}</p>
		<h1 class="bbr-sheet-title">{{ data.title }}</h1>
		<p class="bbr-admin-subtitle">{{ data.subtitle }}</p>
		<div class="bbr-sheet-scroll">
			<table class="bbr-chart">
				<thead>
					<tr class="bbr-admin-banner">
						<th colspan="2"></th>
						<th :colspan="data.columns.length + 1">{{ section.label }}</th>
					</tr>
					<tr>
						<th class="col-sno">S.No.</th>
						<th class="col-std">STD</th>
						<th v-for="c in data.columns" :key="c.key" :class="`m-${c.label}`" :title="monthName(c)">{{ c.label }}</th>
						<th class="col-peak">Highest<br />Count</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="row in section.rows" :key="row.key">
						<td class="col-sno">{{ row.idx }}</td>
						<td class="col-std">{{ row.label }}</td>
						<td
							v-for="c in data.columns"
							:key="c.key"
							:class="cls(row.values[c.key])"
							@click="open(row.values[c.key], row.label, c.key, row.key)"
						>
							{{ num(row.values[c.key]) }}
						</td>
						<td
							class="col-peak"
							:class="cls(row.highest)"
							:title="peakTitle(row.highest_month)"
							@click="open(row.highest, row.label, row.highest_month, row.key)"
						>
							{{ num(row.highest) }}
						</td>
					</tr>
				</tbody>
				<tfoot>
					<tr class="bbr-admin-total">
						<td class="col-sno"></td>
						<td class="col-std">TOTAL</td>
						<td
							v-for="c in data.columns"
							:key="c.key"
							:class="cls(section.totals.values[c.key])"
							@click="open(section.totals.values[c.key], section.label, c.key, null)"
						>
							{{ num(section.totals.values[c.key]) }}
						</td>
						<td
							class="col-peak"
							:class="cls(section.totals.highest)"
							:title="peakTitle(section.totals.highest_month)"
							@click="open(section.totals.highest, section.label, section.totals.highest_month, null)"
						>
							{{ num(section.totals.highest) }}
						</td>
					</tr>
				</tfoot>
			</table>
		</div>
	</section>
</template>
