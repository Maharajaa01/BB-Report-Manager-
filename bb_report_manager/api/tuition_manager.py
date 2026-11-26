"""Manager Charts 3 and 4, read on the tuition site ("Manager wiro" register):

	parent_complaint  PARENTS COMPLAINT - STD & MONTH WISE
	                  Parent Complaint records, by the month they were received
	discontinued      DISCONTINUED STUDENTS COUNT - STD & MONTH WISE
	                  students who left in the month (a rejoined student counts
	                  in the month they left)

Rows are the Manager chart's STD x gender rows; filters are the usual student
filters. Each report carries an `insights` block (see api.insights).
"""

from collections import Counter

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, today

from bb_report_manager.api import insights as ins
from bb_report_manager.api.common import check_access, get_month_columns, parse_filters, serialize_columns
from bb_report_manager.api.tuition import (
	_as_list,
	_detail_sort,
	_get_academic_year,
	_get_enrolment_periods,
	_get_rows,
	_get_students,
	_month_events,
	_require_tuition_site,
	_student_detail,
	_year_label,
)
from bb_report_manager.api.tuition_admin import leaving_reasons

TITLES = {
	"parent_complaint": "PARENTS COMPLAINT - STD & MONTH WISE",
	"discontinued": "DISCONTINUED STUDENTS COUNT - STD & MONTH WISE",
}


class Sheet:
	def __init__(self, filters):
		check_access()
		_require_tuition_site()
		self.filters = parse_filters(filters)
		self.year = _get_academic_year(self.filters.academic_year)
		self.today = getdate(today())
		self.months = get_month_columns(self.year.start_date, self.year.end_date, self.filters.month)
		self.rows = _get_rows(self.filters, self.year)
		self.row_keys = {r["key"] for r in self.rows}
		self.label_of = {r["key"]: r["label"] for r in self.rows}

	def month_of(self, day):
		day = getdate(day)
		return next((m for m in self.months if m["start"] <= day <= m["end"]), None)

	def grid(self, counts):
		"""counts {(row_key, month_key): n} -> sheet rows and footer."""
		rows = []
		for idx, r in enumerate(self.rows, 1):
			values = {
				m["key"]: None if m["start"] > self.today else counts.get((r["key"], m["key"]), 0) for m in self.months
			}
			rows.append({**r, "idx": idx, "values": values, "total": sum(v or 0 for v in values.values())})
		return rows, ins.grid_totals(rows, self.months, self.today)

	def head(self, report):
		return {
			"report": report,
			"title": TITLES[report],
			"academic_year": self.year.name,
			"academic_year_label": _year_label(self.year),
			"generated_on": str(self.today),
			"columns": serialize_columns(self.months),
		}

	def by_gender(self, counts):
		"""({month: boys}, {month: girls}) from {(row_key, month): n}."""
		boys, girls = Counter(), Counter()
		for (row_key, month_key), n in counts.items():
			(boys if row_key.endswith("|Boys") else girls)[month_key] += n
		return boys, girls

	def month_totals(self, counts):
		totals = Counter()
		for (_row, month_key), n in counts.items():
			totals[month_key] += n
		return totals

	def row_totals(self, counts):
		"""{row label: n} for the bar list, with the label -> row key map that makes bars clickable."""
		totals = Counter()
		for (row_key, _m), n in counts.items():
			totals[self.label_of[row_key]] += n
		return totals, {v: k for k, v in self.label_of.items()}


# ------------------------------------------------------------------ discontinued


def _leavers(sheet):
	"""[(student, month)] for every student who left in a started month of the sheet."""
	students = _get_students(sheet.filters, sheet.rows)
	periods = _get_enrolment_periods(students)
	out = []
	for s in students:
		if f"{s.standard}|{s.gender}" not in sheet.row_keys:
			continue
		for m in ins.started(sheet.months, sheet.today):
			if _month_events(periods[s.name], m)[2]:
				out.append((s, m))
	return out, periods


