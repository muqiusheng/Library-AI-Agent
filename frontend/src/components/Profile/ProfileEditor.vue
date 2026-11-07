<template>
  <div class="space-y-6">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div><h1 class="text-2xl font-semibold text-navy">我的学习画像</h1><p class="mt-2 text-sm leading-6 text-ink/60">{{ store.effectiveProfile && !store.errorMessage ? '这里展示当前用于推荐的信息。手工确认的内容需要你同意后才会更新。' : '读取画像后，你可以查看推荐使用的信息及其来源。' }}</p></div>
      <button class="secondary" :disabled="store.loading || busy" @click="reload">{{ store.loading ? '同步中…' : '刷新画像' }}</button>
    </header>
    <div v-if="store.errorMessage" role="alert" class="rounded-xl border border-amber/30 bg-amber/10 p-4 text-sm leading-6 text-navy">{{ store.errorMessage }}。当前保留上次读取的内容，请刷新后确认。</div>
    <p v-if="saved" role="status" class="text-sm text-moss">画像已更新，后续推荐会使用最新信息。</p>
    <div v-if="store.loading && !store.effectiveProfile" role="status" class="rounded-3xl bg-white p-8 text-sm text-ink/60">正在读取有效画像…</div>
    <template v-else>
      <article v-if="display" class="grid gap-8 rounded-3xl bg-white p-6 shadow-card sm:p-8 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.8fr)]">
        <section class="min-w-0">
          <div class="flex items-start justify-between gap-4"><div><p class="text-xs font-medium tracking-wider text-ink/55">{{ store.effectiveProfile ? '当前生效' : '基础填写 · 待同步' }}</p><h2 class="mt-2 break-words text-2xl font-semibold text-navy">{{ display.major || '专业尚未填写' }}</h2><p class="mt-2 text-sm text-ink/70">{{ display.grade || '年级尚未填写' }}</p><SourceNote :source="sources.major" /><SourceNote v-if="sources.grade" :source="sources.grade" /></div><button class="secondary shrink-0" @click="beginEdit">修改画像</button></div>
          <dl class="mt-7 space-y-6">
            <div><dt class="caption">学习基础</dt><dd class="mt-2 whitespace-pre-wrap break-words text-sm leading-7 text-navy">{{ foundation || '尚未说明' }}</dd><SourceNote v-if="!Object.keys(store.effectiveProfile?.abilities ?? {}).length" :source="sources.foundation" /></div>
            <div><dt class="caption">难度偏好</dt><dd class="mt-2 text-sm font-medium text-navy">{{ difficultyLabels[display.difficulty_preference] }}</dd><SourceNote :source="sources.difficulty_preference" /></div>
            <div><dt class="caption">学习目标</dt><dd class="mt-2 flex flex-wrap gap-2"><span v-for="item in display.learning_goals" :key="item" class="tag">{{ item }}</span><span v-if="!display.learning_goals.length" class="text-sm text-ink/50">暂未设置</span></dd><SourceNote :source="sources.learning_goals" /></div>
            <div><dt class="caption">兴趣方向</dt><dd class="mt-2 flex flex-wrap gap-2"><span v-for="item in display.interests" :key="item" class="tag bg-sage/15 text-moss">{{ item }}</span><span v-if="!display.interests.length" class="text-sm text-ink/50">暂未设置</span></dd><SourceNote :source="sources.interests" /></div>
            <div><dt class="caption">当前课程</dt><dd class="mt-2 break-words text-sm leading-6 text-ink/70">{{ store.profile?.courses.join('、') || '暂未设置' }}</dd></div>
          </dl>
        </section>
        <div class="min-w-0 rounded-2xl bg-paper p-5 sm:p-6"><AbilityProfile :profile="store.effectiveProfile" /></div>
      </article>
      <section v-else class="rounded-3xl bg-white p-7 text-sm text-ink/60">暂无可展示的画像，请刷新重试。</section>
      <section class="rounded-3xl bg-white p-5 shadow-card sm:p-7" aria-labelledby="memory-heading">
        <div class="flex flex-wrap items-center justify-between gap-4"><div><h2 id="memory-heading" class="text-lg font-semibold text-navy">画像记录与依据</h2><p class="mt-2 text-xs leading-6 text-ink/60">“当前生效”的记录已用于画像。历史版本仅供追溯，学习成就单独保留为学习记录。</p></div><label class="flex min-h-11 cursor-pointer items-center gap-2 text-sm text-ink/70"><input type="checkbox" :checked="store.showHistory" :disabled="store.loading || busy" @change="changeHistory" />显示历史版本</label></div>
        <p class="mt-3 text-xs text-ink/55 sm:hidden">左右滑动表格可查看来源与操作。</p>
        <div class="mt-5 overflow-x-auto rounded-2xl border border-ink/10" tabindex="0" aria-label="画像记录，可横向滚动">
          <table class="w-full min-w-[660px] text-left text-sm"><thead class="bg-paper text-xs text-ink/65"><tr><th class="cell font-medium">类型与状态</th><th class="cell font-medium">内容</th><th class="cell font-medium">来源与时间</th><th class="cell font-medium">操作</th></tr></thead>
            <tbody class="divide-y divide-ink/10"><tr v-for="memory in paginatedMemories" :key="memory.id" :class="!memory.is_active && 'text-ink/55'"><td class="cell"><p class="font-medium text-navy">{{ categoryLabel(memory.category) }}</p><p class="mt-1 text-xs" :class="memoryStatus(memory, store.effectiveProfile) === '当前生效' ? 'text-moss' : 'text-ink/55'">{{ memoryStatus(memory, store.effectiveProfile) }}</p></td><td class="cell max-w-sm"><p v-if="editingId !== memory.id" class="whitespace-pre-wrap break-words leading-6">{{ memoryValue(memory.value_json) }}</p><form v-else class="space-y-2" @submit.prevent="saveMemory(memory)"><select v-if="memory.category === 'foundation'" v-model="editValue" class="field" aria-label="知识点水平"><option v-for="(label, level) in abilityLabels" :key="level" :value="level">{{ label }}</option></select><input v-else v-model="editValue" class="field" aria-label="记忆内容" /><p v-if="Array.isArray(memory.value_json)" class="text-xs text-ink/55">多项内容用逗号分隔；留空可清除。</p><div class="flex gap-2"><button class="primary" :disabled="busy">保存</button><button type="button" class="secondary" :disabled="busy" @click="editingId = null">取消</button></div></form></td><td class="cell text-xs leading-6 text-ink/60"><p>{{ sourceLabels[memory.source] }}</p><p>{{ formatProfileDate(memory.created_at) }}</p><p v-if="memory.is_user_edited" class="text-moss">手工确认</p><details v-if="evidenceFor(memory)" class="mt-1"><summary class="cursor-pointer">查看原文依据</summary><p class="mt-2 max-w-xs whitespace-pre-wrap break-words">{{ evidenceFor(memory) }}</p></details></td><td class="cell"><div v-if="memory.is_active" class="flex flex-wrap gap-2"><button v-if="canEdit(memory)" class="secondary" :disabled="busy" @click="startEdit(memory)">修改</button><button class="secondary text-red-700" :disabled="busy" @click="removeMemory(memory.id)">删除</button></div><span v-else class="text-xs text-ink/50">已失效</span></td></tr><tr v-if="!store.memories.length"><td colspan="4" class="p-7 text-center leading-7 text-ink/60">暂无画像记录。你可以在对话中说明自己的基础、目标和长期偏好。</td></tr></tbody>
          </table>
        </div>
        <nav v-if="store.memories.length" aria-label="画像记录分页" class="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-ink/60"><span class="tabular-nums">共 {{ store.memories.length }} 条 · 第 {{ currentPage }} / {{ maxPage }} 页</span><div class="flex gap-2"><button class="secondary" :disabled="currentPage <= 1" @click="currentPage--">上一页</button><button class="secondary" :disabled="currentPage >= maxPage" @click="currentPage++">下一页</button></div></nav>
      </section>
    </template>
    <dialog ref="editDialog" aria-labelledby="profile-edit-heading" class="w-[calc(100%-2rem)] max-w-lg rounded-3xl bg-white p-0 text-ink shadow-card">
      <form class="space-y-5 p-6 sm:p-8" @submit.prevent="saveProfile">
        <div class="flex items-center justify-between gap-3"><h2 id="profile-edit-heading" class="text-xl font-semibold text-navy">修改画像</h2><button class="secondary" type="button" aria-label="关闭修改画像" :disabled="busy" @click="editDialog?.close()">关闭</button></div>
        <p class="text-xs leading-6 text-ink/60">只保存你改动的内容，其他对话记忆会保留。</p>
        <p v-if="store.errorMessage" role="alert" class="text-sm text-red-700">{{ store.errorMessage }}</p>
        <div class="grid gap-4 sm:grid-cols-2"><label><span class="caption">年级</span><input v-model="form.grade" class="field" required /></label><label><span class="caption">专业</span><input v-model="form.major" class="field" required /></label></div>
        <label class="block"><span class="caption">基础说明</span><textarea v-model="form.foundation" class="field min-h-24 py-3" required /><span class="mt-2 block text-xs leading-6 text-ink/60">修改此项会以新说明重新整理知识点基础；也可以在下方记录中单独修改某个知识点。</span></label>
        <label class="block"><span class="caption">学习目标</span><input v-model="goalsText" class="field" /><span class="mt-1 block text-xs text-ink/55">多项内容用逗号分隔，留空表示暂未设置。</span></label>
        <label class="block"><span class="caption">兴趣方向</span><input v-model="interestsText" class="field" /></label>
        <label class="block"><span class="caption">难度偏好</span><select v-model="form.difficulty_preference" class="field"><option v-for="(label, value) in difficultyLabels" :key="value" :value="value">{{ label }}</option></select></label>
        <CourseSelector v-model="coursesText" :grade="form.grade" :major="form.major" />
        <label class="block"><span class="caption">职业方向</span><input v-model="form.career_direction" class="field" /></label>
        <div class="flex justify-end gap-3"><button class="secondary" type="button" :disabled="busy" @click="editDialog?.close()">取消</button><button class="primary" :disabled="busy">{{ busy ? '保存中…' : '保存更改' }}</button></div>
      </form>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import CourseSelector from '@/components/auth/CourseSelector.vue'
