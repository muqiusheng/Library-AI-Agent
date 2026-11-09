<template>
  <Teleport to="body">
    <div
      ref="panel"
      role="dialog"
      aria-labelledby="delete-conversation-title"
      aria-describedby="delete-conversation-description"
      :aria-busy="busy"
      class="fixed z-[70] rounded-2xl border border-ink/10 bg-paper p-4 text-ink shadow-[0_12px_36px_rgba(23,35,29,0.16)]"
      :style="position"
      @keydown.esc.stop.prevent="dismiss"
    >
      <h3 id="delete-conversation-title" class="text-sm font-semibold">删除对话？</h3>
      <p class="mt-2 truncate text-sm text-ink/80" :title="title">{{ title }}</p>
      <p id="delete-conversation-description" class="mt-1 text-xs leading-5 text-ink/65">删除后，对话记录将无法恢复。</p>
      <p v-if="error" role="alert" class="mt-3 text-xs leading-5 text-red-700">{{ error }}</p>
      <div class="mt-4 flex justify-end gap-2 border-t border-ink/10 pt-3">
        <button ref="cancelButton" type="button" :disabled="busy" class="min-h-10 rounded-lg px-4 text-sm hover:bg-ink/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy disabled:opacity-50" @click="dismiss">取消</button>
        <button type="button" :disabled="busy" class="min-h-10 rounded-lg bg-red-700 px-4 text-sm font-medium text-white hover:bg-red-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700 disabled:cursor-wait disabled:opacity-60" @click="$emit('confirm')">{{ busy ? '正在删除…' : '删除' }}</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import type { CSSProperties } from 'vue'

const props = defineProps<{ anchor: HTMLElement; title: string; busy: boolean; error: string }>()
const emit = defineEmits<{ close: []; confirm: [] }>()
const panel = ref<HTMLElement | null>(null)
const cancelButton = ref<HTMLButtonElement | null>(null)
const position = ref<CSSProperties>({ visibility: 'hidden' })

function place() {
  const anchor = props.anchor.getBoundingClientRect()
  const width = Math.min(320, window.innerWidth - 24)
  const height = panel.value?.offsetHeight ?? 200
  const left = anchor.right + 8 + width <= window.innerWidth - 12
    ? anchor.right + 8
    : Math.max(12, Math.min(anchor.right - width, window.innerWidth - width - 12))
  position.value = {
    width: `${width}px`, left: `${left}px`,
    top: `${Math.max(12, Math.min(anchor.top, window.innerHeight - height - 12))}px`,
    maxHeight: 'calc(100dvh - 24px)', overflowY: 'auto'
  }
}

function dismiss() { if (!props.busy) emit('close') }
function outside(event: Event) {
  const target = event.target as Node | null
  if (target && !panel.value?.contains(target) && !props.anchor.contains(target)) dismiss()
}
function escape(event: KeyboardEvent) {
  if (event.key === 'Escape') { event.preventDefault(); dismiss() }
}
function scroll(event: Event) {
  if (!panel.value?.contains(event.target as Node)) dismiss()
}

onMounted(async () => {
  await nextTick()
  place()
  cancelButton.value?.focus({ preventScroll: true })
  document.addEventListener('pointerdown', outside)
  document.addEventListener('focusin', outside)
  document.addEventListener('keydown', escape)
  document.addEventListener('scroll', scroll, true)
  window.addEventListener('resize', place)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', outside)
  document.removeEventListener('focusin', outside)
  document.removeEventListener('keydown', escape)
  document.removeEventListener('scroll', scroll, true)
  window.removeEventListener('resize', place)
  if (props.anchor.isConnected) props.anchor.focus({ preventScroll: true })
})
</script>
