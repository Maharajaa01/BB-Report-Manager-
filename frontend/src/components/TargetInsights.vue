<script setup lang="ts">
/**
 * The detail under a Target sheet, for the sheet's month: headline tiles, the
 * year's trend, mistakes by category, the people with the most mistakes and the
 * month per group (STD - Batch / department). Clicking a month switches the sheet to it.
 */
import { computed } from "vue"

import type { TargetInsights } from "@/api/types"
import BarList, { type BarRow } from "@/components/BarList.vue"
import StackedChart, { type StackBar } from "@/components/StackedChart.vue"
import { num, signed } from "@/lib/format"

const props = defineProps<{
	data: TargetInsights
	/** Category drawn as the lower stack: Attendance (Leave) for students, Attendance for staff. */
	lowerKey: string
	staff: boolean
	link: (id: string) => string
}>()
const emit = defineEmits<{ month: [key: string] }>()

const s = computed(() => props.data.summary)
const categories = computed(() => s.value.by_category)
const lowerLabel = computed(() => categories.value.find((c) => c.key === props.lowerKey)?.label ?? "Attendance")
const noun = computed(() => (props.staff ? "staff" : "students"))

// Fewer mistakes is better: a rise reads red.
const delta = computed(() => (s.value.prev_total === null ? null : s.value.total - s.value.prev_total))
const arrow = (d: number) => (d > 0 ? "▲" : d < 0 ? "▼" : "■")
const worst = computed(() => [...categories.value].sort((a, b) => b.count - a.count)[0])
const prevShort = computed(() => s.value.prev_label?.split(" ")[0].slice(0, 3) ?? "")

const bars = computed<StackBar[]>(() =>
	props.data.trend.map((t) => ({
		key: t.key,
		label: t.label,
		short: t.short,
		running: t.running,
		lower: t.by_category[props.lowerKey] ?? 0,
		upper: t.total - (t.by_category[props.lowerKey] ?? 0),
		extra: categories.value
			.filter((c) => c.key !== props.lowerKey && t.by_category[c.key])
			.map((c) => ({ label: c.label, value: num(t.by_category[c.key]) })),
	})),
)

const categoryRows = computed<BarRow[]>(() =>
	[...categories.value]
		.sort((a, b) => b.count - a.count)
		.map((c) => {
			const d = c.prev === null ? null : c.count - c.prev
			return {
				label: c.label,
				count: c.count,
				note: d === null ? "" : `${arrow(d)} ${signed(d)} vs ${prevShort.value}`,
				noteClass: d === null ? "" : d > 0 ? "bad" : d < 0 ? "good" : "",
			}
		}),
)
</script>

<template>
	<section class="bbr-tiles" aria-label="Summary">
		<div class="bbr-tile static">
			<span class="bbr-tile-label">Mistakes · {{ data.month_label }}</span>
			<span class="bbr-tile-value">{{ num(s.total) }}</span>
			<span class="bbr-tile-sub">
				<span v-if="delta !== null" class="bbr-delta" :class="{ down: delta > 0, up: delta < 0 }">
					{{ arrow(delta) }} {{ signed(delta) }} vs {{ s.prev_label }}
				</span>
				<span>across every category</span>
			</span>
		</div>
		<div class="bbr-tile static">
			<span class="bbr-tile-label">Biggest category</span>
			<span class="bbr-tile-value">{{ worst && worst.count ? worst.label : "–" }}</span>
			<span class="bbr-tile-sub">
				{{ worst && worst.count ? `${num(worst.count)} mistakes, ${Math.round((100 * worst.count) / (s.total || 1))}% of the month` : "no mistakes this month" }}
			</span>
		</div>
		<div class="bbr-tile static">
			<span class="bbr-tile-label">{{ staff ? "Staff" : "Students" }} with a mistake</span>
			<span class="bbr-tile-value">{{ num(s.people) }}</span>
			<span class="bbr-tile-sub">{{ s.people ? `${(s.total / s.people).toFixed(1)} mistakes each on average` : "a clean month" }}</span>
		</div>
		<div class="bbr-tile static" :class="{ warn: s.ten_plus }">
			<span class="bbr-tile-label">10+ in a category</span>
			<span class="bbr-tile-value">{{ num(s.ten_plus) }}</span>
			<span class="bbr-tile-sub">{{ noun }} on the 10+ sheet this month</span>
		</div>
	</section>

	<div class="bbr-grid-2">
		<StackedChart
			title="Mistakes per month"
			:series="[lowerLabel, 'Other mistakes']"
			:bars="bars"
			total-label="Mistakes"
			:note="`Click a month to open the sheets for it.${bars.some((b) => b.running) ? ' * running month, counted till today.' : ''}`"
			@open="emit('month', $event)"
		/>
		<BarList :title="`By category · ${data.month_label}`" :rows="categoryRows" empty="No mistakes this month." />
	</div>

	<div class="bbr-grid-2">
		<section class="bbr-card">
			<div class="bbr-card-head"><h2>Most mistakes · {{ data.month_label }}</h2></div>
			<div class="bbr-table-scroll">
				<table class="bbr-table">
					<thead>
						<tr>
							<th>#</th>
							<th>{{ staff ? "Staff" : "Student" }}</th>
							<th v-for="c in categories" :key="c.key" class="num" :title="c.label">{{ c.label.replace(/ \(.*\)/, "") }}</th>
							<th class="num">Total</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(p, i) in data.top" :key="p.id">
							<td>{{ i + 1 }}</td>
							<td>
								<a :href="link(p.id)" target="_blank" rel="noopener">{{ p.name }}</a><br />
								<small class="bbr-muted">{{ p.detail }}</small>
							</td>
							<td v-for="c in categories" :key="c.key" class="num" :class="{ 'bbr-muted': !p.by_category[c.key] }">
								{{ p.by_category[c.key] || "·" }}
							</td>
							<td class="num strong">{{ num(p.count) }}</td>
						</tr>
						<tr v-if="!data.top.length"><td :colspan="categories.length + 3" class="bbr-empty">No mistakes this month</td></tr>
					</tbody>
				</table>
			</div>
		</section>

		<section class="bbr-card">
			<div class="bbr-card-head"><h2>By {{ data.group_head.toLowerCase() }} · {{ data.month_label }}</h2></div>
			<div class="bbr-table-scroll">
				<table class="bbr-table">
					<thead>
						<tr>
							<th>{{ data.group_head }}</th>
							<th v-for="c in categories" :key="c.key" class="num" :title="c.label">{{ c.label.replace(/ \(.*\)/, "") }}</th>
							<th class="num">Total</th>
							<th class="num">{{ staff ? "Staff" : "Students" }}</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="g in data.groups" :key="g.label">
							<td>{{ g.label }}</td>
							<td v-for="c in categories" :key="c.key" class="num" :class="{ 'bbr-muted': !g.by_category[c.key] }">
								{{ g.by_category[c.key] || "·" }}
							</td>
							<td class="num strong">{{ num(g.total) }}</td>
							<td class="num">{{ num(g.people) }}</td>
						</tr>
						<tr v-if="!data.groups.length"><td :colspan="categories.length + 3" class="bbr-empty">No mistakes this month</td></tr>
					</tbody>
				</table>
			</div>
		</section>
	</div>
</template>
