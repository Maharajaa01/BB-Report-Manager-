"""Single entry point for the /bb-reports dashboard.

The browser only ever calls these methods on the site it is logged in to
(the ERP site). Each report says where its data lives:

	tuition -- bbacademy.dreamtechsolution.com, reached over its REST API with
	           the key/secret in BB Report Settings (or called in-process when
	           the dashboard runs on the tuition site itself)
	erp     -- this site
"""

import json

import frappe
import requests
from frappe import _

from bb_report_manager.api.common import check_access, parse_filters

TUITION = "tuition"
ERP = "erp"

REPORTS = {
	"student_count": {
		"source": TUITION,
		"method": "bb_report_manager.api.tuition.get_student_count",
		"detail": "bb_report_manager.api.tuition.get_student_count_detail",
	},
	# Admin dashboard ("Admin Wiro" registers)
	**{
		key: {
			"source": TUITION,
			"method": f"bb_report_manager.api.tuition_admin.get_{key}",
			"detail": "bb_report_manager.api.tuition_admin.get_admin_detail",
		}
		for key in ("admin_enquiry", "admin_total", "admin_actual", "admin_discontinued")
	},
}


@frappe.whitelist()
def get_filter_options():
	check_access()
	options = _call(TUITION, "bb_report_manager.api.tuition.get_filter_options", {})
	# Lets the dashboard link a student number to its record on the tuition site.
	options["tuition_site_url"] = (
		"" if _is_local(TUITION) else (frappe.db.get_single_value("BB Report Settings", "tuition_site_url") or "").rstrip("/")
	)
	return options


@frappe.whitelist()
def get_report(report, filters=None):
	check_access()
	spec = _get_spec(report)
	return _call(spec["source"], spec["method"], {"filters": _dump(filters)})


@frappe.whitelist()
def get_report_detail(report, filters=None, row_key=None, month_key=None, kind=None, batch=None, section=None):
	check_access()
	spec = _get_spec(report)
	if not spec.get("detail"):
		frappe.throw(_("This report has no drill-down"))
	return _call(
		spec["source"],
		spec["detail"],
		{
			"filters": _dump(filters),
			"row_key": row_key,
			"month_key": month_key,
			"kind": kind or "present",
			"batch": batch,
			"section": section,
		},
	)


def _get_spec(report):
	spec = REPORTS.get(report)
	if not spec:
		frappe.throw(_("Unknown report: {0}").format(report))
	return spec


def _dump(filters):
	return json.dumps(parse_filters(filters), default=str)


def _call(source, method, params):
	# Unset arguments are left out, so each endpoint only receives what it accepts.
	params = {k: v for k, v in params.items() if v is not None}
	if source == ERP or _is_local(source):
		return frappe.get_attr(method)(**params)
	return _call_tuition(method, params)


def _is_local(source):
	"""The dashboard can also be opened on the tuition site itself."""
	return source == TUITION and bool(frappe.db.exists("DocType", "Student"))


def _call_tuition(method, params):
	settings = frappe.get_cached_doc("BB Report Settings")
	base_url = (settings.tuition_site_url or "").rstrip("/")
	api_secret = settings.get_password("api_secret", raise_exception=False)
	if not (base_url and settings.api_key and api_secret):
		frappe.throw(
			_("Tuition site connection is not configured. Set it in {0}.").format(
				'<a href="/app/bb-report-settings">BB Report Settings</a>'
			)
		)

	try:
		response = requests.post(
			f"{base_url}/api/method/{method}",
			data={k: v for k, v in params.items() if v is not None},
			headers={
				"Authorization": f"token {settings.api_key}:{api_secret}",
				"Accept": "application/json",
			},
			timeout=settings.timeout or 30,
		)
	except requests.RequestException as e:
		frappe.log_error(title="BB Report: tuition site unreachable")
		frappe.throw(_("Could not reach the tuition site: {0}").format(e))

	try:
		payload = response.json()
	except ValueError:
		payload = {}

	if response.status_code != 200:
		frappe.throw(
			_("Tuition site returned an error ({0}): {1}").format(
				response.status_code, _remote_message(payload) or response.reason
			)
		)
	return payload.get("message")


def _remote_message(payload):
	try:
		messages = json.loads(payload.get("_server_messages") or "[]")
		return " ".join(json.loads(m).get("message", "") for m in messages)
	except Exception:
		return payload.get("exception") or payload.get("exc_type")
