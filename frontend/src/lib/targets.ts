/** Target Chart helpers shared by the Asst. Manager and TL dashboards. */
import type { TargetGridReport, TargetPerson, TenPlusReport } from "@/api/types"
import type { Cell } from "@/lib/csv"

/** "Last 2 Places": how many names a cell prints. */
export const LAST_PLACES = 2

/** "R.SANA (4), S.K.DEEPIKA (3)" */
export const lastPlaces = (people: TargetPerson[]) =>
	people
		.slice(0, LAST_PLACES)
		.map((p) => `${p.name.trim()} (${p.count})`)
		.join(", ")

export function gridCsv(d: TargetGridReport): Cell[][] {
	const rows: Cell[][] = []
	for (const t of d.tables) {
		rows.push([], [t.label], ["S.No", d.row_head, ...d.categories.flatMap((c) => [`${c.label} - Last 2`, `${c.label} - Total`])])
		for (const r of t.rows) {
			const blank = r.future || t.future
			rows.push([
				r.idx,
				r.label,
				...d.categories.flatMap((c) => (blank ? ["", ""] : [lastPlaces(r.cells[c.key].people), r.cells[c.key].total])),
			])
		}
		rows.push(["", "TOTAL", ...d.categories.flatMap((c) => ["", t.totals[c.key]])])
	}
	return rows
}

export function tenPlusCsv(d: TenPlusReport): Cell[][] {
	const rows: Cell[][] = []
	for (const l of d.lists) {
		rows.push([], [l.label], ["S.No", "Name", d.sub_head, "Total Mistake"])
		l.people.forEach((p, i) => rows.push([i + 1, p.name.trim(), p.detail, p.count]))
		if (!l.people.length) rows.push(["", "Nobody reached 10"])
	}
	return rows
}
