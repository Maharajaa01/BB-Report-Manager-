<script setup lang="ts">
import { computed, ref, watchEffect } from "vue"
import { useRoute } from "vue-router"

import FilterBar from "@/components/FilterBar.vue"
import { DASHBOARDS, type Dashboard, reportByPath, reportsOf } from "@/lib/reports"
import { loadOptions, options, useFilters } from "@/lib/store"
import AdminView from "@/views/AdminView.vue"
import ComingSoon from "@/views/ComingSoon.vue"
import FeesPendingView from "@/views/FeesPendingView.vue"
import ManagerGridView from "@/views/ManagerGridView.vue"
import ProblemsView from "@/views/ProblemsView.vue"
import StudentCountView from "@/views/StudentCountView.vue"
import TargetView from "@/views/TargetView.vue"

/** Each ready report's view exposes refresh() and exportCsv(). */
interface ReportHandle {
	refresh: () => void
	exportCsv: () => void
}

const VIEWS: Record<string, unknown> = {
	student_count: StudentCountView,
	fees_pending: FeesPendingView,
	parent_complaint: ManagerGridView,
	discontinued: ManagerGridView,
	kpi_points: ManagerGridView,
	staff_count: ManagerGridView,
	work_mistakes: ManagerGridView,
	critical_problems: ProblemsView,
	single_sheet_problems: ProblemsView,
	admin_enquiry: AdminView,
	admin_total: AdminView,
	admin_actual: AdminView,
	admin_discontinued: AdminView,
	am_weekly: TargetView,
	am_monthly: TargetView,
	am_ten_plus: TargetView,
	tl_weekly: TargetView,
	tl_monthly: TargetView,
	tl_ten_plus: TargetView,
	// Same STD x month count sheet as the Admin registers.
	tl_discontinued: AdminView,
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
	document.title = `${report.value.nav} · ${DASHBOARDS.find((d) => d.key === dashboard.value)?.title ?? ""}`
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
