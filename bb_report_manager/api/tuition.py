"""Report APIs that read the tuition site's own data (Student, Fee Invoice,
Parent Complaint ...). Installed and called on bbacademy.dreamtechsolution.com;
the dashboard on the ERP site reaches them through api.dashboard.

Every student report takes the same filters:
	academic_year (required), month, standard, batch, gender
"""

import re

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today

from bb_report_manager.api.common import (
	check_access,
	get_month_columns,
	parse_filters,
	serialize_columns,
)

GENDERS = ["Boys", "Girls"]


def _require_tuition_site():
	if not frappe.db.exists("DocType", "Student"):
		frappe.throw(_("Student data is not available on this site"))


# ---------------------------------------------------------------- filters


@frappe.whitelist()
def get_filter_options():
	check_access()
	_require_tuition_site()

	years = frappe.get_all(
		"Academic Year",
		fields=["name", "start_date", "end_date", "is_active"],
		order_by="start_date desc, name asc",
	)
	# The master year is named like "2026-2027"; the others are per-standard sub years.
	default = next(
		(y.name for y in years if y.is_active and re.fullmatch(r"\d{4}\s*-\s*\d{4}", y.name)),
		years[0].name if years else None,
	)

	return {
		"academic_years": years,
		"default_academic_year": default,
		"standards": frappe.get_all(
			"Standard",
			filters={"is_active": 1},
			fields=["name", "group", "academic_order"],
			order_by="academic_order asc, name asc",
		),
		"batches": frappe.get_all(
			"Batch", filters={"is_active": 1}, fields=["name"], order_by="display_order asc, name asc"
		),
		"genders": GENDERS,
	}


def _get_academic_year(name):
	if not name:
		frappe.throw(_("Academic Year is required"))
	year = frappe.db.get_value(
		"Academic Year", name, ["name", "start_date", "end_date"], as_dict=True
	)
	if not year:
		frappe.throw(_("Academic Year {0} not found").format(name))
	year.standards = frappe.get_all(
		"Standard Detail",
		filters={"parenttype": "Academic Year", "parent": name},
		pluck="standard",
	)
	return year


# ------------------------------------------------------------------ rows


def _row_label(standard, gender):
	"""'6TH STD - GIRLS', '11TH SCIENCE - BOYS' -- as written on the manager chart."""
	name = standard.name.upper()
	if standard.group in (None, "", "General"):
		name = f"{name} STD"
	return f"{name} - {gender.upper()}"


def _get_rows(filters, year):
	"""Standard x Gender rows in chart order: General standards list Girls
	first, Science/Commerce list Boys first (as on the printed chart)."""
	std_filters = {"is_active": 1}
	if filters.standard:
		std_filters["name"] = ("in", _as_list(filters.standard))
	elif year.standards:
		std_filters["name"] = ("in", year.standards)

	standards = frappe.get_all(
		"Standard",
		filters=std_filters,
		fields=["name", "group", "academic_order"],
		order_by="academic_order asc, `group` desc",
	)

	genders = _as_list(filters.gender) if filters.gender else GENDERS
	rows = []
	for std in standards:
		order = ["Girls", "Boys"] if std.group in (None, "", "General") else ["Boys", "Girls"]
		for gender in order:
			if gender in genders:
				rows.append(
					{
						"key": f"{std.name}|{gender}",
						"label": _row_label(std, gender),
						"standard": std.name,
						"gender": gender,
					}
				)
	return rows


def _as_list(value):
	if isinstance(value, (list, tuple)):
		return list(value)
	return [v.strip() for v in str(value).split(",") if v.strip()]


# --------------------------------------------- report 1: actual students
#
# Each student is reduced to enrolment spans [(start, end_or_None), ...].
# From those spans every number on the page is derived the same way, so the
# grid, the summary tiles, the movement table and the drill-downs always agree:
#
#   present in month M   start <= M.end   and (end is None or end >= M.start)
#   enrolled at close of day D   start <= D and (end is None or end > D)
#   joined / rejoined in M   a span (first / later) starts in M
#   discontinued in M        a span ends in M


