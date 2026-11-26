"""Admin dashboard APIs (the "Admin Wiro" registers), read on the tuition site.

Four reports, each split into the three sections the paper registers use:

	junior        6th - 9th STD, Boys and Girls rows
	senior_boys   10th - 12th STD Boys, 11th/12th split by subject group
	senior_girls  10th - 12th STD Girls, the same rows

	admin_enquiry       Enquiry (E) and Joined (J) per month
	admin_total         TOTAL STUDENTS COUNT: admitted on/before the month end,
	                    including students who later left
	admin_actual        ACTUAL STUDENTS COUNT: enrolled on any day of the month
	                    (the same rule as Manager Report 1)
	admin_discontinued  DISCONTINUED STUDENTS COUNT: left during the month

Student-count sheets end in a "Highest Count" column: the peak month in the row.
Filters are the usual: academic_year (required), month, standard, batch, gender.
"""

from collections import Counter

import frappe
from frappe import _
from frappe.utils import getdate, today

from bb_report_manager.api.common import (
	check_access,
	get_month_columns,
	parse_filters,
	serialize_columns,
)
from bb_report_manager.api.tuition import (
	GENDERS,
	_as_list,
	_detail_sort,
	_get_academic_year,
	_get_enrolment_periods,
	_month_events,
	_present_in,
	_require_tuition_site,
	_student_detail,
	_year_label,
)

# Subject groups as the registers abbreviate them.
GROUP_CODES = {
	"Business Maths": "BM",
	"Computer Application": "CA",
	"Biology": "BIO",
	"Computer Science": "CS",
}
# Rows the paper register always prints for 11th and 12th, in its order.
FIXED_GROUPS = [
	("Commerce", "Business Maths"),
	("Commerce", "Computer Application"),
	("Science", "Biology"),
	("Science", "Computer Science"),
]
STATISTICS = "Statistics"
NO_GROUP = ""

SECTIONS = {
	"junior": "6th To 9th Std",
	"senior_boys": "10th To 12th Std - Boys",
	"senior_girls": "10th To 12th Std - Girls",
}

METRICS = {
	"admin_total": "TOTAL STUDENTS COUNT LIST",
	"admin_actual": "ACTUAL STUDENTS COUNT LIST",
	"admin_discontinued": "DISCONTINUED STUDENTS COUNT",
	"admin_enquiry": "ENQUIRY & JOINERS COUNT LIST",
}


# ------------------------------------------------------------------ rows


def _ordinal(standard):
	"""'11TH Commerce' -> '11TH'"""
	return standard.name.split()[0].upper()


def _is_senior(standard):
	return (standard.academic_order or 0) >= 10


def _uses_group(standard):
	"""Only 11th and 12th are split by subject group."""
	return (standard.academic_order or 0) >= 11


def _section_for(standard, gender):
	if not _is_senior(standard):
		return "junior"
	return "senior_boys" if gender == "Boys" else "senior_girls"


def _row_key(standard_name, gender, group=NO_GROUP):
	return f"{standard_name}|{gender}|{group or NO_GROUP}"


def _row_label(standard, gender, group):
	if not _is_senior(standard):
		return f"{_ordinal(standard)} STD - {gender.upper()}"
	if not _uses_group(standard):
		return f"{_ordinal(standard)} STD"
	if group == STATISTICS:
		return f"{_ordinal(standard)} STATISTICS"
	stream = (standard.group or "").upper()
	code = GROUP_CODES.get(group) or (group.upper() if group else "GROUP NOT SET")
	return f"{_ordinal(standard)} {stream} ({code})".replace("  ", " ")


