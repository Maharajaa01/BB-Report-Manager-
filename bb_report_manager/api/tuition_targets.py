"""TL Target Chart -- 6th to 12th STD student mistakes, read on the tuition site.

The "TL - TARGET 6th TO 12th STD" register, one sheet per report:

	tl_weekly        Last 2 Place (with Total Mistake) - Weekly Report, 4 weeks of the month
	tl_monthly       Last 2 Place (with Total Mistake) - Monthly Report
	tl_ten_plus      10+ Mistake - Monthly Report
	tl_discontinued  Discontinue Students, STD x month

Rows are the nine standards (6th ... 12th Sci). A mistake is:

	Discipline          Student Performance Tracker, Behaviour graded Discipline
	Critical            Behaviour graded Critical
	Attendance (Leave)  Student Attendance marked Absent
	Study               Study graded Incomplete
	Test                Test graded Fail
	Home Work (Fail)    H.W graded Not Done

Mistakes are counted against the standard and batch the student was in on the
day (the tracker and attendance rows record both). The register is printed for
Girls; the Gender filter picks the sheet, and no gender means both.
"""

from collections import Counter

import frappe
from frappe import _
from frappe.utils import getdate, today

from bb_report_manager.api.common import check_access, get_month_columns, parse_filters, serialize_columns
from bb_report_manager.api.targets import (
	Grid,
	build_insights,
	month_weeks,
	pick_month,
	serialize_period,
	ten_plus,
	week_of,
)
from bb_report_manager.api.tuition_admin import batch_breakdown, in_batch, leaving_reasons, period_label
from bb_report_manager.api.tuition import (
	GENDERS,
	_as_list,
	_detail_sort,
	_get_academic_year,
	_get_enrolment_periods,
	_require_tuition_site,
	_student_detail,
	_year_label,
)

CATEGORIES = [
	{"key": "discipline", "label": "Discipline"},
	{"key": "critical", "label": "Critical"},
	{"key": "leave", "label": "Attendance (Leave)"},
	{"key": "study", "label": "Study"},
	{"key": "test", "label": "Test"},
	{"key": "homework", "label": "Home Work (Fail)"},
]

# (tracker category, result) -> register column
TRACKER_MISTAKES = {
	("Behaviour", "Discipline"): "discipline",
	("Behaviour", "Critical"): "critical",
	("Study", "Incomplete"): "study",
	("Test", "Fail"): "test",
	("H.W", "Not Done"): "homework",
}

# The 10+ sheet's four lists. Critical is a behaviour grade, so it counts
# towards Discipline (as in the student's own monthly mistake record).
TEN_PLUS_GROUPS = [
	{"key": "discipline", "label": "10+ Discipline mistake", "categories": {"discipline", "critical"}},
	{"key": "leave", "label": "10+ Attendance mistake", "categories": {"leave"}},
	{"key": "study_test", "label": "10+ Study & Test mistake", "categories": {"study", "test"}},
	{"key": "homework", "label": "10+ Home Work mistake", "categories": {"homework"}},
]

GROUP_SHORT = {"Commerce": "Com", "Science": "Sci"}


# ------------------------------------------------------------------ rows


def _std_label(std):
	"""'11TH Commerce' -> '11th Com', '6TH' -> '6th'"""
	label = std.name.split()[0].lower()
	short = GROUP_SHORT.get(std.group or "")
	return f"{label} {short}" if short else label


