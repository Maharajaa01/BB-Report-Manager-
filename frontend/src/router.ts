import { createRouter, createWebHistory } from "vue-router"

import { reportsOf } from "@/lib/reports"
import ReportView from "@/views/ReportView.vue"

export const router = createRouter({
	// Served by Frappe at /bb-reports and /bb-reports/<anything> (website_route_rules).
	history: createWebHistory("/bb-reports"),
	routes: [
		{ path: "/", redirect: { name: "report", params: { report: reportsOf("manager")[0].path } } },
		{ path: "/admin", redirect: { name: "admin-report", params: { report: reportsOf("admin")[0].path } } },
		{ path: "/admin/:report", name: "admin-report", component: ReportView, meta: { dashboard: "admin" } },
		{ path: "/:report", name: "report", component: ReportView, meta: { dashboard: "manager" } },
		{ path: "/:pathMatch(.*)*", redirect: "/" },
	],
})