@frappe.whitelist()
def get_discontinued(filters=None):
	sheet = Sheet(filters)
	leavers, periods = _leavers(sheet)
	counts = Counter((f"{s.standard}|{s.gender}", m["key"]) for s, m in leavers)
	rows, totals = sheet.grid(counts)

	per_month = sheet.month_totals(counts)
	boys, girls = sheet.by_gender(counts)
	by_row, keys = sheet.row_totals(counts)
	done = ins.started(sheet.months, sheet.today)
	worst = max(done, key=lambda m: per_month[m["key"]], default=None)
	unique = {s.name: s for s, _m in leavers}
	by_batch = Counter()
	for s in unique.values():
		by_batch[(s.current_batch or "No batch", s.gender)] += 1
	batches = sorted({b for b, _g in by_batch})
	recent = sorted(leavers, key=lambda sm: str(sm[0].discontinued__date or sm[1]["end"]), reverse=True)[:12]

	return {
		**sheet.head("discontinued"),
		"rows": rows,
		"totals": totals,
		"insights": {
			"tiles": [
				ins.delta_tile("Left", per_month, sheet.months, sheet.today, higher_is_good=False,
					sub="students who discontinued", open_kind="discontinued"),
				ins.tile("Left so far this year", sum(per_month.values()),
					f"{len(done)} months · {sum(per_month.values()) / max(len(done), 1):.1f} a month",
					open={"kind": "discontinued", "month": None}),
				ins.tile("Worst month", per_month[worst["key"]] if worst else None,
					ins.month_label(worst) if worst and per_month[worst["key"]] else "nobody has left",
					open={"kind": "discontinued", "month": worst["key"]} if worst and per_month[worst["key"]] else None),
				ins.tile("Boys · Girls", f"{sum(boys.values())} · {sum(girls.values())}", "left so far this year"),
			],
			"chart": ins.chart("Students who left, per month", ["Boys", "Girls"], sheet.months, sheet.today, boys, girls,
				note="Click a month to see who left."),
			"bars": [
				ins.bar_list("By STD · so far this year", by_row, keys),
				ins.bar_list("Why they left", {r["label"]: r["count"] for r in leaving_reasons(unique.values())}, limit=8),
			],
			"tables": [
				ins.table(
					"By batch · so far this year",
					[ins.col("batch", "Batch"), ins.col("boys", "Boys", True), ins.col("girls", "Girls", True), ins.col("total", "Total", True)],
					[{"batch": b if b == "No batch" else f"Batch {b}", "boys": by_batch[(b, "Boys")], "girls": by_batch[(b, "Girls")],
						"total": by_batch[(b, "Boys")] + by_batch[(b, "Girls")]} for b in batches],
					empty="Nobody has left this year.",
				),
				ins.table(
					"Most recent leavers",
					[ins.col("left_on", "Left on", kind="date"), ins.col("student_name", "Student", kind="link"), ins.col("std", "STD"),
						ins.col("batch", "Batch"), ins.col("reason", "Reason")],
					[{"left_on": s.discontinued__date or (periods[s.name][-2][1] if len(periods[s.name]) > 1 else m["end"]),
						"student_name": s.student_name, "link": f"/app/student/{s.name}", "std": sheet.label_of.get(f"{s.standard}|{s.gender}"),
						"batch": s.current_batch, "reason": s.discontinue_reason_category or s.discontinued_reason} for s, m in recent],
					link_key="link",
					empty="Nobody has left this year.",
				),
			],
		},
	}


# ------------------------------------------------------------------ parents complaint


def _complaints(sheet):
	standards = sorted({r["standard"] for r in sheet.rows})
	if not standards:
		return []
	values = {
		"standards": standards,
		"genders": sorted({r["gender"] for r in sheet.rows}),
		"start": sheet.months[0]["start"],
		"end": sheet.months[-1]["end"],
	}
	batch = ""
	if sheet.filters.batch:
		values["batches"] = _as_list(sheet.filters.batch)
		batch = "and ifnull(c.batch, s.current_batch) in %(batches)s"
	rows = frappe.db.sql(
		f"""
		select c.name, c.student, ifnull(c.student_name, s.student_name) as student_name,
			ifnull(c.standard, s.standard) as standard, s.gender, ifnull(c.batch, s.current_batch) as batch,
			c.status, c.complaint_for, c.complained_by, c.complaint, c.resolution_notes,
			ifnull(c.received_on, c.creation) as received_on, c.resolved_on
		from `tabParent Complaint` c
		join `tabStudent` s on s.name = c.student
		where c.docstatus < 2
			and date(ifnull(c.received_on, c.creation)) between %(start)s and %(end)s
			and ifnull(c.standard, s.standard) in %(standards)s
			and s.gender in %(genders)s
			{batch}
		order by received_on desc
		""",
		values,
		as_dict=True,
	)
	for r in rows:
		r.row_key = f"{r.standard}|{r.gender}"
		r.month = sheet.month_of(r.received_on)
	return [r for r in rows if r.row_key in sheet.row_keys and r.month]


def _is_open(c):
	return (c.status or "Open") != "Resolved"


