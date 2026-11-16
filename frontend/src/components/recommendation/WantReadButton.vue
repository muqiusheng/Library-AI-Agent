<template>
  <div class="flex flex-wrap items-center gap-2">
    <span v-if="showHeat && status" class="text-xs text-black/45">{{ status.heat_count ? `近30天有 ${status.heat_count} 人标记想读` : '近30天暂无人标记想读' }}</span>
    <button type="button" class="inline-flex min-h-10 items-center gap-1.5 rounded-xl border px-3 text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sage disabled:opacity-50"
      :class="status?.wanted ? 'border-sage/30 bg-sage/10 text-sage' : 'border-black/10 text-navy hover:bg-paper'"
      :aria-pressed="Boolean(status?.wanted)" :aria-label="status?.wanted ? '取消想读' : '想读'"
      :disabled="store.busy[bookId] || (!status && !error)" @click="act">
      <svg aria-hidden="true" class="h-4 w-4" viewBox="0 0 24 24" :fill="status?.wanted ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.7"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z" /></svg>
      {{ !status ? (error ? '重试加载' : '加载中…') : status.wanted ? '已想读' : '想读' }}
    </button>
    <span v-if="message || error" role="status" class="text-xs" :class="error ? 'text-red-700' : 'text-sage'">{{ error || message }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useReadingInterestStore } from '@/stores/readingInterest'
const props = defineProps<{ bookId: string; showHeat?: boolean }>()
const store = useReadingInterestStore()
const status = computed(() => store.statuses[props.bookId])
const message = ref(''), error = ref('')
async function load() {
  error.value = ''
  try { await store.ensure(props.bookId) } catch { error.value = '加载未成功，请重试' }
}
watch(() => props.bookId, () => { message.value = ''; void load() }, { immediate: true })
async function act() {
  if (!status.value) { await load(); return }
  error.value = ''; message.value = ''
  try { await store.toggle(props.bookId); message.value = status.value.wanted ? '已加入想读' : '已取消想读' }
  catch { error.value = '操作未成功，请重试' }
}
</script>