def _get_students(filters, rows):
	conditions = ["s.admission_date is not null"]
	values = {}

	standards = sorted({r["standard"] for r in rows})
	if not standards:
		return []
	conditions.append("s.standard in %(standards)s")
	values["standards"] = standards

	conditions.append("s.gender in %(genders)s")
	values["genders"] = sorted({r["gender"] for r in rows})

	if filters.batch:
		conditions.append("s.current_batch in %(batches)s")
		values["batches"] = _as_list(filters.batch)

	return frappe.db.sql(
		f"""
		select s.name, s.student_name, s.standard, s.gender, s.current_batch,
			s.status, s.admission_date, s.discontinued__date, s.suspended_date,
			s.rejoined_date, s.discontinue_reason_category, s.discontinued_reason,
			s.school_name, s.area, s.father_name, s.preferred_mobile_number,
			s.father_mobile_number, s.mother_mobile_number, s.guardian_mobile_number,
			s.monthly_fee, s.scholarship_student, s.yearly_fees_student, s.academic_year
		from `tabStudent` s
		where {" and ".join(conditions)}
		""",
		values,
		as_dict=True,
	)


def _get_enrolment_periods(students):
	"""Spans each student was enrolled: [(start, end_or_None), ...].

	A student is enrolled from admission until discontinued (or suspended).
	Every Student Rejoin Log closes one earlier span at its discontinued date
	and opens a new one at its rejoined date.
	"""
	if not students:
		return {}

	rejoins = {}
	for r in frappe.get_all(
		"Student Rejoin Log",
		filters={"student": ("in", [s.name for s in students])},
		fields=["student", "discontinued_date", "rejoined_date"],
		order_by="rejoined_date asc",
	):
		rejoins.setdefault(r.student, []).append(r)

	periods = {}
	for s in students:
		spans = []
		start = getdate(s.admission_date)
		for r in rejoins.get(s.name, []):
			if r.discontinued_date and r.rejoined_date:
				spans.append((start, getdate(r.discontinued_date)))
				start = getdate(r.rejoined_date)

		end = None
		if s.status == "Discontinued":
			end = getdate(s.discontinued__date) if s.discontinued__date else start
		elif s.status == "Suspended" and s.suspended_date:
			end = getdate(s.suspended_date)
		spans.append((start, end))
		periods[s.name] = spans
	return periods


def _present_in(spans, month):
	"""Enrolled at any point during the month."""
	return any(start <= month["end"] and (end is None or end >= month["start"]) for start, end in spans)


def _enrolled_on(spans, day):
	"""Still enrolled at the close of `day` (leaving that day means not enrolled)."""
	return any(start <= day and (end is None or end > day) for start, end in spans)


def _in_month(day, month):
	return day is not None and month["start"] <= day <= month["end"]


def _month_events(spans, month):
	"""(joined, rejoined, discontinued) flags for one student in one month."""
	joined = _in_month(spans[0][0], month)
	rejoined = any(_in_month(start, month) for start, _end in spans[1:])
	left = any(_in_month(end, month) for _start, end in spans)
	return joined, rejoined, left


def _closing_day(month, today_date):
	"""Strength is read at month end -- or today for the running month."""
	return min(month["end"], today_date)