class Context:
	def __init__(self, filters):
		check_access()
		_require_tuition_site()
		self.filters = parse_filters(filters)
		self.year = _get_academic_year(self.filters.academic_year)
		self.today = getdate(today())

		std_filters = {"is_active": 1}
		if self.filters.standard:
			std_filters["name"] = ("in", _as_list(self.filters.standard))
		elif self.year.standards:
			std_filters["name"] = ("in", self.year.standards)
		self.standards = frappe.get_all(
			"Standard",
			filters=std_filters,
			fields=["name", "group", "academic_order"],
			order_by="academic_order asc, `group` asc",
		)
		self.rows = [{"key": s.name, "label": _std_label(s)} for s in self.standards]
		self.std_label = {s.name: _std_label(s) for s in self.standards}
		self.genders = _as_list(self.filters.gender) if self.filters.gender else GENDERS

	@property
	def gender_label(self):
		return " & ".join(self.genders) if len(self.genders) > 1 else self.genders[0]

	def head(self, report, title):
		return {
			"report": report,
			"title": title,
			"subtitle": f"6th to 12th STD - {self.gender_label}",
			"academic_year": self.year.name,
			"academic_year_label": _year_label(self.year),
			"generated_on": str(self.today),
		}

	def month(self):
		return pick_month(self.year.start_date, self.year.end_date, self.filters.month)

	def mistakes(self, start, end):
		"""Every mistake in [start, end]: (student, standard, batch, date, category) rows."""
		if not self.standards:
			return []
		values = {
			"start": start,
			"end": min(getdate(end), self.today),
			"standards": [s.name for s in self.standards],
			"genders": self.genders,
			"results": sorted({r for _c, r in TRACKER_MISTAKES}),
		}
		batch_cond = ""
		if self.filters.batch:
			values["batches"] = _as_list(self.filters.batch)
			batch_cond = "and x.batch in %(batches)s"

		tracker = frappe.db.sql(
			f"""
			select x.student, x.standard, x.batch, x.date, x.category, x.result
			from `tabStudent Performance Tracker` x
			join `tabStudent` s on s.name = x.student
			where x.date between %(start)s and %(end)s
				and x.result in %(results)s
				and x.standard in %(standards)s
				and s.gender in %(genders)s
				{batch_cond}
			""",
			values,
			as_dict=True,
		)
		absent = frappe.db.sql(
			f"""
			select x.student, x.standard, x.batch, x.attendance_date as date
			from `tabStudent Attendance` x
			join `tabStudent` s on s.name = x.student
			where x.attendance_date between %(start)s and %(end)s
				and x.status = 'Absent'
				and x.docstatus < 2
				and x.standard in %(standards)s
				and s.gender in %(genders)s
				{batch_cond}
			""",
			values,
			as_dict=True,
		)

		out = []
		for r in tracker:
			cat = TRACKER_MISTAKES.get((r.category, r.result))
			if cat:
				out.append(frappe._dict(r, category=cat))
		out.extend(frappe._dict(r, category="leave") for r in absent)
		return out

	def people(self, events):
		"""Student id -> {id, name, sub}; sub is the student's latest standard and batch in the period."""
		ids = sorted({e.student for e in events})
		students = {
			r.name: r
			for r in frappe.get_all("Student", filters={"name": ("in", ids)}, fields=["name", "student_name", "current_batch"])
		} if ids else {}
		names = {k: v.student_name for k, v in students.items()}
		latest, batches = {}, {}
		for e in sorted(events, key=lambda e: e.date):
			latest[e.student] = e
			if e.batch:  # some attendance rows carry no batch
				batches[e.student] = e.batch
		out = {}
		for sid in ids:
			std = self.std_label.get(latest[sid].standard, latest[sid].standard)
			batch = batches.get(sid) or (students[sid].current_batch if sid in students else "") or ""
			out[sid] = {
				"id": sid,
				"name": (names.get(sid) or sid).strip(),
				"detail": f"{std} - {batch}" if batch else std,
			}
		return out


def _load(ctx):
	"""The sheet's month, its mistakes, and the year's mistakes for the detail under the sheet."""
	month = ctx.month()
	year_events = ctx.mistakes(ctx.year.start_date, ctx.year.end_date)
	people = ctx.people(year_events)
	events = [e for e in year_events if month["start"] <= getdate(e.date) <= month["end"]]
	insights = build_insights(
		[
			# Grouped under the student's latest known STD - batch: attendance rows often carry no batch.
			(e.student, e.category, getdate(e.date), people[e.student]["detail"])
			for e in year_events
		],
		month,
		get_month_columns(ctx.year.start_date, ctx.year.end_date),
		CATEGORIES,
		people,
		TEN_PLUS_GROUPS,
		ctx.today,
	)
	insights["group_head"] = "STD - Batch"
	return month, events, people, insights


def _grid_response(ctx, report, title, period_label, tables):
	return {
		**ctx.head(report, title),
		"period": period_label,
		"row_head": "STD",
		"categories": CATEGORIES,
		"tables": tables,
	}


# ------------------------------------------------------------------ endpoints


@frappe.whitelist()
def get_tl_weekly(filters=None):
	ctx = Context(filters)
	month, events, people, insights = _load(ctx)
	weeks = month_weeks(month)

	grids = {w["key"]: Grid(CATEGORIES) for w in weeks}
	for e in events:
		wk = week_of(weeks, e.date)
		if wk:
			grids[wk].add(e.standard, e.category, e.student)

	tables = [
		{**serialize_period(w), "future": w["start"] > ctx.today, **grids[w["key"]].build(ctx.rows, people)}
		for w in weeks
	]
	return {
		**_grid_response(
			ctx,
			"tl_weekly",
			"Last 2 Place (with Total Mistake) - Weekly Report",
			f"{month['month']} {month['year']}",
			tables,
		),
		"insights": insights,
	}


@frappe.whitelist()
def get_tl_monthly(filters=None):
	ctx = Context(filters)
	month, events, people, insights = _load(ctx)
	grid = Grid(CATEGORIES)
	for e in events:
		grid.add(e.standard, e.category, e.student)
	label = f"{month['month']} {month['year']}"
	table = {"key": month["key"], "label": label, "start": str(month["start"]), "end": str(month["end"]),
		"future": month["start"] > ctx.today, **grid.build(ctx.rows, people)}
	return {
		**_grid_response(ctx, "tl_monthly", "Last 2 Place (with Total Mistake) - Monthly Report", label, [table]),
		"insights": insights,
	}


