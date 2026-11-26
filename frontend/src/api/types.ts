/** Shapes returned by bb_report_manager.api.dashboard (see api/tuition.py). */

export interface AcademicYear {
	name: string
	start_date: string
	end_date: string
	is_active: number
}

export interface FilterOptions {
	academic_years: AcademicYear[]
	default_academic_year: string | null
	standards: { name: string; group: string | null; academic_order: number }[]
	batches: { name: string }[]
	genders: string[]
	/** Base URL of the tuition site, for linking to Student records ("" when local). */
	tuition_site_url: string
}

export interface Filters {
	academic_year: string
	month: string
	standard: string
	batch: string
	gender: string
}

export interface MonthColumn {
	key: string // "2026-10"
	label: string // "OCT"
	month: string // "October"
	year: number
}

export interface GridRow {
	key: string // "10TH|Boys"
	label: string // "10TH STD - BOYS"
	standard: string
	gender: string
	idx: number
	values: Record<string, number | null>
	total: number
}

export interface MovementRow {
	key: string
	label: string // "October 2026"
	short: string // "OCT"
	opening: number
	joined: number
	rejoined: number
	discontinued: number
	closing: number
	net: number
	present: number
	boys: number
	girls: number
	running: boolean
}

export interface Summary {
	as_of: string
	strength: number
	strength_prev: number | null
	strength_prev_label: string | null
	boys: number
	girls: number
	opening: number
	joined: number
	rejoined: number
	discontinued: number
	enrolled: number
	retention: number | null
	period: string
}

export interface BatchBreakdown {
	month_key: string
	label: string
	batches: string[]
	rows: { standard: string; values: Record<string, number>; no_batch: number; boys: number; girls: number; total: number }[]
	totals: { values: Record<string, number>; no_batch: number; boys: number; girls: number; total: number }
}

export interface StudentCountReport {
	report: "student_count"
	title: string
	academic_year: string
	academic_year_label: string
	generated_on: string
	columns: MonthColumn[]
	rows: GridRow[]
	totals: { values: Record<string, number | null>; total: number }
	summary: Summary | null
	movement: MovementRow[]
	batch_breakdown: BatchBreakdown | null
}

export type DetailKind = "present" | "opening" | "joined" | "rejoined" | "discontinued" | "closing"

/** What a clicked number stands for; sent to get_report_detail. */
export interface DetailQuery {
	kind: DetailKind | FeeKind
	row?: string | null
	month?: string | null
	batch?: string | null
}

export interface StudentDetail {
	student: string
	student_name: string
	standard: string
	gender: string
	batch: string | null
	status: string
	admission_date: string | null
	discontinued_date: string | null
	rejoined_date: string | null
	discontinue_reason: string | null
	father_name: string | null
	mobile: string | null
	school: string | null
	area: string | null
	monthly_fee: number | null
	scholarship: number
	events: string[]
}

// ------------------------------------------------------------------ admin dashboard

export type AdminMetric = "admin_enquiry" | "admin_total" | "admin_actual" | "admin_discontinued"
export type AdminSectionKey = "junior" | "senior_boys" | "senior_girls"
/** Count sheets also serve the TL "Discontinue Students" sheet, a single "tl" section. */
export type CountSectionKey = AdminSectionKey | "tl"
export type AdminKind = "enquiry" | "joined" | "total" | "actual" | "discontinued"

export interface EJ {
	e: number
	j: number
}

interface AdminRowBase {
	key: string // "11TH Commerce|Girls|Business Maths"
	label: string // "11TH COMMERCE (BM)"
	standard: string
	gender: string
	group: string
	idx: number
}

export interface AdminCountRow extends AdminRowBase {
	values: Record<string, number | null>
	highest: number | null
	highest_month: string | null
}

export interface AdminEnquiryRow extends AdminRowBase {
	values: Record<string, EJ | null>
	total: EJ
}

export interface AdminCountSection {
	key: CountSectionKey
	label: string
	rows: AdminCountRow[]
	totals: { values: Record<string, number | null>; highest: number | null; highest_month: string | null }
}

