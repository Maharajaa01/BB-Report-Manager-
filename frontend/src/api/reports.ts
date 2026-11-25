import { call } from "./client"
import type { AdminDetailQuery, DetailQuery, DetailResult, FilterOptions, Filters, StudentDetail } from "./types"

export const getFilterOptions = () => call<FilterOptions>("get_filter_options")

export const getReport = <T>(report: string, filters: Partial<Filters>, signal?: AbortSignal) =>
	call<T>("get_report", { report, filters }, signal)

export const getReportDetail = (report: string, filters: Partial<Filters>, q: DetailQuery) =>
	call<StudentDetail[]>("get_report_detail", {
		report,
		filters,
		kind: q.kind,
		row_key: q.row,
		month_key: q.month,
		batch: q.batch,
	})

export const getAdminDetail = (report: string, filters: Partial<Filters>, q: AdminDetailQuery) =>
	call<DetailResult>("get_report_detail", {
		report,
		filters,
		kind: q.kind,
		row_key: q.row,
		month_key: q.month,
		section: q.section,
	})
