<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-semibold text-navy">我的学习画像</h1>
      <p class="mt-2 text-sm text-black/45">你拥有最终决定权，手工修改的记忆不会被 AI 覆盖。</p>
    </div>
    <div v-if="store.loading && !store.profile" class="grid gap-5 lg:grid-cols-2"><div v-for="n in 2" :key="n" class="h-80 animate-pulse rounded-3xl bg-white" /></div>
      <div v-else class="mt-7 space-y-6">
        <!-- Hero Dashboard Card -->
        <article class="relative flex flex-col lg:flex-row gap-8 rounded-3xl bg-gradient-to-br from-[#f8fafc] to-[#e2e8f0] p-6 shadow-card sm:p-8 border border-white/50">
          <button class="absolute right-5 top-5 z-10 grid h-9 w-9 place-items-center rounded-full bg-white/60 text-navy shadow-sm backdrop-blur-md transition-colors hover:bg-white" @click="isEditingProfile = true" aria-label="修改画像">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
          </button>
          
          <div class="flex-1 space-y-8">
            <div>
              <h2 class="text-3xl font-bold tracking-tight text-navy">{{ store.profile?.major || form.major }}</h2>
              <div class="mt-2 flex items-center gap-3">
                <span class="rounded-full bg-navy px-3 py-1 text-xs font-semibold text-white">{{ store.profile?.grade || form.grade }}</span>
                <span class="rounded-full bg-white/60 px-3 py-1 text-xs font-medium text-navy shadow-sm backdrop-blur-sm">{{ store.profile?.career_direction || form.careerDirection || '职业方向未定' }}</span>
              </div>
            </div>
            
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <span class="block text-xs font-semibold text-black/40 uppercase tracking-wider">学习基础</span>
                <span class="mt-1 block font-medium text-navy">{{ store.profile?.foundation || form.foundation }}</span>
              </div>
              <div>
                <span class="block text-xs font-semibold text-black/40 uppercase tracking-wider">难度偏好</span>
                <span class="mt-1 block font-medium text-navy">
                  {{ { 'beginner': '轻松入门', 'progressive': '循序渐进', 'intermediate': '有一定挑战', 'advanced': '偏进阶' }[store.profile?.difficulty_preference || form.difficultyPreference] }}
                </span>
              </div>
            </div>

            <div class="space-y-4">
              <div>
                <span class="block text-xs font-semibold text-black/40 uppercase tracking-wider">学习目标</span>
                <div class="mt-2 flex flex-wrap gap-2">
                  <span v-for="item in (store.profile?.learning_goals?.length ? store.profile.learning_goals : form.learningGoals)" :key="item" class="rounded-lg bg-white/60 px-3 py-1.5 text-xs font-medium text-navy shadow-sm backdrop-blur-sm">{{ item }}</span>
                  <span v-if="!(store.profile?.learning_goals?.length || form.learningGoals.length)" class="text-xs text-black/30">暂未设置</span>
                </div>
              </div>
              <div>
                <span class="block text-xs font-semibold text-black/40 uppercase tracking-wider">兴趣方向</span>
                <div class="mt-2 flex flex-wrap gap-2">
                  <span v-for="item in (store.profile?.interests?.length ? store.profile.interests : form.interests)" :key="item" class="rounded-lg bg-sage/15 px-3 py-1.5 text-xs font-medium text-sage shadow-sm backdrop-blur-sm">{{ item }}</span>
                  <span v-if="!(store.profile?.interests?.length || form.interests.length)" class="text-xs text-black/30">暂未设置</span>
                </div>
              </div>
              <div>
                <span class="block text-xs font-semibold text-black/40 uppercase tracking-wider">当前课程</span>
                <div class="mt-2 flex flex-wrap gap-2">
                  <span v-for="item in (store.profile?.courses?.length ? store.profile.courses : form.courses)" :key="item" class="rounded-lg border border-black/5 bg-white/40 px-3 py-1.5 text-[11px] font-medium text-black/60 shadow-sm backdrop-blur-sm">{{ item }}</span>
                  <span v-if="!(store.profile?.courses?.length || form.courses.length)" class="text-xs text-black/30">暂未设置</span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="w-full lg:w-[400px] shrink-0 flex flex-col items-center justify-center rounded-2xl bg-white/30 p-4 shadow-inner backdrop-blur-sm">
            <h3 class="mb-4 text-sm font-semibold tracking-wider text-navy">多维能力评估</h3>
            <RadarChart v-if="store.memories.length > 0" :memories="store.memories" />
            <div v-else class="flex h-[300px] w-full items-center justify-center text-sm text-black/30">
              暂无足够数据生成图谱
            </div>
          </div>
        </article>

        <!-- Edit Profile Modal -->
        <Teleport to="body">
          <Transition enter-active-class="transition duration-200 ease-out" enter-from-class="opacity-0 scale-95" enter-to-class="opacity-100 scale-100" leave-active-class="transition duration-150 ease-in" leave-from-class="opacity-100 scale-100" leave-to-class="opacity-0 scale-95">
            <div v-if="isEditingProfile" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
              <form class="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl sm:p-8" @submit.prevent="saveProfile">
                <div class="mb-6 flex items-center justify-between">
                  <h2 class="text-xl font-semibold text-navy">修改基础画像</h2>
                  <button type="button" class="text-black/40 hover:text-black" @click="isEditingProfile = false" aria-label="关闭">
                    <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
                  </button>
                </div>
                
                <div class="mt-5 grid gap-4 sm:grid-cols-2">
                  <label><span class="label">年级</span><CustomSelect v-model="form.grade" :options="grades.map(g => ({label: g, value: g}))" /></label>
                  <label><span class="label">专业</span><CustomSelect v-model="form.major" :options="majors.map(m => ({label: m, value: m}))" /></label>
                </div>
                <label class="mt-4 block"><span class="label">现有基础</span><CustomSelect v-model="form.foundation" :options="foundations.map(f => ({label: f, value: f}))" /></label>
                <fieldset class="mt-5"><legend class="label">学习目标</legend><div class="mt-2 flex flex-wrap gap-2"><button v-for="item in goalOptions" :key="item" class="chip" :class="form.learningGoals.includes(item) && 'chip-active'" type="button" @click="toggle(form.learningGoals, item)">{{ item }}</button></div></fieldset>
                <fieldset class="mt-5"><legend class="label">兴趣方向</legend><div class="mt-2 flex flex-wrap gap-2"><button v-for="item in interestOptions" :key="item" class="chip" :class="form.interests.includes(item) && 'chip-active'" type="button" @click="toggle(form.interests, item)">{{ item }}</button></div></fieldset>
                <div class="mt-5"><CourseSelector v-model="coursesText" :grade="form.grade" :major="form.major" /></div>
                <div class="mt-5 grid gap-4 sm:grid-cols-2">
                  <label><span class="label">难度偏好</span><CustomSelect v-model="form.difficultyPreference" :options="[{label: '轻松入门', value: 'beginner'}, {label: '循序渐进', value: 'progressive'}, {label: '有一定挑战', value: 'intermediate'}, {label: '偏进阶', value: 'advanced'}]" /></label>
                  <label><span class="label">职业方向</span><CustomSelect v-model="form.careerDirection" :options="[{label: '暂未确定', value: ''}, ...careerOptions.map(c => ({label: c, value: c}))]" /></label>
                </div>
                
                <div class="mt-8 flex justify-end gap-3">
                  <button class="rounded-xl px-5 py-2.5 text-sm font-medium text-black/60 transition-colors hover:bg-black/5" type="button" @click="isEditingProfile = false">取消</button>
                  <button class="rounded-xl bg-navy px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-navy/90" type="submit">保存更改</button>
                </div>
              </form>
            </div>
          </Transition>
        </Teleport>

        <section class="rounded-3xl bg-white p-5 shadow-card sm:p-7">
          <div class="flex items-start justify-between gap-3"><div><h2 class="text-lg font-semibold text-navy">动态记忆</h2><p class="mt-1 text-xs leading-5 text-black/40">基于您的对话与学习历程生成的智能画像，随时可追溯与干预。</p></div></div>
          
          <div class="mt-5 space-y-3">
            <div class="overflow-x-auto overflow-y-hidden rounded-2xl border border-black/5">
              <table class="w-full text-left text-sm">
                <thead class="bg-paper text-xs text-black/50">
                  <tr>
                    <th class="whitespace-nowrap px-4 py-3 font-medium">类型 / 来源</th>
                    <th class="px-4 py-3 font-medium">记忆内容</th>
                    <th class="whitespace-nowrap px-4 py-3 font-medium">时间</th>
                    <th class="whitespace-nowrap px-4 py-3 font-medium">操作</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-black/5">
                  <tr v-for="memory in paginatedMemories" :key="memory.id" class="transition-colors hover:bg-black/[0.02]" :class="!memory.is_active && 'opacity-50'">
                    <td class="whitespace-nowrap px-4 py-3 align-top">
                      <div class="flex flex-col items-start gap-1">
                        <span class="font-medium text-sage">{{ categoryLabel(memory.category) }}</span>
                        <div class="flex flex-wrap gap-1">
                          <span class="rounded-full bg-paper px-1.5 py-0.5 text-[10px] text-black/40">{{ sourceLabel(memory.source) }}</span>
                          <span v-if="memory.is_user_edited" class="rounded-full bg-amber/15 px-1.5 py-0.5 text-[10px] text-navy">手工优先</span>
                        </div>
                      </div>
                    </td>
                    <td class="px-4 py-3 align-top text-black/70">
                      <p v-if="editingId !== memory.id" class="leading-relaxed">{{ memoryValue(memory.value_json) }}</p>
                      <form v-else class="flex gap-2" @submit.prevent="saveMemory(memory.id)">
                        <input v-model="editValue" class="field mt-0 min-h-8 text-xs" aria-label="记忆内容" />
                        <button class="shrink-0 rounded-lg bg-navy px-2 py-1 text-xs text-white">保存</button>
                        <button class="shrink-0 text-xs text-black/40" type="button" @click="editingId = null">取消</button>
                      </form>
                    </td>
                    <td class="whitespace-nowrap px-4 py-3 align-top text-[11px] text-black/40">
                      {{ formatDate(memory.created_at) }}<br/>
                      置信度 {{ Math.round(memory.confidence * 100) }}%
                    </td>
                    <td class="whitespace-nowrap px-4 py-3 align-top">
                      <div v-if="memory.is_active" class="flex flex-col gap-2">
                        <button class="text-left text-xs font-medium text-navy hover:underline" type="button" @click="startEdit(memory)">修改</button>
                        <button class="text-left text-xs font-medium text-red-600 hover:underline" type="button" @click="store.removeMemory(memory.id)">删除</button>
                      </div>
                    </td>
                  </tr>
                  <tr v-if="!store.memories.length">
                    <td colspan="4" class="p-8 text-center text-sm text-black/40">继续和 AI 对话，长期学习信息会逐步沉淀在这里。</td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            <div v-if="store.memories.length > 0" class="mt-4 flex items-center justify-between text-sm text-black/50">
              <div class="flex items-center gap-2">
                <span>每页显示</span>
                <select v-model="pageSize" @change="currentPage = 1" class="rounded-lg border border-black/10 bg-white px-2 py-1 text-xs outline-none">
                  <option :value="5">5</option>
                  <option :value="10">10</option>
                </select>
                <span>条</span>
              </div>
              <div class="flex items-center gap-4">
                <span>共 {{ store.memories.length }} 条，第 {{ currentPage }} / {{ Math.ceil(store.memories.length / pageSize) || 1 }} 页</span>
                <div class="flex gap-1">
                  <button class="rounded-lg border border-black/10 px-3 py-1 hover:bg-black/5 disabled:opacity-50" :disabled="currentPage === 1" @click="currentPage--">上一页</button>
                  <button class="rounded-lg border border-black/10 px-3 py-1 hover:bg-black/5 disabled:opacity-50" :disabled="currentPage >= Math.ceil(store.memories.length / pageSize)" @click="currentPage++">下一页</button>
                </div>
              </div>
            </div>
          </div>
        </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import CourseSelector from '@/components/auth/CourseSelector.vue'
