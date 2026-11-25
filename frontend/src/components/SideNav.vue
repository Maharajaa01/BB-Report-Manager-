<script setup lang="ts">
import { computed } from "vue"

import { DASHBOARDS, type Dashboard, reportsOf, routeName } from "@/lib/reports"

const props = defineProps<{ dashboard: Dashboard }>()
const reports = computed(() => reportsOf(props.dashboard))
const heading = computed(() => DASHBOARDS.find((d) => d.key === props.dashboard)?.title ?? "")
</script>

<template>
	<nav class="bbr-sidebar" aria-label="Reports">
		<h4>{{ heading }}</h4>
		<template v-for="(r, i) in reports" :key="r.key">
			<RouterLink
				v-if="r.ready"
				class="bbr-nav-item"
				active-class="active"
				:to="{ name: routeName(dashboard), params: { report: r.path }, query: $route.query }"
			>
				<span class="bbr-nav-swatch" :style="{ background: r.bg }"></span>
				<span>{{ i + 1 }}. {{ r.nav }}</span>
			</RouterLink>
			<button v-else type="button" class="bbr-nav-item" disabled>
				<span class="bbr-nav-swatch" :style="{ background: r.bg }"></span>
				<span>{{ i + 1 }}. {{ r.nav }}</span>
				<span class="bbr-nav-soon">Soon</span>
			</button>
		</template>
	</nav>
</template>
