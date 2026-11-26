"""Manager Charts 5 - 9, read on the ERP site ("Manager wiro" register):

	kpi_points             KPI POINTS - POSTING STAFF'S - MONTH WISE
	                       penalty points from BB Performance Manager's ranking engine
	                       (lower is better), one row per posting role
	staff_count            STAFF'S COUNT - MONTH WISE: staff employed on any day of the
	                       month, by kind (posting / subject / morning / evening / internship / other)
	work_mistakes          POSTING STAFF'S WORK LIST MISTAKES - MONTH WISE: missed
	                       Employee Worklist Entries, per staff, split Daily / Weekly / Monthly
	critical_problems      CRITICAL PROBLEMS - MONTH WISE: Urgent Helpdesk Issues and
	                       Critical Employee Mistakes, listed under the month they arose
	single_sheet_problems  ASST. MANAGER & MANAGER - SINGLE SHEET PROBLEMS: the month's
	                       Helpdesk Issues (complaints and struggles) and whether each is solved

Helpdesk Issues marked "MD Only" are never shown. Each report carries an
`insights` block (see api.insights).
"""

import re
from collections import Counter, defaultdict

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate, time_diff_in_hours, today

from bb_report_manager.api import insights as ins
from bb_report_manager.api.common import check_access, get_month_columns, parse_filters, serialize_columns
from bb_report_manager.api.erp_targets import _academic_year
from bb_report_manager.api.targets import pick_month

TITLES = {
	"kpi_points": "KPI POINTS - POSTING STAFF'S - MONTH WISE",
	"staff_count": "STAFF'S COUNT - MONTH WISE",
	"work_mistakes": "POSTING STAFF'S WORK LIST MISTAKES - MONTH WISE",
	"critical_problems": "CRITICAL PROBLEMS - MONTH WISE",
	"single_sheet_problems": "ASST. MANAGER & MANAGER - SINGLE SHEET PROBLEMS",
}


class Sheet:
	def __init__(self, filters):
		check_access()
		self.filters = parse_filters(filters)
		self.start, self.end = _academic_year(self.filters.academic_year)
		self.today = getdate(today())
		self.months = get_month_columns(self.start, self.end, self.filters.month)
		self.done = ins.started(self.months, self.today)

	def head(self, report, row_head):
		return {
			"report": report,
			"title": TITLES[report],
			"row_head": row_head,
			"academic_year": self.filters.academic_year,
			"academic_year_label": f"{self.start.year} - {self.end.year}",
			"generated_on": str(self.today),
			"columns": serialize_columns(self.months),
		}

	def month_of(self, day):
		day = getdate(day)
		return next((m for m in self.months if m["start"] <= day <= m["end"]), None)


def _grid_rows(sheet, row_defs, value):
	"""row_defs [{key, label}], value(row_key, month) -> n | None."""
	rows = []
	for idx, r in enumerate(row_defs, 1):
		values = {m["key"]: (None if m["start"] > sheet.today else value(r["key"], m)) for m in sheet.months}
		rows.append({**r, "idx": idx, "values": values, "total": ins.n(sum(flt(v) for v in values.values() if v))})
	return rows


def _norm(text):
	return re.sub(r"[^A-Z0-9 ]+", " ", (text or "").upper())


# ------------------------------------------------------------------ employees


def _employees():
	rows = frappe.db.sql(
		"""
		select e.name, e.employee_name, e.designation, e.department, e.default_shift, e.status,
			e.date_of_joining, e.relieving_date, e.employment_type, s.start_time, s.end_time
		from `tabEmployee` e
		left join `tabShift Type` s on s.name = e.default_shift
		""",
		as_dict=True,
	)
	for r in rows:
		r.kind = _staff_kind(r)
	return rows


def _employed_in(e, month):
	"""Employed on any day of the month (the Performance Manager's eligibility rule)."""
	if e.date_of_joining and getdate(e.date_of_joining) > month["end"]:
		return False
	if e.relieving_date and getdate(e.relieving_date) < month["start"]:
		return False
	return e.status == "Active" or bool(e.relieving_date)


def _hours(t):
	if t is None:
		return None
	return t.total_seconds() / 3600 if hasattr(t, "total_seconds") else None


STAFF_KINDS = [
	("posting", "Posting Staff"),
	("subject", "Subject Staff"),
	("morning", "Morning Staff"),
	("evening", "Evening Staff"),
	("internship", "Internship Staff"),
	("other", "Other Staff"),
]


