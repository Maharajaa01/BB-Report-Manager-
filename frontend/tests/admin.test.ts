import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"

import type { AdminCountReport, AdminEnquiryReport } from "@/api/types"
import AdminCountSheet from "@/components/AdminCountSheet.vue"
import EnquirySheet from "@/components/EnquirySheet.vue"
import { reportByPath } from "@/lib/reports"

const columns = [
	{ key: "2026-10", label: "OCT", month: "October", year: 2026 },
	{ key: "2026-11", label: "NOV", month: "November", year: 2026 },
]

const actual: AdminCountReport = {
	report: "admin_actual",
	title: "ACTUAL STUDENTS COUNT LIST",
	subtitle: "STD WISE & MONTH WISE",
	academic_year: "2026-2027",
	academic_year_label: "2026 - 2027",
	generated_on: "2026-11-25",
	columns,
	sections: [
		{
			key: "senior_girls",
			label: "10th To 12th Std - Girls",
			rows: [
				{ key: "11TH Commerce|Girls|Statistics", label: "11TH STATISTICS", standard: "11TH Commerce", gender: "Girls", group: "Statistics", idx: 1, values: { "2026-10": 0, "2026-11": 1 }, highest: 1, highest_month: "2026-11" },
				{ key: "11TH Commerce|Girls|Computer Application", label: "11TH COMMERCE (CA)", standard: "11TH Commerce", gender: "Girls", group: "Computer Application", idx: 2, values: { "2026-10": 0, "2026-11": 0 }, highest: 0, highest_month: null },
			],
			totals: { values: { "2026-10": 0, "2026-11": 1 }, highest: 1, highest_month: "2026-11" },
		},
	],
}

describe("AdminCountSheet", () => {
	const w = mount(AdminCountSheet, { props: { report: reportByPath("admin", "actual-students")!, data: actual, section: actual.sections[0] } })

	it("prints S.No, STD, months, then Highest Count -- no TOTAL column", () => {
		// "Highest<br>Count" reads as one word in textContent
		const heads = w.findAll("thead tr:nth-child(2) th").map((th) => th.text())
		expect(heads).toEqual(["S.No.", "STD", "OCT", "NOV", "HighestCount"])
		expect(w.find(".bbr-admin-banner").text()).toContain("10th To 12th Std - Girls")
	})

	it("shows the peak month on hover and opens that month from the Highest cell", async () => {
		const peak = w.findAll("tbody tr")[0].find("td.col-peak")
		expect(peak.attributes("title")).toBe("Peak: November 2026")
		await peak.trigger("click")
		expect(w.emitted("open")![0][0]).toMatchObject({ kind: "actual", row: "11TH Commerce|Girls|Statistics", month: "2026-11", section: null })
	})

	it("drills a TOTAL-row number down by section", async () => {
		await w.find("tfoot td.col-peak").trigger("click")
		expect(w.emitted("open")![1][0]).toMatchObject({ kind: "actual", row: null, month: "2026-11", section: "senior_girls" })
	})
})

const enquiry: AdminEnquiryReport = {
	report: "admin_enquiry",
	title: "ENQUIRY & JOINERS COUNT LIST",
	subtitle: "BLACK BUILDING (BB) ACADEMY PVT. LTD.",
	academic_year: "2026-2027",
	academic_year_label: "2026 - 2027",
	generated_on: "2026-11-25",
	columns,
	sections: [
		{
			key: "junior",
			label: "6th To 9th Std",
			rows: [{ key: "6TH|Boys|", label: "6TH STD - BOYS", standard: "6TH", gender: "Boys", group: "", idx: 1, values: { "2026-10": { e: 2, j: 1 }, "2026-11": { e: 0, j: 2 } }, total: { e: 2, j: 3 } }],
			totals: { values: { "2026-10": { e: 2, j: 1 }, "2026-11": { e: 0, j: 2 } }, total: { e: 2, j: 3 } },
		},
	],
	summary: { enquiries: 2, joined: 3, conversion: 150, by_status: [], by_source: [], no_group: 0, period: "" },
}

describe("EnquirySheet", () => {
	const w = mount(EnquirySheet, { props: { data: enquiry, section: enquiry.sections[0], batch: "II" } })

	it("splits each month into E and J and shows the register header", () => {
		expect(w.findAll(".bbr-enq-ej th").map((t) => t.text())).toEqual(["E", "J", "E", "J", "E", "J"])
		expect(w.find(".bbr-enq-badge").text()).toBe("BOYS & GIRLS")
		expect(w.find(".bbr-enq-box").text()).toContain("Batch : II")
	})

	it("opens enquiries from E and joiners from J; a zero does nothing", async () => {
		const cells = w.findAll("tbody td")
		await cells[2].trigger("click") // OCT E = 2
		await cells[3].trigger("click") // OCT J = 1
		await cells[4].trigger("click") // NOV E = 0
		const opened = w.emitted("open")!.map((e) => (e[0] as { kind: string; month: string }))
		expect(opened.map((o) => [o.kind, o.month])).toEqual([["enquiry", "2026-10"], ["joined", "2026-10"]])
	})
})
