<script setup lang="ts">
import { computed } from "vue"

import type { FilterOptions, Filters } from "@/api/types"
import { MONTHS, monthsBetween } from "@/lib/format"

const props = defineProps<{
	options: FilterOptions
	filters: Filters
	student: boolean
	canExport: boolean
}>()

const emit = defineEmits<{
	change: [key: keyof Filters, value: string]
	refresh: []
	export: []
	print: []
}>()

const months = computed(() => {
	const year = props.options.academic_years.find((y) => y.name === props.filters.academic_year)
	return year ? monthsBetween(year.start_date, year.end_date) : MONTHS
})

function onChange(key: keyof Filters, e: Event) {
	emit("change", key, (e.target as HTMLSelectElement).value)
}
</script>

<template>
	<section class="bbr-filters" aria-label="Filters">
		<label>
			Academic Year
			<select :value="filters.academic_year" @change="onChange('academic_year', $event)">
				<option v-for="y in options.academic_years" :key="y.name" :value="y.name">{{ y.name }}</option>
			</select>
		</label>
		<label>
			Month
			<select :value="filters.month" @change="onChange('month', $event)">
				<option value="">All Months</option>
				<option v-for="m in months" :key="m" :value="m">{{ m }}</option>
			</select>
		</label>
		<template v-if="student">
			<label>
				Standard
				<select :value="filters.standard" @change="onChange('standard', $event)">
					<option value="">All Standards</option>
					<option v-for="s in options.standards" :key="s.name" :value="s.name">{{ s.name }}</option>
				</select>
			</label>
			<label>
				Batch
				<select :value="filters.batch" @change="onChange('batch', $event)">
					<option value="">All Batches</option>
					<option v-for="b in options.batches" :key="b.name" :value="b.name">Batch {{ b.name }}</option>
				</select>
			</label>
			<label>
				Gender
				<select :value="filters.gender" @change="onChange('gender', $event)">
					<option value="">All</option>
					<option v-for="g in options.genders" :key="g" :value="g">{{ g }}</option>
				</select>
			</label>
		</template>
		<div class="bbr-filter-actions">
			<button type="button" @click="emit('refresh')">Refresh</button>
			<button v-if="canExport" type="button" class="secondary" @click="emit('export')">Export to Excel</button>
			<button type="button" class="secondary" @click="emit('print')">Print</button>
		</div>
	</section>
</template>