def _staff_kind(e):
	"""First match wins: department first, then designation, then the shift's hours."""
	dept, desig = _norm(e.department), _norm(e.designation)
	start, end = _hours(e.start_time), _hours(e.end_time)
	if "POSTING" in dept:
		return "posting"
	if "INTERN" in dept or "INTERN" in desig:
		return "internship"
	if "MORNING" in dept or (end is not None and end <= 12.5):
		return "morning"
	if "SUBJECT" in desig or ("TEACH" in desig and "NON TEACH" not in desig):
		return "subject"
	if start is not None and start >= 14:
		return "evening"
	return "other"


EMPLOYEE_COLUMNS = [
	ins.col("employee_name", "Staff", kind="link"),
	ins.col("designation", "Designation"),
	ins.col("department", "Department"),
	ins.col("shift", "Shift"),
	ins.col("joined", "Joined", kind="date"),
	ins.col("relieved", "Relieved", kind="date"),
	ins.col("status", "Status"),
]


def _employee_row(e):
	return {
		"employee_name": e.employee_name,
		"link": f"/app/employee/{e.name}",
		"designation": e.designation,
		"department": e.department,
		"shift": e.default_shift,
		"joined": e.date_of_joining,
		"relieved": e.relieving_date,
		"status": e.status,
	}


@frappe.whitelist()
def get_staff_count(filters=None):
	sheet = Sheet(filters)
	staff = _employees()
	employed = {m["key"]: [e for e in staff if _employed_in(e, m)] for m in sheet.done}

	def value(kind, m):
		return sum(1 for e in employed[m["key"]] if e.kind == kind)

	rows = _grid_rows(sheet, [{"key": k, "label": label} for k, label in STAFF_KINDS], value)
	# TOTAL column: distinct staff across the months, not a sum of monthly heads.
	for r in rows:
		r["total"] = len({e.name for m in sheet.done for e in employed[m["key"]] if e.kind == r["key"]})
	everyone = {e.name for m in sheet.done for e in employed[m["key"]]}
	totals = ins.grid_totals(rows, sheet.months, sheet.today, distinct_total=len(everyone))

	per_month = {k: len(v) for k, v in employed.items()}
	posting = {k: sum(1 for e in v if e.kind == "posting") for k, v in employed.items()}
	others = {k: per_month[k] - posting[k] for k in per_month}
	joined = {m["key"]: [e for e in staff if e.date_of_joining and m["start"] <= getdate(e.date_of_joining) <= m["end"]] for m in sheet.done}
	left = {m["key"]: [e for e in staff if e.relieving_date and m["start"] <= getdate(e.relieving_date) <= m["end"]] for m in sheet.done}
	cur, _prev = ins.latest_and_prev(sheet.months, sheet.today)
	now = employed.get(cur["key"], []) if cur else []

	movement = []
	for m in sheet.done:
		movement.append({
			"month": ins.month_label(m),
			"staff": per_month[m["key"]],
			"joined": len(joined[m["key"]]),
			"left": len(left[m["key"]]),
			"interns": sum(1 for e in employed[m["key"]] if e.kind == "internship"),
		})

	return {
		**sheet.head("staff_count", "STAFF"),
		"rows": rows,
		"totals": totals,
		"insights": {
			"tiles": [
				ins.delta_tile("Staff", per_month, sheet.months, sheet.today, sub="employed during the month", open_kind="staff"),
				ins.tile("Joined", len(joined[cur["key"]]) if cur else None, ins.month_label(cur) if cur else "",
					open={"kind": "joined", "month": cur["key"]} if cur and joined[cur["key"]] else None),
				ins.tile("Relieved", len(left[cur["key"]]) if cur else None, ins.month_label(cur) if cur else "",
					open={"kind": "left", "month": cur["key"]} if cur and left[cur["key"]] else None),
				ins.tile("Posting staff", posting.get(cur["key"]) if cur else None,
					f"of {len(now)} staff this month" if cur else "",
					open={"kind": "staff", "month": cur["key"], "row": "posting"} if cur else None),
			],
			"chart": ins.chart("Staff per month", ["Posting staff", "Other staff"], sheet.months, sheet.today, posting, others,
				note="Click a month to see who was employed."),
			"bars": [
				ins.bar_list(f"By kind · {ins.month_label(cur)}" if cur else "By kind",
					Counter(dict(STAFF_KINDS)[e.kind] for e in now), {label: k for k, label in STAFF_KINDS}),
				ins.bar_list(f"By department · {ins.month_label(cur)}" if cur else "By department",
					Counter(e.department or "Not set" for e in now)),
			],
			"tables": [
				ins.table("Month by month",
					[ins.col("month", "Month"), ins.col("staff", "Staff", True), ins.col("joined", "Joined", True),
						ins.col("left", "Relieved", True), ins.col("interns", "Interns", True)],
					movement),
			],
		},
	}


