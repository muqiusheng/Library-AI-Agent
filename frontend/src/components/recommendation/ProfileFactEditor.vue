<template>
  <div class="text-xs">
    <button v-if="!editing" type="button" class="min-h-9 rounded px-2 text-navy hover:bg-ink/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy disabled:opacity-40" :disabled="disabled || fact.value_json === undefined" @click="begin">更正画像</button>
    <form v-else class="mt-2 space-y-3 rounded-lg border border-ink/10 bg-paper p-3" @submit.prevent="save">
      <label class="block space-y-2 text-ink/75">
        <span class="font-medium">更正{{ fact.label }}：{{ isAbility ? abilityTopic : '' }}</span>
        <select v-if="isAbility" v-model="value" class="field" :disabled="saving">
          <option value="none">未学习</option><option value="basic">有基础，熟练程度未确认</option>
          <option value="intermediate">中等水平</option><option value="advanced">进阶水平</option><option value="unknown">尚不确定</option>
        </select>
        <select v-else-if="fact.key === 'difficulty_preference'" v-model="value" class="field" :disabled="saving">
          <option value="beginner">轻松入门</option><option value="progressive">循序渐进</option>
          <option value="intermediate">有一定挑战</option><option value="advanced">偏进阶</option>
        </select>
        <textarea v-else-if="isList" v-model="value" class="field min-h-20 resize-y" :disabled="saving" maxlength="2000" placeholder="每行一项" />
        <input v-else v-model="value" class="field" :disabled="saving" required maxlength="150" />
      </label>
      <p class="leading-5 text-ink/60">保存到个人画像，后续推荐也会采用。保存后将重新执行本轮检索。</p>
      <p v-if="error" class="leading-5 text-red-700" role="alert">{{ error }}</p>
      <div class="flex flex-wrap gap-2">
        <button type="submit" class="min-h-10 rounded-lg bg-navy px-3 font-medium text-white disabled:opacity-50" :disabled="saving || disabled">{{ saving ? '正在保存…' : '保存并重新推荐' }}</button>
        <button type="button" class="min-h-10 rounded-lg px-3 text-ink/65 hover:bg-ink/5 disabled:opacity-40" :disabled="saving" @click="editing = false">取消</button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { correctProfileFact } from '@/api/profile'
import type { ProfileEvidence } from '@/types/analysis'
import { getApiErrorMessage } from '@/utils/apiError'

const props = defineProps<{ fact: ProfileEvidence; disabled?: boolean }>()
const emit = defineEmits<{ saved: [] }>()
const editing = ref(false)
const saving = ref(false)
const value = ref('')
const error = ref('')
const isAbility = computed(() => props.fact.key.startsWith('topic:'))
const isList = computed(() => ['learning_goals', 'interests'].includes(props.fact.key))
const abilityTopic = computed(() => (props.fact.value_json as Record<string, unknown>)?.topic ?? '')
function begin(): void {
  const raw = props.fact.value_json
  value.value = isAbility.value ? String((raw as Record<string, unknown>)?.level ?? 'unknown')
    : Array.isArray(raw) ? raw.join('\n') : String(raw ?? '')
  error.value = ''
  editing.value = true
}
async function save(): Promise<void> {
  if (saving.value || props.disabled) return
  saving.value = true
  error.value = ''
  const nextValue = isAbility.value
    ? { ...(props.fact.value_json as Record<string, unknown>), level: value.value }
    : isList.value ? [...new Set(value.value.split('\n').map(v => v.trim()).filter(Boolean))] : value.value.trim()
  try {
    await correctProfileFact(props.fact.key, nextValue, props.fact.value_json)
    editing.value = false
    emit('saved')
  } catch (cause) {
    error.value = getApiErrorMessage(cause, '画像未保存，请稍后重试')
  } finally { saving.value = false }
}
</script>

<style scoped>
.field { @apply block min-h-10 w-full rounded-lg border border-ink/15 bg-ink/5 px-3 py-2 text-xs text-ink outline-none focus:border-navy focus:ring-1 focus:ring-navy disabled:opacity-50; }
</style>
