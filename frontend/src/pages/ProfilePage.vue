<template>
  <main class="min-h-screen bg-paper px-4 py-5 sm:px-7 sm:py-7">
    <div class="mx-auto max-w-6xl">
      <header class="flex flex-wrap items-center justify-between gap-4">
        <div><p class="text-xs font-semibold uppercase tracking-[0.18em] text-amber">BookPath AI</p><h1 class="mt-2 text-3xl font-semibold text-navy">我的学习画像</h1><p class="mt-2 text-sm text-black/45">你拥有最终决定权，手工修改的记忆不会被 AI 覆盖。</p></div>
        <RouterLink class="rounded-xl border border-black/10 bg-white px-4 py-3 text-sm font-medium text-navy" to="/workspace">返回工作台</RouterLink>
      </header>

      <div v-if="store.loading && !store.profile" class="mt-7 grid gap-5 lg:grid-cols-2"><div v-for="n in 2" :key="n" class="h-80 animate-pulse rounded-3xl bg-white" /></div>
      <div v-else class="mt-7 grid items-start gap-5 lg:grid-cols-[minmax(0,1.05fr)_minmax(360px,.95fr)]">
        <form class="rounded-3xl bg-white p-5 shadow-card sm:p-7" @submit.prevent="saveProfile">
          <h2 class="text-lg font-semibold text-navy">基础画像</h2>
          <div class="mt-5 grid gap-4 sm:grid-cols-2">
            <label><span class="label">年级</span><select v-model="form.grade" class="field"><option v-for="item in grades" :key="item">{{ item }}</option></select></label>
            <label><span class="label">专业</span><select v-model="form.major" class="field"><option v-for="item in majors" :key="item">{{ item }}</option></select></label>
          </div>
          <label class="mt-4 block"><span class="label">现有基础</span><select v-model="form.foundation" class="field"><option v-for="item in foundations" :key="item">{{ item }}</option></select></label>
          <fieldset class="mt-5"><legend class="label">学习目标</legend><div class="mt-2 flex flex-wrap gap-2"><button v-for="item in goalOptions" :key="item" class="chip" :class="form.learningGoals.includes(item) && 'chip-active'" type="button" @click="toggle(form.learningGoals, item)">{{ item }}</button></div></fieldset>
          <fieldset class="mt-5"><legend class="label">兴趣方向</legend><div class="mt-2 flex flex-wrap gap-2"><button v-for="item in interestOptions" :key="item" class="chip" :class="form.interests.includes(item) && 'chip-active'" type="button" @click="toggle(form.interests, item)">{{ item }}</button></div></fieldset>
          <div class="mt-5"><CourseSelector v-model="coursesText" :grade="form.grade" :major="form.major" /></div>
          <div class="mt-5 grid gap-4 sm:grid-cols-2"><label><span class="label">难度偏好</span><select v-model="form.difficultyPreference" class="field"><option value="beginner">轻松入门</option><option value="progressive">循序渐进</option><option value="intermediate">有一定挑战</option><option value="advanced">偏进阶</option></select></label><label><span class="label">职业方向</span><select v-model="form.careerDirection" class="field"><option value="">暂未确定</option><option v-for="item in careerOptions" :key="item">{{ item }}</option></select></label></div>
          <p v-if="saved" class="mt-4 text-sm text-sage" role="status">画像已保存，并记录为手工优先版本。</p>
          <button class="mt-6 min-h-11 rounded-xl bg-navy px-6 font-semibold text-white" type="submit">保存画像</button>
        </form>

        <section class="rounded-3xl bg-white p-5 shadow-card sm:p-7">
          <div class="flex items-start justify-between gap-3"><div><h2 class="text-lg font-semibold text-navy">动态记忆</h2><p class="mt-1 text-xs leading-5 text-black/40">来自对话的长期信息会在这里显示；临时条件不会写入。</p></div><label class="flex shrink-0 items-center gap-2 text-xs text-black/50"><input v-model="showHistory" type="checkbox" @change="store.load(showHistory)" />历史</label></div>
          <div class="mt-5 space-y-3">
            <article v-for="memory in store.memories" :key="memory.id" class="rounded-2xl border p-4" :class="memory.is_active ? 'border-black/8' : 'border-black/5 bg-black/[.02] opacity-60'">
              <div class="flex items-start justify-between gap-3"><div><div class="flex flex-wrap items-center gap-2"><span class="text-xs font-semibold text-sage">{{ categoryLabel(memory.category) }}</span><span class="rounded-full bg-paper px-2 py-1 text-[10px] text-black/40">{{ sourceLabel(memory.source) }}</span><span v-if="memory.is_user_edited" class="rounded-full bg-amber/15 px-2 py-1 text-[10px] text-navy">手工优先</span></div><p class="mt-2 text-sm leading-6 text-black/65">{{ memoryValue(memory.value_json) }}</p><p class="mt-2 text-[10px] text-black/30">置信度 {{ Math.round(memory.confidence * 100) }}% · {{ formatDate(memory.created_at) }}</p></div><div v-if="memory.is_active" class="flex gap-2"><button class="text-xs text-navy" type="button" @click="startEdit(memory)">修改</button><button class="text-xs text-red-600" type="button" @click="store.removeMemory(memory.id)">删除</button></div></div>
              <form v-if="editingId === memory.id" class="mt-3 flex gap-2" @submit.prevent="saveMemory(memory.id)"><input v-model="editValue" class="field mt-0" aria-label="记忆内容" /><button class="rounded-xl bg-navy px-3 text-xs text-white">保存</button><button class="text-xs text-black/40" type="button" @click="editingId = null">取消</button></form>
            </article>
            <p v-if="!store.memories.length" class="rounded-2xl bg-paper px-4 py-8 text-center text-sm text-black/40">继续和 AI 对话，长期学习信息会逐步沉淀在这里。</p>
          </div>
        </section>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import CourseSelector from '@/components/auth/CourseSelector.vue'
