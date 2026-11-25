/**
 * Filter options (loaded once) and the active filters, which live in the URL
 * query so a filtered report can be bookmarked or shared.
 */
import { computed, reactive } from "vue"
import { useRoute, useRouter } from "vue-router"

import { getFilterOptions } from "@/api/reports"
import type { FilterOptions, Filters } from "@/api/types"
import type { ReportDef } from "@/lib/reports"

const FILTER_KEYS: (keyof Filters)[] = ["academic_year", "month", "standard", "batch", "gender"]

export const options = reactive<{ data: FilterOptions | null; error: string; loading: boolean }>({
	data: null,
	error: "",
	loading: false,
})

let pending: Promise<void> | null = null

export function loadOptions(): Promise<void> {
	if (!pending) {
		options.loading = true
		pending = getFilterOptions()
			.then((data) => {
				options.data = data
			})
			.catch((e: Error) => {
				options.error = e.message
				pending = null
			})
			.finally(() => {
				options.loading = false
			})
	}
	return pending
}

export function useFilters() {
	const route = useRoute()
	const router = useRouter()

	const filters = computed<Filters>(() => {
		const q = route.query
		const get = (k: keyof Filters) => (typeof q[k] === "string" ? (q[k] as string) : "")
		return {
			academic_year: get("academic_year") || options.data?.default_academic_year || "",
			month: get("month"),
			standard: get("standard"),
			batch: get("batch"),
			gender: get("gender"),
		}
	})

	function setFilter(key: keyof Filters, value: string) {
		const query: Record<string, string> = {}
		for (const k of FILTER_KEYS) {
			const v = k === key ? value : filters.value[k]
			if (v) query[k] = v
		}
		// The month list depends on the year; drop a month the new year does not have.
		if (key === "academic_year") delete query.month
		router.replace({ query })
	}

	/** Filters sent to the API: staff reports ignore Standard / Batch / Gender. */
	function apiFilters(report: ReportDef): Partial<Filters> {
		const f: Partial<Filters> = { ...filters.value }
		if (!report.student) {
			delete f.standard
			delete f.batch
			delete f.gender
		}
		return f
	}

	function summary(report: ReportDef): string {
		const f = filters.value
		const parts = [`Academic Year ${f.academic_year}`, f.month || "All months"]
		if (report.student) {
			parts.push(f.standard || "All standards", f.batch ? `Batch ${f.batch}` : "All batches", f.gender || "Boys & Girls")
		}
		return parts.join(" · ")
	}

	return { filters, setFilter, apiFilters, summary }
}
