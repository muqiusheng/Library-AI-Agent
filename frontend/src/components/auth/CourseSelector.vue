<template>
  <fieldset>
    <div class="flex items-end justify-between gap-3">
      <div>
        <legend class="text-sm font-medium text-navy">当前课程（可多选）</legend>
        <p class="mt-1 text-xs text-black/40">课程来自统一目录接口，后续可直接接入教学管理系统。</p>
      </div>
      <span v-if="loading" class="text-xs text-sage">加载中…</span>
    </div>

    <label class="mt-3 block">
      <span class="sr-only">搜索课程</span>
      <input v-model="query" class="field" placeholder="搜索课程名称或课程代码" type="search" />
    </label>

    <div v-if="errorMessage" class="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="status">
      {{ errorMessage }}，你可以暂不选择，稍后在画像中补充。
    </div>
    <div v-else class="mt-3 max-h-56 space-y-4 overflow-y-auto rounded-2xl border border-black/5 bg-paper p-3">
      <section v-for="group in groupedOptions" :key="group.category">
        <h3 class="px-1 text-xs font-semibold text-black/40">{{ group.category }}</h3>
        <div class="mt-2 flex flex-wrap gap-2">
          <button
            v-for="course in group.items"
            :key="course.code"
            class="choice"
            :class="isSelected(course.name) && 'choice-selected'"
            type="button"
            :aria-pressed="isSelected(course.name)"
            @click="toggle(course.name)"
          >
            <span>{{ course.name }}</span><span class="ml-1 text-[10px] opacity-55">{{ course.code }}</span>
          </button>
        </div>
      </section>
      <p v-if="!loading && !groupedOptions.length" class="py-5 text-center text-sm text-black/40">没有匹配课程</p>
    </div>

    <div v-if="selected.length" class="mt-3 flex flex-wrap gap-2">
      <span v-for="name in selected" :key="name" class="rounded-full bg-sage/10 px-3 py-1.5 text-xs text-sage">
        {{ name }} <button type="button" aria-label="移除课程" @click="toggle(name)">×</button>
      </span>
    </div>
  </fieldset>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { listCourseOptions, type CourseOption } from '@/api/courses'
import { getApiErrorMessage } from '@/utils/apiError'
import { splitTags } from '@/utils/registration'

const props = defineProps<{ modelValue: string; major: string; grade: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const options = ref<CourseOption[]>([])
const query = ref('')
const loading = ref(false)
const errorMessage = ref('')
const selected = computed(() => splitTags(props.modelValue))
const visibleOptions = computed(() => {
  const normalized = query.value.trim().toLocaleLowerCase()
  if (!normalized) return options.value
  return options.value.filter((course) =>
    `${course.name} ${course.code}`.toLocaleLowerCase().includes(normalized)
  )
})
const groupedOptions = computed(() => {
  const groups = new Map<string, CourseOption[]>()
  visibleOptions.value.forEach((course) => {
    const values = groups.get(course.category) ?? []
    values.push(course)
    groups.set(course.category, values)
  })
  return [...groups].map(([category, items]) => ({ category, items }))
})

watch(
  () => [props.major, props.grade],
  async () => {
    loading.value = true
    errorMessage.value = ''
    try {
      options.value = await listCourseOptions({ major: props.major || undefined, grade: props.grade || undefined })
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '课程目录暂时不可用')
    } finally {
      loading.value = false
    }
  },
  { immediate: true }
)

function isSelected(name: string): boolean {
  return selected.value.includes(name)
}

function toggle(name: string): void {
  const values = isSelected(name)
    ? selected.value.filter((value) => value !== name)
    : [...selected.value, name]
  emit('update:modelValue', values.join('，'))
}
</script>

<style scoped>
.field { @apply min-h-11 w-full rounded-xl border border-black/10 bg-white px-4 text-sm outline-none transition focus:border-navy focus:ring-4 focus:ring-navy/5; }
.choice { @apply min-h-10 rounded-full border border-black/10 bg-white px-3 text-sm text-black/60 transition hover:border-navy hover:text-navy; }
.choice-selected { @apply border-navy bg-navy text-white hover:text-white; }
</style>
