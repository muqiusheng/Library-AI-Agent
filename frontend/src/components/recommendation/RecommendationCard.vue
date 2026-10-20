<template>
  <article class="jelly-hover rounded-2xl border border-black/8 bg-white p-4 shadow-sm sm:p-5">
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
    <div class="mt-4 flex flex-wrap gap-2"><button v-for="item in feedbackOptions" :key="item.type" class="feedback transition-colors" :class="selectedFeedback === item.type && 'feedback-active'" type="button" @click="feedback(item.type)">{{ item.label }}</button></div>
    <div class="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-black/5 pt-4">
      <p class="text-xs text-black/45"><strong class="text-sage">{{ book.available_count }}</strong> 本可借 · {{ book.holdings_count }} 个馆藏副本</p>
      <div class="flex gap-2">
        <!-- Custom Dropdown -->
        <div v-if="dropdownOpen" class="fixed inset-0 z-10" @click="dropdownOpen = false"></div>
        <div class="relative z-20">
          <button class="flex items-center justify-between min-w-[96px] min-h-10 rounded-xl border border-black/10 bg-white px-3 text-xs text-navy focus:outline-none focus:border-navy transition-colors hover:bg-black/5" @click="dropdownOpen = !dropdownOpen">
            <span>{{ stateOptions.find(o => o.value === state)?.label || '阅读状态' }}</span>
            <svg class="ml-2 h-3 w-3 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
          </button>
          <div v-if="dropdownOpen" class="absolute left-0 top-full mt-1 w-full overflow-hidden rounded-xl border border-black/5 bg-white py-1 shadow-lg">
            <button v-for="opt in stateOptions" :key="opt.value" class="block w-full px-3 py-2 text-left text-xs text-navy hover:bg-navy/5" @click="selectState(opt.value)">
              {{ opt.label }}
            </button>
          </div>
        </div>
        <button class="jelly-hover min-h-10 rounded-xl border border-black/10 px-3 text-xs font-medium text-navy" @click="$emit('detail', book)">查看详情</button><button class="jelly-hover min-h-10 rounded-xl bg-navy px-3 text-xs font-medium text-white" @click="$emit('add-to-path', book)">加入路径</button>
      </div>
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
const dropdownOpen = ref(false)
const stateOptions: { value: BookState; label: string }[] = [{ value: 'want_to_read', label: '想读' }, { value: 'reading', label: '阅读中' }, { value: 'completed', label: '已完成' }]
const feedbackOptions: { type: FeedbackType; label: string }[] = [{ type: 'like', label: '喜欢' }, { type: 'not_interested', label: '不感兴趣' }, { type: 'too_hard', label: '太难' }, { type: 'too_easy', label: '太简单' }]
const coverText = computed(() => props.book.topics[0] || '馆藏图书')
const difficultyLabel = computed(() => ({ beginner: '入门', intermediate: '中阶', advanced: '进阶' }[props.book.difficulty] || props.book.difficulty))

async function feedback(type: FeedbackType) {
  if (selectedFeedback.value === type) {
    selectedFeedback.value = null
    notice.value = ''
    return
  }
  selectedFeedback.value = type
  notice.value = '反馈已用于下一轮推荐'
  // Optimistic UI update: run network request in background without blocking
  sendFeedback(props.setId, props.book.book_id, type).catch(() => {
    notice.value = '反馈提交失败，请重试'
    selectedFeedback.value = null
  })
}
async function selectState(val: BookState) { state.value = val; dropdownOpen.value = false; await setBookState(props.book.book_id, val); notice.value = '阅读状态已更新' }
</script>

<style scoped>
.feedback { @apply rounded-full border border-black/10 px-2.5 py-1.5 text-[11px] text-black/45; }
.feedback-active { @apply border-sage bg-sage/10 text-sage; }
</style>
