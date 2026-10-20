<template>
  <div class="relative w-full mt-2">
    <button type="button" class="flex min-h-11 w-full items-center justify-between rounded-xl border border-black/10 bg-white px-3 text-sm outline-none transition-colors hover:border-navy hover:ring-4 hover:ring-navy/5 focus:border-navy focus:ring-4 focus:ring-navy/5" @click="open = !open">
      <span class="truncate text-navy">{{ displayValue || '请选择' }}</span>
      <svg class="h-4 w-4 shrink-0 text-navy opacity-50 transition-transform" :class="{ 'rotate-180': open }" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
    </button>
    <Teleport to="body">
      <div v-if="open" class="fixed inset-0 z-40" @click="open = false"></div>
    </Teleport>
    <Transition enter-active-class="transition duration-100 ease-out" enter-from-class="transform scale-95 opacity-0" enter-to-class="transform scale-100 opacity-100" leave-active-class="transition duration-75 ease-in" leave-from-class="transform scale-100 opacity-100" leave-to-class="transform scale-95 opacity-0">
      <div v-if="open" class="absolute left-0 right-0 top-full z-50 mt-1 max-h-60 origin-top overflow-y-auto rounded-xl border border-black/5 bg-white shadow-xl ring-1 ring-black/5">
        <div class="p-1">
          <button v-for="option in options" :key="option.value" type="button" class="flex w-full items-center rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-paper" :class="modelValue === option.value ? 'font-medium text-sage bg-sage/5' : 'text-navy'" @click="selectOption(option.value)">
            {{ option.label }}
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  modelValue: string
  options: { label: string, value: string }[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const open = ref(false)

const displayValue = computed(() => {
  const selected = props.options.find(o => o.value === props.modelValue)
  return selected ? selected.label : props.modelValue
})

function selectOption(value: string) {
  emit('update:modelValue', value)
  open.value = false
}
</script>