# ------------------------------------------------------------------ KPI points

# The register's posting roles, matched on the designation (first match wins).
KPI_ROLES = [
	("in_6_9", "6th To 9th STD - Incharge", lambda d: "INCHARGE" in d and re.search(r"\b6", d) and "9" in d),
	("in_girls", "10th To 12th STD Girls Incharge", lambda d: "INCHARGE" in d and "GIRLS" in d and "10" in d),
	("in_boys", "10th To 12th STD Boys Incharge", lambda d: "INCHARGE" in d and "BOYS" in d and "10" in d),
	("morning", "Morning Incharge", lambda d: "INCHARGE" in d and "MORNING" in d),
	("maths", "Maths Incharge", lambda d: "INCHARGE" in d and "MATHS" in d),
	("schedule", "Schedule Incharge", lambda d: "INCHARGE" in d and "SCHEDULE" in d),
	("admin", "Admin Incharge", lambda d: "INCHARGE" in d and "ADMIN" in d),
	("social", "Social Media Incharge", lambda d: "SOCIAL" in d),
	("tl", "TL - Team Leader", lambda d: d.split() == ["TL"] or "TEAM LEADER" in d),
	("hr", "HR - Human Resource", lambda d: d.split() == ["HR"] or "HUMAN RESOURCE" in d),
	("asst_manager", "Assistant Manager", lambda d: "MANAGER" in d and ("ASST" in d or "ASSISTANT" in d)),
	("manager", "Manager", lambda d: d.split() == ["MANAGER"]),
]


def _role_of(designation):
	d = " ".join(_norm(designation).split())
	return next((key for key, _label, match in KPI_ROLES if match(d)), None)


def _standings(month):
	"""(status, rows) from the Performance Manager for one calendar month."""
	try:
		from bb_performance_manager.services import periods, ranking
	except ImportError:
		frappe.throw(_("KPI points need the BB Performance Manager app on this site"))
	period = periods.month(month["year"], month["start"].month)
	status, rows = ranking.standings(period)
	if status == ranking.NOT_RANKED:
		rows = ranking.compute(period)  # before "Rankings start on": still worth seeing, live
	for r in rows:
		r.role = _role_of(r.designation)
	return status, rows


KPI_COLUMNS = [
	ins.col("rank", "Rank", True),
	ins.col("employee_name", "Staff", kind="link"),
	ins.col("role", "Role"),
	ins.col("points", "Penalty points", True),
	ins.col("mistakes", "Mistakes", True),
]


def _kpi_row(r):
	return {
		"rank": r.get("rank") if r.get("ranked") else None,
		"employee_name": r.employee_name,
		"link": f"/app/employee/{r.employee}",
		"role": dict((k, label) for k, label, _m in KPI_ROLES).get(r.role, r.designation),
		"points": ins.n(r.points),
		"mistakes": r.mistakes,
	}


