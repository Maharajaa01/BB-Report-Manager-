<script setup lang="ts">
import type { ReportDef } from "@/lib/reports"

defineProps<{ report: ReportDef }>()
</script>

<template>
	<div class="bbr-state">{{ report.nav }} is coming next.</div>
</template>
