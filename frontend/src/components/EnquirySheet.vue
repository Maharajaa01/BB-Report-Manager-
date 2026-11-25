<script setup lang="ts">
/**
 * One page of the Admin "Enquiry & Joiners Count List" register: black-and-white grid
 * inside a coloured frame (green 6th-9th, blue Boys, magenta Girls), each month split
 * into E (enquiries) and J (joined).
 */
import { computed } from "vue"

import type { AdminDetailQuery, AdminEnquiryReport, AdminEnquirySection, EJ, MonthColumn } from "@/api/types"
import { num } from "@/lib/format"

const props = defineProps<{ data: AdminEnquiryReport; section: AdminEnquirySection; batch: string }>()
const emit = defineEmits<{ open: [q: AdminDetailQuery] }>()

const FRAME = { junior: "#00a651", senior_boys: "#2e3192", senior_girls: "#ec008c" }
const BADGE = { junior: "BOYS & GIRLS", senior_boys: "BOYS", senior_girls: "GIRLS" }
const STD_LABEL = { junior: "6th To 9th - STD", senior_boys: "10th To 12th - STD", senior_girls: "10th To 12th - STD" }

const frame = computed(() => FRAME[props.section.key])
const colOf = (key: string | null) => props.data.columns.find((c) => c.key === key)
const monthName = (c: MonthColumn | undefined) => (c ? `${c.month} ${c.year}` : "Whole period")

function open(cell: EJ | null, which: "e" | "j", label: string, month: string | null, row: string | null) {
	if (!cell || !cell[which]) return
	emit("open", {
		kind: which === "e" ? "enquiry" : "joined",
		row,
		month,
		section: row ? null : props.section.key,
		label: [which === "e" ? "Enquiries" : "Joined", label, monthName(colOf(month))].join(" · "),
	})
}
const cls = (cell: EJ | null, which: "e" | "j") => ["num", { zero: cell?.[which] === 0, clickable: !!cell?.[which] }]
const val = (cell: EJ | null, which: "e" | "j") => (cell ? num(cell[which]) : "")
</script>

<template>
	<section class="bbr-enq-sheet" :style="{ '--frame': frame }">
		<header class="bbr-enq-head">
			<div class="bbr-enq-badge">{{ BADGE[section.key] }}</div>
			<div class="bbr-enq-titles">
				<p class="bbr-enq-company">{{ data.subtitle }}</p>
				<h1 class="bbr-enq-title">{{ data.title }}</h1>
				<p class="bbr-enq-std">{{ STD_LABEL[section.key] }}</p>
			</div>
			<div class="bbr-enq-box">
				<div class="bbr-enq-year">{{ data.academic_year_label }}</div>
				<div>Batch : {{ batch || "All" }}</div>
				<div class="bbr-enq-legend"><i></i>E - ENQUIRY</div>
				<div class="bbr-enq-legend"><i></i>J - JOINED</div>
			</div>
		</header>
		<div class="bbr-sheet-scroll">
			<table class="bbr-enq-table">
				<thead>
					<tr>
						<th rowspan="2" class="col-sno">S.No</th>
						<th rowspan="2" class="col-std">STD</th>
						<th v-for="c in data.columns" :key="c.key" colspan="2" :title="monthName(c)">{{ c.label }}</th>
						<th colspan="2" class="col-total">TOTAL</th>
					</tr>
					<tr class="bbr-enq-ej">
						<template v-for="c in data.columns" :key="c.key"><th>E</th><th>J</th></template>
						<th class="col-total">E</th><th class="col-total">J</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="row in section.rows" :key="row.key">
						<td class="col-sno">{{ row.idx }}.</td>
						<td class="col-std">{{ row.label }}</td>
						<template v-for="c in data.columns" :key="c.key">
							<td :class="cls(row.values[c.key], 'e')" @click="open(row.values[c.key], 'e', row.label, c.key, row.key)">
								{{ val(row.values[c.key], "e") }}
							</td>
							<td class="j" :class="cls(row.values[c.key], 'j')" @click="open(row.values[c.key], 'j', row.label, c.key, row.key)">
								{{ val(row.values[c.key], "j") }}
							</td>
						</template>
						<td class="col-total" :class="cls(row.total, 'e')" @click="open(row.total, 'e', row.label, null, row.key)">{{ num(row.total.e) }}</td>
						<td class="col-total j" :class="cls(row.total, 'j')" @click="open(row.total, 'j', row.label, null, row.key)">{{ num(row.total.j) }}</td>
					</tr>
				</tbody>
				<tfoot>
					<tr>
						<td class="col-sno"></td>
						<td class="col-std">TOTAL</td>
						<template v-for="c in data.columns" :key="c.key">
							<td :class="cls(section.totals.values[c.key], 'e')" @click="open(section.totals.values[c.key], 'e', section.label, c.key, null)">
								{{ val(section.totals.values[c.key], "e") }}
							</td>
							<td class="j" :class="cls(section.totals.values[c.key], 'j')" @click="open(section.totals.values[c.key], 'j', section.label, c.key, null)">
								{{ val(section.totals.values[c.key], "j") }}
							</td>
						</template>
						<td class="col-total" :class="cls(section.totals.total, 'e')" @click="open(section.totals.total, 'e', section.label, null, null)">
							{{ num(section.totals.total.e) }}
						</td>
						<td class="col-total j" :class="cls(section.totals.total, 'j')" @click="open(section.totals.total, 'j', section.label, null, null)">
							{{ num(section.totals.total.j) }}
						</td>
					</tr>
				</tfoot>
			</table>
		</div>
	</section>
</template>