@frappe.whitelist()
def get_kpi_points(filters=None):
	sheet = Sheet(filters)
	standings = {m["key"]: _standings(m) for m in sheet.done}

	def value(role, m):
		mine = [r for r in standings[m["key"]][1] if r.role == role]
		return ins.n(sum(flt(r.points) for r in mine)) if mine else None

	rows = _grid_rows(sheet, [{"key": k, "label": label} for k, label, _m in KPI_ROLES], value)
	totals = ins.grid_totals(rows, sheet.months, sheet.today)

	points = {k: sum(flt(r.points) for r in rows_ if r.role) for k, (_s, rows_) in standings.items()}
	mistakes = {k: sum(r.mistakes or 0 for r in rows_ if r.role) for k, (_s, rows_) in standings.items()}
	cur, _prev = ins.latest_and_prev(sheet.months, sheet.today)
	status, now = standings[cur["key"]] if cur else ("", [])
	posting = sorted((r for r in now if r.role), key=lambda r: (flt(r.points), r.mistakes or 0, r.employee_name or ""))
	clean = [r for r in posting if not flt(r.points)]

	return {
		**sheet.head("kpi_points", "POSTING"),
		"rows": rows,
		"totals": totals,
		"insights": {
			"tiles": [
				ins.delta_tile("Penalty points", points, sheet.months, sheet.today, higher_is_good=False,
					sub="all posting roles · lower is better", open_kind="kpi", fmt="points"),
				ins.delta_tile("Mistakes", mistakes, sheet.months, sheet.today, higher_is_good=False,
					sub="counted toward KPI"),
				ins.tile("Clean record", len(clean), f"of {len(posting)} posting staff with no penalty points this month"),
				ins.tile("Ranking", status or "–",
					"Final: saved and will not change" if status == "Final" else "live: changes as mistakes are recorded"),
			],
			"chart": ins.chart("Penalty points per month", ["Penalty points", ""], sheet.months, sheet.today, points,
				note="All posting roles together. Click a month for every staff member's points."),
			"bars": [
				ins.bar_list(f"Points by role · {ins.month_label(cur)}" if cur else "Points by role",
					Counter({dict((k, label) for k, label, _m in KPI_ROLES)[r.role]: flt(r.points) for r in posting if flt(r.points)}),
					{label: k for k, label, _m in KPI_ROLES}),
			],
			"tables": [
				ins.table(f"Posting staff standings · {ins.month_label(cur)}" if cur else "Posting staff standings",
					KPI_COLUMNS, [_kpi_row(r) for r in posting], link_key="link", empty="No posting staff found."),
			],
		},
	}


# ------------------------------------------------------------------ work list mistakes

FREQUENCIES = ["Daily", "Weekly", "Monthly"]


def _worklist_entries(sheet):
	rows = frappe.db.sql(
		"""
		select w.name, w.employee, w.employee_name, w.department, w.worklist, w.frequency, w.status,
			w.period_start, w.period_end, w.due_on, w.mistake, w.remarks, e.designation
		from `tabEmployee Worklist Entry` w
		left join `tabEmployee` e on e.name = w.employee
		where w.period_start between %(start)s and %(end)s and w.docstatus < 2
		""",
		{"start": sheet.months[0]["start"], "end": sheet.months[-1]["end"]},
		as_dict=True,
	)
	for r in rows:
		r.month = sheet.month_of(r.period_start)
		r.missed = r.status == "Missed" or bool(r.mistake)
		r.frequency = r.frequency if r.frequency in FREQUENCIES else "Daily"
	return [r for r in rows if r.month]


WORKLIST_COLUMNS = [
	ins.col("period", "For", kind="date"),
	ins.col("employee_name", "Staff", kind="link"),
	ins.col("worklist", "Work"),
	ins.col("frequency", "Frequency"),
	ins.col("status", "Status"),
	ins.col("due_on", "Due", kind="datetime"),
	ins.col("remarks", "Remarks"),
]


def _worklist_row(r):
	return {
		"period": r.period_start,
		"employee_name": r.employee_name,
		"link": f"/app/employee-worklist-entry/{r.name}",
		"worklist": r.worklist,
		"frequency": r.frequency,
		"status": r.status,
		"due_on": r.due_on,
		"remarks": r.remarks,
	}