class Layout:
	"""The sections and rows of an admin sheet: the register's fixed rows,
	plus a row for any other group that actually has data."""

	def __init__(self, filters, junior_gender_order):
		self.filters = filters
		std_filters = {"is_active": 1}
		if filters.standard:
			std_filters["name"] = ("in", _as_list(filters.standard))
		self.standards = frappe.get_all(
			"Standard",
			filters=std_filters,
			fields=["name", "group", "academic_order"],
			order_by="academic_order asc, `group` asc",
		)
		self.by_name = {s.name: s for s in self.standards}
		self.genders = _as_list(filters.gender) if filters.gender else GENDERS
		self.junior_gender_order = junior_gender_order

	def key_for(self, standard_name, gender, group):
		std = self.by_name.get(standard_name)
		if not std or gender not in self.genders:
			return None
		return _row_key(std.name, gender, group if _uses_group(std) else NO_GROUP)

	def sections(self, seen_keys):
		"""[{key, label, rows: [{key, label, standard, gender, group}]}] in register order."""
		out = []
		for section, label in SECTIONS.items():
			rows = self._section_rows(section, seen_keys)
			if rows:
				out.append({"key": section, "label": label, "rows": rows})
		return out

	def _section_rows(self, section, seen_keys):
		rows = []

		def add(std, gender, group=NO_GROUP):
			key = _row_key(std.name, gender, group)
			if gender in self.genders and not any(r["key"] == key for r in rows):
				rows.append(
					{
						"key": key,
						"label": _row_label(std, gender, group),
						"standard": std.name,
						"gender": gender,
						"group": group,
					}
				)

		if section == "junior":
			for std in self.standards:
				if not _is_senior(std):
					for gender in self.junior_gender_order:
						add(std, gender)
			return rows

		gender = "Boys" if section == "senior_boys" else "Girls"
		seniors = [s for s in self.standards if _is_senior(s)]
		for std in seniors:
			if not _uses_group(std):
				add(std, gender)
		for order in sorted({s.academic_order for s in seniors if _uses_group(s)}):
			for stream, group in FIXED_GROUPS:
				for std in seniors:
					if std.academic_order == order and std.group == stream:
						add(std, gender, group)
		for std in seniors:
			if std.group == "Commerce" and _uses_group(std):
				add(std, gender, STATISTICS)

		# Any other group (Pure Science, Commerce Group, not set ...) that has data.
		for key in sorted(seen_keys):
			std_name, g, group = key.split("|", 2)
			std = self.by_name.get(std_name)
			if std and _section_for(std, g) == section and _uses_group(std):
				add(std, g, group)
		return rows


# ------------------------------------------------------------------ data


def _students(filters, layout):
	if not layout.standards:
		return []
	conditions = ["s.admission_date is not null", "s.standard in %(standards)s", "s.gender in %(genders)s"]
	values = {"standards": [s.name for s in layout.standards], "genders": layout.genders}
	if filters.batch:
		conditions.append("s.current_batch in %(batches)s")
		values["batches"] = _as_list(filters.batch)
	return frappe.db.sql(
		f"""
		select s.name, s.student_name, s.standard, s.gender, s.`group` as subject_group,
			s.current_batch, s.status, s.admission_date, s.discontinued__date, s.suspended_date,
			s.rejoined_date, s.discontinue_reason_category, s.discontinued_reason,
			s.school_name, s.area, s.father_name, s.preferred_mobile_number,
			s.father_mobile_number, s.mother_mobile_number, s.guardian_mobile_number,
			s.monthly_fee, s.scholarship_student
		from `tabStudent` s
		where {" and ".join(conditions)}
		""",
		values,
		as_dict=True,
	)


def _enquiries(filters, layout, year):
	if not layout.standards:
		return []
	return frappe.db.sql(
		"""
		select e.name, e.enquiry_date, e.status, e.standard, e.gender, e.`group` as subject_group,
			e.applicant_name, e.father_name, e.father_number, e.mother_number, e.guardian_number,
			e.school_name, e.area, e.source, e.remarks, e.next_follow_up_date
		from `tabStudent Enquiry Form` e
		where e.enquiry_date between %(start)s and %(end)s
			and e.standard in %(standards)s and e.gender in %(genders)s
		""",
		{
			"start": year.start_date,
			"end": year.end_date,
			"standards": [s.name for s in layout.standards],
			"genders": layout.genders,
		},
		as_dict=True,
	)


