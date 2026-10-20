<template>
  <main class="min-h-screen bg-paper">
    <section class="flex min-h-screen items-center justify-center px-5 py-10 sm:px-10">
      <div class="w-full max-w-md">
        <div class="rounded-3xl bg-white p-6 shadow-card sm:p-10">
          <!-- Brand & Logo -->
          <div class="mb-8 flex flex-col items-center text-center">
            <div class="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-navy/5 text-navy">
              <svg class="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
              </svg>
            </div>
            <h1 class="text-2xl font-bold text-navy">书途智引</h1>
            <p class="mt-1 text-[11px] font-bold uppercase tracking-[0.2em] text-amber">BookPath AI</p>
          </div>

          <!-- Form Header -->
          <div class="mb-6 text-center">
            <h2 class="text-lg font-semibold tracking-tight text-slate-800">登录学习工作台</h2>
            <p class="mt-2 text-sm text-black/50">继续你的馆藏推荐、阅读路径与学习进度。</p>
          </div>

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
          <div class="mt-4 flex flex-col items-center">
            <label class="flex items-center gap-2 text-xs text-black/60 cursor-pointer">
              <input v-model="form.agreed" type="checkbox" class="rounded border-black/20 text-navy focus:ring-navy/20 cursor-pointer" />
              <span>我已阅读并同意 <RouterLink class="font-medium text-navy hover:underline" target="_blank" @click.stop to="/privacy">隐私说明</RouterLink></span>
            </label>
            <span v-if="errors.agreed" class="mt-1.5 block text-xs text-red-700">{{ errors.agreed }}</span>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const registered = computed(() => route.query.registered === '1')
const form = reactive({
  studentNo: typeof route.query.studentNo === 'string' ? route.query.studentNo : '',
  password: '',
  agreed: false
})
const errors = reactive({ studentNo: '', password: '', agreed: '' })

async function submit(): Promise<void> {
  errors.studentNo = form.studentNo ? '' : '请输入学号'
  errors.password = form.password ? '' : '请输入密码'
  errors.agreed = form.agreed ? '' : '请先阅读并同意隐私说明'
  
  if (errors.studentNo || errors.password || errors.agreed) return
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
