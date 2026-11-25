<script setup lang="ts">
import { computed } from "vue"

import type { BatchBreakdown, DetailQuery } from "@/api/types"
import { num } from "@/lib/format"

const props = defineProps<{ data: BatchBreakdown; gender: string }>()
const emit = defineEmits<{ open: [q: DetailQuery] }>()

const showNone = computed(() => props.data.totals.no_batch > 0)

function open(v: number, standard: string | null, batch: string | null) {
	if (!v) return
	emit("open", {
		kind: "closing",
		month: props.data.month_key,
		row: standard ? `${standard}|${props.gender}` : null,
		batch,
	})
}
</script>

<template>
	<section class="bbr-card">
		<div class="bbr-card-head"><h2>Standard × batch strength · {{ data.label }}</h2></div>
		<div class="bbr-table-scroll">
			<table class="bbr-table">
				<thead>
					<tr>
						<th>Standard</th>
						<th v-for="b in data.batches" :key="b" class="num">Batch {{ b }}</th>
						<th v-if="showNone" class="num">No batch</th>
						<th class="num">Boys</th>
						<th class="num">Girls</th>
						<th class="num">Total</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="r in data.rows" :key="r.standard">
						<td>{{ r.standard }}</td>
						<td v-for="b in data.batches" :key="b" class="num" :class="{ clickable: r.values[b] }" @click="open(r.values[b], r.standard, b)">
							{{ num(r.values[b]) }}
						</td>
						<td v-if="showNone" class="num" :class="{ clickable: r.no_batch }" @click="open(r.no_batch, r.standard, '__none__')">
							{{ num(r.no_batch) }}
						</td>
						<td class="num">{{ num(r.boys) }}</td>
						<td class="num">{{ num(r.girls) }}</td>
						<td class="num strong" :class="{ clickable: r.total }" @click="open(r.total, r.standard, null)">{{ num(r.total) }}</td>
					</tr>
				</tbody>
				<tfoot>
					<tr>
						<td>TOTAL</td>
						<td v-for="b in data.batches" :key="b" class="num" :class="{ clickable: data.totals.values[b] }" @click="open(data.totals.values[b], null, b)">
							{{ num(data.totals.values[b]) }}
						</td>
						<td v-if="showNone" class="num" :class="{ clickable: data.totals.no_batch }" @click="open(data.totals.no_batch, null, '__none__')">
							{{ num(data.totals.no_batch) }}
						</td>
						<td class="num">{{ num(data.totals.boys) }}</td>
						<td class="num">{{ num(data.totals.girls) }}</td>
						<td class="num strong" :class="{ clickable: data.totals.total }" @click="open(data.totals.total, null, null)">
							{{ num(data.totals.total) }}
						</td>
					</tr>
				</tfoot>
			</table>
		</div>
	</section>
</template>