export interface AdminEnquirySection {
	key: AdminSectionKey
	label: string
	rows: AdminEnquiryRow[]
	totals: { values: Record<string, EJ | null>; total: EJ }
}

export interface EnquirySummary {
	enquiries: number
	joined: number
	conversion: number | null
	by_status: { label: string; count: number }[]
	by_source: { label: string; count: number }[]
	no_group: number
	period: string
}

interface AdminReportBase {
	title: string
	subtitle: string
	academic_year: string
	academic_year_label: string
	generated_on: string
	columns: MonthColumn[]
}

export interface AdminCountReport extends AdminReportBase {
	report: "admin_total" | "admin_actual" | "admin_discontinued"
	sections: AdminCountSection[]
	/** Standard x batch: the latest month for strength sheets, every month so far for discontinued. */
	batch_breakdown?: BatchBreakdown
	/** Discontinued only: why students left, most common first. */
	reasons?: { label: string; count: number }[]
}

export interface AdminEnquiryReport extends AdminReportBase {
	report: "admin_enquiry"
	sections: AdminEnquirySection[]
	summary: EnquirySummary
}

export type AdminReport = AdminCountReport | AdminEnquiryReport

export interface AdminDetailQuery {
	kind: AdminKind
	row?: string | null
	month?: string | null
	section?: CountSectionKey | null
	/** Narrow the drill-down to one standard and/or batch ("__none__" = no batch). */
	standard?: string | null
	batch?: string | null
	/** Shown in the dialog title. */
	label: string
}

export interface EnquiryDetail {
	enquiry: string
	applicant_name: string
	enquiry_date: string | null
	standard: string
	group: string | null
	gender: string
	status: string
	source: string | null
	father_name: string | null
	mobile: string | null
	school: string | null
	area: string | null
	remarks: string | null
	next_follow_up_date: string | null
}

export type DetailResult =
	| { type: "table"; site: "tuition" | "erp"; columns: TableColumn[]; rows: Record<string, unknown>[]; link_key?: string | null }
	| { type: "student"; rows: StudentDetail[] }
	| { type: "enquiry"; rows: EnquiryDetail[] }
	| { type: "fee"; rows: FeeDetail[] }

// ------------------------------------------------------------------ Manager Report 2: fees pending after the 15th

export interface FeeColumn extends MonthColumn {
	/** ok = judged; future = its 15th has not passed; no_data = before invoices began */
	state: "ok" | "future" | "no_data"
}

export interface FeeMonth {
	key: string
	label: string
	short: string
	due: number
	on_time: number
	pending: number
	pending_pct: number | null
	balance_on_cutoff: number
	paid_late: number
	still_pending: number
	still_pending_amount: number
}

export interface FeesPendingReport {
	report: "fees_pending"
	title: string
	academic_year: string
	academic_year_label: string
	generated_on: string
	columns: FeeColumn[]
	rows: GridRow[]
	totals: { values: Record<string, number | null>; total: number }
	monthly: FeeMonth[]
	data_from: string | null
	yearly_students: number
	summary: {
		month: string
		pending: number
		pending_prev: number | null
		prev_label: string | null
		due: number
		pending_pct: number | null
		balance_on_cutoff: number
		still_pending: number
		still_pending_amount: number
		paid_late: number
	} | null
	batch_breakdown: BatchBreakdown | null
}

export type FeeKind = "pending" | "due" | "on_time" | "paid_late" | "still_pending"

export interface FeeDetail extends StudentDetail {
	fee_month: string
	fee_month_key: string
	fee: number | null
	paid_by_cutoff: number | null
	balance_on_cutoff: number | null
	paid_late_on: string | null
	still_pending: boolean
	pending_today: number | null
	on_time: boolean
}

// ------------------------------------------------------------------ Target Charts (Asst. Manager, TL)

export interface TargetPerson {
	id: string
	name: string
	/** "10th - II" for a student, "Designation - Department" for staff */
	detail: string
	count: number
}

export interface TargetCell {
	total: number
	/** Everyone with a mistake in the cell, most mistakes first; the first two are the "last 2 places". */
	people: TargetPerson[]
}

