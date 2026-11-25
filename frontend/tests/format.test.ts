import { describe, expect, it } from "vitest"

import { toCsv } from "@/lib/csv"
import { date, monthsBetween, niceStep, num, signed } from "@/lib/format"

describe("format", () => {
	it("lists the months of an April-March academic year in order", () => {
		expect(monthsBetween("2026-04-01", "2027-03-31")).toEqual([
			"April", "May", "June", "July", "August", "September",
			"October", "November", "December", "January", "February", "March",
		])
	})

	it("does not repeat a month for an April-April year", () => {
		const m = monthsBetween("2026-04-01", "2027-04-30")
		expect(m).toHaveLength(12)
		expect(m[0]).toBe("April")
	})

	it("formats numbers, blanks and dates", () => {
		expect(num(null)).toBe("")
		expect(num(0)).toBe("0")
		expect(num(123456)).toBe("1,23,456")
		expect(signed(5)).toBe("+5")
		expect(signed(-3)).toBe("-3")
		expect(date("2026-10-16")).toBe("16-10-2026")
		expect(date(null)).toBe("")
	})

	it("picks round axis steps", () => {
		expect(niceStep(72)).toBe(100)
		expect(niceStep(18)).toBe(20)
		expect(niceStep(4)).toBe(5)
	})
})

describe("csv", () => {
	it("quotes commas, quotes and newlines", () => {
		expect(toCsv([["a,b", 'say "hi"', "x\ny", null, 3]])).toBe('"a,b","say ""hi""","x\ny",,3')
	})
})
