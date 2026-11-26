import { call } from "./client"
import type { AdminDetailQuery, ManagerQuery, DetailQuery, DetailResult, FeeDetail, FilterOptions, Filters, StudentDetail } from "./types"

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
		// A standard picked from a breakdown narrows the filters for this one call.
		filters: q.standard ? { ...filters, standard: q.standard } : filters,
		kind: q.kind,
		row_key: q.row,
		month_key: q.month,
		section: q.section,
		batch: q.batch,
	})

export const getFeeDetail = (filters: Partial<Filters>, q: DetailQuery) =>
	call<FeeDetail[]>("get_report_detail", {
		report: "fees_pending",
		filters,
		kind: q.kind,
		row_key: q.row,
		month_key: q.month,
		batch: q.batch,
	})

export const getManagerDetail = (report: string, filters: Partial<Filters>, q: ManagerQuery) =>
	call<DetailResult>("get_report_detail", {
		report,
		filters,
		kind: q.kind,
		row_key: q.row,
		month_key: q.month,
		section: q.section,
		batch: q.batch,
	})
