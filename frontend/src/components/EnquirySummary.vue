<script setup lang="ts">
/** Headline numbers and the enquiry funnel / sources (one-hue bars, value at the tip). */
import { computed } from "vue"

import type { EnquirySummary } from "@/api/types"
import { num } from "@/lib/format"

const props = defineProps<{ summary: EnquirySummary }>()

const maxOf = (rows: { count: number }[]) => Math.max(1, ...rows.map((r) => r.count))
const statusMax = computed(() => maxOf(props.summary.by_status))
const sourceMax = computed(() => maxOf(props.summary.by_source))
const pct = (n: number) => (props.summary.enquiries ? Math.round((100 * n) / props.summary.enquiries) : 0)
</script>

<template>
	<section class="bbr-tiles" aria-label="Enquiry summary">
		<div class="bbr-tile static">
			<span class="bbr-tile-label">Enquiries</span>
			<span class="bbr-tile-value">{{ num(summary.enquiries) }}</span>
			<span class="bbr-tile-sub">{{ summary.period }}</span>
		</div>
		<div class="bbr-tile static">
			<span class="bbr-tile-label">Joined</span>
			<span class="bbr-tile-value">{{ num(summary.joined) }}</span>
			<span class="bbr-tile-sub">students admitted in the same months</span>
		</div>
		<div class="bbr-tile static">
			<span class="bbr-tile-label">Joined per 100 enquiries</span>
			<span class="bbr-tile-value">{{ summary.conversion === null ? "–" : `${summary.conversion}%` }}</span>
			<span class="bbr-tile-sub">joined ÷ enquiries (not every joiner came through an enquiry)</span>
		</div>
		<div class="bbr-tile static" :class="{ warn: summary.no_group }">
			<span class="bbr-tile-label">11th/12th enquiries without a group</span>
			<span class="bbr-tile-value">{{ num(summary.no_group) }}</span>
			<span class="bbr-tile-sub">{{ summary.no_group ? "shown as “Group not set” rows" : "every enquiry has a group" }}</span>
		</div>
	</section>

	<div class="bbr-grid-2">
		<section class="bbr-card">
			<div class="bbr-card-head"><h2>Enquiries by status</h2></div>
			<ul class="bbr-bars">
				<li v-for="r in summary.by_status" :key="r.label">
					<span class="bbr-bar-label">{{ r.label }}</span>
					<span class="bbr-bar-track"><span class="bbr-bar" :style="{ width: `${(100 * r.count) / statusMax}%` }"></span></span>
					<span class="bbr-bar-value">{{ num(r.count) }} <small>{{ pct(r.count) }}%</small></span>
				</li>
			</ul>
		</section>
		<section class="bbr-card">
			<div class="bbr-card-head"><h2>Enquiries by source</h2></div>
			<ul class="bbr-bars">
				<li v-for="r in summary.by_source" :key="r.label">
					<span class="bbr-bar-label">{{ r.label }}</span>
					<span class="bbr-bar-track"><span class="bbr-bar" :style="{ width: `${(100 * r.count) / sourceMax}%` }"></span></span>
					<span class="bbr-bar-value">{{ num(r.count) }} <small>{{ pct(r.count) }}%</small></span>
				</li>
			</ul>
		</section>
	</div>
</template>
