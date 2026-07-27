<template>
  <main class="min-h-screen bg-paper lg:grid lg:grid-cols-[340px_minmax(0,1fr)]">
    <aside class="bg-navy px-5 py-6 text-white lg:min-h-screen lg:px-9 lg:py-12">
      <RouterLink class="text-xs font-semibold uppercase tracking-[0.24em] text-amber" to="/login">BookPath AI</RouterLink>
      <h1 class="mt-3 text-2xl font-semibold">创建你的学习画像</h1>
      <p class="mt-3 text-sm leading-6 text-white/60">三步完成，之后的每次推荐都会以此为起点。</p>

      <ol class="mt-7 grid grid-cols-3 gap-2 lg:mt-12 lg:block lg:space-y-5">
        <li v-for="item in steps" :key="item.number" class="flex items-center gap-3 lg:gap-4">
          <span
            class="grid h-9 w-9 shrink-0 place-items-center rounded-full border text-sm font-semibold"
            :class="step >= item.number ? 'border-amber bg-amber text-navy' : 'border-white/25 text-white/45'"
          >{{ item.number }}</span>
          <div class="hidden lg:block">
            <p class="text-sm font-medium" :class="step >= item.number ? 'text-white' : 'text-white/45'">{{ item.title }}</p>
            <p class="mt-0.5 text-xs text-white/35">{{ item.caption }}</p>
          </div>
        </li>
      </ol>
    </aside>

    <section class="px-4 py-6 sm:px-8 lg:px-14 lg:py-12">
      <div class="mx-auto max-w-3xl">
        <header class="flex items-start justify-between gap-4">
          <div>
            <p class="text-sm font-semibold text-amber">第 {{ step }} 步，共 3 步</p>
            <h2 class="mt-2 text-2xl font-semibold text-navy sm:text-3xl">{{ steps[step - 1].heading }}</h2>
          </div>
          <RouterLink class="text-sm font-medium text-navy hover:underline" to="/login">返回登录</RouterLink>
        </header>

        <div v-if="draftRestored" class="mt-5 rounded-xl bg-sage/10 px-4 py-3 text-sm text-sage" role="status">
          已恢复上次草稿。出于安全考虑，密码不会被保存，请重新填写。
        </div>

        <form class="mt-7 rounded-3xl bg-white p-5 shadow-card sm:p-8" novalidate @submit.prevent="next">
          <div v-if="step === 1" class="space-y-5">
            <div class="grid gap-5 sm:grid-cols-2">
              <FormField v-model="form.studentNo" autocomplete="username" label="学号" placeholder="4–64 位字母、数字、- 或 _" :error="errors.studentNo" />
              <FormField v-model="form.displayName" label="姓名或昵称（可选）" placeholder="推荐卡片中如何称呼你" />
            </div>
            <FormField v-model="form.password" autocomplete="new-password" label="密码" placeholder="8–16 位" type="password" :error="errors.password" />
            <FormField v-model="form.confirmPassword" autocomplete="new-password" label="确认密码" placeholder="再次输入密码" type="password" :error="errors.confirmPassword" />
            <FormField v-model="form.registrationCode" autocomplete="off" label="邀请码（如管理员要求）" placeholder="未启用邀请码时可留空" type="password" />
            <p class="rounded-xl bg-paper px-4 py-3 text-xs leading-6 text-black/50">密码只用于本系统登录，不会保存在注册草稿或浏览器明文存储中。</p>
          </div>

          <div v-else-if="step === 2" class="space-y-5">
            <div class="grid gap-5 sm:grid-cols-2">
              <label class="block">
                <span class="text-sm font-medium text-navy">年级</span>
                <select v-model="form.grade" class="field" :class="errors.grade && 'field-error'">
                  <option value="">请选择</option><option v-for="grade in grades" :key="grade">{{ grade }}</option>
                </select>
                <span v-if="errors.grade" class="error-text">{{ errors.grade }}</span>
              </label>
              <label class="block">
                <span class="text-sm font-medium text-navy">专业</span>
                <select v-model="form.major" class="field" :class="errors.major && 'field-error'">
                  <option value="">请选择</option><option v-for="major in majors" :key="major">{{ major }}</option>
                </select>
                <span v-if="errors.major" class="error-text">{{ errors.major }}</span>
              </label>
            </div>
            <fieldset>
              <legend class="text-sm font-medium text-navy">已有基础</legend>
              <div class="mt-2 grid gap-2 sm:grid-cols-2">
                <button v-for="item in foundationOptions" :key="item.value" class="choice-card" :class="form.foundation === item.value && 'choice-card-selected'" type="button" @click="form.foundation = item.value">
                  <span class="font-medium">{{ item.label }}</span><span class="mt-1 block text-xs opacity-65">{{ item.caption }}</span>
                </button>
              </div>
              <span v-if="errors.foundation" class="error-text">{{ errors.foundation }}</span>
            </fieldset>
            <CourseSelector v-model="form.courses" :grade="form.grade" :major="form.major" />
          </div>

          <div v-else class="space-y-5">
            <fieldset>
              <legend class="text-sm font-medium text-navy">学习目标（可多选）</legend>
              <div class="mt-2 flex flex-wrap gap-2"><button v-for="item in learningGoalOptions" :key="item" class="suggestion" :class="hasTag('learningGoals', item) && 'suggestion-selected'" type="button" :aria-pressed="hasTag('learningGoals', item)" @click="toggleTag('learningGoals', item)">{{ item }}</button></div>
              <span v-if="errors.learningGoals" class="error-text">{{ errors.learningGoals }}</span>
            </fieldset>
            <FormField v-model="form.learningGoals" label="补充目标（可选）" placeholder="可直接补充或调整，用逗号分隔" />
            <div class="grid gap-5 sm:grid-cols-2">
              <label class="block">
                <span class="text-sm font-medium text-navy">难度偏好</span>
                <select v-model="form.difficultyPreference" class="field">
                  <option value="beginner">轻松入门</option><option value="progressive">循序渐进</option><option value="intermediate">有一定挑战</option><option value="advanced">偏进阶</option>
                </select>
              </label>
              <label class="block"><span class="text-sm font-medium text-navy">职业方向（可选）</span><select v-model="form.careerDirection" class="field"><option value="">暂未确定</option><option v-for="item in careerOptions" :key="item">{{ item }}</option></select></label>
            </div>
            <fieldset><legend class="text-sm font-medium text-navy">兴趣方向（可多选）</legend><div class="mt-2 flex flex-wrap gap-2"><button v-for="item in interestOptions" :key="item" class="suggestion" :class="hasTag('interests', item) && 'suggestion-selected'" type="button" :aria-pressed="hasTag('interests', item)" @click="toggleTag('interests', item)">{{ item }}</button></div></fieldset>
            <FormField v-model="form.readBooks" label="已读或已借图书（可选）" placeholder="用逗号分隔填写书名" />
          </div>

          <div v-if="auth.errorMessage" class="mt-6 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">{{ auth.errorMessage }}</div>

          <footer class="mt-8 flex items-center justify-between gap-3 border-t border-black/5 pt-6">
            <button v-if="step > 1" class="min-h-11 rounded-xl border border-black/10 px-5 font-medium text-navy" type="button" @click="step--">上一步</button>
            <span v-else class="text-xs text-black/40">草稿已自动保存</span>
            <button class="min-h-11 rounded-xl bg-navy px-6 font-semibold text-white disabled:opacity-60" :disabled="auth.loading" type="submit">
              {{ step < 3 ? '继续' : auth.loading ? '正在创建…' : '完成注册' }}
            </button>
          </footer>
        </form>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import CourseSelector from '@/components/auth/CourseSelector.vue'
