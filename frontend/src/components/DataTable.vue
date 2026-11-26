<script setup lang="ts">
/** Any server-described table: columns say how to print each cell (date, link, check, number). */
import type { TableColumn } from "@/api/types"
import { cellText } from "@/lib/cells"

defineProps<{
	columns: TableColumn[]
	rows: Record<string, unknown>[]
	linkKey?: string | null
	/** Prefix for record links: the tuition site's URL, or "" for this site. */
	linkBase?: string
	empty?: string
	numbered?: boolean
}>()
</script>

<template>
	<div class="bbr-table-scroll">
		<table class="bbr-table bbr-list">
			<thead>
				<tr>
					<th v-if="numbered">#</th>
					<th v-for="c in columns" :key="c.key" :class="{ num: c.num }">{{ c.label }}</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(r, i) in rows" :key="i" :class="{ 'bbr-row-alert': r.overdue }">
					<td v-if="numbered">{{ i + 1 }}</td>
					<td v-for="c in columns" :key="c.key" :class="{ num: c.num, nowrap: c.kind === 'date' || c.kind === 'datetime' }">
						<a
							v-if="c.kind === 'link' && linkKey && r[linkKey]"
							:href="`${linkBase ?? ''}${r[linkKey]}`"
							target="_blank"
							rel="noopener"
						>{{ cellText(r[c.key], c) }}</a>
						<span v-else-if="c.kind === 'check'" class="bbr-check" :class="r[c.key] ? 'yes' : 'no'">
							{{ r[c.key] ? "✓ Yes" : "✗ No" }}
						</span>
						<template v-else>{{ cellText(r[c.key], c) }}</template>
					</td>
				</tr>
				<tr v-if="!rows.length">
					<td :colspan="columns.length + (numbered ? 1 : 0)" class="bbr-empty">{{ empty || "Nothing to show" }}</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>
