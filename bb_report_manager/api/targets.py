"""Shared by the two Target Chart dashboards (Asst. Manager and TL).

Both paper registers are built the same way: a grid whose cells hold the
"Last 2 Places (with Total Mistake)" -- the two people with the most mistakes
in that category for that period, with their count -- plus a "10+ Mistake"
sheet listing everyone who reached ten in a category in the month.

Each cell carries the full ranking, so the dashboard shows the last two places
and opens the rest on click without another request.
"""

from collections import Counter

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today

from bb_report_manager.api.common import get_month_columns

TEN_PLUS = 10
LAST_PLACES = 2

# The register's four weeks. The 4th week runs to the month end, so the 29th-31st
# are not dropped (the paper prints "22 to 28").
WEEKS = [(1, 7), (8, 14), (15, 21), (22, None)]
ORDINALS = ["1st", "2nd", "3rd", "4th"]


def pick_month(start_date, end_date, month=None):
	"""The one month a weekly / 10+ sheet covers: the Month filter, else the
	running month of the academic year (or its nearest end)."""
	columns = get_month_columns(start_date, end_date)
	if not columns:
		frappe.throw(_("The academic year has no months"))
	if month:
		for c in columns:
			if c["month"] == month:
				return c
		frappe.throw(_("{0} is not in this academic year").format(month))
	now = getdate(today())
	for c in columns:
		if c["start"] <= now <= c["end"]:
			return c
	return columns[-1] if now > columns[-1]["end"] else columns[0]


def month_weeks(month):
	weeks = []
	for i, (first, last) in enumerate(WEEKS):
		start = add_days(month["start"], first - 1)
		end = month["end"] if last is None else add_days(month["start"], last - 1)
		weeks.append(
			{
				"key": f"w{i + 1}",
				"label": f"{ORDINALS[i]} Week ({first:02d} to {getdate(end).day:02d})",
				"start": getdate(start),
				"end": getdate(end),
			}
		)
	return weeks


def week_of(weeks, day):
	day = getdate(day)
	for w in weeks:
		if w["start"] <= day <= w["end"]:
			return w["key"]
	return None


def ranking(counter, people):
	"""Counter {person_id: mistakes} -> [{id, name, sub, count}], most mistakes first."""
	return [
		{**people[pid], "count": n}
		for pid, n in sorted(counter.items(), key=lambda kv: (-kv[1], (people[kv[0]]["name"] or "").upper()))
	]


class Grid:
	"""rows x categories, each cell a Counter of mistakes per person."""

	def __init__(self, categories):
		self.categories = categories
		self.cells = {}

	def add(self, row_key, category, person_id):
		self.cells.setdefault((row_key, category), Counter())[person_id] += 1

	def build(self, rows, people):
		out = []
		for idx, row in enumerate(rows, 1):
			cells = {}
			for cat in self.categories:
				counter = self.cells.get((row["key"], cat["key"]), Counter())
				cells[cat["key"]] = {"total": sum(counter.values()), "people": ranking(counter, people)}
			out.append({**row, "idx": idx, "cells": cells})
		totals = {c["key"]: sum(r["cells"][c["key"]]["total"] for r in out) for c in self.categories}
		return {"rows": out, "totals": totals}


def ten_plus(per_person, groups, people):
	"""per_person {(person_id, category): n} -> one list per 10+ group."""
	out = []
	for group in groups:
		counter = Counter()
		for (pid, cat), n in per_person.items():
			if cat in group["categories"]:
				counter[pid] += n
		hit = Counter({pid: n for pid, n in counter.items() if n >= TEN_PLUS})
		out.append({"key": group["key"], "label": group["label"], "people": ranking(hit, people)})
	return out


def serialize_period(p):
	return {**{k: v for k, v in p.items() if k not in ("start", "end")}, "start": str(p["start"]), "end": str(p["end"])}


# ------------------------------------------------------------------ insights
#
# The detail under every Target sheet, always for the sheet's month:
#   summary    totals per category, vs the month before, people involved, 10+ count
#   trend      every month of the year so far, per category
#   top        the 10 people with the most mistakes in the month, per category
#   groups     the month per group (STD - Batch for students, department for staff)
#
# `events` are normalised tuples: (person_id, category_key, date, group_label).


TOP_PEOPLE = 10


def _by_category(categories, events):
	counts = Counter(cat for _p, cat, _d, _g in events)
	return {c["key"]: counts[c["key"]] for c in categories}


def build_insights(events, month, year_months, categories, people, ten_plus_groups, today):
	today = getdate(today)
	in_month = lambda e, m: m["start"] <= e[2] <= m["end"]  # noqa: E731
	mine = [e for e in events if in_month(e, month)]

	idx = next((i for i, m in enumerate(year_months) if m["key"] == month["key"]), None)
	prev = year_months[idx - 1] if idx else None
	prev_events = [e for e in events if in_month(e, prev)] if prev else []

	per_person = Counter((p, cat) for p, cat, _d, _g in mine)
	ten = ten_plus(per_person, ten_plus_groups, people)
	cur_cats, prev_cats = _by_category(categories, mine), _by_category(categories, prev_events)

	trend = []
	for m in year_months:
		if m["start"] > today:
			break
		by_cat = _by_category(categories, [e for e in events if in_month(e, m)])
		trend.append(
			{
				"key": m["key"],
				"label": f"{m['month']} {m['year']}",
				"short": m["label"],
				"running": m["end"] > today,
				"by_category": by_cat,
				"total": sum(by_cat.values()),
			}
		)

	totals = Counter(p for p, _c, _d, _g in mine)
	top = []
	for pid, n in sorted(totals.items(), key=lambda kv: (-kv[1], people[kv[0]]["name"].upper()))[:TOP_PEOPLE]:
		top.append({**people[pid], "count": n, "by_category": {c["key"]: per_person[(pid, c["key"])] for c in categories}})

	groups = {}
	for p, cat, _d, g in mine:
		row = groups.setdefault(g or "Not set", {"label": g or "Not set", "by_category": Counter(), "people": set()})
		row["by_category"][cat] += 1
		row["people"].add(p)
	group_rows = sorted(
		(
			{
				"label": r["label"],
				"by_category": {c["key"]: r["by_category"][c["key"]] for c in categories},
				"total": sum(r["by_category"].values()),
				"people": len(r["people"]),
			}
			for r in groups.values()
		),
		key=lambda r: (-r["total"], r["label"]),
	)

	return {
		"month_key": month["key"],
		"month_label": f"{month['month']} {month['year']}" + (" (till today)" if month["end"] > today >= month["start"] else ""),
		"summary": {
			"total": sum(cur_cats.values()),
			"prev_total": sum(prev_cats.values()) if prev else None,
			"prev_label": f"{prev['month']} {prev['year']}" if prev else None,
			"people": len(totals),
			"ten_plus": len({p["id"] for group in ten for p in group["people"]}),
			"by_category": [
				{**c, "count": cur_cats[c["key"]], "prev": prev_cats[c["key"]] if prev else None} for c in categories
			],
		},
		"trend": trend,
		"top": top,
		"groups": group_rows,
	}