@frappe.whitelist()
def get_tl_ten_plus(filters=None):
	ctx = Context(filters)
	month, events, people, insights = _load(ctx)
	per_person = Counter((e.student, e.category) for e in events)
	return {
		**ctx.head("tl_ten_plus", "10+ Mistake - Monthly Report"),
		"period": f"{month['month']} {month['year']}",
		"sub_head": "STD & Batch",
		"lists": ten_plus(per_person, TEN_PLUS_GROUPS, people),
		"insights": insights,
	}


# ------------------------------------------------------------------ discontinued


def _discontinued_students(ctx):
	if not ctx.standards:
		return [], {}
	values = {"standards": [s.name for s in ctx.standards], "genders": ctx.genders}
	batch_cond = ""
	if ctx.filters.batch:
		values["batches"] = _as_list(ctx.filters.batch)
		batch_cond = "and s.current_batch in %(batches)s"
	students = frappe.db.sql(
		f"""
		select s.name, s.student_name, s.standard, s.gender, s.current_batch, s.status,
			s.admission_date, s.discontinued__date, s.suspended_date, s.rejoined_date,
			s.discontinue_reason_category, s.discontinued_reason, s.school_name, s.area,
			s.father_name, s.preferred_mobile_number, s.father_mobile_number,
			s.mother_mobile_number, s.guardian_mobile_number, s.monthly_fee, s.scholarship_student
		from `tabStudent` s
		where s.admission_date is not null
			and s.standard in %(standards)s
			and s.gender in %(genders)s
			{batch_cond}
		""",
		values,
		as_dict=True,
	)
	return students, _get_enrolment_periods(students)


def _left_in(spans, month):
	return any(end is not None and month["start"] <= end <= month["end"] for _start, end in spans)


@frappe.whitelist()
def get_tl_discontinued(filters=None):
	"""Shaped like an Admin count sheet (one section), so the dashboard reuses it."""
	ctx = Context(filters)
	months = get_month_columns(ctx.year.start_date, ctx.year.end_date, ctx.filters.month)
	students, periods = _discontinued_students(ctx)

	rows = []
	for idx, row in enumerate(ctx.rows, 1):
		mine = [s for s in students if s.standard == row["key"]]
		values = {
			m["key"]: (None if m["start"] > ctx.today else sum(1 for s in mine if _left_in(periods[s.name], m)))
			for m in months
		}
		rows.append({"key": row["key"], "label": row["label"].upper(), "standard": row["key"], "gender": ctx.gender_label,
			"group": "", "idx": idx, "values": values, **_highest(values)})

	totals = {m["key"]: (None if m["start"] > ctx.today else sum(r["values"][m["key"]] or 0 for r in rows)) for m in months}
	head = ctx.head("admin_discontinued", f"6th to 12th STD - {ctx.gender_label} - Discontinue Students".upper())
	elapsed = [m for m in months if m["start"] <= ctx.today]
	extra = {}
	if elapsed:
		left = [s for s in students if any(_left_in(periods[s.name], m) for m in elapsed)]
		extra["batch_breakdown"] = batch_breakdown(
			left, [r["key"] for r in ctx.rows], "", period_label(elapsed, ctx.today), ctx.filters.batch
		)
		extra["reasons"] = leaving_reasons(left)
	return {
		**head,
		**extra,
		"subtitle": "STD WISE & MONTH WISE",
		"columns": serialize_columns(months),
		"sections": [{"key": "tl", "label": f"6th To 12th Std - {ctx.gender_label}", "rows": rows,
			"totals": {"values": totals, **_highest(totals)}}],
	}


def _highest(values):
	best_key, best = None, None
	for key, v in values.items():
		if v is not None and (best is None or v > best):
			best_key, best = key, v
	return {"highest": best, "highest_month": best_key if best else None}


@frappe.whitelist()
def get_tl_discontinued_detail(filters=None, row_key=None, month_key=None, kind=None, section=None, batch=None):
	ctx = Context(filters)
	months = [
		m for m in get_month_columns(ctx.year.start_date, ctx.year.end_date, ctx.filters.month)
		if m["start"] <= ctx.today and (not month_key or m["key"] == month_key)
	]
	students, periods = _discontinued_students(ctx)
	picked = [
		s for s in students
		if (not row_key or s.standard == row_key)
		and in_batch(s, batch)
		and any(_left_in(periods[s.name], m) for m in months)
	]
	month = months[0] if len(months) == 1 else None
	return {"type": "student", "rows": [_student_detail(s, periods[s.name], month) for s in sorted(picked, key=_detail_sort)]}
