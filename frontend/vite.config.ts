import { fileURLToPath, URL } from "node:url"

import vue from "@vitejs/plugin-vue"
import { defineConfig } from "vitest/config"

const APP = "bb_report_manager"
// dns_multitenant bench: the dev proxy must send the site name as Host
const SITE = process.env.BBREPORT_SITE || "bbacademy-erp.dreamtechsolution.com"

export default defineConfig({
	plugins: [vue()],
	base: `/assets/${APP}/reports/`,
	resolve: {
		alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
	},
	build: {
		outDir: `../${APP}/public/reports`,
		emptyOutDir: true,
		target: "es2019",
		sourcemap: false,
		rollupOptions: {
			output: {
				entryFileNames: "assets/[name].[hash].js",
				chunkFileNames: "assets/[name].[hash].js",
				assetFileNames: "assets/[name].[hash].[ext]",
			},
		},
	},
	server: {
		port: 8084,
		proxy: {
			"^/(api|assets|files|private|login)": {
				target: process.env.BBREPORT_BACKEND || "http://127.0.0.1:8000",
				changeOrigin: false,
				headers: { Host: SITE },
			},
		},
	},
	test: {
		environment: "jsdom",
	},
})
