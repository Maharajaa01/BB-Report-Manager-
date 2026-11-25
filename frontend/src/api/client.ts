/**
 * Thin wrapper over the whitelisted methods in bb_report_manager.api.dashboard.
 * Every report read is a GET, so no CSRF token is needed for them.
 */

const PREFIX = "/api/method/bb_report_manager.api.dashboard."

export class ApiError extends Error {
	status: number

	constructor(message: string, status = 0) {
		super(message)
		this.name = "ApiError"
		this.status = status
	}
}

function htmlToText(html: string): string {
	const div = document.createElement("div")
	div.innerHTML = html.replace(/<br\s*\/?>/gi, "\n")
	return (div.textContent || "").trim()
}

/** Frappe sends user-facing errors as JSON strings inside `_server_messages`. */
export function parseServerMessages(raw: unknown): string[] {
	if (typeof raw !== "string" || !raw) return []
	try {
		return (JSON.parse(raw) as unknown[])
			.map((entry) => {
				const parsed = (typeof entry === "string" ? JSON.parse(entry) : entry) as { message?: string }
				return htmlToText(String(parsed.message ?? ""))
			})
			.filter(Boolean)
	} catch {
		return []
	}
}

function errorFrom(status: number, payload: Record<string, unknown> | null): ApiError {
	const messages = parseServerMessages(payload?._server_messages)
	let message = messages[messages.length - 1]
	if (!message) {
		if (status === 403) message = "You do not have permission to view these reports."
		else if (status >= 500) message = "The server ran into a problem. Please try again shortly."
		else message = String(payload?.exception ?? "") || "Something went wrong. Please try again."
	}
	return new ApiError(message, status)
}

export async function call<T>(name: string, args: Record<string, unknown> = {}, signal?: AbortSignal): Promise<T> {
	const params = new URLSearchParams()
	for (const [k, v] of Object.entries(args)) {
		if (v === undefined || v === null || v === "") continue
		params.set(k, typeof v === "object" ? JSON.stringify(v) : String(v))
	}
	const qs = params.toString()

	let response: Response
	try {
		response = await fetch(PREFIX + name + (qs ? `?${qs}` : ""), {
			headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
			credentials: "same-origin",
			cache: "no-store",
			signal,
		})
	} catch (e) {
		if ((e as Error).name === "AbortError") throw e
		throw new ApiError("Cannot reach the server. Check your connection and try again.")
	}

	let payload: Record<string, unknown> | null = null
	try {
		payload = await response.json()
	} catch {
		payload = null
	}
	if (response.status === 403 && /Login to access|session_expired/i.test(String(payload?.exception ?? ""))) {
		window.location.replace(`/login?redirect-to=${encodeURIComponent(location.pathname + location.search)}`)
	}
	if (!response.ok) throw errorFrom(response.status, payload)
	return (payload?.message ?? null) as T
}
