import frappe

REPORT_ROLE = "BB Report Viewer"


def after_install():
	ensure_role()


def ensure_role():
	"""Users with this role can open /bb-reports and call the report APIs."""
	if not frappe.db.exists("Role", REPORT_ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": REPORT_ROLE, "desk_access": 1}).insert(
			ignore_permissions=True
		)
