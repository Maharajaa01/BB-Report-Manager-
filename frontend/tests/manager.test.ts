import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"

import type { ManagerInsights as Insights } from "@/api/types"
import DataTable from "@/components/DataTable.vue"
import ManagerInsights from "@/components/ManagerInsights.vue"
import { cellText, tileValue } from "@/lib/cells"
import { REPORTS } from "@/lib/reports"

const insights: Insights = {
	tiles: [
		{ label: "Left · November 2026", value: 2, sub: "", delta: 3, delta_label: "vs October 2026", higher_is_good: false, open: { kind: "discontinued", month: "2026-11" } },
		{ label: "Resolved", value: 40, fmt: "pct", sub: "", delta: null, delta_label: "", higher_is_good: true, open: null },
	],
	chart: { title: "Per month", series: ["Boys", "Girls"], note: "", bars: [{ key: "2026-11", label: "November 2026", short: "NOV", running: true, lower: 1, upper: 1 }] },
	bars: [{ title: "By STD · this year", rows: [{ label: "10TH STD - BOYS", count: 2, key: "10TH|Boys" }] }],
	tables: [{ title: "Recent", columns: [{ key: "on", label: "On", kind: "date" }, { key: "name", label: "Name", kind: "link" }], rows: [{ on: "2026-11-02", name: "A", link: "/app/student/S1" }], link_key: "link" }],
}

describe("manager charts", () => {
	it("every Manager register sheet is ready", () => {
		expect(REPORTS.filter((r) => r.dashboard === "manager").every((r) => r.ready)).toBe(true)
	})

	it("prints tiles, flags a rise as bad when lower is better, and drills into rows", async () => {
		const w = mount(ManagerInsights, { props: { data: insights, kind: "discontinued", linkBase: "https://t" } })
		const first = w.find("button.bbr-tile")
		expect(first.find(".bbr-delta").classes()).toContain("down")
		expect(w.text()).toContain("40%")
		await w.find(".bbr-bars li.clickable").trigger("click")
		expect(w.emitted("open")?.[0][0]).toEqual({ kind: "discontinued", row: "10TH|Boys" })
		expect(w.find("a[href='https://t/app/student/S1']").text()).toBe("A")
	})

	it("formats cells by kind", () => {
		expect(cellText("2026-11-19 15:49:00", { key: "x", label: "", kind: "datetime" })).toBe("19-11-2026 15:49")
		expect(cellText(null, { key: "x", label: "" })).toBe("–")
		expect(tileValue(insights.tiles[1])).toBe("40%")
		const t = mount(DataTable, { props: { columns: [{ key: "s", label: "Solved", kind: "check" }], rows: [{ s: true }, { s: false }] } })
		expect(t.findAll(".bbr-check").map((c) => c.text())).toEqual(["✓ Yes", "✗ No"])
	})
})
