<template>
  <details class="mt-4 rounded-lg border border-ink/10 bg-paper p-3">
    <summary class="min-h-9 cursor-pointer text-xs font-medium text-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy">候选对比视图 · {{ candidates.length }} 本候选</summary>
    <p class="mt-2 text-xs leading-5 text-ink/60">选择 2–3 本并排比较。未入选不等于不适合，未提供的书籍信息保留未知。</p>
    <div class="mt-3 grid gap-2 sm:grid-cols-2">
      <label v-for="book in candidates" :key="book.book_id" class="flex min-h-10 cursor-pointer items-start gap-2 rounded-lg bg-ink/[0.025] p-2 text-xs leading-5" :class="!selected.includes(book.book_id) && selected.length >= 3 ? 'opacity-50' : ''">
        <input v-model="selected" class="mt-1 shrink-0 accent-navy" type="checkbox" :value="book.book_id" :disabled="!selected.includes(book.book_id) && selected.length >= 3" />
        <span class="min-w-0 break-words"><span class="text-ink/80">{{ book.title }}</span><span class="ml-2 text-ink/55">{{ book.selected ? `已入选 · 第 ${book.rank} 本` : '未入选' }}</span></span>
      </label>
    </div>
    <p v-if="chosen.length < 2" class="mt-3 text-xs text-ink/60" role="status">再选择一本书即可比较。</p>
    <div v-else class="mt-4 overflow-x-auto rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy" tabindex="0" role="region" aria-label="候选图书对比表，可左右滚动">
      <table class="w-full min-w-[620px] table-fixed border-collapse text-left text-xs leading-6">
        <caption class="sr-only">候选图书的内容、排序依据和借阅条件对比</caption>
        <colgroup><col class="w-24" /><col v-for="book in chosen" :key="book.book_id" /></colgroup>
        <thead><tr><th class="cell font-medium text-ink/60" scope="col">比较维度</th><th v-for="book in chosen" :key="book.book_id" class="cell align-top font-semibold text-navy" scope="col">{{ book.title }}</th></tr></thead>
        <tbody>
          <tr><th class="cell" scope="row">本轮结果</th><td v-for="book in chosen" :key="book.book_id" class="cell">{{ book.selection_note || (book.selected ? '已入选' : '未入选') }}</td></tr>
          <tr><th class="cell" scope="row">适配依据</th><td v-for="book in chosen" :key="book.book_id" class="cell"><span class="mb-1 block text-[11px] text-ink/55">{{ book.method === 'llm' ? '简介分析' : '规则初筛' }}</span>{{ book.reason }}</td></tr>
          <tr><th class="cell" scope="row">简介摘录</th><td v-for="book in chosen" :key="book.book_id" class="cell">{{ book.description_excerpt || '暂无简介，内容与先修要求无法确认。' }}</td></tr>
          <tr><th class="cell" scope="row">主题标签</th><td v-for="book in chosen" :key="book.book_id" class="cell">{{ book.topics?.join('、') || '未标注' }}</td></tr>
          <tr><th class="cell" scope="row">难度标签</th><td v-for="book in chosen" :key="book.book_id" class="cell">{{ difficulty(book.difficulty) }}</td></tr>
          <tr><th class="cell" scope="row">可借副本</th><td v-for="book in chosen" :key="book.book_id" class="cell tabular-nums">{{ book.available_count }} 本</td></tr>
          <tr v-for="(label, key) in scoreLabels" :key="key"><th class="cell" scope="row">{{ label }}</th><td v-for="book in chosen" :key="book.book_id" class="cell tabular-nums">{{ book.scores[key] ?? '未提供' }}</td></tr>
        </tbody>
      </table>
    </div>
    <p class="mt-2 text-[11px] leading-5 text-ink/55">分项为初筛参考分，不代表适配概率。简介未说明先修要求时，不能推断为零基础可读。</p>
  </details>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { BookComparison } from '@/types/analysis'
const props = defineProps<{ candidates: BookComparison[] }>()
const selected = ref<string[]>([])
watch(() => props.candidates, (books) => {
  const kept = selected.value.filter(id => books.some(book => book.book_id === id))
  selected.value = kept.length >= 2 ? kept.slice(0, 3) : books.slice(0, 2).map(book => book.book_id)
}, { immediate: true })
const chosen = computed(() => selected.value.map(id => props.candidates.find(book => book.book_id === id)).filter((book): book is BookComparison => Boolean(book)))
const scoreLabels = { goal: '目标匹配', difficulty: '难度匹配', major: '专业相关', interest: '兴趣相关', semantic: '语义相关', availability: '可借情况' }
function difficulty(value?: string | null): string {
  return ({ beginner: '入门', intermediate: '中阶', advanced: '进阶' } as Record<string, string>)[value || ''] || value || '未标注'
}
</script>

<style scoped>
.cell { @apply break-words border-b border-ink/10 p-3 align-top text-ink/70; }
tbody th { @apply font-medium text-ink/60; }
</style>
