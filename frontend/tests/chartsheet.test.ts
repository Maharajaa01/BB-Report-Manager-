import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"

import type { StudentCountReport } from "@/api/types"
import ChartSheet from "@/components/ChartSheet.vue"
import { REPORTS } from "@/lib/reports"

const data: StudentCountReport = {
	report: "student_count",
	title: "ACTUAL STUDENTS COUNT - STD & MONTH WISE",
	academic_year: "2026-2027",
	academic_year_label: "2026 - 2027",
	generated_on: "2026-11-25",
	columns: [
		{ key: "2026-10", label: "OCT", month: "October", year: 2026 },
		{ key: "2026-12", label: "DEC", month: "December", year: 2026 },
	],
	rows: [
		{ key: "6TH|Girls", label: "6TH STD - GIRLS", standard: "6TH", gender: "Girls", idx: 1, values: { "2026-10": 4, "2026-12": null }, total: 5 },
		{ key: "6TH|Boys", label: "6TH STD - BOYS", standard: "6TH", gender: "Boys", idx: 2, values: { "2026-10": 0, "2026-12": null }, total: 0 },
	],
	totals: { values: { "2026-10": 4, "2026-12": null }, total: 5 },
	summary: null,
	movement: [],
	batch_breakdown: null,
}

describe("ChartSheet", () => {
	const wrapper = mount(ChartSheet, { props: { report: REPORTS[0], data } })

	it("keeps the printed column order: S.No, STD, TOTAL, then months", () => {
		const heads = wrapper.findAll("thead th").map((th) => th.text())
		expect(heads).toEqual(["S.No.", "STD", "TOTAL", "OCT", "DEC"])
	})

	it("shows the year, title and month colour classes", () => {
		expect(wrapper.find(".bbr-sheet-year").text()).toBe("ACADEMIC YEAR : 2026 - 2027")
		expect(wrapper.find(".bbr-sheet-title").text()).toBe(data.title)
		expect(wrapper.find("th.m-OCT").exists()).toBe(true)
	})

	it("leaves future months blank and greys zeros", () => {
		const cells = wrapper.findAll("tbody tr")[1].findAll("td")
		expect(cells[3].classes()).toContain("zero")
		expect(cells[4].text()).toBe("")
	})

	it("emits a drill-down for a clicked number, not for a zero", async () => {
		const first = wrapper.findAll("tbody tr")[0].findAll("td")
		await first[3].trigger("click")
		await wrapper.findAll("tbody tr")[1].findAll("td")[3].trigger("click")
		expect(wrapper.emitted("open")).toEqual([[{ kind: "present", row: "6TH|Girls", month: "2026-10" }]])
	})
})
