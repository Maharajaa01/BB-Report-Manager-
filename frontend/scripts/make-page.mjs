/**
 * Turn the Vite build into the Frappe website page.
 *
 * Run after `vite build`: writes www/bb-reports.html from the built index.html,
 * with the signed-in user's name and CSRF token injected (Frappe renders it as Jinja;
 * www/bb-reports.py supplies the context and keeps guests out).
 */
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import { dirname, join, relative, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const HERE = dirname(fileURLToPath(import.meta.url))
const APP = resolve(HERE, "../../bb_report_manager")
const OUT = resolve(APP, "public/reports")

const html = readFileSync(join(OUT, "index.html"), "utf-8")
if (!html.includes("</head>")) {
	console.error("make-page: built index.html has no </head>")
	process.exit(1)
}
if (/\{\{|\{%/.test(html)) {
	console.error("make-page: built index.html contains Jinja delimiters")
	process.exit(1)
}

const page = html.replace(
	"</head>",
	'    <script>window.csrf_token = "{{ csrf_token }}"; window.bbreport_user = {{ user_full_name | tojson }};</script>\n  </head>',
)
const target = resolve(APP, "www/bb-reports.html")
mkdirSync(dirname(target), { recursive: true })
writeFileSync(target, page)
// The shell is served by Frappe, not from /assets.
rmSync(join(OUT, "index.html"))
console.log(`make-page: wrote ${relative(resolve(APP, ".."), target)}`)
