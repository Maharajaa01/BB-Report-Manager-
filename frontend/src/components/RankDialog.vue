<script setup lang="ts">
/** Everyone behind one Target Chart cell, most mistakes first. Opens when `cell` is set. */
import { nextTick, ref, watch } from "vue"

import type { TargetCell } from "@/api/types"
import { downloadCsv, slug } from "@/lib/csv"
import { LAST_PLACES } from "@/lib/targets"

const props = defineProps<{
	cell: TargetCell | null
	title: string
	filterSummary: string
	detailHead: string
	link: (id: string) => string
}>()
const emit = defineEmits<{ close: [] }>()

const dialog = ref<HTMLDialogElement | null>(null)

watch(
	() => props.cell,
	async (cell) => {
		await nextTick()
		if (cell && !dialog.value?.open) dialog.value?.showModal()
		if (!cell && dialog.value?.open) dialog.value.close()
	},
)

function exportCsv() {
	if (!props.cell) return
	downloadCsv(slug(props.title), [
		[props.title],
		[props.filterSummary],
		[],
		["Place", "Name", props.detailHead, "Mistakes"],
		...props.cell.people.map((p, i) => [i + 1, p.name.trim(), p.detail, p.count]),
	])
}
</script>

<template>
	<dialog ref="dialog" class="bbr-dialog bbr-rank-dialog" @close="emit('close')">
		<div class="bbr-dialog-head">
			<h3>{{ title }}</h3>
			<button type="button" aria-label="Close" @click="dialog?.close()">&times;</button>
		</div>
		<div v-if="cell" class="bbr-dialog-body">
			<div class="bbr-detail-tools">
				<span class="bbr-detail-count">
					{{ cell.total }} mistakes by {{ cell.people.length }} {{ cell.people.length === 1 ? "person" : "people" }}.
					The top {{ LAST_PLACES }} are the "last 2 places" on the sheet.
				</span>
				<button type="button" class="bbr-btn secondary" @click="exportCsv">Export to Excel</button>
			</div>
			<table class="bbr-table bbr-list">
				<thead>
					<tr><th>Place</th><th>Name</th><th>{{ detailHead }}</th><th class="num">Mistakes</th></tr>
				</thead>
				<tbody>
					<tr v-for="(p, i) in cell.people" :key="p.id" :class="{ 'bbr-rank-last': i < LAST_PLACES }">
						<td>{{ i + 1 }}</td>
						<td><a :href="link(p.id)" target="_blank" rel="noopener">{{ p.name }}</a></td>
						<td>{{ p.detail }}</td>
						<td class="num strong">{{ p.count }}</td>
					</tr>
				</tbody>
			</table>
		</div>
	</dialog>
</template>
