<script setup lang="ts">
/**
 * The detail under an Admin count sheet (Total / Actual / Discontinued, and the
 * TL Discontinue sheet): headline tiles, Boys / Girls per month, the latest
 * month by standard, standard x batch, and why students left.
 * Every number opens the students behind it.
 */
import { computed } from "vue"

import type { AdminCountReport, AdminDetailQuery, AdminKind, DetailQuery } from "@/api/types"
import BarList, { type BarRow } from "@/components/BarList.vue"
import BatchTable from "@/components/BatchTable.vue"
import StackedChart, { type StackBar } from "@/components/StackedChart.vue"
import { num, signed } from "@/lib/format"

const props = defineProps<{ data: AdminCountReport; gender: string }>()
const emit = defineEmits<{ open: [q: AdminDetailQuery] }>()

const kind = computed(() => props.data.report.replace("admin_", "") as AdminKind)
const leaving = computed(() => kind.value === "discontinued")
const noun = computed(() => ({ total: "Total students", actual: "Actual students", discontinued: "Discontinued" })[kind.value as "total"] ?? "Students")

const rows = computed(() => props.data.sections.flatMap((s) => s.rows))

interface MonthTotal {
	key: string
	label: string
	short: string
	boys: number
	girls: number
	total: number
}

/** Months that have started, with Boys / Girls summed over every row. */
const months = computed<MonthTotal[]>(() =>
	props.data.columns
		.filter((c) => rows.value.some((r) => r.values[c.key] !== null))
		.map((c) => {
			const sum = (g: string) => rows.value.filter((r) => r.gender === g).reduce((a, r) => a + (r.values[c.key] ?? 0), 0)
			const boys = sum("Boys")
			const girls = sum("Girls")
			// TL rows carry "Girls" / "Boys & Girls" as gender: count them all in the total.
			const total = rows.value.reduce((a, r) => a + (r.values[c.key] ?? 0), 0)
			return { key: c.key, label: `${c.month} ${c.year}`, short: c.label, boys, girls, total }
		}),
)
const latest = computed(() => months.value[months.value.length - 1] ?? null)
const prev = computed(() => months.value[months.value.length - 2] ?? null)
const delta = computed(() => (latest.value && prev.value ? latest.value.total - prev.value.total : null))
const peak = computed(() => months.value.reduce<MonthTotal | null>((a, m) => (!a || m.total > a.total ? m : a), null))
const yearSum = computed(() => months.value.reduce((a, m) => a + m.total, 0))
const first = computed(() => months.value[0] ?? null)
const split = computed(() => !!latest.value?.total && latest.value.boys + latest.value.girls === latest.value.total)
const arrow = (d: number) => (d > 0 ? "▲" : d < 0 ? "▼" : "■")
// More students is good; more leaving is bad.
const deltaClass = (d: number) => (leaving.value ? { down: d > 0, up: d < 0 } : { up: d > 0, down: d < 0 })

function openMonth(key: string | null, label: string) {
	emit("open", { kind: kind.value, month: key, label })
}

/** Rows not split by gender (TL sheet for Boys & Girls) can't be stacked: one series then. */
const splittable = computed(() => months.value.every((m) => m.boys + m.girls === m.total))
const series = computed<[string, string]>(() => (splittable.value ? ["Boys", "Girls"] : [noun.value, ""]))
const bars = computed<StackBar[]>(() =>
	months.value.map((m) => ({
		key: m.key,
		label: m.label,
		short: m.short,
		lower: splittable.value ? m.boys : m.total,
		upper: splittable.value ? m.girls : 0,
	})),
)

/** Strength: the latest month. Leavers are few per month, so: every month so far. */
const standardPeriod = computed(() =>
	leaving.value && first.value && latest.value && first.value !== latest.value
		? `${first.value.label} – ${latest.value.label}`
		: latest.value?.label ?? "",
)
const byStandard = computed<BarRow[]>(() => {
	const m = latest.value
	if (!m) return []
	const keys = leaving.value ? months.value.map((x) => x.key) : [m.key]
	const totals = new Map<string, number>()
	for (const r of rows.value)
		totals.set(r.standard, (totals.get(r.standard) ?? 0) + keys.reduce((a, k) => a + (r.values[k] ?? 0), 0))
	return [...totals.entries()]
		.map(([standard, count]) => ({ label: standard, count, key: standard }))
		.filter((r) => r.count > 0)
		.sort((a, b) => b.count - a.count)
})

