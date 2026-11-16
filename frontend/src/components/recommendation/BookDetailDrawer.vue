<template>
  <Teleport to="body">
    <dialog ref="dialog" class="m-auto w-[calc(100%-2rem)] max-w-2xl rounded-3xl bg-transparent p-0 backdrop:bg-black/35" @cancel.prevent="$emit('close')" @click="backdrop">
      <p v-if="loading" role="status" class="rounded-3xl bg-white p-8 text-navy">正在加载馆藏详情…</p>
      <div v-else-if="error && !detail" class="rounded-3xl bg-white p-8"><p role="alert">{{ error }}</p><button class="mt-4 rounded-xl border px-4 py-2" @click="$emit('close')">关闭</button></div>
      <template v-else-if="detail">
      <div class="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-3xl bg-white p-5 shadow-2xl sm:p-8">
        <header class="flex items-start justify-between gap-4"><div><p class="text-xs font-semibold uppercase tracking-[0.16em] text-sage">馆藏详情</p><h2 class="mt-2 text-2xl font-semibold text-navy">{{ detail.title }}</h2><p class="mt-2 text-sm text-black/45">{{ detail.responsible_person || '责任者未注明' }}</p></div><button class="jelly-hover grid h-10 w-10 place-items-center rounded-xl border border-black/10 text-xl" aria-label="关闭详情" @click="$emit('close')">×</button></header>
        <div class="mt-5 flex flex-wrap items-center gap-3"><WantReadButton :book-id="detail.book_id" show-heat /><ReadingProgressSelect :book-id="detail.book_id" /></div>
        <p class="mt-4 rounded-xl bg-sage/10 px-4 py-3 text-sm text-sage">请前往一楼大厅自助借书机办理借阅。</p>
        <p v-if="error" role="alert" class="mt-3 text-sm text-red-700">{{ error }}</p>
        <div class="mt-6 grid grid-cols-2 gap-3 rounded-2xl bg-paper p-4 text-sm"><div><p class="text-xs text-black/40">ISBN</p><p class="mt-1 font-medium">{{ detail.isbn || '未提供' }}</p></div><div><p class="text-xs text-black/40">出版社 / 年份</p><p class="mt-1 font-medium">{{ detail.publisher || '未提供' }} {{ detail.publication_year || '' }}</p></div></div>
        <p v-if="detail.description" class="mt-6 text-sm leading-7 text-black/60">{{ detail.description }}</p>
        <MatchBreakdown class="mt-6" v-if="book?.scores && book.total_score !== undefined" :scores="book.scores" :total="book.total_score" />
        <section class="mt-7"><h3 class="font-semibold text-navy">馆藏副本（{{ detail.holdings_count }}）</h3><p class="mt-2 rounded-xl bg-amber/10 px-3 py-2 text-xs leading-5 text-amber-800">预约为演示模拟操作，尚未同步学校图书馆系统，不能代替真实占座或借阅。</p><div class="mt-3 space-y-3"><article v-for="holding in detail.holdings" :key="holding.id" class="rounded-2xl border border-black/8 p-4 text-sm"><div class="flex items-center justify-between gap-2"><strong class="text-navy">{{ holding.collection_location || '馆藏地未注明' }}</strong><span class="rounded-full px-2 py-1 text-xs" :class="holding.book_status === 'available' ? 'bg-sage/10 text-sage' : 'bg-amber/15 text-amber-700'">{{ holding.book_status === 'available' ? '在馆' : holding.book_status }}</span></div><dl class="mt-3 grid grid-cols-2 gap-3 text-xs"><div><dt class="text-black/40">所在地</dt><dd class="mt-1">{{ holding.current_location || '—' }}</dd></div><div><dt class="text-black/40">排架号</dt><dd class="mt-1">{{ holding.shelf_number || '—' }}</dd></div><div class="col-span-2"><dt class="text-black/40">索书号</dt><dd class="mt-1 font-medium">{{ holding.call_number || '—' }}</dd></div></dl><div v-if="holding.book_status === 'available' && holding.circulation_status === 'lendable'" class="mt-3 flex items-center justify-between border-t border-black/5 pt-3"><span class="text-xs text-sage">{{ reservationNotice[holding.id] }}</span><button class="jelly-hover rounded-xl bg-navy px-3 py-2 text-xs font-semibold text-white disabled:opacity-50" :disabled="reserving === holding.id || Boolean(reservationNotice[holding.id])" @click="reserve(holding.id)">{{ reserving === holding.id ? '预约中…' : reservationNotice[holding.id] ? '已模拟预约' : '模拟预约' }}</button></div></article></div></section>
      </div>
      </template>
    </dialog>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, reactive, ref, watch } from 'vue'
import { createReservation } from '@/api/notifications'
import { getCatalogDetail, type CatalogDetail } from '@/api/readingInterest'
import { useReadingInterestStore } from '@/stores/readingInterest'
import type { RecommendationCardData } from '@/types/recommendation'
import MatchBreakdown from './MatchBreakdown.vue'
import WantReadButton from './WantReadButton.vue'
import ReadingProgressSelect from './ReadingProgressSelect.vue'

const props = defineProps<{ book: (Pick<RecommendationCardData, 'book_id' | 'title'> & Partial<RecommendationCardData>) | null }>()
const emit = defineEmits<{ close: [] }>()
const dialog = ref<HTMLDialogElement | null>(null)
const detail = ref<CatalogDetail | null>(null), loading = ref(false), error = ref('')
const interest = useReadingInterestStore()
watch(() => props.book?.book_id, async (id) => {
  detail.value = null; error.value = ''
  if (!id) { dialog.value?.close(); return }
  loading.value = true
  await nextTick()
  if (!dialog.value?.open) dialog.value?.showModal()
  try {
    const result = await getCatalogDetail(id)
    if (props.book?.book_id === id) { detail.value = result; interest.accept([result]) }
  } catch { if (props.book?.book_id === id) error.value = '详情加载失败，图书可能已不在当前馆藏中，请稍后重试。' }
  finally { if (props.book?.book_id === id) loading.value = false }
}, { immediate: true })
function backdrop(event: MouseEvent) {
  if (!dialog.value || event.target !== dialog.value) return
  const rect = dialog.value.getBoundingClientRect()
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) emit('close')
}
const reserving = ref<string | null>(null)
const reservationNotice = reactive<Record<string, string>>({})
async function reserve(holdingId: string) {
  reserving.value = holdingId; error.value = ''
  try { await createReservation(holdingId); reservationNotice[holdingId] = '已创建模拟预约'; window.dispatchEvent(new CustomEvent('bookpath:notification-changed')) }
  catch { error.value = '预约未成功，请重试' }
  finally { reserving.value = null }
}
</script>
