<script setup lang="ts">
import { computed, ref, watchEffect } from "vue"
import { useRoute } from "vue-router"

import FilterBar from "@/components/FilterBar.vue"
import { type Dashboard, reportByPath, reportsOf } from "@/lib/reports"
import { loadOptions, options, useFilters } from "@/lib/store"
import AdminView from "@/views/AdminView.vue"
import ComingSoon from "@/views/ComingSoon.vue"
import StudentCountView from "@/views/StudentCountView.vue"

/** Each ready report's view exposes refresh() and exportCsv(). */
interface ReportHandle {
	refresh: () => void
	exportCsv: () => void
}

const VIEWS: Record<string, unknown> = {
	student_count: StudentCountView,
	admin_enquiry: AdminView,
	admin_total: AdminView,
	admin_actual: AdminView,
	admin_discontinued: AdminView,
}

const route = useRoute()
const { filters, setFilter } = useFilters()
const view = ref<ReportHandle | null>(null)

const dashboard = computed<Dashboard>(() => (route.meta.dashboard as Dashboard) || "manager")
const report = computed(
	() => reportByPath(dashboard.value, String(route.params.report)) || reportsOf(dashboard.value)[0],
)
const component = computed(() => (report.value.ready ? VIEWS[report.value.key] : null))

const print = () => window.print()

watchEffect(() => {
	document.title = `${report.value.nav} · ${dashboard.value === "admin" ? "Admin" : "Manager"} Charts`
})
</script>

<template>
	<div v-if="options.error" class="bbr-state error">
		{{ options.error }}
		<div><button type="button" class="bbr-btn secondary" @click="loadOptions">Try again</button></div>
	</div>
	<div v-else-if="!options.data" class="bbr-state">Loading…</div>
	<template v-else>
		<FilterBar
			:options="options.data"
			:filters="filters"
			:student="!!report.student"
			:can-export="!!component"
			@change="setFilter"
			@refresh="view?.refresh()"
			@export="view?.exportCsv()"
			@print="print"
		/>
		<!-- key: a fresh view per report, so AdminView never shows one sheet's data under another's title -->
		<component :is="component" v-if="component" :key="report.key" ref="view" :report="report" />
		<ComingSoon v-else :report="report" />
	</template>
</template>