function openStandard(standard: string) {
	const m = latest.value
	if (m) emit("open", { kind: kind.value, month: leaving.value ? null : m.key, standard, label: `${standard} · ${standardPeriod.value}` })
}

/** BatchTable speaks the Manager chart's query; map it to an admin drill-down. */
function openBatch(q: DetailQuery) {
	const standard = q.row ? q.row.split("|")[0] : null
	const batch = q.batch ?? null
	const bd = props.data.batch_breakdown
	const parts = [standard, batch === "__none__" ? "No batch" : batch ? `Batch ${batch}` : null, bd?.label]
	emit("open", { kind: kind.value, month: q.month || null, standard, batch, label: parts.filter(Boolean).join(" · ") })
}

const reasons = computed<BarRow[]>(() => (props.data.reasons ?? []).map((r) => ({ label: r.label, count: r.count })))
</script>

<template>
	<template v-if="latest">
		<section class="bbr-tiles" aria-label="Summary">
			<button type="button" class="bbr-tile" @click="openMonth(latest.key, latest.label)">
				<span class="bbr-tile-label">{{ noun }} · {{ latest.label }}</span>
				<span class="bbr-tile-value">{{ num(latest.total) }}</span>
				<span class="bbr-tile-sub">
					<span v-if="delta !== null && prev" class="bbr-delta" :class="deltaClass(delta)">
						{{ arrow(delta) }} {{ signed(delta) }} vs {{ prev.label }}
					</span>
					<span>click to see the students</span>
				</span>
			</button>
			<div v-if="split" class="bbr-tile static">
				<span class="bbr-tile-label">Boys · Girls</span>
				<span class="bbr-tile-value">{{ num(latest.boys) }} <small>·</small> {{ num(latest.girls) }}</span>
				<span class="bbr-tile-sub">
					<span class="bbr-split">
						<span class="boys" :style="{ flex: latest.boys || 0.0001 }"></span>
						<span class="girls" :style="{ flex: latest.girls || 0.0001 }"></span>
					</span>
					<span>{{ latest.label }}</span>
				</span>
			</div>
			<button v-if="peak" type="button" class="bbr-tile" @click="openMonth(peak.key, peak.label)">
				<span class="bbr-tile-label">{{ leaving ? "Worst month" : "Highest month" }}</span>
				<span class="bbr-tile-value">{{ num(peak.total) }}</span>
				<span class="bbr-tile-sub">{{ peak.total ? peak.label : "no students in any month" }}</span>
			</button>
			<button v-if="leaving" type="button" class="bbr-tile" @click="openMonth(null, `${first?.label} - ${latest.label}`)">
				<span class="bbr-tile-label">Left so far this year</span>
				<span class="bbr-tile-value">{{ num(yearSum) }}</span>
				<span class="bbr-tile-sub">{{ first?.label }} – {{ latest.label }} · {{ (yearSum / months.length).toFixed(1) }} a month</span>
			</button>
			<div v-else-if="first && first !== latest" class="bbr-tile static">
				<span class="bbr-tile-label">Change since {{ first.label }}</span>
				<span class="bbr-tile-value">
					<span class="bbr-delta" :class="deltaClass(latest.total - first.total)">{{ signed(latest.total - first.total) }}</span>
				</span>
				<span class="bbr-tile-sub">{{ num(first.total) }} → {{ num(latest.total) }}</span>
			</div>
		</section>

		<div class="bbr-grid-2">
			<StackedChart
				:title="`${noun} per month`"
				:series="series"
				:bars="bars"
				:total-label="noun"
				note="Click a month to see the students."
				@open="openMonth($event, months.find((m) => m.key === $event)?.label ?? '')"
			/>
			<BarList :title="`By standard · ${standardPeriod}`" :rows="byStandard" empty="No students in this period." @open="openStandard" />
		</div>

		<div :class="{ 'bbr-grid-2': reasons.length }">
			<BatchTable
				v-if="data.batch_breakdown && data.batch_breakdown.rows.length"
				:data="data.batch_breakdown"
				:gender="gender"
				:title="leaving ? 'Left by standard × batch' : 'Standard × batch'"
				@open="openBatch"
			/>
			<BarList v-if="reasons.length" title="Why students left" :rows="reasons" :limit="8" />
		</div>
	</template>
</template>