class AdminReport:
	def __init__(self, filters, metric):
		_require_tuition_site()
		if metric not in METRICS:
			frappe.throw(_("Unknown admin report {0}").format(metric))
		self.metric = metric
		self.filters = filters
		self.today = getdate(today())
		self.year = _get_academic_year(filters.academic_year)
		self.months = get_month_columns(self.year.start_date, self.year.end_date, filters.month)
		self.elapsed = [m for m in self.months if m["start"] <= self.today]
		# The enquiry register lists Boys before Girls; the student registers Girls first.
		self.layout = Layout(filters, GENDERS if metric == "admin_enquiry" else ["Girls", "Boys"])
		self.students = _students(filters, self.layout)
		self.periods = _get_enrolment_periods(self.students)
		self.enquiries = _enquiries(filters, self.layout, self.year) if metric == "admin_enquiry" else []

	def student_key(self, s):
		return self.layout.key_for(s.standard, s.gender, s.subject_group)

	def enquiry_key(self, e):
		return self.layout.key_for(e.standard, e.gender, e.subject_group)

	# -- who counts where (shared by numbers and drill-downs)

	def members(self, kind, month):
		"""Students (or enquiries) behind one month's number."""
		if kind == "enquiry":
			return [e for e in self.enquiries if e.enquiry_date and month["start"] <= e.enquiry_date <= month["end"]]
		if kind == "joined":
			return [s for s in self.students if _month_events(self.periods[s.name], month)[0]]
		if kind == "total":
			return [s for s in self.students if self.periods[s.name][0][0] <= month["end"]]
		if kind == "actual":
			return [s for s in self.students if _present_in(self.periods[s.name], month)]
		if kind == "discontinued":
			return [s for s in self.students if _month_events(self.periods[s.name], month)[2]]
		frappe.throw(_("Unknown detail type {0}").format(kind))

	def key_of(self, kind, record):
		return self.enquiry_key(record) if kind == "enquiry" else self.student_key(record)

	def counts(self, kind):
		"""{month_key: Counter(row_key -> n)} for elapsed months."""
		return {m["key"]: Counter(k for r in self.members(kind, m) if (k := self.key_of(kind, r))) for m in self.elapsed}

	# -- sheets

	def build(self):
		kinds = ["enquiry", "joined"] if self.metric == "admin_enquiry" else [self.metric.removeprefix("admin_")]
		counts = {k: self.counts(k) for k in kinds}
		seen = {key for per_month in counts.values() for c in per_month.values() for key in c}
		elapsed = {m["key"] for m in self.elapsed}

		sections = []
		for section in self.layout.sections(seen):
			rows = []
			for idx, row in enumerate(section["rows"], 1):
				rows.append({**row, "idx": idx, **self._row_values(row["key"], counts, kinds, elapsed)})
			sections.append({**section, "rows": rows, "totals": self._totals(rows, kinds)})
		return sections

	def _row_values(self, key, counts, kinds, elapsed):
		if self.metric == "admin_enquiry":
			values = {
				m["key"]: (
					{"e": counts["enquiry"][m["key"]][key], "j": counts["joined"][m["key"]][key]}
					if m["key"] in elapsed
					else None
				)
				for m in self.months
			}
			done = [v for v in values.values() if v]
			return {"values": values, "total": {"e": sum(v["e"] for v in done), "j": sum(v["j"] for v in done)}}

		kind = kinds[0]
		values = {m["key"]: (counts[kind][m["key"]][key] if m["key"] in elapsed else None) for m in self.months}
		return {"values": values, **_highest(values)}

	def _totals(self, rows, kinds):
		if self.metric == "admin_enquiry":
			values = {}
			for m in self.months:
				cells = [r["values"][m["key"]] for r in rows if r["values"][m["key"]] is not None]
				values[m["key"]] = (
					{"e": sum(c["e"] for c in cells), "j": sum(c["j"] for c in cells)} if cells else None
				)
			return {
				"values": values,
				"total": {"e": sum(r["total"]["e"] for r in rows), "j": sum(r["total"]["j"] for r in rows)},
			}
		values = {}
		for m in self.months:
			cells = [r["values"][m["key"]] for r in rows if r["values"][m["key"]] is not None]
			values[m["key"]] = sum(cells) if cells else None
		return {"values": values, **_highest(values)}

	def enquiry_summary(self, sections):
		mine = [e for e in self.enquiries if self.enquiry_key(e)]
		enquiries = sum(s["totals"]["total"]["e"] for s in sections)
		joined = sum(s["totals"]["total"]["j"] for s in sections)
		return {
			"enquiries": enquiries,
			"joined": joined,
			"conversion": round(100.0 * joined / enquiries, 1) if enquiries else None,
			"by_status": _ordered_counts(Counter(e.status or "Not set" for e in mine), ["Open", "Follow-up", "Converted", "Lost"]),
			"by_source": _ordered_counts(Counter(e.source or "Not set" for e in mine), []),
			"no_group": sum(1 for e in mine if e.subject_group in (None, "") and self.layout.by_name[e.standard].academic_order >= 11),
			"period": f"{self.elapsed[0]['month']} {self.elapsed[0]['year']} - {self.elapsed[-1]['month']} {self.elapsed[-1]['year']}"
			if self.elapsed
			else "",
		}


