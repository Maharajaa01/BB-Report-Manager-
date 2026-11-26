"""Asst. Manager Target Chart -- posting staff mistakes, read on the ERP site.

The "ASSISTANT MANAGER TARGET CHART" register:

	am_weekly    Posting Staff - Last 2 Places (with Total Mistake) - Weekly Report
	am_monthly   Posting Staff - Last 2 Places (with Total Mistake) - Monthly Report (April ... March)
	am_ten_plus  Posting Staff - 10+ Mistake - Monthly Report

A mistake is one Employee Mistake (BB Performance Manager) that is Active and
not Withdrawn on review, filed under its Mistake Category:

	Discipline, Critical Mistakes, Worklist Mistakes, Attendance Mistakes,
	Office Culture Fit (either spelling of the category)

Other categories (e.g. Dangerous Mistakes) are not on this register.
"""

import re
from collections import Counter

import frappe
from frappe import _
from frappe.utils import getdate, today

from bb_report_manager.api.common import check_access, get_month_columns, parse_filters
from bb_report_manager.api.targets import (
	Grid,
	build_insights,
	month_weeks,
	pick_month,
	serialize_period,
	ten_plus,
	week_of,
)

CATEGORIES = [
	{"key": "discipline", "label": "Discipline"},
	{"key": "critical", "label": "Critical"},
	{"key": "worklist", "label": "Work List"},
	{"key": "attendance", "label": "Attendance"},
	{"key": "culture", "label": "Office Culture Fit"},
]

TEN_PLUS_GROUPS = [
	{"key": c["key"], "label": f"10+ {c['label']} mistake" if c["key"] != "culture" else "10+ Office Culture Fit", "categories": {c["key"]}}
	for c in CATEGORIES
]


def _column_for(category):
	"""Mistake Category name -> register column. Matched loosely: the site has
	both 'Office  Culture Fit' and 'Office Fit Culture'."""
	c = re.sub(r"\s+", " ", (category or "").lower())
	if "culture" in c:
		return "culture"
	if "critical" in c:
		return "critical"
	if "worklist" in c or "work list" in c:
		return "worklist"
	if "attendance" in c:
		return "attendance"
	if "discipline" in c:
		return "discipline"
	return None


def _academic_year(name):
	"""The ERP has no Academic Year records; the tuition site's master year is
	named '2026-2027' and runs April to March."""
	if name and frappe.db.exists("DocType", "Academic Year") and frappe.db.exists("Academic Year", name):
		y = frappe.db.get_value("Academic Year", name, ["start_date", "end_date"], as_dict=True)
		if y.start_date and y.end_date:
			return getdate(y.start_date), getdate(y.end_date)
	m = re.match(r"\s*(\d{4})", name or "")
	if not m:
		frappe.throw(_("Academic Year is required"))
	start = int(m.group(1))
	return getdate(f"{start}-04-01"), getdate(f"{start + 1}-03-31")


class Context:
	def __init__(self, filters):
		check_access()
		self.filters = parse_filters(filters)
		self.start, self.end = _academic_year(self.filters.academic_year)
		self.today = getdate(today())

	def head(self, report, title):
		return {
			"report": report,
			"title": title,
			"subtitle": "Assistant Manager Target Chart",
			"academic_year": self.filters.academic_year,
			"academic_year_label": f"{self.start.year} - {self.end.year}",
			"generated_on": str(self.today),
		}

	def mistakes(self, start, end):
		rows = frappe.db.sql(
			"""
			select employee, employee_name, designation, department, category, mistake_date as date
			from `tabEmployee Mistake`
			where mistake_date between %(start)s and %(end)s
				and ifnull(record_status, 'Active') = 'Active'
				and ifnull(resolution_status, '') != 'Withdrawn'
				and docstatus < 2
			""",
			{"start": start, "end": min(getdate(end), self.today)},
			as_dict=True,
		)
		out = []
		for r in rows:
			col = _column_for(r.category)
			if col and r.employee:
				r.column = col
				out.append(r)
		return out

	@staticmethod
	def people(events):
		out = {}
		for e in events:
			out[e.employee] = {
				"id": e.employee,
				"name": (e.employee_name or e.employee).strip(),
				"detail": " - ".join(x for x in (e.designation, e.department) if x),
			}
		return out


