/// <reference types="vite/client" />

declare module "*.vue" {
	import type { DefineComponent } from "vue"
	const component: DefineComponent<object, object, unknown>
	export default component
}

interface Window {
	csrf_token?: string
	/** Full name of the signed-in user (set by www/bb-reports.html). */
	bbreport_user?: string
}
