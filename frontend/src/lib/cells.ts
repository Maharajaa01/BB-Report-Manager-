/** Printing server-described table cells and insight tiles. */
import type { InsightTile, TableColumn } from "@/api/types"
import { date, num } from "@/lib/format"

/** "2026-11-19 15:49:00" -> "19-11-2026 15:49" */
export function dateTime(v: unknown): string {
	if (!v) return ""
	const s = String(v)
	const time = s.slice(11, 16)
	return time && time !== "00:00" ? `${date(s)} ${time}` : date(s)
}

export function cellText(v: unknown, c: TableColumn): string {
	if (v === null || v === undefined || v === "") return c.num ? "" : "–"
	if (c.kind === "date") return date(String(v))
	if (c.kind === "datetime") return dateTime(v)
	if (c.kind === "check") return v ? "Yes" : "No"
	if (c.num && typeof v === "number") return num(v)
	return String(v)
}

export function tileValue(t: InsightTile): string {
	if (t.value === null || t.value === undefined) return "–"
	if (typeof t.value === "string") return t.value
	if (t.fmt === "pct") return `${num(t.value)}%`
	return num(t.value)
}