NO_BATCH = "__none__"


def month_label(month, today):
	return f"{month['month']} {month['year']}" + (" (till today)" if month["end"] > today else "")


def period_label(months, today):
	"""'April - November 2026' for a run of months (empty key = the whole period in drill-downs)."""
	first, last = months[0], months[-1]
	return month_label(first, today) if first is last else f"{first['month']} {first['year']} - {month_label(last, today)}"


def batch_breakdown(members, standards, month_key, label, batch_filter=None):
	"""Standard x current batch for a set of students (BatchBreakdown on the dashboard).
	month_key "" means the whole period when a cell is opened."""
	batches = frappe.get_all("Batch", filters={"is_active": 1}, order_by="display_order asc, name asc", pluck="name")
	if batch_filter:
		batches = [b for b in batches if b in _as_list(batch_filter)]
	rows = []
	for std in standards:
		mine = [s for s in members if s.standard == std]
		if not mine:
			continue
		rows.append(
			{
				"standard": std,
				"values": {b: sum(1 for s in mine if s.current_batch == b) for b in batches},
				"no_batch": sum(1 for s in mine if s.current_batch not in batches),
				"boys": sum(1 for s in mine if s.gender == "Boys"),
				"girls": sum(1 for s in mine if s.gender == "Girls"),
				"total": len(mine),
			}
		)
	return {
		"month_key": month_key,
		"label": label,
		"batches": batches,
		"rows": rows,
		"totals": {
			"values": {b: sum(r["values"][b] for r in rows) for b in batches},
			"no_batch": sum(r["no_batch"] for r in rows),
			"boys": sum(r["boys"] for r in rows),
			"girls": sum(r["girls"] for r in rows),
			"total": sum(r["total"] for r in rows),
		},
	}


