<template>
  <div class="rounded-2xl bg-paper p-4">
    <div class="flex items-center justify-between"><span class="text-sm font-semibold text-navy">匹配度详情</span><span class="text-lg font-bold text-navy">{{ Math.round(total) }}%</span></div>
    <div class="mt-4 space-y-2.5">
      <div v-for="item in dimensions" :key="item.label" class="grid grid-cols-[76px_1fr_34px] items-center gap-2 text-xs">
        <span class="text-black/50">{{ item.label }}</span><span class="h-1.5 overflow-hidden rounded-full bg-black/5"><span class="block h-full rounded-full bg-sage" :style="{ width: `${item.value}%` }" /></span><span class="text-right text-black/45">{{ Math.round(item.value) }}</span>
      </div>
    </div>
    <p class="mt-4 text-[11px] leading-5 text-black/40">匹配度为推荐模型评分，仅用于排序参考。</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ScoreBreakdown } from '@/types/recommendation'

const props = defineProps<{ total: number; scores: ScoreBreakdown }>()
const dimensions = computed(() => [
  { label: '学习目标', value: props.scores.goal }, { label: '难度', value: props.scores.difficulty },
  { label: '专业课程', value: props.scores.major }, { label: '兴趣', value: props.scores.interest },
  { label: '语义', value: props.scores.semantic }, { label: '馆藏可用', value: props.scores.availability }
])
</script>
