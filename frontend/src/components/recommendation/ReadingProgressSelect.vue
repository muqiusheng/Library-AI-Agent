<template>
  <label class="flex items-center gap-2 text-xs text-black/50">
    <span class="sr-only">阅读进度</span>
    <select :value="status?.state || 'not_started'" :disabled="!status || store.busy[bookId]" aria-label="阅读进度"
      class="min-h-10 rounded-xl border border-black/10 bg-white px-3 text-xs text-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy disabled:opacity-50" @change="change">
      <option value="not_started">未开始</option><option value="reading">阅读中</option><option value="completed">已完成</option>
    </select>
    <span v-if="error" role="status" class="text-red-700">{{ error }}</span>
  </label>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { BookState } from '@/api/engagement'
import { useReadingInterestStore } from '@/stores/readingInterest'
const props = defineProps<{ bookId: string }>()
const store = useReadingInterestStore(), error = ref('')
const status = computed(() => store.statuses[props.bookId])
watch(() => props.bookId, () => { void store.ensure(props.bookId).catch(() => { error.value = '进度加载失败' }) }, { immediate: true })
async function change(event: Event) {
  const select = event.target as HTMLSelectElement
  error.value = ''
  try { await store.progress(props.bookId, select.value as BookState) }
  catch { error.value = '进度更新未成功，请重试' }
  finally { select.value = status.value?.state || 'not_started' }
}
</script>