export interface TargetRow {
	key: string
	label: string
	idx: number
	future?: boolean
	cells: Record<string, TargetCell>
}

export interface TargetTable {
	key: string
	label: string
	start?: string
	end?: string
	future?: boolean
	rows: TargetRow[]
	totals: Record<string, number>
}

export interface TargetInsights {
	month_key: string
	month_label: string
	/** "STD - Batch" or "Department" */
	group_head: string
	summary: {
		total: number
		prev_total: number | null
		prev_label: string | null
		people: number
		ten_plus: number
		by_category: { key: string; label: string; count: number; prev: number | null }[]
	}
	trend: { key: string; label: string; short: string; running: boolean; by_category: Record<string, number>; total: number }[]
	top: (TargetPerson & { by_category: Record<string, number> })[]
	groups: { label: string; by_category: Record<string, number>; total: number; people: number }[]
}

interface TargetBase {
	insights: TargetInsights
	title: string
	subtitle: string
	academic_year: string
	academic_year_label: string
	generated_on: string
	/** "November 2026" -- the month the sheet covers */
	period: string
}

export interface TargetGridReport extends TargetBase {
	report: "am_weekly" | "am_monthly" | "tl_weekly" | "tl_monthly"
	row_head: string
	categories: { key: string; label: string }[]
	tables: TargetTable[]
}

export interface TenPlusReport extends TargetBase {
	report: "am_ten_plus" | "tl_ten_plus"
	sub_head: string
	lists: { key: string; label: string; people: TargetPerson[] }[]
}

export type TargetReport = TargetGridReport | TenPlusReport

// ------------------------------------------------------------------ Manager Charts 3 - 9 (generic shapes)

/** A drill-down the dashboard sends back: which records sit behind a number. */
export interface ManagerQuery {
	kind: string
	row?: string | null
	month?: string | null
	section?: string | null
	batch?: string | null
}

export interface TableColumn {
	key: string
	label: string
	num?: boolean
	/** how the cell prints: date / datetime / link / check */
	kind?: "date" | "datetime" | "link" | "check" | null
}

export interface TableBlock {
	title: string
	columns: TableColumn[]
	rows: Record<string, unknown>[]
	link_key?: string | null
	empty?: string
}

export interface InsightTile {
	label: string
	value: number | string | null
	fmt?: "points" | "pct" | null
	sub: string
	delta: number | null
	delta_label: string
	higher_is_good: boolean
	open: ManagerQuery | null
}

export interface ManagerInsights {
	tiles: InsightTile[]
	chart: {
		title: string
		series: [string, string]
		bars: { key: string; label: string; short: string; running: boolean; lower: number; upper: number }[]
		note: string
	}
	bars: { title: string; rows: { label: string; count: number; key: string | null }[]; limit?: number }[]
	tables: TableBlock[]
}

export interface SheetRow {
	key: string
	label: string
	idx: number
	values: Record<string, number | null>
	total: number
	/** Work list sheet: Daily / Weekly / Monthly behind each month's number. */
	split?: Record<string, Record<string, number>>
}

export interface ManagerGridReport {
	report: "parent_complaint" | "discontinued" | "kpi_points" | "staff_count" | "work_mistakes"
	title: string
	row_head?: string
	academic_year: string
	academic_year_label: string
	generated_on: string
	columns: MonthColumn[]
	rows: SheetRow[]
	totals: { values: Record<string, number | null>; total: number }
	insights: ManagerInsights
}

export interface ProblemRow {
	date: string
	title: string
	who: string | null
	role: string | null
	kind: string | null
	status: string
	solved: boolean
	solved_at: string | null
	assigned: string | null
	source: string
	priority: string | null
	overdue: boolean
	link: string
}

export interface CriticalProblemsReport {
	report: "critical_problems"
	title: string
	academic_year_label: string
	generated_on: string
	columns: MonthColumn[]
	items: Record<string, ProblemRow[]>
	future: string[]
	insights: ManagerInsights
}

export interface SingleSheetReport {
	report: "single_sheet_problems"
	title: string
	academic_year_label: string
	generated_on: string
	period: string
	month_key: string
	rows: ProblemRow[]
	insights: ManagerInsights
}
