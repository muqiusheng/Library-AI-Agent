<template>
  <details v-if="source" class="mt-2 text-xs leading-5 text-ink/55">
    <summary class="cursor-pointer rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy">
      {{ sourceLabels[source.source] ?? '画像记录' }} · {{ formatProfileDate(source.updated_at) }}
    </summary>
    <p class="mt-2 whitespace-pre-wrap break-words border-l-2 border-sage/30 pl-3 text-ink/70">{{ source.evidence || (source.is_user_edited ? '由你手工确认或修改。' : '来源已记录，原文暂不可用。') }}</p>
  </details>
  <p v-else class="mt-2 text-xs leading-5 text-ink/50">基础画像填写</p>
</template>

<script setup lang="ts">
import type { ProfileFactSource } from '@/types/profile'
import { formatProfileDate, sourceLabels } from '@/utils/profilePresentation'
defineProps<{ source?: ProfileFactSource }>()
</script>
