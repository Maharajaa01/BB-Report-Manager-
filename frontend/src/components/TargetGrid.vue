<script setup lang="ts">
/**
 * One "Last 2 Place (with Total Mistake)" table of a Target Chart: rows are
 * standards (TL) or weeks / months (Asst. Manager), columns the mistake
 * categories. Each cell names the two people with the most mistakes and the
 * cell's total; clicking it opens the full ranking.
 */
import type { TargetCell, TargetGridReport, TargetRow, TargetTable } from "@/api/types"
import { LAST_PLACES } from "@/lib/targets"

const props = defineProps<{ data: TargetGridReport; table: TargetTable; heading?: string }>()
const emit = defineEmits<{ open: [title: string, cell: TargetCell] }>()

const blank = (row: TargetRow) => !!(row.future || props.table.future)

function open(row: TargetRow, label: string, cell: TargetCell) {
	if (!cell.total) return
	emit("open", `${label} · ${row.label} · ${props.table.label}`, cell)
}
</script>

<template>
	<div class="bbr-target-table">
		<h2 v-if="heading" class="bbr-target-heading">{{ heading }}</h2>
		<div class="bbr-sheet-scroll">
			<table class="bbr-chart bbr-target">
				<thead>
					<tr>
						<th class="col-sno">S.No</th>
						<th class="col-std">{{ data.row_head }}</th>
						<th v-for="c in data.categories" :key="c.key">{{ c.label }}</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="row in table.rows" :key="row.key">
						<td class="col-sno">{{ row.idx }}</td>
						<td class="col-std">{{ row.label }}</td>
						<template v-for="c in data.categories" :key="c.key">
							<td v-if="blank(row)" class="bbr-target-cell future"></td>
							<td
								v-else
								class="bbr-target-cell"
								:class="{ zero: !row.cells[c.key].total, clickable: !!row.cells[c.key].total }"
								:title="row.cells[c.key].total ? 'Click for everyone in this cell' : 'No mistakes'"
								@click="open(row, c.label, row.cells[c.key])"
							>
								<template v-if="row.cells[c.key].total">
									<ol>
										<li v-for="p in row.cells[c.key].people.slice(0, LAST_PLACES)" :key="p.id">
											<span class="who">{{ p.name }}</span>
											<b>{{ p.count }}</b>
										</li>
									</ol>
									<small>
										Total {{ row.cells[c.key].total }}
										<template v-if="row.cells[c.key].people.length > LAST_PLACES">
											· +{{ row.cells[c.key].people.length - LAST_PLACES }} more
										</template>
									</small>
								</template>
								<template v-else>0</template>
							</td>
						</template>
					</tr>
				</tbody>
				<tfoot>
					<tr>
						<td class="col-sno"></td>
						<td class="col-std">TOTAL</td>
						<td v-for="c in data.categories" :key="c.key" class="num">{{ table.totals[c.key] }}</td>
					</tr>
				</tfoot>
			</table>
		</div>
	</div>
</template>
