<script setup lang="ts">
import { computed } from "vue"

import type { DetailKind, DetailQuery, MovementRow } from "@/api/types"
import { num, signed } from "@/lib/format"

const props = defineProps<{ movement: MovementRow[] }>()
const emit = defineEmits<{ open: [q: DetailQuery] }>()

const totals = computed(() => {
	const sum = (k: "joined" | "rejoined" | "discontinued") => props.movement.reduce((a, m) => a + m[k], 0)
	const first = props.movement[0]
	const last = props.movement[props.movement.length - 1]
	return {
		opening: first.opening,
		joined: sum("joined"),
		rejoined: sum("rejoined"),
		discontinued: sum("discontinued"),
		closing: last.closing,
		net: last.closing - first.opening,
	}
})

function open(v: number, kind: DetailKind, month: string | null) {
	if (v) emit("open", { kind, month })
}
</script>

<template>
	<section class="bbr-card">
		<div class="bbr-card-head"><h2>Month-wise student movement</h2></div>
		<div class="bbr-table-scroll">
			<table class="bbr-table">
				<thead>
					<tr>
						<th>Month</th>
						<th class="num">Opening</th>
						<th class="num">+ New</th>
						<th class="num">+ Rejoined</th>
						<th class="num">− Left</th>
						<th class="num">Closing</th>
						<th class="num">Net</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="m in movement" :key="m.key">
						<td>{{ m.label }}{{ m.running ? " *" : "" }}</td>
						<td class="num" :class="{ clickable: m.opening }" @click="open(m.opening, 'opening', m.key)">{{ num(m.opening) }}</td>
						<td class="num pos" :class="{ clickable: m.joined }" @click="open(m.joined, 'joined', m.key)">{{ num(m.joined) }}</td>
						<td class="num pos" :class="{ clickable: m.rejoined }" @click="open(m.rejoined, 'rejoined', m.key)">{{ num(m.rejoined) }}</td>
						<td class="num neg" :class="{ clickable: m.discontinued }" @click="open(m.discontinued, 'discontinued', m.key)">
							{{ num(m.discontinued) }}
						</td>
						<td class="num strong" :class="{ clickable: m.closing }" @click="open(m.closing, 'closing', m.key)">{{ num(m.closing) }}</td>
						<td class="num" :class="{ pos: m.net > 0, neg: m.net < 0 }">{{ signed(m.net) }}</td>
					</tr>
				</tbody>
				<tfoot>
					<tr>
						<td>Period</td>
						<td class="num">{{ num(totals.opening) }}</td>
						<td class="num pos" :class="{ clickable: totals.joined }" @click="open(totals.joined, 'joined', null)">{{ num(totals.joined) }}</td>
						<td class="num pos" :class="{ clickable: totals.rejoined }" @click="open(totals.rejoined, 'rejoined', null)">{{ num(totals.rejoined) }}</td>
						<td class="num neg" :class="{ clickable: totals.discontinued }" @click="open(totals.discontinued, 'discontinued', null)">
							{{ num(totals.discontinued) }}
						</td>
						<td class="num strong">{{ num(totals.closing) }}</td>
						<td class="num">{{ signed(totals.net) }}</td>
					</tr>
				</tfoot>
			</table>
		</div>
		<p class="bbr-card-note">Opening + New + Rejoined − Left = Closing.</p>
	</section>
</template>
