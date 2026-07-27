<template>
  <article class="rounded-2xl border border-black/8 bg-white p-4 shadow-sm sm:p-5">
    <div class="flex gap-4">
      <div class="grid h-28 w-20 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-navy to-navy-light px-2 text-center text-xs font-semibold leading-5 text-white">{{ coverText }}</div>
      <div class="min-w-0 flex-1">
        <div class="flex items-start justify-between gap-3">
          <div><h4 class="text-base font-semibold leading-6 text-navy sm:text-lg">{{ book.title }}</h4><p class="mt-1 text-xs text-black/45">{{ book.responsible_person || '责任者未注明' }}<span v-if="book.publication_year"> · {{ book.publication_year }}</span></p></div>
          <button class="shrink-0 rounded-full bg-amber/15 px-3 py-1.5 text-sm font-bold text-navy" @click="showScore = !showScore">{{ Math.round(book.total_score) }}%</button>
        </div>
        <div class="mt-3 flex flex-wrap gap-1.5"><span v-for="topic in book.topics.slice(0, 3)" :key="topic" class="rounded-full bg-sage/10 px-2.5 py-1 text-[11px] text-sage">{{ topic }}</span><span class="rounded-full bg-paper px-2.5 py-1 text-[11px] text-black/55">{{ difficultyLabel }}</span><span class="rounded-full bg-paper px-2.5 py-1 text-[11px] text-black/55">{{ book.learning_stage }}</span></div>
        <p class="mt-3 line-clamp-3 text-sm leading-6 text-black/60">{{ book.reason }}</p>
      </div>
    </div>
    <MatchBreakdown v-if="showScore" class="mt-4" :scores="book.scores" :total="book.total_score" />
    <div class="mt-4 flex flex-wrap gap-2"><button v-for="item in feedbackOptions" :key="item.type" class="feedback" :class="selectedFeedback === item.type && 'feedback-active'" type="button" :disabled="submitting" @click="feedback(item.type)">{{ item.label }}</button></div>
    <div class="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-black/5 pt-4">
      <p class="text-xs text-black/45"><strong class="text-sage">{{ book.available_count }}</strong> 本可借 · {{ book.holdings_count }} 个馆藏副本</p>
      <div class="flex gap-2"><select v-model="state" class="min-h-10 rounded-xl border border-black/10 bg-white px-2 text-xs text-navy" aria-label="阅读状态" @change="updateState"><option value="">阅读状态</option><option value="want_to_read">想读</option><option value="reading">阅读中</option><option value="completed">已完成</option></select><button class="min-h-10 rounded-xl border border-black/10 px-3 text-xs font-medium text-navy" @click="$emit('detail', book)">查看详情</button><button class="min-h-10 rounded-xl bg-navy px-3 text-xs font-medium text-white" @click="$emit('add-to-path', book)">加入路径</button></div>
    </div>
    <p v-if="notice" class="mt-2 text-right text-xs text-sage" role="status">{{ notice }}</p>
  </article>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { sendFeedback, setBookState, type BookState, type FeedbackType } from '@/api/engagement'
import type { RecommendationCardData } from '@/types/recommendation'
import MatchBreakdown from './MatchBreakdown.vue'

const props = defineProps<{ book: RecommendationCardData; setId: string }>()
defineEmits<{ detail: [book: RecommendationCardData]; 'add-to-path': [book: RecommendationCardData] }>()
const showScore = ref(false)
const submitting = ref(false); const selectedFeedback = ref<FeedbackType | null>(null); const state = ref<BookState | ''>(''); const notice = ref('')
const feedbackOptions: { type: FeedbackType; label: string }[] = [{ type: 'like', label: '喜欢' }, { type: 'not_interested', label: '不感兴趣' }, { type: 'too_hard', label: '太难' }, { type: 'too_easy', label: '太简单' }, { type: 'read', label: '已读' }]
const coverText = computed(() => props.book.topics[0] || '馆藏图书')
const difficultyLabel = computed(() => ({ beginner: '入门', intermediate: '中阶', advanced: '进阶' }[props.book.difficulty] || props.book.difficulty))
async function feedback(type: FeedbackType) { submitting.value = true; try { await sendFeedback(props.setId, props.book.book_id, type); selectedFeedback.value = type; notice.value = '反馈已用于下一轮推荐' } finally { submitting.value = false } }
async function updateState() { if (!state.value) return; await setBookState(props.book.book_id, state.value); notice.value = '阅读状态已更新' }
</script>

<style scoped>
.feedback { @apply rounded-full border border-black/10 px-2.5 py-1.5 text-[11px] text-black/45 disabled:opacity-50; }
.feedback-active { @apply border-sage bg-sage/10 text-sage; }
</style>