import FormField from '@/components/auth/FormField.vue'
import { useAuthStore } from '@/stores/auth'
import {
  clearRegistrationDraft,
  emptyRegistrationForm,
  loadRegistrationDraft,
  saveRegistrationDraft,
  splitTags,
  toRegisterPayload,
  type RegistrationForm
} from '@/utils/registration'

const router = useRouter()
const auth = useAuthStore()
const savedDraft = loadRegistrationDraft()
const form = reactive<RegistrationForm>({ ...emptyRegistrationForm(), ...(savedDraft ?? {}) })
const step = ref(Math.min(3, Math.max(1, savedDraft?.step ?? 1)))
const draftRestored = ref(Boolean(savedDraft))
const errors = reactive({ studentNo: '', password: '', confirmPassword: '', grade: '', major: '', foundation: '', learningGoals: '' })
const grades = ['大一', '大二', '大三', '大四', '研究生', '其他']
const majors = ['计算机科学与技术', '软件工程', '人工智能', '数据科学与大数据技术', '网络工程', '信息安全', '数字媒体技术', '其他']
const foundationOptions = [
  { label: '零基础', value: '没有编程基础，希望从概念和案例开始', caption: '尚未系统学习编程' },
  { label: '了解基础概念', value: '了解基本编程概念，需要通过练习巩固', caption: '接触过语法或入门课程' },
  { label: '能完成小程序', value: '能够独立完成简单程序，希望提升工程能力', caption: '具备基础编码经验' },
  { label: '有项目经验', value: '有完整项目经验，希望深入原理和高级实践', caption: '适合进阶内容' }
]
const learningGoalOptions = ['课程预习与复习', '掌握编程入门', '完成课程项目', '准备考试', '提升工程实践', '拓展专业方向']
const interestOptions = ['项目案例', 'Web 开发', '人工智能', '数据分析', '算法与竞赛', '移动开发', '网络安全', '理论原理']
const careerOptions = ['后端开发', '前端开发', '全栈开发', '数据分析', '算法工程', '人工智能', '测试与质量', '网络安全', '产品与项目管理']
const steps = [
  { number: 1, title: '账号', caption: '建立身份', heading: '先创建你的账号' },
  { number: 2, title: '学习背景', caption: '了解起点', heading: '告诉我们你从哪里开始' },
  { number: 3, title: '目标偏好', caption: '明确方向', heading: '最后，确定你想去哪里' }
]

