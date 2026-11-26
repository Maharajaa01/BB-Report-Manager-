"""The detail under a Manager sheet, built server-side in one generic shape so a
single dashboard component renders every report:

	tiles   [{label, value, sub, delta, delta_label, higher_is_good, open}]
	chart   {title, series: [lower, upper], bars: [{key, label, short, running, lower, upper}], note}
	bars    [{title, rows: [{label, count, key}], clickable}]
	tables  [{title, columns: [{key, label, num}], rows: [{...}], link_key}]

`open` on a tile, and `key` on a bar row (a sheet row key), are drill-down
queries the dashboard sends back to the report's detail endpoint.
"""

from collections import Counter

from frappe.utils import flt


def n(v):
	"""2.0 -> 2, 2.5 -> 2.5: whole numbers print without a decimal."""
	v = round(flt(v), 2)
	return int(v) if v == int(v) else v


def tile(label, value, sub="", delta=None, delta_label="", higher_is_good=True, open=None, fmt=None):
	return {
		"label": label,
		"value": value,
		"fmt": fmt,  # "points" / "pct" / "hours" -- how the dashboard prints the value
		"sub": sub,
		"delta": delta,
		"delta_label": delta_label,
		"higher_is_good": higher_is_good,
		"open": open,
	}


def month_label(m):
	return f"{m['month']} {m['year']}"


def started(months, today):
	return [m for m in months if m["start"] <= today]


def latest_and_prev(months, today):
	done = started(months, today)
	return (done[-1] if done else None), (done[-2] if len(done) > 1 else None)


def delta_tile(label, values, months, today, higher_is_good=True, sub="", open_kind=None, fmt=None):
	"""The latest started month's value with its change from the month before."""
	cur, prev = latest_and_prev(months, today)
	if not cur:
		return tile(label, None, "no month has started yet")
	v = values.get(cur["key"]) or 0
	p = (values.get(prev["key"]) or 0) if prev else None
	return tile(
		f"{label} · {month_label(cur)}",
		n(v),
		sub,
		delta=None if p is None else n(flt(v) - flt(p)),
		delta_label=f"vs {month_label(prev)}" if prev else "",
		higher_is_good=higher_is_good,
		open={"kind": open_kind, "month": cur["key"]} if open_kind else None,
		fmt=fmt,
	)


def chart(title, series, months, today, lower, upper=None, note=""):
	"""Stacked columns for every started month; `lower` / `upper` are {month_key: n}."""
	bars = []
	for m in started(months, today):
		bars.append(
			{
				"key": m["key"],
				"label": month_label(m),
				"short": m["label"],
				"running": m["end"] > today,
				"lower": n(lower.get(m["key"], 0)),
				"upper": n((upper or {}).get(m["key"], 0)),
			}
		)
	return {"title": title, "series": series, "bars": bars, "note": note}


def bar_list(title, counter, keys=None, limit=0):
	"""counter {label: n} -> ranked rows; `keys` maps a label to a sheet row key (clickable)."""
	rows = [
		{"label": label, "count": n(count), "key": (keys or {}).get(label)}
		for label, count in sorted(Counter(counter).items(), key=lambda kv: (-kv[1], str(kv[0])))
		if count
	]
	return {"title": title, "rows": rows, "limit": limit}


def table(title, columns, rows, link_key=None, empty="Nothing to show"):
	return {"title": title, "columns": columns, "rows": rows, "link_key": link_key, "empty": empty}


def col(key, label, num=False, kind=None):
	"""kind: "date" / "datetime" / "link" / "check" -- how the dashboard prints the cell."""
	return {"key": key, "label": label, "num": num, "kind": kind}


def grid_totals(rows, months, today, distinct_total=None):
	"""Footer totals for a month grid; future months stay blank."""
	values = {}
	for m in months:
		values[m["key"]] = None if m["start"] > today else n(sum(flt(r["values"][m["key"]] or 0) for r in rows))
	total = distinct_total if distinct_total is not None else n(sum(flt(r["total"] or 0) for r in rows))
	return {"values": values, "total": total}