class StudentCount:
	"""Everything report 1 shows, computed once per request."""

	def __init__(self, filters):
		_require_tuition_site()
		self.filters = filters
		self.today = getdate(today())
		self.year = _get_academic_year(filters.academic_year)
		self.months = get_month_columns(self.year.start_date, self.year.end_date, filters.month)
		self.elapsed = [m for m in self.months if m["start"] <= self.today]
		self.rows = _get_rows(filters, self.year)
		self.students = _get_students(filters, self.rows)
		self.periods = _get_enrolment_periods(self.students)

	# -- who is in which bucket (shared by the numbers and the drill-downs)

	def present(self, month):
		return [s for s in self.students if _present_in(self.periods[s.name], month)]

	def enrolled_on(self, day):
		return [s for s in self.students if _enrolled_on(self.periods[s.name], day)]

	def opening(self, month):
		return self.enrolled_on(add_days(month["start"], -1))

	def closing(self, month):
		return self.enrolled_on(_closing_day(month, self.today))

	def event(self, month, kind):
		pos = {"joined": 0, "rejoined": 1, "discontinued": 2}[kind]
		return [s for s in self.students if _month_events(self.periods[s.name], month)[pos]]

	def reference_month(self):
		"""Month the batch breakdown and 'current strength' are read for:
		the chosen month, else the latest month that has started."""
		return self.elapsed[-1] if self.elapsed else None

	# -- sections

	def grid(self):
		future = {m["key"] for m in self.months if m["key"] not in {e["key"] for e in self.elapsed}}
		present = {m["key"]: self.present(m) for m in self.elapsed}

		data, all_students = [], set()
		month_totals = {m["key"]: (None if m["key"] in future else 0) for m in self.months}
		for idx, row in enumerate(self.rows, 1):
			values, row_students = {}, set()
			for m in self.months:
				if m["key"] in future:
					values[m["key"]] = None
					continue
				members = [s for s in present[m["key"]] if _row_key(s) == row["key"]]
				values[m["key"]] = len(members)
				month_totals[m["key"]] += len(members)
				row_students.update(s.name for s in members)
			all_students.update(row_students)
			data.append({**row, "idx": idx, "values": values, "total": len(row_students)})

		return data, {"values": month_totals, "total": len(all_students)}

	def movement(self):
		out = []
		for m in self.elapsed:
			joined = len(self.event(m, "joined"))
			rejoined = len(self.event(m, "rejoined"))
			left = len(self.event(m, "discontinued"))
			opening = len(self.opening(m))
			closing = len(self.closing(m))
			out.append(
				{
					"key": m["key"],
					"label": f"{m['month']} {m['year']}",
					"short": m["label"],
					"opening": opening,
					"joined": joined,
					"rejoined": rejoined,
					"discontinued": left,
					"closing": closing,
					"net": closing - opening,
					"present": len(self.present(m)),
					"boys": sum(1 for s in self.closing(m) if s.gender == "Boys"),
					"girls": sum(1 for s in self.closing(m) if s.gender == "Girls"),
					"running": m["end"] > self.today,
				}
			)
		return out

	def summary(self, movement):
		if not movement:
			return None
		first, last = movement[0], movement[-1]
		prev = movement[-2] if len(movement) > 1 else None
		enrolled = sum(1 for s in self.students if any(_present_in(self.periods[s.name], m) for m in self.elapsed))
		left = sum(r["discontinued"] for r in movement)
		return {
			"as_of": last["label"] + (" (till today)" if last["running"] else ""),
			"strength": last["closing"],
			"strength_prev": prev["closing"] if prev else None,
			"strength_prev_label": prev["label"] if prev else None,
			"boys": last["boys"],
			"girls": last["girls"],
			"opening": first["opening"],
			"joined": sum(r["joined"] for r in movement),
			"rejoined": sum(r["rejoined"] for r in movement),
			"discontinued": left,
			"enrolled": enrolled,
			"retention": round(100.0 * (enrolled - left) / enrolled, 1) if enrolled else None,
			"period": f"{first['label']} - {last['label']}",
		}

	def batch_breakdown(self):
		month = self.reference_month()
		if not month:
			return None
		batches = [b for b in frappe.get_all("Batch", filters={"is_active": 1}, order_by="display_order asc", pluck="name")]
		if self.filters.batch:
			batches = [b for b in batches if b in _as_list(self.filters.batch)]

		enrolled = self.closing(month)
		standards = []
		for row in self.rows:
			if row["standard"] not in standards:
				standards.append(row["standard"])

		rows = []
		for std in standards:
			members = [s for s in enrolled if s.standard == std]
			counts = {b: sum(1 for s in members if s.current_batch == b) for b in batches}
			rows.append(
				{
					"standard": std,
					"values": counts,
					"no_batch": sum(1 for s in members if s.current_batch not in batches),
					"boys": sum(1 for s in members if s.gender == "Boys"),
					"girls": sum(1 for s in members if s.gender == "Girls"),
					"total": len(members),
				}
			)
		totals = {
			"values": {b: sum(r["values"][b] for r in rows) for b in batches},
			"no_batch": sum(r["no_batch"] for r in rows),
			"boys": sum(r["boys"] for r in rows),
			"girls": sum(r["girls"] for r in rows),
			"total": sum(r["total"] for r in rows),
		}
		return {
			"month_key": month["key"],
			"label": f"{month['month']} {month['year']}" + (" (till today)" if month["end"] > self.today else ""),
			"batches": batches,
			"rows": rows,
			"totals": totals,
		}


