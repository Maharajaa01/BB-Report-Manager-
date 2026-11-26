<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue"
import { useRoute } from "vue-router"

import SideNav from "@/components/SideNav.vue"
import { DASHBOARDS, type Dashboard, defaultQuery, reportsOf, routeName } from "@/lib/reports"
import { loadOptions } from "@/lib/store"

const route = useRoute()
const userName = window.bbreport_user || ""
const menuOpen = ref(false)
const dashboard = computed<Dashboard>(() => (route.meta.dashboard as Dashboard) || "manager")
const title = computed(() => DASHBOARDS.find((d) => d.key === dashboard.value)?.title ?? "")

watch(() => route.fullPath, () => (menuOpen.value = false))
onMounted(loadOptions)
</script>

<template>
	<header class="bbr-appbar">
		<button class="bbr-menu-btn" type="button" aria-label="Reports menu" @click="menuOpen = !menuOpen">&#9776;</button>
		<div class="bbr-brand">
			<span class="bbr-brand-title">BB ACADEMY</span>
			<span class="bbr-brand-sub">{{ title }}</span>
		</div>
		<nav class="bbr-switch" aria-label="Dashboard">
			<RouterLink
				v-for="d in DASHBOARDS"
				:key="d.key"
				:class="{ active: d.key === dashboard }"
				:to="{ name: routeName(d.key), params: { report: reportsOf(d.key)[0].path }, query: { ...defaultQuery(d.key), ...route.query } }"
			>
				{{ d.label }}
			</RouterLink>
		</nav>
		<div class="bbr-user">
			<template v-if="userName">{{ userName }} · </template>
			<a href="/app/bb-reports" title="BB Reports workspace in Desk">Desk</a> · <a href="/?cmd=web_logout">Logout</a>
		</div>
	</header>

	<div class="bbr-layout">
		<SideNav :dashboard="dashboard" :class="{ open: menuOpen }" />
		<main class="bbr-main">
			<RouterView />
		</main>
	</div>
</template>