import CustomSelect from '@/components/Profile/CustomSelect.vue'
import RadarChart from '@/components/Profile/RadarChart.vue'
import { useProfileStore } from '@/stores/profile'
import type { DifficultyPreference } from '@/types/auth'
import type { MemorySource, ProfileMemoryData } from '@/types/profile'
import { splitTags } from '@/utils/registration'

const store = useProfileStore()
const isEditingProfile = ref(false)
const currentPage = ref(1); const pageSize = ref(10); const saved = ref(false); const editingId = ref<string | null>(null); const editValue = ref('')
const paginatedMemories = computed(() => store.memories.slice((currentPage.value - 1) * pageSize.value, currentPage.value * pageSize.value))
const form = reactive({ grade: '大一', major: '计算机科学与技术', foundation: '没有编程基础，希望从概念和案例开始', learningGoals: [] as string[], interests: [] as string[], difficultyPreference: 'progressive' as DifficultyPreference, courses: [] as string[], careerDirection: '' })
const coursesText = computed({ get: () => form.courses.join('，'), set: (value: string) => { form.courses = splitTags(value) } })
const grades = ['大一', '大二', '大三', '大四', '研究生', '其他']; const majors = ['计算机科学与技术', '软件工程', '人工智能', '数据科学与大数据技术', '网络工程', '信息安全', '数字媒体技术', '其他']
const foundations = ['没有编程基础，希望从概念和案例开始', '了解基本编程概念，需要通过练习巩固', '能够独立完成简单程序，希望提升工程能力', '有完整项目经验，希望深入原理和高级实践']
const goalOptions = ['课程预习与复习', '掌握编程入门', '完成课程项目', '准备考试', '提升工程实践', '拓展专业方向']; const interestOptions = ['项目案例', 'Web 开发', '人工智能', '数据分析', '算法与竞赛', '移动开发', '网络安全', '理论原理']; const careerOptions = ['后端开发', '前端开发', '全栈开发', '数据分析', '算法工程', '人工智能', '测试与质量', '网络安全', '产品与项目管理']
onMounted(async () => { await store.load(true); if (store.profile) Object.assign(form, { grade: store.profile.grade, major: store.profile.major, foundation: store.profile.foundation, learningGoals: [...store.profile.learning_goals], interests: [...store.profile.interests], difficultyPreference: store.profile.difficulty_preference, courses: [...store.profile.courses], careerDirection: store.profile.career_direction ?? '' }) })
function toggle(values: string[], item: string) { const index = values.indexOf(item); if (index >= 0) values.splice(index, 1); else values.push(item) }
async function saveProfile() { saved.value = false; await store.save({ grade: form.grade, major: form.major, foundation: form.foundation, learning_goals: form.learningGoals, interests: form.interests, difficulty_preference: form.difficultyPreference, courses: form.courses, career_direction: form.careerDirection || null }); saved.value = true; isEditingProfile.value = false }
function memoryValue(value: unknown) {
  if (typeof value === 'object' && value !== null) {
    const record = value as Record<string, unknown>
    if (record.stage && record.path && record.objective) {
      return `完成学习路径「${record.path}」阶段「${record.stage}」: ${record.objective}`
    }
    return String(record.label ?? record.topic ?? JSON.stringify(value))
  }
  return String(value)
}
function startEdit(memory: ProfileMemoryData) { editingId.value = memory.id; editValue.value = memoryValue(memory.value_json) }
async function saveMemory(id: string) { await store.editMemory(id, editValue.value.trim()); editingId.value = null }
function categoryLabel(value: string) { return ({ foundation: '学习基础', interest: '兴趣方向', profile: '基础画像', achievement: '学习成就' } as Record<string, string>)[value] ?? value }
function sourceLabel(value: MemorySource) { return ({ registration: '注册', conversation: '对话提取', manual: '手工修改', feedback: '反馈' })[value] }
function formatDate(value: string) { return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
</script>

<style scoped>
.label { @apply text-sm font-medium text-navy; }
.field { @apply mt-2 min-h-11 w-full rounded-xl border border-black/10 bg-white px-3 text-sm outline-none focus:border-navy focus:ring-4 focus:ring-navy/5; }
.chip { @apply min-h-10 rounded-full border border-black/10 px-3 text-sm text-black/55; }
.chip-active { @apply border-navy bg-navy text-white; }
</style>
