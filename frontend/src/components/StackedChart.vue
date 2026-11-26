<script setup lang="ts">
/**
 * Two-series stacked columns, one per month (categorical slot 1 below, slot 2 on top).
 * Columns <= 38px with a 4px rounded cap, 2px surface gap between segments,
 * hairline grid, total on each cap, per-column hover/focus tooltip; click opens the month.
 */
import { computed, ref } from "vue"

import { niceStep, num } from "@/lib/format"

export interface StackBar {
	key: string
	label: string // "October 2026"
	short: string // "OCT"
	running?: boolean
	lower: number
	upper: number
	/** Extra tooltip lines, e.g. Joined / Left. */
	extra?: { label: string; value: string }[]
}

const props = defineProps<{
	title: string
	series: [string, string] // [lower, upper] labels; an empty upper label = single series
	bars: StackBar[]
	totalLabel?: string
	note?: string
}>()
const emit = defineEmits<{ open: [key: string] }>()

const W = 640
const H = 300
const L = 44
const R = 12
const T = 28
const B = 34

const total = (b: StackBar) => b.lower + b.upper

const scale = computed(() => {
	const max = Math.max(...props.bars.map(total), 1)
	const step = niceStep(max / 4)
	const top = Math.ceil(max / step) * step
	const ticks: number[] = []
	for (let v = 0; v <= top; v += step) ticks.push(v)
	return { top, ticks }
})

const y = (v: number) => T + (H - T - B) * (1 - v / scale.value.top)
const band = computed(() => (W - L - R) / Math.max(props.bars.length, 1))
const bw = computed(() => Math.min(38, band.value * 0.56))

function roundTop(x: number, top: number, w: number, h: number, r = 4): string {
	if (h <= 0) return ""
	r = Math.min(r, h, w / 2)
	return `M${x},${top + h} V${top + r} Q${x},${top} ${x + r},${top} H${x + w - r} Q${x + w},${top} ${x + w},${top + r} V${top + h} Z`
}

const columns = computed(() =>
	props.bars.map((b, i) => {
		const cx = L + band.value * i + band.value / 2
		const x = cx - bw.value / 2
		const yLower = y(b.lower)
		const yTop = y(total(b))
		const gap = b.lower && b.upper ? 2 : 0
		return {
			b,
			cx,
			x,
			hitX: L + band.value * i,
			yTop,
			// The top segment carries the rounded cap; the one under it stays square.
			lowerCap: b.upper ? null : roundTop(x, yLower, bw.value, y(0) - yLower),
			lowerRect: b.upper && b.lower ? { y: yLower, h: y(0) - yLower } : null,
			upper: b.upper ? roundTop(x, yTop, bw.value, Math.max(0, yLower - yTop - gap)) : "",
		}
	}),
)

const active = ref<number | null>(null)
const wrap = ref<HTMLElement | null>(null)
const tipLeft = ref(0)

function show(i: number, e: Event) {
	active.value = i
	const box = wrap.value?.getBoundingClientRect()
	const hit = (e.target as Element).getBoundingClientRect()
	if (!box) return
	const centre = hit.left - box.left + hit.width / 2
	tipLeft.value = centre + 170 > box.width ? Math.max(0, centre - 170 - 8) : centre + 8
}
</script>

<template>
	<section class="bbr-card">
		<div class="bbr-card-head">
			<h2>{{ title }}</h2>
			<div class="bbr-legend">
				<span><i class="sw s-1"></i>{{ series[0] }}</span>
				<span v-if="series[1]"><i class="sw s-2"></i>{{ series[1] }}</span>
			</div>
		</div>
		<div ref="wrap" class="bbr-chart-wrap" @pointerleave="active = null">
			<svg class="bbr-svg" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="xMidYMid meet">
				<g v-for="v in scale.ticks" :key="v">
					<line class="bbr-gridline" :x1="L" :x2="W - R" :y1="y(v)" :y2="y(v)" />
					<text class="bbr-axis" :x="L - 8" :y="y(v) + 4" text-anchor="end">{{ num(v) }}</text>
				</g>
				<g v-for="(c, i) in columns" :key="c.b.key" class="bbr-col" :class="{ dim: active !== null && active !== i }">
					<rect v-if="c.lowerRect" class="s-1" :x="c.x" :y="c.lowerRect.y" :width="bw" :height="c.lowerRect.h" />
					<path v-if="c.lowerCap" class="s-1" :d="c.lowerCap" />
					<path v-if="c.upper" class="s-2" :d="c.upper" />
					<text class="bbr-cap" :x="c.cx" :y="c.yTop - 6" text-anchor="middle">{{ num(total(c.b)) }}</text>
					<text class="bbr-axis" :x="c.cx" :y="H - B + 18" text-anchor="middle">{{ c.b.short }}{{ c.b.running ? "*" : "" }}</text>
					<rect
						class="bbr-hit"
						:x="c.hitX"
						:y="T - 20"
						:width="band"
						:height="H - T - B + 20"
						tabindex="0"
						role="img"
						:aria-label="`${c.b.label}: ${total(c.b)} total, ${c.b.lower} ${series[0]}, ${c.b.upper} ${series[1]}`"
						@pointerenter="show(i, $event)"
						@focus="show(i, $event)"
						@blur="active = null"
						@click="emit('open', c.b.key)"
						@keydown.enter="emit('open', c.b.key)"
					/>
				</g>
			</svg>
			<div v-if="active !== null" class="bbr-tooltip" :style="{ left: `${tipLeft}px`, top: '8px' }">
				<div class="tt-head">{{ bars[active].label }}{{ bars[active].running ? " (till today)" : "" }}</div>
				<div class="tt-row"><i class="tt-key"></i><b>{{ num(total(bars[active])) }}</b><span>{{ totalLabel || "Total" }}</span></div>
				<div class="tt-row"><i class="tt-key s-1"></i><b>{{ num(bars[active].lower) }}</b><span>{{ series[0] }}</span></div>
				<div v-if="series[1]" class="tt-row"><i class="tt-key s-2"></i><b>{{ num(bars[active].upper) }}</b><span>{{ series[1] }}</span></div>
				<div v-for="x in bars[active].extra || []" :key="x.label" class="tt-row">
					<i class="tt-key"></i><b>{{ x.value }}</b><span>{{ x.label }}</span>
				</div>
			</div>
		</div>
		<p v-if="note" class="bbr-card-note">{{ note }}</p>
	</section>
</template>
