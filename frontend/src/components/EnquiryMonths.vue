<script setup lang="ts">
/** Enquiries and joiners month by month, plus enquiries by standard. Numbers open the records. */
import { computed } from "vue"

import type { AdminDetailQuery, AdminEnquiryReport } from "@/api/types"
import BarList, { type BarRow } from "@/components/BarList.vue"
import { num } from "@/lib/format"

const props = defineProps<{ data: AdminEnquiryReport }>()
const emit = defineEmits<{ open: [q: AdminDetailQuery] }>()

const rows = computed(() => props.data.sections.flatMap((s) => s.rows))

const months = computed(() =>
	props.data.columns
		.filter((c) => rows.value.some((r) => r.values[c.key]))
		.map((c) => {
			const e = rows.value.reduce((a, r) => a + (r.values[c.key]?.e ?? 0), 0)
			const j = rows.value.reduce((a, r) => a + (r.values[c.key]?.j ?? 0), 0)
			return { key: c.key, label: `${c.month} ${c.year}`, e, j, rate: e ? Math.round((100 * j) / e) : null }
		}),
)
const maxE = computed(() => Math.max(1, ...months.value.map((m) => m.e)))

const byStandard = computed<BarRow[]>(() => {
	const totals = new Map<string, number>()
	for (const r of rows.value) totals.set(r.standard, (totals.get(r.standard) ?? 0) + r.total.e)
	return [...totals.entries()].map(([label, count]) => ({ label, count, key: label })).sort((a, b) => b.count - a.count)
})

const open = (kind: "enquiry" | "joined", month: string | null, label: string, standard?: string) =>
	emit("open", { kind, month, standard: standard ?? null, label })
</script>

<template>
	<div v-if="months.length" class="bbr-grid-2">
		<section class="bbr-card">
			<div class="bbr-card-head"><h2>Month by month</h2></div>
			<div class="bbr-table-scroll">
				<table class="bbr-table">
					<thead>
						<tr><th>Month</th><th class="num">Enquiries</th><th></th><th class="num">Joined</th><th class="num">Joined per 100</th></tr>
					</thead>
					<tbody>
						<tr v-for="m in months" :key="m.key">
							<td>{{ m.label }}</td>
							<td class="num" :class="{ clickable: m.e }" @click="m.e && open('enquiry', m.key, `Enquiries · ${m.label}`)">{{ num(m.e) }}</td>
							<td class="bbr-inline-bar"><span class="bbr-bar" :style="{ width: `${(100 * m.e) / maxE}%` }"></span></td>
							<td class="num" :class="{ clickable: m.j }" @click="m.j && open('joined', m.key, `Joined · ${m.label}`)">{{ num(m.j) }}</td>
							<td class="num">{{ m.rate === null ? "–" : `${m.rate}%` }}</td>
						</tr>
					</tbody>
				</table>
			</div>
		</section>
		<BarList
			title="Enquiries by standard"
			:rows="byStandard"
			@open="(std) => open('enquiry', null, `Enquiries · ${std}`, std)"
		/>
	</div>
</template>
