<template>
  <section class="text-navy">
    <header class="flex flex-wrap items-end justify-between gap-4">
      <div><p class="text-xs font-medium tracking-widest text-sage">{{ mine ? '留给下一次阅读' : '从大家的阅读意愿中发现好书' }}</p><h1 class="mt-2 text-2xl font-semibold">{{ mine ? '我的想读' : '热门想读榜' }}</h1><p class="mt-2 text-sm text-black/50">{{ mine ? '收藏阅读意愿，在合适的时候翻开它。' : '按所选时间内标记过想读的用户去重统计；取消想读不会撤销历史记录。' }}</p></div>
      <RouterLink v-if="!admin" class="min-h-10 rounded-xl border border-black/10 px-4 py-2.5 text-sm hover:bg-white" to="/workspace">返回智能推荐</RouterLink>
    </header>

    <div class="mt-7 flex flex-wrap items-center justify-between gap-3">
      <div v-if="!mine" role="group" aria-label="热度时间范围" class="inline-flex rounded-xl bg-black/5 p-1">
        <button v-for="period in periods" :key="period.days" type="button" class="min-h-10 rounded-lg px-4 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-sage" :class="days === period.days ? 'bg-white text-navy shadow-sm' : 'text-black/50 hover:text-navy'" :aria-pressed="days === period.days" @click="days = period.days; page = 1">{{ period.label }}</button>
      </div>
      <p class="text-xs text-black/45">{{ mine ? `共 ${result.total} 本想读图书` : `${periodLabel} · ${admin ? `共 ${result.total} 本` : '最多展示20本'}` }}</p>
      <button class="min-h-10 px-3 text-xs text-sage underline underline-offset-4 disabled:opacity-50" :disabled="loading" @click="load">刷新</button>
    </div>

    <p v-if="error" role="alert" class="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">{{ error }} <button class="underline" @click="load">重试</button></p>
    <div v-if="loading" role="status" aria-label="正在加载图书" class="mt-5 space-y-3"><div v-for="n in 3" :key="n" class="h-24 animate-pulse rounded-2xl bg-black/5 motion-reduce:animate-none" /></div>
    <div v-else-if="!error && !result.items.length" class="mt-5 rounded-2xl border border-dashed border-black/15 px-5 py-16 text-center">
      <p class="text-lg font-medium">{{ mine ? '还没有想读的书' : '这段时间还没有想读记录' }}</p>
      <p class="mt-2 text-sm text-black/45">{{ mine ? '去智能推荐中发现一本吧。' : '每一次想读，都为下一位读者留下发现好书的线索。' }}</p>
      <RouterLink v-if="!admin" class="mt-6 inline-flex rounded-xl bg-navy px-5 py-3 text-sm font-medium text-white" to="/workspace">前往智能推荐</RouterLink>
    </div>

    <div v-else-if="!error && admin" class="mt-5 overflow-x-auto rounded-2xl border border-black/5 bg-white">
      <table class="w-full min-w-[700px] text-left text-sm"><thead class="border-b border-black/5 bg-paper text-xs text-black/45"><tr><th class="p-4">排名</th><th class="p-4">图书 / 作者</th><th class="p-4">ISBN</th><th class="p-4 text-right">想读人数</th><th class="p-4 text-right">馆藏 / 可借</th><th class="p-4">操作</th></tr></thead><tbody class="divide-y divide-black/5"><tr v-for="book in result.items" :key="book.book_id"><td class="p-4 font-semibold tabular-nums" :class="(book.rank || 0) <= 3 ? 'text-sage' : 'text-black/40'">{{ book.rank }}</td><td class="max-w-xs p-4"><button class="text-left font-medium hover:underline" @click="selected = book">{{ book.title }}</button><p class="mt-1 text-xs text-black/45">{{ book.responsible_person || '责任者未注明' }}</p></td><td class="p-4 text-xs text-black/50">{{ book.isbn || '未提供' }}</td><td class="p-4 text-right font-semibold tabular-nums">{{ book.heat_count }}</td><td class="p-4 text-right tabular-nums">{{ book.holdings_count }} / {{ book.available_count }}</td><td class="p-4"><button class="min-h-10 text-xs text-sage underline" @click="selected = book">查看详情</button></td></tr></tbody></table>
    </div>
    <ol v-else-if="!error" class="mt-5 divide-y divide-black/5 rounded-2xl bg-white px-4 sm:px-6">
      <li v-for="book in result.items" :key="book.book_id" class="flex gap-4 py-5 sm:gap-6">
        <span v-if="!mine" class="w-7 shrink-0 pt-1 text-xl font-semibold tabular-nums" :class="(book.rank || 0) <= 3 ? 'text-sage' : 'text-black/30'">{{ book.rank }}</span>
        <div class="min-w-0 flex-1"><button class="text-left text-base font-semibold leading-6 hover:underline" @click="selected = book">{{ book.title }}</button><p class="mt-1 text-xs text-black/45">{{ book.responsible_person || '责任者未注明' }}</p><div class="mt-3 flex flex-wrap items-center justify-between gap-3"><p class="text-xs text-black/45"><span v-if="!mine" class="mr-3"><strong class="font-semibold text-navy">{{ book.heat_count }}</strong> 人标记想读</span><span v-else class="mr-3">{{ book.added_at ? new Date(book.added_at).toLocaleDateString('zh-CN') + ' 加入' : '' }}</span><strong class="font-medium text-sage">{{ book.available_count }}</strong> 本可借 · {{ book.holdings_count }} 个副本</p><WantReadButton :book-id="book.book_id" /></div></div>
      </li>
    </ol>
    <nav v-if="(admin || mine) && result.total > 20" aria-label="图书分页" class="mt-5 flex items-center justify-end gap-4 text-sm"><button class="min-h-10 rounded-xl border border-black/10 px-4 disabled:opacity-35" :disabled="page === 1 || loading" @click="page--">上一页</button><span class="text-black/50">{{ page }} / {{ Math.ceil(result.total / 20) }}</span><button class="min-h-10 rounded-xl border border-black/10 px-4 disabled:opacity-35" :disabled="page * 20 >= result.total || loading" @click="page++">下一页</button></nav>
    <BookDetailDrawer :book="selected" @close="selected = null" />
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { getPopular, getWanted, type BookList, type InterestBook } from '@/api/readingInterest'
import { useReadingInterestStore } from '@/stores/readingInterest'
import WantReadButton from './WantReadButton.vue'
import BookDetailDrawer from './BookDetailDrawer.vue'
const props = defineProps<{ mine?: boolean; admin?: boolean }>()
const store = useReadingInterestStore()
const days = ref(30), page = ref(1), loading = ref(false), error = ref('')
const selected = ref<InterestBook | null>(null)
const result = ref<BookList>({ items: [], total: 0, page: 1, page_size: 20 })
const periods = [{ days: 7, label: '近7天' }, { days: 30, label: '近30天' }, { days: 365, label: '近一年' }]
const periodLabel = computed(() => periods.find(p => p.days === days.value)?.label)
let request = 0
async function load() {
  const serial = ++request
  loading.value = true; error.value = ''
  try {
    const data = props.mine ? await getWanted(page.value) : await getPopular(days.value, page.value, props.admin)
    if (serial !== request) return
    if (page.value > 1 && !data.items.length) { page.value = Math.max(1, Math.ceil(data.total / 20)); return }
    result.value = data
    // A ranking's count belongs to its chosen period. Never replace the shared 30-day count.
    if (props.mine) store.accept(data.items)
  } catch { if (serial === request) error.value = '图书列表加载失败，请重试。' }
  finally { if (serial === request) loading.value = false }
}
watch([days, page, () => props.mine, () => props.admin], () => { void load() }, { immediate: true })
watch(() => store.revision, () => { void load() })
</script>
