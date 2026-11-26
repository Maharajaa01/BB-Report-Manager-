/**
 * Every dashboard sheet, in the order of its paper register.
 * bg = page background in the PDF (CMYK converted to RGB); dark = needs light heading text.
 */
export type Dashboard = "manager" | "admin" | "asst_manager" | "tl"

export interface ReportDef {
	key: string
	dashboard: Dashboard
	path: string
	title: string
	nav: string
	bg: string
	dark?: boolean
	/** Student reports take Standard / Batch / Gender filters too. */
	student?: boolean
	ready?: boolean
}

export const DASHBOARDS: { key: Dashboard; label: string; title: string }[] = [
	{ key: "manager", label: "Manager", title: "Manager Charts" },
	{ key: "admin", label: "Admin", title: "Admin Charts" },
	{ key: "asst_manager", label: "Asst. Manager", title: "Asst. Manager Target Chart" },
	{ key: "tl", label: "TL", title: "TL Target Chart" },
]

export const REPORTS: ReportDef[] = [
	// "Manager wiro" PDF
	{ key: "student_count", dashboard: "manager", path: "student-count", title: "ACTUAL STUDENTS COUNT - STD & MONTH WISE", nav: "Actual Students Count", bg: "#9fd33a", student: true, ready: true },
	{ key: "fees_pending", dashboard: "manager", path: "fees-pending", title: "AFTER 15TH FEES PENDING COUNT - STD & MONTH WISE", nav: "Fees Pending After 15th", bg: "#2e3192", dark: true, student: true, ready: true },
	{ key: "parent_complaint", dashboard: "manager", path: "parents-complaint", title: "PARENTS COMPLAINT - STD & MONTH WISE", nav: "Parents Complaint", bg: "#ed1c24", dark: true, student: true, ready: true },
	{ key: "discontinued", dashboard: "manager", path: "discontinued", title: "DISCONTINUED STUDENTS COUNT - STD & MONTH WISE", nav: "Discontinued Students", bg: "#fffbcc", student: true, ready: true },
	{ key: "kpi_points", dashboard: "manager", path: "kpi-points", title: "KPI POINTS - POSTING STAFF'S - MONTH WISE", nav: "KPI Points - Posting Staff", bg: "#a329cc", dark: true, ready: true },
	{ key: "staff_count", dashboard: "manager", path: "staff-count", title: "STAFF'S COUNT - MONTH WISE", nav: "Staff's Count", bg: "#3d5c99", dark: true, ready: true },
	{ key: "work_mistakes", dashboard: "manager", path: "work-mistakes", title: "POSTING STAFF'S WORK LIST MISTAKES - MONTH WISE", nav: "Work List Mistakes", bg: "#b1361e", dark: true, ready: true },
	{ key: "critical_problems", dashboard: "manager", path: "critical-problems", title: "CRITICAL PROBLEMS - MONTH WISE", nav: "Critical Problems", bg: "#ec008c", dark: true, ready: true },
	{ key: "single_sheet_problems", dashboard: "manager", path: "single-sheet-problems", title: "ASST. MANAGER & MANAGER - SINGLE SHEET PROBLEMS", nav: "Single Sheet Problems", bg: "#047b00", dark: true, ready: true },

	// "Admin Wiro" PDFs: Enquiry & Joined Count List, Students Count List
	{ key: "admin_enquiry", dashboard: "admin", path: "enquiry-joiners", title: "ENQUIRY & JOINERS COUNT LIST", nav: "Enquiry & Joiners Count", bg: "#ffffff", student: true, ready: true },
	{ key: "admin_total", dashboard: "admin", path: "total-students", title: "TOTAL STUDENTS COUNT LIST", nav: "Total Students Count", bg: "#ffffcc", student: true, ready: true },
	{ key: "admin_actual", dashboard: "admin", path: "actual-students", title: "ACTUAL STUDENTS COUNT LIST", nav: "Actual Students Count", bg: "#e8f5e0", student: true, ready: true },
	{ key: "admin_discontinued", dashboard: "admin", path: "discontinued", title: "DISCONTINUED STUDENTS COUNT", nav: "Discontinued Students", bg: "#fdf0ec", student: true, ready: true },

	// "ASSISTANT MANAGER TARGET CHART - 2026" PDF: posting staff mistakes
	{ key: "am_weekly", dashboard: "asst_manager", path: "weekly", title: "POSTING STAFF - LAST 2 PLACES - WEEKLY REPORT", nav: "Weekly Report", bg: "#d6ece0", ready: true },
	{ key: "am_monthly", dashboard: "asst_manager", path: "monthly", title: "POSTING STAFF - LAST 2 PLACES - MONTHLY REPORT", nav: "Monthly Report", bg: "#dfe4f2", ready: true },
	{ key: "am_ten_plus", dashboard: "asst_manager", path: "ten-plus", title: "POSTING STAFF - 10+ MISTAKE - MONTHLY REPORT", nav: "10+ Mistake", bg: "#fffbd6", ready: true },

	// "TL - TARGET 6th TO 12th STD - Girls - 2026" PDF: student mistakes
	{ key: "tl_weekly", dashboard: "tl", path: "weekly", title: "LAST 2 PLACE - WEEKLY REPORT", nav: "Weekly Report", bg: "#fffbd1", student: true, ready: true },
	{ key: "tl_monthly", dashboard: "tl", path: "monthly", title: "LAST 2 PLACE - MONTHLY REPORT", nav: "Monthly Report", bg: "#d6eef3", student: true, ready: true },
	{ key: "tl_ten_plus", dashboard: "tl", path: "ten-plus", title: "10+ MISTAKE - MONTHLY REPORT", nav: "10+ Mistake", bg: "#f8d3e5", student: true, ready: true },
	{ key: "tl_discontinued", dashboard: "tl", path: "discontinued", title: "DISCONTINUE STUDENTS", nav: "Discontinue Students", bg: "#d6eef3", student: true, ready: true },
]

export const reportsOf = (dashboard: Dashboard) => REPORTS.filter((r) => r.dashboard === dashboard)

export const reportByPath = (dashboard: Dashboard, path: string) =>
	REPORTS.find((r) => r.dashboard === dashboard && r.path === path)

const ROUTE_NAMES: Record<Dashboard, string> = {
	manager: "report",
	admin: "admin-report",
	asst_manager: "asst-manager-report",
	tl: "tl-report",
}

export const routeName = (dashboard: Dashboard) => ROUTE_NAMES[dashboard]

/** The TL register is printed per gender, Girls first: opening it without a gender picks Girls. */
export const defaultQuery = (dashboard: Dashboard): Record<string, string> => (dashboard === "tl" ? { gender: "Girls" } : {})
