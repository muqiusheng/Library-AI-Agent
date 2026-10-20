<template>
  <section class="max-w-2xl">
    <h2 class="text-xl font-semibold text-navy">外观设置</h2>
    <p class="mt-2 text-sm text-black/50">选择你喜欢的主题配色，系统会即刻应用到全局。</p>

    <div class="mt-8 grid gap-4 sm:grid-cols-2">
      <button
        v-for="theme in themes"
        :key="theme.id"
        class="relative flex items-center gap-4 rounded-2xl border p-4 text-left transition-all hover:border-navy/30"
        :class="themeStore.currentTheme === theme.id ? 'border-navy bg-navy/5 shadow-sm' : 'border-black/10 bg-white'"
        @click="themeStore.setTheme(theme.id)"
      >
        <div class="grid h-12 w-12 shrink-0 place-items-center rounded-full text-white" :style="{ backgroundColor: theme.color }">
          <svg v-if="themeStore.currentTheme === theme.id" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div>
          <h3 class="font-semibold text-navy">{{ theme.name }}</h3>
          <p class="mt-1 text-xs text-black/45">{{ theme.desc }}</p>
        </div>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useThemeStore, type Theme } from '@/stores/theme'

const themeStore = useThemeStore()

const themes: { id: Theme; name: string; desc: string; color: string }[] = [
  {
    id: 'classic',
    name: '原木经典',
    desc: '温柔护眼的复古色调',
    color: '#14283d'
  },
  {
    id: 'mist',
    name: '晨雾灰绿',
    desc: '低饱和的宁静植物色系',
    color: '#374b46'
  },
  {
    id: 'sand',
    name: '暖砂驼色',
    desc: '舒适自然的大地暖色',
    color: '#4b4137'
  },
  {
    id: 'dusk',
    name: '苍霭蓝灰',
    desc: '低调克制的高级灰蓝',
    color: '#323c4b'
  }
]
</script>
