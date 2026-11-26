<script setup lang="ts">
/**
 * The detail under a Manager sheet, rendered from the server's generic insights
 * block: tiles, a month chart, ranked bar lists and tables. Every clickable piece
 * emits the drill-down query the report's detail endpoint understands.
 */
import { computed } from "vue"

import type { ManagerInsights, ManagerQuery } from "@/api/types"
import BarList from "@/components/BarList.vue"
import DataTable from "@/components/DataTable.vue"
import StackedChart, { type StackBar } from "@/components/StackedChart.vue"
import { tileValue } from "@/lib/cells"
import { signed } from "@/lib/format"

const props = defineProps<{
	data: ManagerInsights
	/** Detail kind a clicked month or bar opens (e.g. "complaint", "staff"). */
	kind: string
	linkBase: string
}>()
const emit = defineEmits<{ open: [q: ManagerQuery, title: string] }>()

const arrow = (d: number) => (d > 0 ? "▲" : d < 0 ? "▼" : "■")
const deltaClass = (d: number, higherIsGood: boolean) => (d === 0 ? {} : { up: d > 0 === higherIsGood, down: d > 0 !== higherIsGood })

const bars = computed<StackBar[]>(() => props.data.chart.bars)
const monthLabel = (key: string) => props.data.chart.bars.find((b) => b.key === key)?.label ?? key
</script>

<template>
	<section class="bbr-tiles" aria-label="Summary">
		<template v-for="t in data.tiles" :key="t.label">
			<button v-if="t.open" type="button" class="bbr-tile" @click="emit('open', t.open, t.label)">
				<span class="bbr-tile-label">{{ t.label }}</span>
				<span class="bbr-tile-value">{{ tileValue(t) }}</span>
				<span class="bbr-tile-sub">
					<span v-if="t.delta !== null" class="bbr-delta" :class="deltaClass(t.delta, t.higher_is_good)">
						{{ arrow(t.delta) }} {{ signed(t.delta) }} {{ t.delta_label }}
					</span>
					<span>{{ t.sub }}</span>
				</span>
			</button>
			<div v-else class="bbr-tile static">
				<span class="bbr-tile-label">{{ t.label }}</span>
				<span class="bbr-tile-value" :class="{ 'bbr-tile-text': typeof t.value === 'string' && t.value.length > 6 }">{{ tileValue(t) }}</span>
				<span class="bbr-tile-sub">
					<span v-if="t.delta !== null" class="bbr-delta" :class="deltaClass(t.delta, t.higher_is_good)">
						{{ arrow(t.delta) }} {{ signed(t.delta) }} {{ t.delta_label }}
					</span>
					<span>{{ t.sub }}</span>
				</span>
			</div>
		</template>
	</section>

	<div class="bbr-grid-2">
		<StackedChart
			:title="data.chart.title"
			:series="data.chart.series"
			:bars="bars"
			:note="`${data.chart.note}${bars.some((b) => b.running) ? ' * running month, counted till today.' : ''}`"
			@open="emit('open', { kind, month: $event }, monthLabel($event))"
		/>
		<BarList
			v-if="data.bars[0]"
			:title="data.bars[0].title"
			:rows="data.bars[0].rows.map((r) => ({ label: r.label, count: r.count, key: r.key ?? undefined }))"
			:limit="data.bars[0].limit"
			@open="(row) => emit('open', { kind, row }, `${data.bars[0].title.split(' · ')[0]} · ${data.bars[0].rows.find((r) => r.key === row)?.label}`)"
		/>
	</div>

	<div v-if="data.bars.length > 1" class="bbr-grid-2">
		<BarList
			v-for="b in data.bars.slice(1)"
			:key="b.title"
			:title="b.title"
			:rows="b.rows.map((r) => ({ label: r.label, count: r.count, key: r.key ?? undefined }))"
			:limit="b.limit"
			@open="(row) => emit('open', { kind, row }, `${b.title.split(' · ')[0]} · ${b.rows.find((r) => r.key === row)?.label}`)"
		/>
	</div>

	<section v-for="t in data.tables" :key="t.title" class="bbr-card">
		<div class="bbr-card-head"><h2>{{ t.title }}</h2></div>
		<DataTable :columns="t.columns" :rows="t.rows" :link-key="t.link_key" :link-base="linkBase" :empty="t.empty" />
	</section>
</template>
