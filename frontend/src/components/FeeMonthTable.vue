<script setup lang="ts">
import type { DetailQuery, FeeKind, FeeMonth } from "@/api/types"
import { num, rupees } from "@/lib/format"

defineProps<{ monthly: FeeMonth[] }>()
const emit = defineEmits<{ open: [q: DetailQuery] }>()

function open(v: number, kind: FeeKind, month: string | null) {
	if (v) emit("open", { kind, month })
}
const sum = (rows: FeeMonth[], k: keyof FeeMonth) => rows.reduce((a, r) => a + Number(r[k] || 0), 0)
</script>

<template>
	<section class="bbr-card">
		<div class="bbr-card-head"><h2>Month-wise fee collection against the 15th</h2></div>
		<div class="bbr-table-scroll">
			<table class="bbr-table">
				<thead>
					<tr>
						<th>Month</th>
						<th class="num">Fee due</th>
						<th class="num">Paid by 15th</th>
						<th class="num">Pending after 15th</th>
						<th class="num">%</th>
						<th class="num">Owed on 15th</th>
						<th class="num">Paid later</th>
						<th class="num">Still unpaid</th>
						<th class="num">Still unpaid ₹</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="m in monthly" :key="m.key">
						<td>{{ m.label }}</td>
						<td class="num" :class="{ clickable: m.due }" @click="open(m.due, 'due', m.key)">{{ num(m.due) }}</td>
						<td class="num pos" :class="{ clickable: m.on_time }" @click="open(m.on_time, 'on_time', m.key)">{{ num(m.on_time) }}</td>
						<td class="num neg strong" :class="{ clickable: m.pending }" @click="open(m.pending, 'pending', m.key)">{{ num(m.pending) }}</td>
						<td class="num">{{ m.pending_pct === null ? "–" : `${m.pending_pct}%` }}</td>
						<td class="num">{{ rupees(m.balance_on_cutoff) }}</td>
						<td class="num" :class="{ clickable: m.paid_late }" @click="open(m.paid_late, 'paid_late', m.key)">{{ num(m.paid_late) }}</td>
						<td class="num neg" :class="{ clickable: m.still_pending }" @click="open(m.still_pending, 'still_pending', m.key)">
							{{ num(m.still_pending) }}
						</td>
						<td class="num neg">{{ rupees(m.still_pending_amount) }}</td>
					</tr>
				</tbody>
				<tfoot v-if="monthly.length > 1">
					<tr>
						<td>Period</td>
						<td class="num">{{ num(sum(monthly, "due")) }}</td>
						<td class="num pos">{{ num(sum(monthly, "on_time")) }}</td>
						<td class="num neg clickable" @click="open(sum(monthly, 'pending'), 'pending', null)">{{ num(sum(monthly, "pending")) }}</td>
						<td class="num">
							{{ sum(monthly, "due") ? `${Math.round((1000 * sum(monthly, "pending")) / sum(monthly, "due")) / 10}%` : "–" }}
						</td>
						<td class="num">{{ rupees(sum(monthly, "balance_on_cutoff")) }}</td>
						<td class="num">{{ num(sum(monthly, "paid_late")) }}</td>
						<td class="num neg clickable" @click="open(sum(monthly, 'still_pending'), 'still_pending', null)">
							{{ num(sum(monthly, "still_pending")) }}
						</td>
						<td class="num neg">{{ rupees(sum(monthly, "still_pending_amount")) }}</td>
					</tr>
				</tfoot>
			</table>
		</div>
		<p class="bbr-card-note">
			Fee due = enrolled on the 15th and billed for that month. Paid by 15th + Pending after 15th = Fee due;
			Pending = Paid later + Still unpaid.
		</p>
	</section>
</template>