@frappe.whitelist()
def get_work_mistakes(filters=None):
	sheet = Sheet(filters)
	entries = _worklist_entries(sheet)
	missed = [r for r in entries if r.missed]
	counts = Counter((r.employee, r.month["key"]) for r in missed)
	split = defaultdict(Counter)  # (employee, month) -> frequency -> n
	for r in missed:
		split[(r.employee, r.month["key"])][r.frequency] += 1

	staff = {}
	for r in entries:
		staff.setdefault(r.employee, {"key": r.employee, "label": r.employee_name or r.employee, "designation": r.designation})
	row_defs = sorted(staff.values(), key=lambda s: s["label"].upper())
	rows = _grid_rows(sheet, row_defs, lambda emp, m: counts.get((emp, m["key"]), 0))
	for r in rows:
		r["split"] = {k: dict(split[(r["key"], k)]) for k in r["values"] if split.get((r["key"], k))}
	totals = ins.grid_totals(rows, sheet.months, sheet.today)

	per_month = Counter(r.month["key"] for r in missed)
	daily = Counter(r.month["key"] for r in missed if r.frequency == "Daily")
	longer = Counter(r.month["key"] for r in missed if r.frequency != "Daily")
	cur, _prev = ins.latest_and_prev(sheet.months, sheet.today)
	due_now = [r for r in entries if cur and r.month["key"] == cur["key"] and r.status not in ("Pending", "Excused")]
	done_now = [r for r in due_now if r.status == "Completed"]
	per_staff = defaultdict(Counter)
	for r in missed:
		per_staff[r.employee][r.frequency] += 1

	return {
		**sheet.head("work_mistakes", "STAFF"),
		"rows": rows,
		"totals": totals,
		"insights": {
			"tiles": [
				ins.delta_tile("Missed work", per_month, sheet.months, sheet.today, higher_is_good=False,
					sub="work list entries missed", open_kind="worklist"),
				ins.tile("Done on time", round(100 * len(done_now) / len(due_now)) if due_now else None,
					f"{len(done_now)} of {len(due_now)} entries due this month" if due_now else "no work list entries this month",
					fmt="pct"),
				ins.tile("Staff who missed", len({r.employee for r in missed if cur and r.month["key"] == cur["key"]}),
					ins.month_label(cur) if cur else ""),
				ins.tile("Waiting", sum(1 for r in entries if r.status in ("Pending", "Submitted")), "entries pending or awaiting verification"),
			],
			"chart": ins.chart("Missed work per month", ["Daily works", "Weekly & monthly works"], sheet.months, sheet.today, daily, longer,
				note="Click a month to see every missed entry."),
			"bars": [
				ins.bar_list("Most missed work · this year", Counter(r.worklist or "Not set" for r in missed), limit=10),
				ins.bar_list("By staff · this year", Counter(staff[r.employee]["label"] for r in missed),
					{s["label"]: s["key"] for s in staff.values()}),
			],
			"tables": [
				ins.table("Daily / Weekly / Monthly · this year",
					[ins.col("staff", "Staff"), ins.col("designation", "Designation"),
						*[ins.col(f.lower(), f"{f} works", True) for f in FREQUENCIES], ins.col("total", "Total", True)],
					[{"staff": staff[e]["label"], "designation": staff[e]["designation"],
						**{f.lower(): c[f] for f in FREQUENCIES}, "total": sum(c.values())}
						for e, c in sorted(per_staff.items(), key=lambda kv: -sum(kv[1].values()))],
					empty="No work list entry was missed this year."),
			],
		},
	}


# ------------------------------------------------------------------ problems


def _issues(start, end, urgent_only=False, problems_only=False):
	"""Helpdesk Issues raised in [start, end], never the MD-only ones."""
	conds = ["date(i.creation) between %(start)s and %(end)s", "ifnull(i.visibility, '') != 'MD Only'"]
	if urgent_only:
		conds.append("i.priority = 'Urgent'")
	if problems_only:
		conds.append("ifnull(i.issue_type, '') in ('Complaint', 'Struggle', '')")
	rows = frappe.db.sql(
		f"""
		select i.name, i.subject, i.issue_type, i.priority, i.status, i.department, i.helpdesk_class,
			i.employee_name, i.designation, i.assigned_to_name, i.creation, i.resolved_at, i.due_by,
			i.is_overdue, i.raised_by
		from `tabHelpdesk Issue` i
		where {" and ".join(conds)}
		order by i.creation asc
		""",
		{"start": start, "end": end},
		as_dict=True,
	)
	out = []
	for r in rows:
		out.append(frappe._dict(
			source="Helpdesk",
			date=getdate(r.creation),
			at=r.creation,
			title=r.subject,
			who=r.employee_name or r.raised_by,
			role=r.designation,
			assigned=r.assigned_to_name,
			kind=r.issue_type,
			priority=r.priority,
			department=r.department,
			area=r.helpdesk_class,
			status=r.status,
			solved=r.status == "Resolved",
			solved_at=r.resolved_at,
			overdue=bool(r.is_overdue) and r.status != "Resolved",
			hours=time_diff_in_hours(r.resolved_at, r.creation) if r.resolved_at else None,
			link=f"/app/helpdesk-issue/{r.name}",
		))
	return out


