"""Helpers shared by every report API: permission check, filter parsing and
the list of month columns an academic year (and optional month filter) covers."""

import json

import frappe
from frappe import _
from frappe.utils import add_months, get_first_day, get_last_day, getdate

from bb_report_manager.install import REPORT_ROLE

MONTH_NAMES = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December",
]


def check_access():
	if frappe.session.user == "Guest":
		raise frappe.PermissionError(_("Please log in to view reports"))
	roles = set(frappe.get_roles())
	if not roles.intersection({REPORT_ROLE, "System Manager", "Administrator"}):
		raise frappe.PermissionError(_("You need the {0} role to view reports").format(REPORT_ROLE))


def parse_filters(filters):
	if isinstance(filters, str):
		filters = json.loads(filters or "{}")
	return frappe._dict({k: v for k, v in (filters or {}).items() if v not in (None, "", [])})


def get_month_columns(start_date, end_date, month=None):
	"""One column per calendar month from start_date to end_date.

	`month` (a month name such as "August") narrows it to that single month
	of the academic year.
	"""
	columns = []
	current = get_first_day(start_date)
	end = getdate(end_date)
	while current <= end:
		name = MONTH_NAMES[current.month - 1]
		if not month or month == name:
			columns.append(
				{
					"key": current.strftime("%Y-%m"),
					"label": current.strftime("%b").upper(),
					"month": name,
					"year": current.year,
					"start": current,
					"end": get_last_day(current),
				}
			)
		current = add_months(current, 1)
	return columns


def serialize_columns(columns):
	return [{k: v for k, v in c.items() if k not in ("start", "end")} for c in columns]
