import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"

import type { AdminCountReport, TargetGridReport, TargetInsights as Insights } from "@/api/types"
import AdminInsights from "@/components/AdminInsights.vue"
import TargetGrid from "@/components/TargetGrid.vue"
import TargetInsights from "@/components/TargetInsights.vue"
import { REPORTS, reportByPath, routeName } from "@/lib/reports"
import { gridCsv, lastPlaces } from "@/lib/targets"

const people = [
	{ id: "S1", name: "R.SANA", detail: "10th - III", count: 4 },
	{ id: "S2", name: "S.K.DEEPIKA ", detail: "10th - III", count: 3 },
	{ id: "S3", name: "M.KRISHIKA", detail: "10th - II", count: 1 },
]
const empty = { total: 0, people: [] }

const insights: Insights = {
	month_key: "2026-11",
	month_label: "November 2026 (till today)",
	group_head: "STD - Batch",
	summary: {
		total: 12,
		prev_total: 9,
		prev_label: "October 2026",
		people: 3,
		ten_plus: 1,
		by_category: [
			{ key: "discipline", label: "Discipline", count: 4, prev: 6 },
			{ key: "leave", label: "Attendance (Leave)", count: 8, prev: 3 },
		],
	},
	trend: [
		{ key: "2026-10", label: "October 2026", short: "OCT", running: false, by_category: { discipline: 6, leave: 3 }, total: 9 },
		{ key: "2026-11", label: "November 2026", short: "NOV", running: true, by_category: { discipline: 4, leave: 8 }, total: 12 },
	],
	top: [{ ...people[0], count: 8, by_category: { discipline: 3, leave: 5 } }],
	groups: [{ label: "10th - III", by_category: { discipline: 4, leave: 8 }, total: 12, people: 3 }],
}

const weekly: TargetGridReport = {
	report: "tl_weekly",
	title: "Last 2 Place (with Total Mistake) - Weekly Report",
	subtitle: "6th to 12th STD - Girls",
	academic_year: "2026-2027",
	academic_year_label: "2026 - 2027",
	generated_on: "2026-11-25",
	period: "November 2026",
	row_head: "STD",
	categories: [
		{ key: "discipline", label: "Discipline" },
		{ key: "test", label: "Test" },
	],
	insights,
	tables: [
		{
			key: "w2",
			label: "2nd Week (08 to 14)",
			rows: [{ key: "10TH", label: "10th", idx: 1, cells: { discipline: { total: 8, people }, test: empty } }],
			totals: { discipline: 8, test: 0 },
		},
		{
			key: "w4",
			label: "4th Week (22 to 30)",
			future: true,
			rows: [{ key: "10TH", label: "10th", idx: 1, cells: { discipline: empty, test: empty } }],
			totals: { discipline: 0, test: 0 },
		},
	],
}

describe("target charts", () => {
	it("registers both dashboards with routable reports", () => {
		expect(reportByPath("tl", "weekly")?.key).toBe("tl_weekly")
		expect(reportByPath("asst_manager", "ten-plus")?.key).toBe("am_ten_plus")
		expect(routeName("asst_manager")).toBe("asst-manager-report")
		// AM sheets are staff sheets: no Standard / Batch / Gender filters.
		expect(REPORTS.filter((r) => r.dashboard === "asst_manager").every((r) => !r.student)).toBe(true)
	})

	it("prints the last 2 places and opens the whole cell", async () => {
		const w = mount(TargetGrid, { props: { data: weekly, table: weekly.tables[0] } })
		const cells = w.findAll("td.bbr-target-cell")
		expect(cells[0].findAll("li").map((li) => li.text())).toEqual(["R.SANA4", "S.K.DEEPIKA 3"])
		expect(cells[0].text()).toContain("Total 8")
		expect(cells[0].text()).toContain("+1 more")
		expect(cells[1].text()).toBe("0")

		await cells[1].trigger("click")
		expect(w.emitted("open")).toBeUndefined()
		await cells[0].trigger("click")
		expect(w.emitted("open")?.[0]).toEqual(["Discipline · 10th · 2nd Week (08 to 14)", weekly.tables[0].rows[0].cells.discipline])
	})

	it("leaves weeks that have not started blank", () => {
		const w = mount(TargetGrid, { props: { data: weekly, table: weekly.tables[1] } })
		expect(w.findAll("td.bbr-target-cell.future")).toHaveLength(2)
	})

	it("exports names with counts", () => {
		expect(lastPlaces(people)).toBe("R.SANA (4), S.K.DEEPIKA (3)")
		const rows = gridCsv(weekly)
		expect(rows).toContainEqual([1, "10th", "R.SANA (4), S.K.DEEPIKA (3)", 8, "", 0])
		expect(rows).toContainEqual([1, "10th", "", "", "", ""])
	})

	it("shows the month's detail: change, biggest category, top people, groups", async () => {
		const w = mount(TargetInsights, { props: { data: insights, lowerKey: "leave", staff: false, link: (id: string) => `/s/${id}` } })
		const tiles = w.findAll(".bbr-tile").map((t) => t.text())
		expect(tiles[0]).toContain("12")
		expect(tiles[0]).toContain("▲ +3 vs October 2026")
		expect(tiles[1]).toContain("Attendance (Leave)")
		expect(w.find(".bbr-bar-note.good").text()).toContain("▼ -2 vs Oct") // discipline fell
		expect(w.find("a[href='/s/S1']").exists()).toBe(true)
		expect(w.text()).toContain("10th - III")
		await w.find(".bbr-hit").trigger("click")
		expect(w.emitted("month")?.[0]).toEqual(["2026-10"])
	})
})

describe("admin detail", () => {
	const columns = [
		{ key: "2026-10", label: "OCT", month: "October", year: 2026 },
		{ key: "2026-11", label: "NOV", month: "November", year: 2026 },
		{ key: "2026-12", label: "DEC", month: "December", year: 2026 },
	]
	const row = (standard: string, gender: string, values: (number | null)[]) => ({
		key: `${standard}|${gender}|`, label: standard, standard, gender, group: "", idx: 1,
		values: Object.fromEntries(columns.map((c, i) => [c.key, values[i]])), highest: null, highest_month: null,
	})
	const data: AdminCountReport = {
		report: "admin_discontinued", title: "DISCONTINUED", subtitle: "", academic_year: "2026-2027",
		academic_year_label: "2026 - 2027", generated_on: "2026-11-25", columns,
		sections: [{ key: "junior", label: "6th To 9th Std", rows: [row("6TH", "Boys", [2, 1, null]), row("7TH", "Girls", [0, 3, null])],
			totals: { values: {}, highest: null, highest_month: null } }],
		reasons: [{ label: "Fees", count: 4 }, { label: "Moved", count: 2 }],
	}

	it("totals started months, flags a rise in leavers as bad, and drills into a standard", async () => {
		const w = mount(AdminInsights, { props: { data, gender: "" } })
		const first = w.find(".bbr-tile")
		expect(first.text()).toContain("4")
		expect(first.find(".bbr-delta").classes()).toContain("down") // 2 -> 4 leavers
		expect(w.text()).toContain("Left so far this year")
		expect(w.text()).toContain("Why students left")
		await w.findAll(".bbr-bars li.clickable")[0].trigger("click")
		// leavers by standard cover every month so far: 6TH 3, 7TH 3 -> first row opens the whole period
		expect(w.emitted("open")?.[0][0]).toMatchObject({ kind: "discontinued", month: null })
	})
})
