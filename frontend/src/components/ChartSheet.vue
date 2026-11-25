<script setup lang="ts">
/** The chart exactly as printed in the "Manager wiro" PDF: S.No | STD | TOTAL | months. */
import type { DetailQuery, StudentCountReport } from "@/api/types"
import { num } from "@/lib/format"
import type { ReportDef } from "@/lib/reports"

defineProps<{ report: ReportDef; data: StudentCountReport }>()
const emit = defineEmits<{ open: [q: DetailQuery] }>()

function open(v: number | null | undefined, q: Omit<DetailQuery, "kind">) {
	if (v) emit("open", { kind: "present", ...q })
}
const cls = (v: number | null | undefined) => ["num", { zero: v === 0, clickable: !!v }]
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
						<th class="col-std">STD</th>
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
							:class="cls(row.values[c.key])"
							@click="open(row.values[c.key], { row: row.key, month: c.key })"
						>
							{{ num(row.values[c.key]) }}
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
							:class="cls(data.totals.values[c.key])"
							@click="open(data.totals.values[c.key], { month: c.key })"
						>
							{{ num(data.totals.values[c.key]) }}
						</td>
					</tr>
				</tfoot>
			</table>
		</div>
		<div v-else class="bbr-state">No rows match these filters.</div>
	</section>
</template>
