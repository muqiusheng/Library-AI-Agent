<template>
  <section aria-labelledby="ability-heading" class="w-full">
    <h3 id="ability-heading" class="text-lg font-semibold text-navy">知识点基础</h3>
    <p class="mt-2 text-xs leading-6 text-ink/60">按你的自述记录，用于匹配图书难度。未提及的知识点保留未知。</p>
    <ul v-if="rows.length" class="mt-5 divide-y divide-ink/10">
      <li v-for="row in rows" :key="row.key" class="py-4 first:pt-0">
        <div class="flex items-start justify-between gap-4">
          <span class="break-words text-sm font-semibold text-navy">{{ row.topic }}</span>
          <span class="shrink-0 rounded-full px-3 py-1 text-xs font-medium"
            :class="row.level === 'none' || row.level === 'unknown' ? 'bg-ink/5 text-ink/65' : 'bg-sage/15 text-moss'">
            {{ abilityLabels[row.level] ?? '尚不确定' }}
          </span>
        </div>
        <SourceNote :source="row.source" />
      </li>
    </ul>
    <p v-else class="mt-6 rounded-xl bg-paper p-5 text-sm leading-7 text-ink/60">还没有明确的知识点记录。你可以在对话中说明“我没学过 Python”或“我了解 Java 基础”。</p>
    <p class="mt-4 text-xs leading-6 text-ink/50">这些记录不代表经过测评的能力分数。</p>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { EffectiveProfile } from '@/types/profile'
import { abilityLabels, abilityRows } from '@/utils/profilePresentation'
import SourceNote from './SourceNote.vue'
const props = defineProps<{ profile: EffectiveProfile | null }>()
const rows = computed(() => abilityRows(props.profile))
</script>
