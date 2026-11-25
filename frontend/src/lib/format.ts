export const MONTHS = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December",
]

/** 1234 -> "1,234" (Indian grouping); null/undefined -> "". */
export function num(v: number | null | undefined): string {
	return v === null || v === undefined ? "" : Number(v).toLocaleString("en-IN")
}

/** "2026-10-16" -> "16-10-2026" */
export function date(v: string | null | undefined): string {
	if (!v) return ""
	const [y, m, d] = String(v).slice(0, 10).split("-")
	return `${d}-${m}-${y}`
}

export function signed(v: number): string {
	return (v > 0 ? "+" : "") + num(v)
}

/** Month names an academic year covers, in order: "2026-04-01".."2027-03-31" -> April..March */
export function monthsBetween(start: string, end: string): string[] {
	const out: string[] = []
	const [sy, sm] = start.split("-").map(Number)
	const [ey, em] = end.split("-").map(Number)
	let y = sy
	let m = sm
	while (y < ey || (y === ey && m <= em)) {
		const name = MONTHS[m - 1]
		if (!out.includes(name)) out.push(name)
		m += 1
		if (m > 12) {
			m = 1
			y += 1
		}
	}
	return out
}

/** A round step for ~4 gridlines up to `max`. */
export function niceStep(raw: number): number {
	const pow = Math.pow(10, Math.floor(Math.log10(Math.max(raw, 1))))
	const f = raw / pow
	return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * pow
}