import AbilityProfile from './AbilityProfile.vue'
import SourceNote from './SourceNote.vue'
import { useProfileStore } from '@/stores/profile'
import type { ProfileSummary } from '@/types/auth'
import type { ProfileMemoryData, ProfileUpdatePayload } from '@/types/profile'
import { abilityLabels, categoryLabel, difficultyLabels, foundationText, formatProfileDate, memoryStatus, memoryValue, sourceLabels } from '@/utils/profilePresentation'

const store = useProfileStore()
const display = computed(() => store.displayProfile)
const sources = computed(() => store.effectiveProfile?.sources ?? {})
const foundation = computed(() => foundationText(store.effectiveProfile, display.value?.foundation ?? ''))
const busy = ref(false)
const saved = ref(false)
const editDialog = ref<HTMLDialogElement | null>(null)
const currentPage = ref(1)
const maxPage = computed(() => Math.max(1, Math.ceil(store.memories.length / 10)))
const paginatedMemories = computed(() => store.memories.slice((currentPage.value - 1) * 10, currentPage.value * 10))
watch(maxPage, value => { currentPage.value = Math.min(currentPage.value, value) })
const editingId = ref<string | null>(null)
const editValue = ref('')
const form = reactive<ProfileSummary>({ grade: '', major: '', foundation: '', learning_goals: [], interests: [], difficulty_preference: 'progressive', courses: [], read_books: [], career_direction: null })
let initial: ProfileSummary = JSON.parse(JSON.stringify(form))
const split = (value: string) => [...new Set(value.split(/[，,、\n]/).map(item => item.trim()).filter(Boolean))]
const goalsText = computed({ get: () => form.learning_goals.join('，'), set: value => { form.learning_goals = split(value) } })
const interestsText = computed({ get: () => form.interests.join('，'), set: value => { form.interests = split(value) } })
const coursesText = computed({ get: () => form.courses.join('，'), set: value => { form.courses = split(value) } })
onMounted(reload)
async function reload() { try { await store.load() } catch { /* The store exposes a retryable error. */ } }
async function changeHistory(event: Event) { const input = event.target as HTMLInputElement; try { await store.load(input.checked); currentPage.value = 1 } catch { input.checked = store.showHistory } }
function beginEdit() {
  saved.value = false
  Object.assign(form, store.profile, display.value, { foundation: store.profile?.foundation ?? '', courses: [...(store.profile?.courses ?? [])], read_books: [...(store.profile?.read_books ?? [])], career_direction: store.profile?.career_direction ?? null })
  initial = JSON.parse(JSON.stringify(form))
  editDialog.value?.showModal()
}
async function saveProfile() {
  const patch: ProfileUpdatePayload = {}
  const fields = ['grade', 'major', 'foundation', 'learning_goals', 'interests', 'difficulty_preference', 'courses', 'career_direction'] as const
  for (const field of fields) if (JSON.stringify(form[field]) !== JSON.stringify(initial[field])) Object.assign(patch, { [field]: form[field] })
  if (!Object.keys(patch).length) { editDialog.value?.close(); return }
  busy.value = true
  try { await store.save(patch); editDialog.value?.close(); saved.value = true } catch { /* Keep the form and show the store error. */ } finally { busy.value = false }
}
function canEdit(memory: ProfileMemoryData) { return memory.category === 'foundation' ? typeof memory.value_json === 'object' && memory.value_json !== null : Array.isArray(memory.value_json) || typeof memory.value_json === 'string' }
function startEdit(memory: ProfileMemoryData) {
  editingId.value = memory.id
  if (memory.category === 'foundation') { const level = (memory.value_json as { level?: string }).level; editValue.value = level === 'beginner' ? 'basic' : level ?? 'unknown' }
  else editValue.value = Array.isArray(memory.value_json) ? memory.value_json.join('，') : String(memory.value_json ?? '')
}
async function saveMemory(memory: ProfileMemoryData) {
  busy.value = true
  let value: unknown = editValue.value.trim()
  if (memory.category === 'foundation') value = { ...(memory.value_json as object), level: editValue.value }
  else if (Array.isArray(memory.value_json)) value = split(editValue.value)
  try { await store.editMemory(memory.id, value); editingId.value = null; saved.value = true } catch { /* Keep the editor open. */ } finally { busy.value = false }
}
async function removeMemory(id: string) { busy.value = true; try { await store.removeMemory(id); saved.value = true } catch { /* The store shows the error. */ } finally { busy.value = false } }
function evidenceFor(memory: ProfileMemoryData) { return Object.values(sources.value).find(source => source.memory_id === memory.id)?.evidence }
</script>

<style scoped>
.caption { @apply block text-xs font-medium tracking-wider text-ink/60; }
.field { @apply mt-2 min-h-11 w-full rounded-xl border border-ink/15 bg-paper px-3 text-sm text-navy outline-none focus:border-navy focus:ring-2 focus:ring-navy/10; }
.primary { @apply min-h-11 rounded-xl bg-navy px-4 text-sm font-medium text-white transition-colors hover:bg-navy/90 disabled:cursor-wait disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy; }
.secondary { @apply min-h-11 rounded-xl border border-ink/10 px-3 text-sm font-medium text-navy transition-colors hover:bg-ink/5 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy; }
.tag { @apply rounded-lg bg-paper px-3 py-1.5 text-xs font-medium text-navy; }
.cell { @apply px-4 py-3 align-top; }
dialog { max-height: 90vh; overflow-y: auto; }
dialog::backdrop { background: rgb(0 0 0 / 0.4); }
</style>