def _load(ctx, month):
	"""The year's mistakes, everyone in them, and the detail under the sheet for `month`."""
	year_events = ctx.mistakes(ctx.start, ctx.end)
	people = ctx.people(year_events)
	insights = build_insights(
		[(e.employee, e.column, getdate(e.date), e.department) for e in year_events],
		month,
		get_month_columns(ctx.start, ctx.end),
		CATEGORIES,
		people,
		TEN_PLUS_GROUPS,
		ctx.today,
	)
	insights["group_head"] = "Department"
	return year_events, people, insights


def _in(e, period):
	return period["start"] <= getdate(e.date) <= period["end"]


def _grid_response(ctx, report, title, period, row_head, tables):
	return {
		**ctx.head(report, title),
		"period": period,
		"row_head": row_head,
		"categories": CATEGORIES,
		"tables": tables,
	}


@frappe.whitelist()
def get_am_weekly(filters=None):
	ctx = Context(filters)
	month = pick_month(ctx.start, ctx.end, ctx.filters.month)
	weeks = month_weeks(month)
	year_events, people, insights = _load(ctx, month)
	events = [e for e in year_events if _in(e, month)]
	grid = Grid(CATEGORIES)
	for e in events:
		wk = week_of(weeks, e.date)
		if wk:
			grid.add(wk, e.column, e.employee)
	rows = [{"key": w["key"], "label": w["label"], "future": w["start"] > ctx.today} for w in weeks]
	label = f"{month['month']} {month['year']}"
	return {
		**_grid_response(
			ctx,
			"am_weekly",
			"Posting Staff - Last 2 Places (with Total Mistake) - Weekly Report",
			label,
			"Weeks",
			[{"key": month["key"], "label": label, **grid.build(rows, people)}],
		),
		"insights": insights,
	}


@frappe.whitelist()
def get_am_monthly(filters=None):
	ctx = Context(filters)
	months = get_month_columns(ctx.start, ctx.end, ctx.filters.month)
	# The detail under the sheet follows the picked month, or the running one.
	events, people, insights = _load(ctx, pick_month(ctx.start, ctx.end, ctx.filters.month))
	grid = Grid(CATEGORIES)
	for e in events:
		key = getdate(e.date).strftime("%Y-%m")
		grid.add(key, e.column, e.employee)
	rows = [{"key": m["key"], "label": m["month"], "future": m["start"] > ctx.today} for m in months]
	label = f"Academic Year {ctx.start.year} - {ctx.end.year}"
	return {**_grid_response(
		ctx,
		"am_monthly",
		"Posting Staff - Last 2 Places (with Total Mistake) - Monthly Report",
		label if not ctx.filters.month else f"{months[0]['month']} {months[0]['year']}" if months else label,
		"Month",
		[{"key": "year", "label": label, **serialize_period({"start": ctx.start, "end": ctx.end}), **grid.build(rows, people)}],
	), "insights": insights}


@frappe.whitelist()
def get_am_ten_plus(filters=None):
	ctx = Context(filters)
	month = pick_month(ctx.start, ctx.end, ctx.filters.month)
	year_events, people, insights = _load(ctx, month)
	per_person = Counter((e.employee, e.column) for e in year_events if _in(e, month))
	return {
		**ctx.head("am_ten_plus", "Posting Staff - 10+ Mistake - Monthly Report"),
		"period": f"{month['month']} {month['year']}",
		"sub_head": "Designation",
		"lists": ten_plus(per_person, TEN_PLUS_GROUPS, people),
		"insights": insights,
	}