def leaving_reasons(students):
	"""Why students left: [{label, count}], most common first."""
	counts = Counter((s.discontinue_reason_category or s.discontinued_reason or "Not recorded").strip() for s in students)
	return [{"label": k, "count": n} for k, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def in_batch(student, batch):
	if not batch:
		return True
	if batch == NO_BATCH:
		return not student.current_batch
	return student.current_batch == batch


def _highest(values):
	"""Peak month of a row: {'highest': n, 'highest_month': 'YYYY-MM'} (earliest month on a tie)."""
	best_key, best = None, None
	for key, v in values.items():
		if v is not None and (best is None or v > best):
			best_key, best = key, v
	# A row that never rose above zero has no peak month.
	return {"highest": best, "highest_month": best_key if best else None}


def _ordered_counts(counter, order):
	keys = [k for k in order if k in counter] + sorted(k for k in counter if k not in order)
	return [{"label": k, "count": counter[k]} for k in keys]


# ------------------------------------------------------------------ endpoints


def _report(filters, metric):
	check_access()
	report = AdminReport(parse_filters(filters), metric)
	sections = report.build()
	out = {
		"report": metric,
		"title": METRICS[metric],
		"subtitle": "STD WISE & MONTH WISE" if metric != "admin_enquiry" else "BLACK BUILDING (BB) ACADEMY PVT. LTD.",
		"academic_year": report.year.name,
		"academic_year_label": _year_label(report.year),
		"generated_on": str(report.today),
		"columns": serialize_columns(report.months),
		"sections": sections,
	}
	if metric == "admin_enquiry":
		out["summary"] = report.enquiry_summary(sections)
	elif report.elapsed:
		kind = metric.removeprefix("admin_")
		standards = [std.name for std in report.layout.standards]
		if kind == "discontinued":
			# Few leave in any one month: the detail covers every month so far.
			left = {s.name: s for m in report.elapsed for s in report.members(kind, m) if report.student_key(s)}
			out["batch_breakdown"] = batch_breakdown(
				list(left.values()), standards, "", period_label(report.elapsed, report.today), report.filters.batch
			)
			out["reasons"] = leaving_reasons(left.values())
		else:
			# Strength: the picked month, else the latest one started.
			month = report.elapsed[-1]
			members = [s for s in report.members(kind, month) if report.student_key(s)]
			out["batch_breakdown"] = batch_breakdown(
				members, standards, month["key"], month_label(month, report.today), report.filters.batch
			)
	return out


@frappe.whitelist()
def get_admin_enquiry(filters=None):
	return _report(filters, "admin_enquiry")


@frappe.whitelist()
def get_admin_total(filters=None):
	return _report(filters, "admin_total")


@frappe.whitelist()
def get_admin_actual(filters=None):
	return _report(filters, "admin_actual")


@frappe.whitelist()
def get_admin_discontinued(filters=None):
	return _report(filters, "admin_discontinued")


ADMIN_KINDS = ("enquiry", "joined", "total", "actual", "discontinued")


@frappe.whitelist()
def get_admin_detail(filters=None, row_key=None, month_key=None, kind="actual", section=None, batch=None):
	"""Students -- or enquiries for kind=enquiry -- behind any admin number.

	row_key   'STANDARD|Gender|Group' (one row), or empty with section= for a TOTAL row
	month_key 'YYYY-MM'; empty = the whole period ('total' then means admitted by the last month)
	"""
	check_access()
	if kind not in ADMIN_KINDS:
		frappe.throw(_("Unknown detail type {0}").format(kind))
	metric = "admin_enquiry" if kind in ("enquiry", "joined") else f"admin_{kind}"
	report = AdminReport(parse_filters(filters), metric)

	months = [m for m in report.elapsed if not month_key or m["key"] == month_key]
	if kind == "total" and not month_key:
		months = months[-1:]  # admitted by the end of the period

	picked = {}
	for m in months:
		for r in report.members(kind, m):
			key = report.key_of(kind, r)
			if not key or (row_key and key != row_key):
				continue
			if section and not row_key:
				std_name, gender, _group = key.split("|", 2)
				std = report.layout.by_name.get(std_name)
				if not std or _section_for(std, gender) != section:
					continue
			if kind != "enquiry" and not in_batch(r, batch):
				continue
			picked[r.name] = r

	if kind == "enquiry":
		return {"type": "enquiry", "rows": [_enquiry_detail(e) for e in sorted(picked.values(), key=_enquiry_sort)]}

	month = months[0] if len(months) == 1 else None
	return {
		"type": "student",
		"rows": [_student_detail(s, report.periods[s.name], month) for s in sorted(picked.values(), key=_detail_sort)],
	}


def _enquiry_sort(e):
	return (str(e.enquiry_date or ""), e.standard or "", (e.applicant_name or "").upper())


def _enquiry_detail(e):
	return {
		"enquiry": e.name,
		"applicant_name": e.applicant_name,
		"enquiry_date": e.enquiry_date,
		"standard": e.standard,
		"group": e.subject_group,
		"gender": e.gender,
		"status": e.status,
		"source": e.source,
		"father_name": e.father_name,
		"mobile": e.father_number or e.mother_number or e.guardian_number,
		"school": e.school_name,
		"area": e.area,
		"remarks": e.remarks,
		"next_follow_up_date": e.next_follow_up_date,
	}