watch([form, step], () => saveRegistrationDraft(form, step.value), { deep: true })

function hasTag(field: 'learningGoals' | 'interests', value: string): boolean {
  return splitTags(form[field]).includes(value)
}

function toggleTag(field: 'learningGoals' | 'interests', value: string): void {
  const current = splitTags(form[field])
  form[field] = (current.includes(value) ? current.filter((item) => item !== value) : [...current, value]).join('，')
}

function validateCurrentStep(): boolean {
  if (step.value === 1) {
    errors.studentNo = /^[A-Za-z0-9_-]{4,64}$/.test(form.studentNo) ? '' : '请输入 4–64 位有效学号'
    errors.password = form.password.length >= 8 && form.password.length <= 16 ? '' : '密码需要 8–16 位'
    errors.confirmPassword = form.confirmPassword === form.password ? '' : '两次输入的密码不一致'
    return !errors.studentNo && !errors.password && !errors.confirmPassword
  }
  if (step.value === 2) {
    errors.grade = form.grade ? '' : '请选择年级'
    errors.major = form.major.trim() ? '' : '请输入专业'
    errors.foundation = form.foundation.trim() ? '' : '请描述已有基础'
    return !errors.grade && !errors.major && !errors.foundation
  }
  errors.learningGoals = form.learningGoals.trim() ? '' : '请至少填写一个学习目标'
  return !errors.learningGoals
}

async function next(): Promise<void> {
  if (!validateCurrentStep()) return
  if (step.value < 3) {
    step.value += 1
    draftRestored.value = false
    return
  }
  try {
    await auth.register(toRegisterPayload(form))
    clearRegistrationDraft()
    await router.replace({ path: '/login', query: { registered: '1', studentNo: form.studentNo } })
  } catch {
    // Store renders the backend's readable error message.
  }
}
</script>

<style scoped>
.field { @apply mt-2 min-h-12 w-full rounded-xl border border-black/10 bg-white px-4 outline-none transition focus:border-navy focus:ring-4 focus:ring-navy/5; }
.field-error { @apply border-red-400 focus:border-red-600 focus:ring-red-50; }
.error-text { @apply mt-1.5 block text-sm text-red-700; }
.suggestion { @apply min-h-10 rounded-full border border-black/10 px-3 text-sm text-black/55 transition hover:border-navy hover:text-navy; }
.suggestion-selected { @apply border-navy bg-navy text-white hover:text-white; }
.choice-card { @apply rounded-2xl border border-black/10 p-4 text-left text-sm text-black/60 transition hover:border-navy; }
.choice-card-selected { @apply border-navy bg-navy text-white; }
</style>
