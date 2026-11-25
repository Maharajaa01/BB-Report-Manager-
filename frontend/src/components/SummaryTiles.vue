<script setup lang="ts">
import { computed } from "vue"

import type { DetailQuery, Summary } from "@/api/types"
import { num, signed } from "@/lib/format"

const props = defineProps<{ summary: Summary; lastMonth: string | null }>()
const emit = defineEmits<{ open: [q: DetailQuery] }>()

const delta = computed(() =>
	props.summary.strength_prev === null ? null : props.summary.strength - props.summary.strength_prev,
)
const pct = (part: number) => Math.round((100 * part) / (props.summary.boys + props.summary.girls || 1))
</script>

<template>
	<section class="bbr-tiles" aria-label="Summary">
		<button type="button" class="bbr-tile" @click="emit('open', { kind: 'closing', month: lastMonth })">
			<span class="bbr-tile-label">Current strength</span>
			<span class="bbr-tile-value">{{ num(summary.strength) }}</span>
			<span class="bbr-tile-sub">
				<span v-if="delta !== null" class="bbr-delta" :class="{ up: delta > 0, down: delta < 0 }">
					{{ delta > 0 ? "▲" : delta < 0 ? "▼" : "■" }} {{ signed(delta) }} vs {{ summary.strength_prev_label }}
				</span>
				<span>as of {{ summary.as_of }}</span>
			</span>
		</button>

		<div class="bbr-tile static">
			<span class="bbr-tile-label">Boys · Girls</span>
			<span class="bbr-tile-value">{{ num(summary.boys) }} <small>·</small> {{ num(summary.girls) }}</span>
			<span class="bbr-split" role="img" :aria-label="`${summary.boys} boys, ${summary.girls} girls`">
				<span class="boys" :style="{ flex: summary.boys }"></span>
				<span class="girls" :style="{ flex: summary.girls }"></span>
			</span>
			<span class="bbr-tile-sub">{{ pct(summary.boys) }}% boys · {{ pct(summary.girls) }}% girls</span>
		</div>

		<button type="button" class="bbr-tile" @click="emit('open', { kind: 'joined' })">
			<span class="bbr-tile-label">New admissions</span>
			<span class="bbr-tile-value">{{ num(summary.joined) }}</span>
			<span class="bbr-tile-sub">{{ summary.period }}</span>
		</button>

		<button type="button" class="bbr-tile" @click="emit('open', { kind: 'discontinued' })">
			<span class="bbr-tile-label">Discontinued</span>
			<span class="bbr-tile-value">{{ num(summary.discontinued) }}</span>
			<span class="bbr-tile-sub">Retention {{ summary.retention === null ? "–" : `${summary.retention}%` }}</span>
		</button>

		<button type="button" class="bbr-tile" @click="emit('open', { kind: 'rejoined' })">
			<span class="bbr-tile-label">Rejoined</span>
			<span class="bbr-tile-value">{{ num(summary.rejoined) }}</span>
			<span class="bbr-tile-sub">came back after leaving</span>
		</button>

		<button type="button" class="bbr-tile" @click="emit('open', { kind: 'present' })">
			<span class="bbr-tile-label">Students served</span>
			<span class="bbr-tile-value">{{ num(summary.enrolled) }}</span>
			<span class="bbr-tile-sub">enrolled at any time in the period</span>
		</button>
	</section>
</template>
