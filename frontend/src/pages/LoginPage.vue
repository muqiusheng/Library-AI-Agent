<template>
  <main class="grid min-h-screen bg-paper lg:grid-cols-[minmax(380px,0.9fr)_minmax(560px,1.1fr)]">
    <AuthBrandPanel />
    <section class="flex items-center justify-center px-5 py-10 sm:px-10">
      <div class="w-full max-w-md">
        <div class="lg:hidden">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-amber">BookPath AI</p>
          <h1 class="mt-2 text-2xl font-semibold text-navy">书途智引</h1>
        </div>

        <div class="mt-10 rounded-3xl bg-white p-6 shadow-card sm:p-9 lg:mt-0">
          <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate">欢迎回来</p>
          <h2 class="mt-3 text-3xl font-semibold tracking-tight text-navy">登录学习工作台</h2>
          <p class="mt-3 text-sm leading-6 text-black/50">继续你的馆藏推荐、阅读路径与学习进度。</p>

          <div v-if="registered" class="mt-6 rounded-2xl border border-sage/20 bg-sage/10 px-4 py-3 text-sm text-sage" role="status">
            注册成功，请使用新账号登录。
          </div>

          <form class="mt-7 space-y-5" novalidate @submit.prevent="submit">
            <label class="block">
              <span class="text-sm font-medium text-navy">学号</span>
              <input
                v-model.trim="form.studentNo"
                autocomplete="username"
                class="mt-2 min-h-12 w-full rounded-xl border border-black/10 px-4 outline-none transition focus:border-navy focus:ring-4 focus:ring-navy/5"
                placeholder="请输入学号"
              />
              <span v-if="errors.studentNo" class="mt-1.5 block text-sm text-red-700">{{ errors.studentNo }}</span>
            </label>

            <label class="block">
              <span class="text-sm font-medium text-navy">密码</span>
              <input
                v-model="form.password"
                autocomplete="current-password"
                class="mt-2 min-h-12 w-full rounded-xl border border-black/10 px-4 outline-none transition focus:border-navy focus:ring-4 focus:ring-navy/5"
                placeholder="请输入密码"
                type="password"
              />
              <span v-if="errors.password" class="mt-1.5 block text-sm text-red-700">{{ errors.password }}</span>
            </label>

            <div v-if="auth.errorMessage" class="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
              {{ auth.errorMessage }}
            </div>

            <button
              class="min-h-12 w-full rounded-xl bg-navy px-5 font-semibold text-white transition hover:bg-navy-light disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="auth.loading"
              type="submit"
            >
              {{ auth.loading ? '正在登录…' : '登录' }}
            </button>
          </form>

          <p class="mt-7 text-center text-sm text-black/50">
            还没有账号？
            <RouterLink class="font-semibold text-navy underline-offset-4 hover:underline" to="/register">创建学习画像</RouterLink>
          </p>
          <p class="mt-4 text-center text-xs text-black/40">
            登录或注册即表示你已阅读
            <RouterLink class="font-medium text-navy hover:underline" to="/privacy">隐私说明</RouterLink>
          </p>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AuthBrandPanel from '@/components/auth/AuthBrandPanel.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const registered = computed(() => route.query.registered === '1')
const form = reactive({
  studentNo: typeof route.query.studentNo === 'string' ? route.query.studentNo : '',
  password: ''
})
const errors = reactive({ studentNo: '', password: '' })

async function submit(): Promise<void> {
  errors.studentNo = form.studentNo ? '' : '请输入学号'
  errors.password = form.password ? '' : '请输入密码'
  if (errors.studentNo || errors.password) return
  try {
    await auth.login({ student_no: form.studentNo, password: form.password })
    const requested = typeof route.query.redirect === 'string' ? route.query.redirect : '/workspace'
    const redirect = auth.isAdmin ? '/admin' : requested.startsWith('/admin') ? '/workspace' : requested
    await router.replace(redirect)
  } catch {
    // Store exposes a readable error message next to the form.
  }
}
</script>
