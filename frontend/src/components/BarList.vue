<script setup lang="ts">
/**
 * A ranked one-hue bar list in a card: label, bar, value at the tip.
 * Rows with `key` are clickable; `note` adds a muted second value (e.g. "▲ 4 vs Oct").
 */
import { computed } from "vue"

import { num } from "@/lib/format"

export interface BarRow {
	label: string
	count: number
	key?: string
	note?: string
	noteClass?: string
}

const props = withDefaults(defineProps<{ title: string; rows: BarRow[]; limit?: number; empty?: string }>(), {
	limit: 0,
	empty: "Nothing to show",
})
const emit = defineEmits<{ open: [key: string] }>()

/** Long tails fold into one "Others" row so the list stays readable. */
const shown = computed<BarRow[]>(() => {
	if (!props.limit || props.rows.length <= props.limit) return props.rows
	const head = props.rows.slice(0, props.limit - 1)
	const rest = props.rows.slice(props.limit - 1)
	return [...head, { label: `Others (${rest.length})`, count: rest.reduce((a, r) => a + r.count, 0) }]
})
const max = computed(() => Math.max(1, ...shown.value.map((r) => r.count)))
const total = computed(() => props.rows.reduce((a, r) => a + r.count, 0))
const pct = (n: number) => (total.value ? Math.round((100 * n) / total.value) : 0)
</script>

<template>
	<section class="bbr-card">
		<div class="bbr-card-head"><h2>{{ title }}</h2></div>
		<ul v-if="total" class="bbr-bars">
			<li
				v-for="r in shown"
				:key="r.label"
				:class="{ clickable: !!r.key && r.count > 0 }"
				:tabindex="r.key && r.count ? 0 : undefined"
				:title="r.label"
				@click="r.key && r.count && emit('open', r.key)"
				@keydown.enter="r.key && r.count && emit('open', r.key)"
			>
				<span class="bbr-bar-label">{{ r.label }}</span>
				<span class="bbr-bar-track"><span class="bbr-bar" :style="{ width: `${(100 * r.count) / max}%` }"></span></span>
				<span class="bbr-bar-value">
					{{ num(r.count) }} <small>{{ pct(r.count) }}%</small>
					<small v-if="r.note" class="bbr-bar-note" :class="r.noteClass">{{ r.note }}</small>
				</span>
			</li>
		</ul>
		<p v-else class="bbr-card-note">{{ empty }}</p>
	</section>
</template>
