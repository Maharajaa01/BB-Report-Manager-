<script setup lang="ts">
/**
 * Month-end strength, stacked Boys (categorical slot 1) / Girls (slot 2).
 * Columns <= ~38px with a 4px rounded cap, 2px surface gap between segments,
 * hairline grid, total on each cap, per-column hover/focus tooltip.
 */
import { computed, ref } from "vue"

import type { DetailQuery, MovementRow } from "@/api/types"
import { niceStep, num } from "@/lib/format"

const props = defineProps<{ movement: MovementRow[] }>()
const emit = defineEmits<{ open: [q: DetailQuery] }>()

const W = 640
const H = 300
const L = 44
const R = 12
const T = 28
const B = 34

const scale = computed(() => {
	const max = Math.max(...props.movement.map((m) => m.closing), 1)
	const step = niceStep(max / 4)
	const top = Math.ceil(max / step) * step
	const ticks: number[] = []
	for (let v = 0; v <= top; v += step) ticks.push(v)
	return { top, ticks }
})

const y = (v: number) => T + (H - T - B) * (1 - v / scale.value.top)
const band = computed(() => (W - L - R) / Math.max(props.movement.length, 1))
const bw = computed(() => Math.min(38, band.value * 0.56))

function roundTop(x: number, top: number, w: number, h: number, r = 4): string {
	if (h <= 0) return ""
	r = Math.min(r, h, w / 2)
	return `M${x},${top + h} V${top + r} Q${x},${top} ${x + r},${top} H${x + w - r} Q${x + w},${top} ${x + w},${top + r} V${top + h} Z`
}

const columns = computed(() =>
	props.movement.map((m, i) => {
		const cx = L + band.value * i + band.value / 2
		const x = cx - bw.value / 2
		const yBoys = y(m.boys)
		const yTop = y(m.closing)
		const gap = m.boys && m.girls ? 2 : 0
		return {
			m,
			cx,
			x,
			hitX: L + band.value * i,
			yTop,
			// The top segment carries the rounded cap; the one under it stays square.
			boys: m.girls ? null : roundTop(x, yBoys, bw.value, y(0) - yBoys),
			boysRect: m.girls && m.boys ? { y: yBoys, h: y(0) - yBoys } : null,
			girls: m.girls ? roundTop(x, yTop, bw.value, Math.max(0, yBoys - yTop - gap)) : "",
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
			<h2>Month-end strength</h2>
			<div class="bbr-legend">
				<span><i class="sw s-boys"></i>Boys</span>
				<span><i class="sw s-girls"></i>Girls</span>
			</div>
		</div>
		<div ref="wrap" class="bbr-chart-wrap" @pointerleave="active = null">
			<svg class="bbr-svg" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="xMidYMid meet">
				<g v-for="v in scale.ticks" :key="v">
					<line class="bbr-gridline" :x1="L" :x2="W - R" :y1="y(v)" :y2="y(v)" />
					<text class="bbr-axis" :x="L - 8" :y="y(v) + 4" text-anchor="end">{{ num(v) }}</text>
				</g>
				<g
					v-for="(c, i) in columns"
					:key="c.m.key"
					class="bbr-col"
					:class="{ dim: active !== null && active !== i }"
				>
					<rect v-if="c.boysRect" class="s-boys" :x="c.x" :y="c.boysRect.y" :width="bw" :height="c.boysRect.h" />
					<path v-if="c.boys" class="s-boys" :d="c.boys" />
					<path v-if="c.girls" class="s-girls" :d="c.girls" />
					<text class="bbr-cap" :x="c.cx" :y="c.yTop - 6" text-anchor="middle">{{ num(c.m.closing) }}</text>
					<text class="bbr-axis" :x="c.cx" :y="H - B + 18" text-anchor="middle">
						{{ c.m.short }}{{ c.m.running ? "*" : "" }}
					</text>
					<rect
						class="bbr-hit"
						:x="c.hitX"
						:y="T - 20"
						:width="band"
						:height="H - T - B + 20"
						tabindex="0"
						role="img"
						:aria-label="`${c.m.label}: ${c.m.closing} students, ${c.m.boys} boys, ${c.m.girls} girls`"
						@pointerenter="show(i, $event)"
						@focus="show(i, $event)"
						@blur="active = null"
						@click="emit('open', { kind: 'closing', month: c.m.key })"
						@keydown.enter="emit('open', { kind: 'closing', month: c.m.key })"
					/>
				</g>
			</svg>
			<div v-if="active !== null" class="bbr-tooltip" :style="{ left: `${tipLeft}px`, top: '8px' }">
				<div class="tt-head">{{ movement[active].label }}{{ movement[active].running ? " (till today)" : "" }}</div>
				<div class="tt-row"><i class="tt-key"></i><b>{{ num(movement[active].closing) }}</b><span>Total</span></div>
				<div class="tt-row"><i class="tt-key s-boys"></i><b>{{ num(movement[active].boys) }}</b><span>Boys</span></div>
				<div class="tt-row"><i class="tt-key s-girls"></i><b>{{ num(movement[active].girls) }}</b><span>Girls</span></div>
				<div class="tt-row">
					<i class="tt-key"></i><b>{{ num(movement[active].joined + movement[active].rejoined) }}</b><span>Joined</span>
				</div>
				<div class="tt-row"><i class="tt-key"></i><b>{{ num(movement[active].discontinued) }}</b><span>Left</span></div>
			</div>
		</div>
		<p v-if="movement.some((m) => m.running)" class="bbr-card-note">* running month, counted till today</p>
	</section>
</template>
