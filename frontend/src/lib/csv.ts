/** CSV with a UTF-8 BOM so Excel opens Tamil/accented names correctly. */

export type Cell = string | number | null | undefined

export function toCsv(rows: Cell[][]): string {
	return rows
		.map((r) =>
			r
				.map((v) => {
					const s = v === null || v === undefined ? "" : String(v)
					return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
				})
				.join(","),
		)
		.join("\r\n")
}

export function slug(s: string): string {
	return s.replace(/[^A-Za-z0-9]+/g, "_").replace(/^_|_$/g, "")
}

export function downloadCsv(name: string, rows: Cell[][]): void {
	const blob = new Blob(["﻿" + toCsv(rows)], { type: "text/csv;charset=utf-8" })
	const a = document.createElement("a")
	a.href = URL.createObjectURL(blob)
	a.download = name.endsWith(".csv") ? name : `${name}.csv`
	document.body.append(a)
	a.click()
	setTimeout(() => {
		URL.revokeObjectURL(a.href)
		a.remove()
	}, 0)
}
