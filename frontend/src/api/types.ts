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
	kind: DetailKind
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
	key: AdminSectionKey
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
	section?: AdminSectionKey | null
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

export type DetailResult = { type: "student"; rows: StudentDetail[] } | { type: "enquiry"; rows: EnquiryDetail[] }