def _complaint_row(c, label_of):
	return {
		"received_on": c.received_on,
		"student_name": c.student_name,
		"link": f"/app/parent-complaint/{c.name}",
		"std": label_of.get(c.row_key, c.standard),
		"batch": c.batch,
		"complaint_for": c.complaint_for,
		"complained_by": c.complained_by,
		"complaint": c.complaint,
		"status": c.status,
		"resolved_on": c.resolved_on,
		"resolution": c.resolution_notes,
	}


COMPLAINT_COLUMNS = [
	ins.col("received_on", "Received", kind="datetime"),
	ins.col("student_name", "Student", kind="link"),
	ins.col("std", "STD"),
	ins.col("batch", "Batch"),
	ins.col("complaint_for", "About"),
	ins.col("complained_by", "From"),
	ins.col("complaint", "Complaint"),
	ins.col("status", "Status"),
	ins.col("resolved_on", "Resolved", kind="datetime"),
	ins.col("resolution", "Resolution"),
]


@frappe.whitelist()
def get_parent_complaint(filters=None):
	sheet = Sheet(filters)
	complaints = _complaints(sheet)
	counts = Counter((c.row_key, c.month["key"]) for c in complaints)
	rows, totals = sheet.grid(counts)

	per_month = sheet.month_totals(counts)
	boys, girls = sheet.by_gender(counts)
	by_row, keys = sheet.row_totals(counts)
	still_open = [c for c in complaints if _is_open(c)]
	resolved = [c for c in complaints if not _is_open(c)]
	days = [date_diff(c.resolved_on, c.received_on) for c in resolved if c.resolved_on]

	return {
		**sheet.head("parent_complaint"),
		"rows": rows,
		"totals": totals,
		"insights": {
			"tiles": [
				ins.delta_tile("Complaints", per_month, sheet.months, sheet.today, higher_is_good=False,
					sub="received from parents", open_kind="complaint"),
				ins.tile("Still open", len(still_open), "waiting for a resolution",
					open={"kind": "complaint", "month": None, "section": "open"} if still_open else None),
				ins.tile("Resolved", round(100 * len(resolved) / len(complaints)) if complaints else None,
					f"{len(resolved)} of {len(complaints)} this year", fmt="pct"),
				ins.tile("Days to resolve", round(sum(days) / len(days), 1) if days else None,
					"average, received to resolved" if days else "no complaint resolved yet"),
			],
			"chart": ins.chart("Complaints per month", ["Boys", "Girls"], sheet.months, sheet.today, boys, girls,
				note="Click a month to read its complaints."),
			"bars": [
				ins.bar_list("By STD · this year", by_row, keys),
				ins.bar_list("What parents complained about", Counter(c.complaint_for or "Not set" for c in complaints)),
				ins.bar_list("Who complained", Counter(c.complained_by or "Not set" for c in complaints)),
			],
			"tables": [
				ins.table(
					"Open complaints, oldest first",
					COMPLAINT_COLUMNS[:8],
					[_complaint_row(c, sheet.label_of) for c in sorted(still_open, key=lambda c: c.received_on)],
					link_key="link",
					empty="No complaint is open.",
				),
			],
		},
	}


# ------------------------------------------------------------------ drill-down


@frappe.whitelist()
def get_manager_detail(filters=None, row_key=None, month_key=None, kind=None, batch=None, section=None):
	"""Students who left, or complaints, behind a number on either sheet."""
	sheet = Sheet(filters)
	months = [m for m in ins.started(sheet.months, sheet.today) if not month_key or m["key"] == month_key]
	keys = {m["key"] for m in months}

	if kind == "complaint":
		picked = [
			c for c in _complaints(sheet)
			if c.month["key"] in keys and (not row_key or c.row_key == row_key) and (section != "open" or _is_open(c))
		]
		return {
			"type": "table",
			"site": "tuition",
			"columns": COMPLAINT_COLUMNS,
			"rows": [_complaint_row(c, sheet.label_of) for c in picked],
			"link_key": "link",
		}

	if kind != "discontinued":
		frappe.throw(_("Unknown detail type {0}").format(kind))
	leavers, periods = _leavers(sheet)
	picked = {}
	for s, m in leavers:
		if m["key"] in keys and (not row_key or f"{s.standard}|{s.gender}" == row_key):
			if batch and (s.current_batch or "__none__") != batch and not (batch == "__none__" and not s.current_batch):
				continue
			picked[s.name] = s
	month = months[0] if len(months) == 1 else None
	return {
		"type": "student",
		"rows": [_student_detail(s, periods[s.name], month) for s in sorted(picked.values(), key=_detail_sort)],
	}
