<script setup lang="ts">
/**
 * The records behind any clicked number -- students, or enquiries for the
 * enquiry sheet -- with search, status tags, parent contact and Excel export.
 * The parent passes `load` (whatever API call fits the report); a new `load`
 * opens the dialog, null closes it.
 */
import { computed, ref, watch } from "vue"

import type { DetailResult, EnquiryDetail, StudentDetail } from "@/api/types"
import { downloadCsv, slug } from "@/lib/csv"
import { date } from "@/lib/format"

const props = defineProps<{
	load: (() => Promise<DetailResult>) | null
	title: string
	filterSummary: string
	tuitionUrl: string
}>()
const emit = defineEmits<{ close: [] }>()

const dialog = ref<HTMLDialogElement | null>(null)
const result = ref<DetailResult | null>(null)
const loading = ref(false)
const error = ref("")
const search = ref("")
let seq = 0

watch(
	() => props.load,
	async (load) => {
		if (!load) {
			if (dialog.value?.open) dialog.value.close()
			return
		}
		const mine = ++seq
		search.value = ""
		result.value = null
		error.value = ""
		loading.value = true
		if (!dialog.value?.open) dialog.value?.showModal()
		try {
			const r = await load()
			if (mine === seq) result.value = r
		} catch (e) {
			if (mine === seq) error.value = (e as Error).message
		} finally {
			if (mine === seq) loading.value = false
		}
	},
)

const matches = (q: string, values: (string | null | undefined)[]) =>
	!q || values.some((v) => String(v || "").toLowerCase().includes(q))

const students = computed<StudentDetail[]>(() => {
	if (result.value?.type !== "student") return []
	const q = search.value.trim().toLowerCase()
	return result.value.rows.filter((s) => matches(q, [s.student, s.student_name, s.father_name, s.mobile, s.school, s.area]))
})

const enquiries = computed<EnquiryDetail[]>(() => {
	if (result.value?.type !== "enquiry") return []
	const q = search.value.trim().toLowerCase()
	return result.value.rows.filter((e) =>
		matches(q, [e.enquiry, e.applicant_name, e.father_name, e.mobile, e.school, e.area, e.source, e.status]),
	)
})

const shownCount = computed(() => (result.value?.type === "enquiry" ? enquiries.value.length : students.value.length))
const totalCount = computed(() => result.value?.rows.length ?? 0)
const noun = computed(() => (result.value?.type === "enquiry" ? "enquir" : "student"))
const plural = (n: number) => (noun.value === "enquir" ? (n === 1 ? "enquiry" : "enquiries") : n === 1 ? "student" : "students")

const link = (doctype: string, name: string) => `${props.tuitionUrl}/app/${doctype}/${encodeURIComponent(name)}`
// A rejoined student is Active again but still carries the date they left.
const hasLeft = (s: StudentDetail) => s.status !== "Active" || !!s.rejoined_date

function exportCsv() {
	const head = [[props.title], [props.filterSummary], []]
	if (result.value?.type === "enquiry") {
		downloadCsv(slug(props.title), [
			...head,
			["Enquiry No", "Applicant", "Father", "Enquiry date", "Standard", "Group", "Gender", "Status", "Source",
				"Mobile", "School", "Area", "Next follow-up", "Remarks"],
			...enquiries.value.map((e) => [e.enquiry, e.applicant_name, e.father_name, date(e.enquiry_date), e.standard,
				e.group, e.gender, e.status, e.source, e.mobile, e.school, e.area, date(e.next_follow_up_date), e.remarks]),
		])
		return
	}
	downloadCsv(slug(props.title), [
		...head,
		["Admission No", "Student", "Father", "Standard", "Batch", "Gender", "Joined", "Status", "Left on", "Reason",
			"Rejoined on", "Parent mobile", "School", "Area", "Monthly fee", "This month"],
		...students.value.map((s) => [s.student, s.student_name, s.father_name, s.standard, s.batch, s.gender,
			date(s.admission_date), s.status, date(s.discontinued_date), s.discontinue_reason, date(s.rejoined_date),
			s.mobile, s.school, s.area, s.monthly_fee, s.events.join(" / ")]),
	])
}
</script>

