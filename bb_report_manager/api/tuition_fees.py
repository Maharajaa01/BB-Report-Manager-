"""Manager Report 2 -- AFTER 15TH FEES PENDING COUNT, STD & MONTH WISE (tuition site).

A student counts as *pending after the 15th* for month M when

  * they were enrolled at the close of the 15th of M, and
  * M's monthly fee was not fully settled by then: some of it was paid after
    the 15th, or it is still unpaid today.

The cutoff is the 15th of every month for every student (not the student's own
Fees Due Date). A month is only judged once its 15th has passed.

Not counted:
  * months marked No Fees / Not Joined / Refunded, or covered by the Starting Payment
  * yearly-fee students (they pay once a year, not monthly) -- reported separately

When was a month settled?  Each submitted Fee Invoice lists the months it pays
(Fees Invoice Details) and carries the invoice date. A month is on time when it
is settled today and every invoice that paid it is dated on/before the 15th.
Months before the first submitted invoice have no payment dates on record, so
they are reported as "no data" rather than as zero.
"""

from collections import defaultdict
from datetime import date

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from bb_report_manager.api.common import MONTH_NAMES, check_access, get_month_columns, parse_filters, serialize_columns
from bb_report_manager.api.tuition import (
	_enrolled_on,
	_get_academic_year,
	_get_enrolment_periods,
	_get_rows,
	_get_students,
	_require_tuition_site,
	_row_key,
	_student_detail,
	_year_label,
)

CUTOFF_DAY = 15
NOT_BILLED = {"No Fees", "Not Joined", "Refunded"}
COVERED = {"Paid", "Paid By Starting Payment"}


def _cutoff(month):
	return date(month["start"].year, month["start"].month, CUTOFF_DAY)


def _month_index(d):
	return d.year * 12 + d.month - 1


# ------------------------------------------------------------------ payment history


def _year_months(start_date, end_date):
	"""[(year, month_no), ...] covered by an academic year."""
	start, end = getdate(start_date), getdate(end_date)
	out, y, m = [], start.year, start.month
	while (y, m) <= (end.year, end.month):
		out.append((y, m))
		y, m = (y + 1, 1) if m == 12 else (y, m + 1)
	return out


class FeeHistory:
	"""Per student: each month's payment row and the invoices that paid it,
	keyed by (year, month_no) so April 2026 and April 2027 stay apart."""

	def __init__(self, students):
		self.rows = defaultdict(dict)  # student -> {(y, m): payment row}
		self.paid = defaultdict(lambda: defaultdict(list))  # student -> (y, m) -> [(invoice_date, amount, no_fee)]
		if not students:
			return

		names = [s.name for s in students]
		years = {
			y.name: _year_months(y.start_date, y.end_date)
			for y in frappe.get_all(
				"Academic Year",
				filters={"name": ("in", list({s.academic_year for s in students if s.academic_year}))},
				fields=["name", "start_date", "end_date"],
			)
		}
		self.student_months = {s.name: years.get(s.academic_year, []) for s in students}

		# Payment rows, in order: the n-th "April" row is the n-th April of the student's year.
		for r in frappe.db.sql(
			"""
			select parent, month, status, amount_need_to_pay, amount_paid, pending, discount_amount
			from `tabStudent Payment Detail`
			where parenttype = 'Student' and parent in %(names)s and month != 'Starting Payment'
			order by parent, idx
			""",
			{"names": names},
			as_dict=True,
		):
			if r.month not in MONTH_NAMES:
				continue
			month_no = MONTH_NAMES.index(r.month) + 1
			used = self.rows[r.parent]
			slot = next(
				(ym for ym in self.student_months.get(r.parent, []) if ym[1] == month_no and ym not in used),
				None,
			)
			if slot:
				used[slot] = r

		# Invoice lines: a month name is matched to the occurrence nearest the invoice date.
		for r in frappe.db.sql(
			"""
			select i.student, i.invoice_date, i.no_fee, d.month, d.paid_amount
			from `tabFees Invoice Details` d
			join `tabFee Invoice` i on i.name = d.parent and d.parenttype = 'Fee Invoice'
			where i.docstatus = 1 and i.student in %(names)s and d.month in %(months)s
			""",
			{"names": names, "months": MONTH_NAMES},
			as_dict=True,
		):
			month_no = MONTH_NAMES.index(r.month) + 1
			candidates = [ym for ym in self.student_months.get(r.student, []) if ym[1] == month_no]
			if not candidates or not r.invoice_date:
				continue
			paid_on = getdate(r.invoice_date)
			slot = min(candidates, key=lambda ym: abs(ym[0] * 12 + ym[1] - 1 - _month_index(paid_on)))
			self.paid[r.student][slot].append((paid_on, flt(r.paid_amount), r.no_fee))

	def check(self, student, month):
		"""How month's fee stood on its 15th: None when it is not billed / covered,
		else a dict with on_time and the amounts and dates behind it."""
		slot = (month["start"].year, month["start"].month)
		row = self.rows[student.name].get(slot)
		payments = sorted(self.paid[student.name].get(slot, []))
		cutoff = _cutoff(month)

		if row and row.status in NOT_BILLED:
			return None
		if any(no_fee for _d, _a, no_fee in payments):
			return None  # waived by a No Fee invoice

		settled_now = bool(row) and (
			row.status in COVERED or (flt(row.pending) <= 0 and flt(row.amount_paid) > 0)
		)
		if row and row.status == "Paid By Starting Payment":
			return {"on_time": True}

		late = [p for p in payments if p[0] > cutoff]
		on_time = settled_now and not late
		if on_time:
			return {"on_time": True}

		fee = flt(row.amount_need_to_pay) if row else 0.0
		fee = fee or flt(student.monthly_fee)
		paid_by_cutoff = sum(a for d, a, _nf in payments if d <= cutoff)
		discount = flt(row.discount_amount) if row else 0.0
		return {
			"on_time": False,
			"fee": fee,
			"paid_by_cutoff": paid_by_cutoff,
			"balance_on_cutoff": max(0.0, fee - paid_by_cutoff - discount),
			"paid_late_on": str(late[-1][0]) if late and settled_now else None,
			"still_pending": not settled_now,
			# A month never invoiced keeps pending = 0 on the Student; what it owes is the fee less any part-payment.
			"pending_today": (
				0.0
				if settled_now
				else (flt(row.pending) if row else 0.0)
				or max(0.0, fee - (flt(row.amount_paid) if row else 0.0) - discount)
			),
			"status_today": row.status if row else "Not billed",
		}