def _row_key(student):
	return f"{student.standard}|{student.gender}"


@frappe.whitelist()
def get_student_count(filters=None):
	"""Report 1 -- ACTUAL STUDENTS COUNT, STD & MONTH WISE.

	Grid: a student counts in a month when enrolled at any point in it
	(admitted on/before the month end, not discontinued before it started;
	rejoined students count again from the rejoin date). Months that have not
	started are blank. Around the grid: summary tiles, month-wise movement
	(opening + joined + rejoined - discontinued = closing) and a
	standard x batch breakdown for the latest month.
	"""
	check_access()
	report = StudentCount(parse_filters(filters))
	rows, totals = report.grid()
	movement = report.movement()

	return {
		"report": "student_count",
		"title": "ACTUAL STUDENTS COUNT - STD & MONTH WISE",
		"academic_year": report.year.name,
		"academic_year_label": _year_label(report.year),
		"generated_on": str(report.today),
		"columns": serialize_columns(report.months),
		"rows": rows,
		"totals": totals,
		"summary": report.summary(movement),
		"movement": movement,
		"batch_breakdown": report.batch_breakdown(),
	}


DETAIL_KINDS = ("present", "opening", "joined", "rejoined", "discontinued", "closing")


@frappe.whitelist()
def get_student_count_detail(filters=None, row_key=None, month_key=None, kind="present", batch=None):
	"""Students behind any number on the report.

	row_key   'STANDARD|Gender' or 'STANDARD|' for all genders of a standard
	month_key 'YYYY-MM'; empty = every elapsed month of the period
	kind      present | opening | joined | rejoined | discontinued | closing
	batch     with kind=closing: one batch ('__none__' = no batch set)
	"""
	check_access()
	if kind not in DETAIL_KINDS:
		frappe.throw(_("Unknown detail type {0}").format(kind))

	report = StudentCount(parse_filters(filters))
	months = [m for m in report.elapsed if not month_key or m["key"] == month_key]

	picked = {}
	for m in months:
		if kind == "present":
			members = report.present(m)
		elif kind == "opening":
			members = report.opening(m)
		elif kind == "closing":
			members = report.closing(m)
		else:
			members = report.event(m, kind)
		for s in members:
			picked[s.name] = s

	students = list(picked.values())
	if row_key:
		std, _sep, gender = row_key.partition("|")
		students = [s for s in students if s.standard == std and (not gender or s.gender == gender)]
	if batch:
		students = [s for s in students if (s.current_batch or "__none__") == batch]

	month = months[0] if len(months) == 1 else None
	return [_student_detail(s, report.periods[s.name], month) for s in sorted(students, key=_detail_sort)]


def _detail_sort(s):
	return (s.standard or "", s.gender or "", (s.student_name or "").upper())


def _student_detail(s, spans, month):
	phone = {
		"Father": s.father_mobile_number,
		"Mother": s.mother_mobile_number,
		"Guardian": s.guardian_mobile_number,
	}.get(s.preferred_mobile_number) or s.father_mobile_number or s.mother_mobile_number or s.guardian_mobile_number

	events = []
	if month:
		joined, rejoined, left = _month_events(spans, month)
		events = [label for flag, label in ((joined, "Joined"), (rejoined, "Rejoined"), (left, "Left")) if flag]

	return {
		"student": s.name,
		"student_name": s.student_name,
		"standard": s.standard,
		"gender": s.gender,
		"batch": s.current_batch,
		"status": s.status,
		"admission_date": s.admission_date,
		# Rejoining clears discontinued__date; the earlier leaving date lives in the rejoin spans.
		"discontinued_date": s.discontinued__date or (spans[-2][1] if len(spans) > 1 else None),
		"rejoined_date": s.rejoined_date,
		"discontinue_reason": s.discontinue_reason_category or s.discontinued_reason,
		"father_name": s.father_name,
		"mobile": phone,
		"school": s.school_name,
		"area": s.area,
		"monthly_fee": s.monthly_fee,
		"scholarship": s.scholarship_student,
		"events": events,
	}


def _year_label(year):
	"""'2026 - 2027' for the chart heading."""
	start, end = getdate(year.start_date), getdate(year.end_date)
	return f"{start.year} - {end.year}" if start.year != end.year else str(start.year)