def _critical_mistakes(start, end):
	rows = frappe.db.sql(
		"""
		select m.name, m.employee_name, m.designation, m.department, m.mistake, m.description,
			m.mistake_date, m.resolution_status, m.acknowledgement_status, m.points
		from `tabEmployee Mistake` m
		where m.mistake_date between %(start)s and %(end)s
			and ifnull(m.record_status, 'Active') = 'Active'
			and ifnull(m.resolution_status, '') != 'Withdrawn'
			and lower(ifnull(m.category, '')) like '%%critical%%'
		""",
		{"start": start, "end": end},
		as_dict=True,
	)
	return [
		frappe._dict(
			source="Critical mistake",
			date=getdate(r.mistake_date),
			at=r.mistake_date,
			title=r.mistake + (f": {r.description}" if r.description else ""),
			who=r.employee_name,
			role=r.designation,
			assigned=None,
			kind="Critical mistake",
			priority="Critical",
			department=r.department,
			area=None,
			status=r.acknowledgement_status or "Recorded",
			solved=True,  # a recorded mistake is dealt with by recording it
			solved_at=None,
			overdue=False,
			hours=None,
			link=f"/app/employee-mistake/{r.name}",
		)
		for r in rows
	]


PROBLEM_COLUMNS = [
	ins.col("date", "Date", kind="date"),
	ins.col("title", "Problem", kind="link"),
	ins.col("who", "Posting name"),
	ins.col("kind", "Type"),
	ins.col("status", "Status"),
	ins.col("solved", "Solved", kind="check"),
	ins.col("solved_at", "Solved on", kind="datetime"),
	ins.col("assigned", "Handled by"),
]


def _problem_row(p):
	return {k: p.get(k) for k in ("date", "title", "who", "role", "kind", "status", "solved", "solved_at", "assigned",
		"source", "priority", "overdue", "link")}


def _problem_insights(sheet, items, month, label):
	per_month = Counter(p.date.strftime("%Y-%m") for p in items)
	solved = Counter(p.date.strftime("%Y-%m") for p in items if p.solved)
	open_ = Counter(p.date.strftime("%Y-%m") for p in items if not p.solved)
	mine = [p for p in items if month and month["start"] <= p.date <= month["end"]]
	still_open = [p for p in items if not p.solved]
	hours = [p.hours for p in items if p.hours is not None]
	return {
		"tiles": [
			ins.delta_tile(label, per_month, sheet.months, sheet.today, higher_is_good=False, open_kind="problem")
			if not sheet.filters.month
			else ins.tile(f"{label} · {ins.month_label(month)}", len(mine), open={"kind": "problem", "month": month["key"]}),
			ins.tile("Still open", len(still_open), "raised this year, not solved yet",
				open={"kind": "problem", "month": None, "section": "open"} if still_open else None),
			ins.tile("Overdue", sum(1 for p in still_open if p.overdue), "past their due time",
				open={"kind": "problem", "month": None, "section": "overdue"} if any(p.overdue for p in still_open) else None),
			ins.tile("Hours to solve", round(sum(hours) / len(hours), 1) if hours else None,
				"average, raised to resolved" if hours else "nothing solved yet"),
		],
		"chart": ins.chart(f"{label} per month", ["Solved", "Still open"], sheet.months, sheet.today, solved, open_,
			note="Click a month to see its problems."),
		"bars": [
			ins.bar_list("Raised by · this year", Counter(p.who or "Not set" for p in items), limit=10),
			ins.bar_list("By area · this year", Counter(p.area or p.department or p.source for p in items), limit=10),
		],
		"tables": [
			ins.table("Open problems, oldest first", PROBLEM_COLUMNS[:5] + [PROBLEM_COLUMNS[7]],
				[_problem_row(p) for p in still_open], link_key="link", empty="Every problem is solved."),
		],
		"_per_month": per_month,
	}


def _critical_items(sheet):
	start, end = sheet.months[0]["start"], sheet.months[-1]["end"]
	return sorted(_issues(start, end, urgent_only=True) + _critical_mistakes(start, end), key=lambda p: str(p.at))


