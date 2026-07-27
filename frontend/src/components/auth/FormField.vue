<template>
  <label class="block">
    <span class="text-sm font-medium text-navy">{{ label }}</span>
    <input
      :value="modelValue"
      :autocomplete="autocomplete"
      class="mt-2 min-h-12 w-full rounded-xl border bg-white px-4 outline-none transition focus:ring-4"
      :class="error ? 'border-red-400 focus:border-red-600 focus:ring-red-50' : 'border-black/10 focus:border-navy focus:ring-navy/5'"
      :placeholder="placeholder"
      :type="type"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
    <span v-if="error" class="mt-1.5 block text-sm text-red-700">{{ error }}</span>
    <span v-else-if="hint" class="mt-1.5 block text-xs text-black/40">{{ hint }}</span>
  </label>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  modelValue: string
  label: string
  placeholder?: string
  type?: string
  autocomplete?: string
  error?: string
  hint?: string
}>(), { placeholder: '', type: 'text', autocomplete: 'off', error: '', hint: '' })

defineEmits<{ 'update:modelValue': [value: string] }>()
</script>
