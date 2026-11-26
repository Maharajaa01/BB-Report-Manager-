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
		{ path: "/asst-manager", redirect: { name: "asst-manager-report", params: { report: reportsOf("asst_manager")[0].path } } },
		{ path: "/asst-manager/:report", name: "asst-manager-report", component: ReportView, meta: { dashboard: "asst_manager" } },
		{ path: "/tl", redirect: { name: "tl-report", params: { report: reportsOf("tl")[0].path }, query: { gender: "Girls" } } },
		{ path: "/tl/:report", name: "tl-report", component: ReportView, meta: { dashboard: "tl" } },
		{ path: "/:report", name: "report", component: ReportView, meta: { dashboard: "manager" } },
		{ path: "/:pathMatch(.*)*", redirect: "/" },
	],
})
