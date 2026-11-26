<script setup lang="ts">
/** "10+ Mistake - Monthly Report": one column per category, everyone with ten or more mistakes. */
import type { TenPlusReport } from "@/api/types"

defineProps<{ data: TenPlusReport; link: (id: string) => string }>()

const COLOURS = ["#d6eef3", "#dff1ea", "#f8d3e5", "#fcd3c1", "#cbe4b4"]
</script>

<template>
	<div class="bbr-tenplus">
		<section
			v-for="(l, i) in data.lists"
			:key="l.key"
			class="bbr-tenplus-col"
			:style="{ '--col-bg': COLOURS[i % COLOURS.length] }"
		>
			<h3>{{ l.label }}</h3>
			<table>
				<thead>
					<tr><th>S.No</th><th>Name &amp; Total Mistake</th><th>{{ data.sub_head }}</th></tr>
				</thead>
				<tbody>
					<tr v-for="(p, n) in l.people" :key="p.id">
						<td>{{ n + 1 }}</td>
						<td>
							<a class="who" :href="link(p.id)" target="_blank" rel="noopener">{{ p.name }}</a>
							<b>{{ p.count }}</b>
						</td>
						<td>{{ p.detail }}</td>
					</tr>
					<tr v-if="!l.people.length"><td colspan="3" class="bbr-empty">Nobody reached 10</td></tr>
				</tbody>
			</table>
		</section>
	</div>
</template>
