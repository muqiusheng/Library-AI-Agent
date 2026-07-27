<template>
  <main class="min-h-screen bg-paper px-4 py-5 sm:px-7 sm:py-7">
    <div class="mx-auto max-w-7xl">
      <header class="flex items-center justify-between gap-4"><div><p class="text-xs font-semibold uppercase tracking-[0.18em] text-amber">BookPath AI</p><h1 class="mt-2 text-3xl font-semibold text-navy">我的学习路径</h1></div><RouterLink class="rounded-xl border border-black/10 bg-white px-4 py-3 text-sm font-medium text-navy" to="/workspace">返回工作台</RouterLink></header>
      <div class="mt-7 grid items-start gap-5 lg:grid-cols-[310px_minmax(0,1fr)]">
        <aside class="rounded-3xl bg-white p-4 shadow-card"><h2 class="px-2 text-sm font-semibold text-navy">已保存路径</h2><div class="mt-3 space-y-2"><button v-for="item in paths" :key="item.id" class="w-full rounded-2xl border p-4 text-left" :class="active?.id === item.id ? 'border-navy bg-navy text-white' : 'border-black/5'" @click="selectPath(item.id)"><p class="line-clamp-2 text-sm font-semibold">{{ item.title }}</p><div class="mt-3 flex items-center justify-between text-xs opacity-60"><span>{{ item.stage_count }} 阶段 · {{ item.book_count }} 本</span><span>{{ Math.round(item.progress) }}%</span></div></button><p v-if="!paths.length" class="px-3 py-8 text-center text-sm text-black/40">从推荐卡点击“加入路径”创建第一条学习路径。</p></div></aside>
        <section v-if="active" class="rounded-3xl bg-white p-5 shadow-card sm:p-7"><div class="flex flex-wrap items-start justify-between gap-4"><div><span class="rounded-full bg-sage/10 px-3 py-1 text-xs text-sage">{{ statusLabel(active.status) }}</span><h2 class="mt-3 text-2xl font-semibold text-navy">{{ active.title }}</h2><p class="mt-2 text-sm text-black/45">目标：{{ active.goal }}</p></div><button v-if="active.status === 'draft'" class="rounded-xl bg-navy px-4 py-2.5 text-sm font-medium text-white" @click="setStatus('active')">开始学习</button></div><div class="mt-6"><div class="flex justify-between text-xs text-black/45"><span>总进度</span><strong class="text-navy">{{ Math.round(active.progress) }}%</strong></div><div class="mt-2 h-2 overflow-hidden rounded-full bg-paper"><div class="h-full rounded-full bg-sage transition-all" :style="{ width: `${active.progress}%` }" /></div></div><ol class="mt-7 space-y-5"><li v-for="stage in active.stages" :key="stage.id" class="relative rounded-2xl border border-black/8 p-5"><div class="flex gap-4"><span class="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-amber/15 text-sm font-bold text-navy">{{ stage.position }}</span><div><h3 class="font-semibold text-navy">{{ stage.title }}</h3><p class="mt-1 text-sm text-black/50">{{ stage.objective }} · {{ stage.duration_text }}</p></div></div><div class="mt-4 space-y-2"><div v-for="book in stage.books" :key="book.book_id" class="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-paper px-4 py-3"><span class="min-w-0 flex-1 text-sm text-black/65">{{ book.title }}</span><select :value="book.state" class="rounded-lg border border-black/10 bg-white px-2 py-1.5 text-xs text-navy" @change="changeBook(book.book_id, ($event.target as HTMLSelectElement).value as BookState)"><option value="want_to_read">想读</option><option value="reading">阅读中</option><option value="completed">已完成</option></select></div></div><p class="mt-3 text-xs text-black/35">完成标准：{{ stage.completion_criteria }}</p></li></ol></section>
        <section v-else class="rounded-3xl bg-white p-12 text-center text-black/40 shadow-card">选择一条路径查看阶段与进度。</section>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import type { BookState } from '@/api/engagement'
import { getLearningPath, listLearningPaths, updatePathBook, updatePathStatus } from '@/api/learningPaths'
import type { LearningPathData, LearningPathStatus, LearningPathSummaryData } from '@/types/learningPath'

const route = useRoute(); const router = useRouter(); const paths = ref<LearningPathSummaryData[]>([]); const active = ref<LearningPathData | null>(null)
onMounted(async () => { paths.value = await listLearningPaths(); const id = typeof route.params.id === 'string' ? route.params.id : paths.value[0]?.id; if (id) await selectPath(id) })
async function selectPath(id: string) { active.value = await getLearningPath(id); await router.replace(`/paths/${id}`) }
async function changeBook(bookId: string, state: BookState) { if (!active.value) return; active.value = await updatePathBook(active.value.id, bookId, state); paths.value = await listLearningPaths() }
async function setStatus(status: LearningPathStatus) { if (!active.value) return; active.value = await updatePathStatus(active.value.id, status); paths.value = await listLearningPaths() }
function statusLabel(value: LearningPathStatus) { return ({ draft: '待开始', active: '学习中', completed: '已完成', archived: '已归档' })[value] }
</script>