@frappe.whitelist()
def get_critical_problems(filters=None):
	sheet = Sheet(filters)
	items = _critical_items(sheet)
	by_month = defaultdict(list)
	for p in items:
		by_month[p.date.strftime("%Y-%m")].append(_problem_row(p))
	cur, _prev = ins.latest_and_prev(sheet.months, sheet.today)
	insights = _problem_insights(sheet, items, cur, "Critical problems")
	insights.pop("_per_month")
	insights["bars"].insert(0, ins.bar_list("By source · this year", Counter(
		"Urgent helpdesk issue" if p.source == "Helpdesk" else "Critical staff mistake" for p in items)))
	return {
		**sheet.head("critical_problems", ""),
		"items": {m["key"]: by_month.get(m["key"], []) for m in sheet.months},
		"future": [m["key"] for m in sheet.months if m["start"] > sheet.today],
		"insights": insights,
	}


@frappe.whitelist()
def get_single_sheet_problems(filters=None):
	sheet = Sheet(filters)
	month = pick_month(sheet.start, sheet.end, sheet.filters.month)
	items = _issues(sheet.months[0]["start"], sheet.months[-1]["end"], problems_only=True)
	mine = [p for p in items if month["start"] <= p.date <= month["end"]]
	insights = _problem_insights(sheet, items, month, "Problems")
	insights.pop("_per_month")
	insights["bars"].insert(0, ins.bar_list(f"Type · {ins.month_label(month)}", Counter(p.kind or "Not set" for p in mine)))
	return {
		**sheet.head("single_sheet_problems", ""),
		"period": ins.month_label(month),
		"month_key": month["key"],
		"rows": [_problem_row(p) for p in mine],
		"insights": insights,
	}


# ------------------------------------------------------------------ drill-down


@frappe.whitelist()
def get_manager_detail(report=None, filters=None, row_key=None, month_key=None, kind=None, batch=None, section=None):
	sheet = Sheet(filters)
	months = [m for m in sheet.done if not month_key or m["key"] == month_key]
	if not months:
		return {"type": "table", "site": "erp", "columns": [], "rows": []}
	start, end = months[0]["start"], months[-1]["end"]

	if kind in ("staff", "joined", "left"):
		staff = _employees()
		if kind == "staff":
			picked = {e.name: e for m in months for e in staff if _employed_in(e, m) and (not row_key or e.kind == row_key)}
		else:
			field = "date_of_joining" if kind == "joined" else "relieving_date"
			picked = {e.name: e for e in staff if e.get(field) and start <= getdate(e.get(field)) <= end}
		rows = [_employee_row(e) for e in sorted(picked.values(), key=lambda e: (e.employee_name or "").upper())]
		for r, e in zip(rows, sorted(picked.values(), key=lambda e: (e.employee_name or "").upper())):
			r["kind"] = dict(STAFF_KINDS)[e.kind]
		return {"type": "table", "site": "erp", "columns": [*EMPLOYEE_COLUMNS[:3], ins.col("kind", "Counted as"), *EMPLOYEE_COLUMNS[3:]],
			"rows": rows, "link_key": "link"}

	if kind == "kpi":
		rows = []
		for m in months:
			_status, standing = _standings(m)
			for r in standing:
				if r.role and (not row_key or r.role == row_key):
					rows.append({**_kpi_row(r), "month": ins.month_label(m)})
		rows.sort(key=lambda r: (r["month"], -flt(r["points"])))
		return {"type": "table", "site": "erp", "columns": [ins.col("month", "Month"), *KPI_COLUMNS], "rows": rows, "link_key": "link"}

	if kind == "worklist":
		picked = [r for r in _worklist_entries(sheet) if r.missed and start <= r.month["start"] <= end and (not row_key or r.employee == row_key)]
		return {"type": "table", "site": "erp", "columns": WORKLIST_COLUMNS,
			"rows": [_worklist_row(r) for r in sorted(picked, key=lambda r: (str(r.period_start), r.employee_name or ""))], "link_key": "link"}

	if kind == "problem":
		if report == "critical_problems":
			items = [p for p in _critical_items(sheet) if start <= p.date <= end]
		else:
			items = _issues(start, end, problems_only=True)
		if section == "open":
			items = [p for p in items if not p.solved]
		elif section == "overdue":
			items = [p for p in items if p.overdue]
		return {"type": "table", "site": "erp", "columns": PROBLEM_COLUMNS, "rows": [_problem_row(p) for p in items], "link_key": "link"}

	frappe.throw(_("Unknown detail type {0}").format(kind))