<template>
	<dialog ref="dialog" class="bbr-dialog" @close="emit('close')">
		<div class="bbr-dialog-head">
			<h3>{{ title }}</h3>
			<button type="button" aria-label="Close" @click="dialog?.close()">&times;</button>
		</div>
		<div class="bbr-dialog-body">
			<div v-if="loading" class="bbr-state">Loading…</div>
			<div v-else-if="error" class="bbr-state error">{{ error }}</div>
			<template v-else-if="result">
				<div class="bbr-detail-tools">
					<input v-model="search" type="search" placeholder="Search name, number, mobile, school…" />
					<span class="bbr-detail-count">{{ shownCount }} of {{ totalCount }} {{ plural(totalCount) }}</span>
					<button type="button" class="bbr-btn secondary" @click="exportCsv">Export to Excel</button>
				</div>

				<div class="bbr-table-scroll">
					<table v-if="result.type === 'enquiry'" class="bbr-table bbr-list">
						<thead>
							<tr>
								<th>#</th><th>Enquiry No</th><th>Applicant</th><th>Date</th><th>Std / Group</th><th>Gender</th>
								<th>Status</th><th>Source</th><th>Mobile</th><th>School / Area</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="(e, i) in enquiries" :key="e.enquiry">
								<td>{{ i + 1 }}</td>
								<td class="nowrap">
									<a :href="link('student-enquiry-form', e.enquiry)" target="_blank" rel="noopener">{{ e.enquiry }}</a>
								</td>
								<td>
									<b>{{ e.applicant_name }}</b>
									<template v-if="e.father_name"><br /><small>F: {{ e.father_name }}</small></template>
									<template v-if="e.remarks"><br /><small>{{ e.remarks }}</small></template>
								</td>
								<td class="nowrap">{{ date(e.enquiry_date) }}</td>
								<td>
									{{ e.standard }}
									<!-- only 11th / 12th are split into subject groups -->
									<template v-if="e.group || /^1[12]/.test(e.standard)">
										<br /><small>{{ e.group || "Group not set" }}</small>
									</template>
								</td>
								<td>{{ e.gender }}</td>
								<td>
									<span class="bbr-tag" :class="`enq-${e.status.toLowerCase()}`">{{ e.status }}</span>
									<template v-if="e.next_follow_up_date"><br /><small>Follow-up {{ date(e.next_follow_up_date) }}</small></template>
								</td>
								<td>{{ e.source }}</td>
								<td><a v-if="e.mobile" :href="`tel:${e.mobile}`">{{ e.mobile }}</a></td>
								<td>
									{{ e.school }}
									<template v-if="e.area"><br /><small>{{ e.area }}</small></template>
								</td>
							</tr>
							<tr v-if="!enquiries.length"><td colspan="10" class="bbr-empty">No enquiries</td></tr>
						</tbody>
					</table>

					<table v-else class="bbr-table bbr-list">
						<thead>
							<tr>
								<th>#</th><th>Adm. No</th><th>Student</th><th>Std</th><th>Batch</th><th>Gender</th>
								<th>Joined</th><th>Status</th><th>Parent mobile</th><th>School / Area</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="(s, i) in students" :key="s.student">
								<td>{{ i + 1 }}</td>
								<td class="nowrap"><a :href="link('student', s.student)" target="_blank" rel="noopener">{{ s.student }}</a></td>
								<td>
									<b>{{ s.student_name }}</b>
									<template v-if="s.father_name"><br /><small>F: {{ s.father_name }}</small></template>
									<span v-for="ev in s.events" :key="ev" class="bbr-tag" :class="ev.toLowerCase()">{{ ev }}</span>
									<span v-if="s.scholarship" class="bbr-tag">Scholarship</span>
								</td>
								<td>{{ s.standard }}</td>
								<td>{{ s.batch }}</td>
								<td>{{ s.gender }}</td>
								<td class="nowrap">{{ date(s.admission_date) }}</td>
								<td>
									<span class="bbr-status" :class="s.status.toLowerCase()">{{ s.status }}</span>
									<template v-if="s.discontinued_date && hasLeft(s)"><br /><small>Left {{ date(s.discontinued_date) }}</small></template>
									<template v-if="s.discontinue_reason && hasLeft(s)"><br /><small>{{ s.discontinue_reason }}</small></template>
									<template v-if="s.rejoined_date"><br /><small>Rejoined {{ date(s.rejoined_date) }}</small></template>
								</td>
								<td><a v-if="s.mobile" :href="`tel:${s.mobile}`">{{ s.mobile }}</a></td>
								<td>
									{{ s.school }}
									<template v-if="s.area"><br /><small>{{ s.area }}</small></template>
								</td>
							</tr>
							<tr v-if="!students.length"><td colspan="10" class="bbr-empty">No students</td></tr>
						</tbody>
					</table>
				</div>
			</template>
		</div>
	</dialog>
</template>