# ------------------------------------------------------------------ report


class FeesPending:
	def __init__(self, filters):
		_require_tuition_site()
		self.filters = filters
		self.today = getdate(today())
		self.year = _get_academic_year(filters.academic_year)
		self.months = get_month_columns(self.year.start_date, self.year.end_date, filters.month)
		self.rows = _get_rows(filters, self.year)
		students = _get_students(filters, self.rows)
		self.yearly = [s for s in students if s.yearly_fees_student]
		self.students = [s for s in students if not s.yearly_fees_student]
		self.periods = _get_enrolment_periods(self.students)
		self.history = FeeHistory(self.students)
		self.data_from = self._first_invoice_month()

	def _first_invoice_month(self):
		first = frappe.db.sql("select min(invoice_date) from `tabFee Invoice` where docstatus = 1")[0][0]
		return date(first.year, first.month, 1) if first else None

	def state(self, month):
		"""'future' (15th not passed yet), 'no_data' (before invoices began) or 'ok'."""
		if _cutoff(month) >= self.today:
			return "future"
		if not self.data_from or month["start"] < self.data_from:
			return "no_data"
		return "ok"

	def judged(self):
		return [m for m in self.months if self.state(m) == "ok"]

	def due(self, month):
		"""(student, check) for everyone whose fee for `month` was due on its 15th."""
		cutoff = _cutoff(month)
		out = []
		for s in self.students:
			if not _enrolled_on(self.periods[s.name], cutoff):
				continue
			result = self.history.check(s, month)
			if result is not None:
				out.append((s, result))
		return out

	def pending(self, month):
		return [(s, r) for s, r in self.due(month) if not r["on_time"]]

	def build(self):
		states = {m["key"]: self.state(m) for m in self.months}
		pending = {m["key"]: self.pending(m) for m in self.judged()}

		data = []
		totals = {m["key"]: (0 if states[m["key"]] == "ok" else None) for m in self.months}
		for idx, row in enumerate(self.rows, 1):
			values, total = {}, 0
			for m in self.months:
				if states[m["key"]] != "ok":
					values[m["key"]] = None
					continue
				n = sum(1 for s, _r in pending[m["key"]] if _row_key(s) == row["key"])
				values[m["key"]] = n
				totals[m["key"]] += n
				total += n
			data.append({**row, "idx": idx, "values": values, "total": total})

		monthly = []
		for m in self.judged():
			due = self.due(m)
			late = [r for _s, r in due if not r["on_time"]]
			monthly.append(
				{
					"key": m["key"],
					"label": f"{m['month']} {m['year']}",
					"short": m["label"],
					"due": len(due),
					"on_time": len(due) - len(late),
					"pending": len(late),
					"pending_pct": round(100.0 * len(late) / len(due), 1) if due else None,
					"balance_on_cutoff": sum(r["balance_on_cutoff"] for r in late),
					"paid_late": sum(1 for r in late if not r["still_pending"]),
					"still_pending": sum(1 for r in late if r["still_pending"]),
					"still_pending_amount": sum(r["pending_today"] for r in late if r["still_pending"]),
				}
			)

		return data, totals, states, monthly

	def batch_breakdown(self, monthly):
		if not monthly:
			return None
		month = next(m for m in self.months if m["key"] == monthly[-1]["key"])
		batches = frappe.get_all("Batch", filters={"is_active": 1}, order_by="display_order asc", pluck="name")
		pending = [s for s, _r in self.pending(month)]
		standards = list(dict.fromkeys(r["standard"] for r in self.rows))
		rows = []
		for std in standards:
			members = [s for s in pending if s.standard == std]
			rows.append(
				{
					"standard": std,
					"values": {b: sum(1 for s in members if s.current_batch == b) for b in batches},
					"no_batch": sum(1 for s in members if s.current_batch not in batches),
					"boys": sum(1 for s in members if s.gender == "Boys"),
					"girls": sum(1 for s in members if s.gender == "Girls"),
					"total": len(members),
				}
			)
		return {
			"month_key": month["key"],
			"label": f"{month['month']} {month['year']}",
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


@frappe.whitelist()
def get_fees_pending(filters=None):
	check_access()
	report = FeesPending(parse_filters(filters))
	rows, totals, states, monthly = report.build()

	last = monthly[-1] if monthly else None
	prev = monthly[-2] if len(monthly) > 1 else None
	return {
		"report": "fees_pending",
		"title": "AFTER 15TH FEES PENDING COUNT - STD & MONTH WISE",
		"academic_year": report.year.name,
		"academic_year_label": _year_label(report.year),
		"generated_on": str(report.today),
		"columns": [{**c, "state": states[c["key"]]} for c in serialize_columns(report.months)],
		"rows": rows,
		"totals": {"values": totals, "total": sum(v for v in totals.values() if v)},
		"monthly": monthly,
		"data_from": str(report.data_from) if report.data_from else None,
		"yearly_students": len(report.yearly),
		"summary": {
			"month": last["label"] if last else None,
			"pending": last["pending"] if last else None,
			"pending_prev": prev["pending"] if prev else None,
			"prev_label": prev["label"] if prev else None,
			"due": last["due"] if last else None,
			"pending_pct": last["pending_pct"] if last else None,
			"balance_on_cutoff": last["balance_on_cutoff"] if last else None,
			"still_pending": last["still_pending"] if last else None,
			"still_pending_amount": last["still_pending_amount"] if last else None,
			"paid_late": last["paid_late"] if last else None,
		}
		if last
		else None,
		"batch_breakdown": report.batch_breakdown(monthly),
	}


FEE_KINDS = ("pending", "due", "on_time", "paid_late", "still_pending")


@frappe.whitelist()
def get_fees_pending_detail(filters=None, row_key=None, month_key=None, kind="pending", batch=None):
	"""Students behind a fees-pending number, with what they owed on the 15th.

	kind  pending (default) | due | on_time | paid_late | still_pending
	"""
	check_access()
	if kind not in FEE_KINDS:
		frappe.throw(_("Unknown detail type {0}").format(kind))
	report = FeesPending(parse_filters(filters))
	months = [m for m in report.judged() if not month_key or m["key"] == month_key]

	out = []
	for m in months:
		for s, r in report.due(m):
			if kind == "pending" and r["on_time"]:
				continue
			if kind == "on_time" and not r["on_time"]:
				continue
			if kind == "paid_late" and (r["on_time"] or r["still_pending"]):
				continue
			if kind == "still_pending" and (r["on_time"] or not r["still_pending"]):
				continue
			if row_key:
				std, _sep, gender = row_key.partition("|")
				if s.standard != std or (gender and s.gender != gender):
					continue
			if batch and (s.current_batch or "__none__") != batch:
				continue
			out.append(
				{
					**_student_detail(s, report.periods[s.name], None),
					"fee_month": f"{m['month']} {m['year']}",
					"fee_month_key": m["key"],
					"fee": r.get("fee"),
					"paid_by_cutoff": r.get("paid_by_cutoff"),
					"balance_on_cutoff": r.get("balance_on_cutoff"),
					"paid_late_on": r.get("paid_late_on"),
					"still_pending": r.get("still_pending", False),
					"pending_today": r.get("pending_today"),
					"on_time": r["on_time"],
				}
			)
	out.sort(key=lambda d: (d["fee_month_key"], d["standard"] or "", d["gender"] or "", (d["student_name"] or "").upper()))
	return out