import { useProfileStore } from '@/stores/profile'
import type { DifficultyPreference } from '@/types/auth'
import type { MemorySource, ProfileMemoryData } from '@/types/profile'
import { splitTags } from '@/utils/registration'

const store = useProfileStore()
const showHistory = ref(false); const saved = ref(false); const editingId = ref<string | null>(null); const editValue = ref('')
const form = reactive({ grade: '大一', major: '计算机科学与技术', foundation: '没有编程基础，希望从概念和案例开始', learningGoals: [] as string[], interests: [] as string[], difficultyPreference: 'progressive' as DifficultyPreference, courses: [] as string[], careerDirection: '' })
const coursesText = computed({ get: () => form.courses.join('，'), set: (value: string) => { form.courses = splitTags(value) } })
const grades = ['大一', '大二', '大三', '大四', '研究生', '其他']; const majors = ['计算机科学与技术', '软件工程', '人工智能', '数据科学与大数据技术', '网络工程', '信息安全', '数字媒体技术', '其他']
const foundations = ['没有编程基础，希望从概念和案例开始', '了解基本编程概念，需要通过练习巩固', '能够独立完成简单程序，希望提升工程能力', '有完整项目经验，希望深入原理和高级实践']
const goalOptions = ['课程预习与复习', '掌握编程入门', '完成课程项目', '准备考试', '提升工程实践', '拓展专业方向']; const interestOptions = ['项目案例', 'Web 开发', '人工智能', '数据分析', '算法与竞赛', '移动开发', '网络安全', '理论原理']; const careerOptions = ['后端开发', '前端开发', '全栈开发', '数据分析', '算法工程', '人工智能', '测试与质量', '网络安全', '产品与项目管理']
onMounted(async () => { await store.load(); if (store.profile) Object.assign(form, { grade: store.profile.grade, major: store.profile.major, foundation: store.profile.foundation, learningGoals: [...store.profile.learning_goals], interests: [...store.profile.interests], difficultyPreference: store.profile.difficulty_preference, courses: [...store.profile.courses], careerDirection: store.profile.career_direction ?? '' }) })
function toggle(values: string[], item: string) { const index = values.indexOf(item); if (index >= 0) values.splice(index, 1); else values.push(item) }
async function saveProfile() { saved.value = false; await store.save({ grade: form.grade, major: form.major, foundation: form.foundation, learning_goals: form.learningGoals, interests: form.interests, difficulty_preference: form.difficultyPreference, courses: form.courses, career_direction: form.careerDirection || null }); saved.value = true }
function memoryValue(value: unknown) { if (typeof value === 'object' && value !== null) { const record = value as Record<string, unknown>; return String(record.label ?? record.topic ?? JSON.stringify(value)) } return String(value) }
function startEdit(memory: ProfileMemoryData) { editingId.value = memory.id; editValue.value = memoryValue(memory.value_json) }
async function saveMemory(id: string) { await store.editMemory(id, editValue.value.trim()); editingId.value = null }
function categoryLabel(value: string) { return ({ foundation: '学习基础', interest: '兴趣方向', profile: '基础画像' } as Record<string, string>)[value] ?? value }
function sourceLabel(value: MemorySource) { return ({ registration: '注册', conversation: '对话提取', manual: '手工修改', feedback: '反馈' })[value] }
function formatDate(value: string) { return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
</script>

<style scoped>
.label { @apply text-sm font-medium text-navy; }
.field { @apply mt-2 min-h-11 w-full rounded-xl border border-black/10 bg-white px-3 text-sm outline-none focus:border-navy focus:ring-4 focus:ring-navy/5; }
.chip { @apply min-h-10 rounded-full border border-black/10 px-3 text-sm text-black/55; }
.chip-active { @apply border-navy bg-navy text-white; }
</style>
