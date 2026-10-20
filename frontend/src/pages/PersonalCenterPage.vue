<template>
  <main class="flex h-screen w-full overflow-hidden bg-paper">
    <div v-if="mobileMenuOpen" class="fixed inset-0 z-30 bg-black/35 lg:hidden" @click="mobileMenuOpen = false" />
    
    <!-- Left Sidebar -->
    <aside class="fixed inset-y-0 left-0 z-40 flex w-[280px] shrink-0 flex-col bg-navy p-5 text-white transition-all duration-300 lg:static" :class="[desktopSidebarOpen ? 'lg:translate-x-0 lg:ml-0' : 'lg:-translate-x-full lg:-ml-[280px]', mobileMenuOpen ? 'translate-x-0' : '-translate-x-full']">
      <div class="flex items-start justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-amber">BookPath AI</p>
          <h1 class="mt-2 text-2xl font-semibold">个人中心</h1>
        </div>
        <button class="grid h-10 w-10 place-items-center rounded-xl bg-white/10 lg:hidden" @click="mobileMenuOpen = false">×</button>
      </div>
      
      <nav class="mt-8 flex-1 space-y-2 text-sm">
        <RouterLink class="block rounded-xl px-4 py-3 text-white/60 hover:bg-white/5" active-class="!bg-white/15 !text-white font-medium" to="/personal-center/basic">
          基本信息
        </RouterLink>
        <RouterLink class="block rounded-xl px-4 py-3 text-white/60 hover:bg-white/5" active-class="!bg-white/15 !text-white font-medium" to="/personal-center/profile">
          我的画像
        </RouterLink>
        <RouterLink class="block rounded-xl px-4 py-3 text-white/60 hover:bg-white/5" active-class="!bg-white/15 !text-white font-medium" to="/personal-center/paths">
          学习路径
        </RouterLink>
        <RouterLink class="block rounded-xl px-4 py-3 text-white/60 hover:bg-white/5" active-class="!bg-white/15 !text-white font-medium" to="/personal-center/theme">
          外观设置
        </RouterLink>
      </nav>
      
      <div class="mt-3 border-t border-white/10 pt-4">
        <RouterLink class="flex h-11 w-full items-center justify-center rounded-xl bg-white text-sm font-semibold text-navy" to="/workspace">返回工作台</RouterLink>
      </div>
    </aside>

    <!-- Right Content Area -->
    <section class="flex min-w-0 flex-1 flex-col overflow-y-auto bg-paper">
      <header class="flex items-center gap-4 border-b border-black/5 px-4 py-4 sm:px-6">
        <button class="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-black/10 lg:hidden" @click="mobileMenuOpen = true">☰</button>
        <button class="hidden h-10 w-10 shrink-0 place-items-center rounded-xl border border-black/10 text-black/50 hover:bg-black/5 lg:grid" @click="desktopSidebarOpen = !desktopSidebarOpen">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" />
          </svg>
        </button>
        <h2 class="truncate font-semibold text-navy lg:hidden">个人中心</h2>
      </header>
        <div class="flex-1 p-5 sm:p-7">
          <RouterView />
        </div>
      </section>
  </main>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const mobileMenuOpen = ref(false)
const desktopSidebarOpen = ref(true)

// Close mobile menu on route change
watch(() => route.path, () => {
  mobileMenuOpen.value = false
})
</script>
