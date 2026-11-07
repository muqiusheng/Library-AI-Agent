<template>
  <div>
  <details class="process rounded-xl bg-ink/[0.025] text-sm" :open="expanded" @toggle="onToggle">
    <summary class="flex min-h-11 cursor-pointer list-none items-center gap-3 rounded-xl px-3 py-2.5 text-ink/65 hover:bg-ink/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy sm:px-4">
      <span class="grid h-5 w-5 shrink-0 place-items-center" :class="trace.status === 'error' ? 'text-red-700' : 'text-sage'" aria-hidden="true">
        <svg v-if="running" class="h-4 w-4 motion-safe:animate-spin" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="1.5" opacity=".2" /><path d="M10 3a7 7 0 0 1 7 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" /></svg>
        <svg v-else-if="trace.status === 'complete'" class="h-4 w-4" viewBox="0 0 20 20" fill="none"><path d="m5 10 3 3 7-7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" /></svg>
        <span v-else>{{ trace.status === 'error' ? '!' : 'Ⅱ' }}</span>
      </span>
      <span class="min-w-0 flex-1">
        <span class="block font-medium text-ink/75" role="status">{{ headline }}</span>
        <span v-if="trace.profile_evidence.length || trace.comparisons.length" class="mt-0.5 block text-xs text-ink/60">
          {{ trace.profile_evidence.length }} 条参考画像 · {{ trace.comparisons.length }} 本重点图书
          <span v-if="(trace.attempt ?? 1) > 1"> · 第 {{ trace.attempt }} 次处理</span>
        </span>
      </span>
      <span class="shrink-0 text-xs tabular-nums text-ink/60" aria-hidden="true">{{ running ? '已用时' : '用时' }} {{ duration(trace.elapsed_ms + extraTime) }}</span>
      <svg class="h-3.5 w-3.5 shrink-0 text-ink/50 transition-transform duration-150 motion-reduce:transition-none" :class="expanded ? 'rotate-180' : ''" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m5 7.5 5 5 5-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </summary>

    <div class="space-y-5 px-3 pb-4 sm:px-4">
      <p v-if="trace.retry_note" class="rounded-lg bg-sage/10 p-3 text-xs leading-5 text-moss">{{ trace.retry_note }}</p>
      <ol class="space-y-3 border-l border-ink/10 pl-4" aria-label="执行阶段">
        <li v-for="(step, index) in trace.steps" :key="`${step.id}-${index}`" class="relative">
          <span class="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full ring-4 ring-paper" :class="step.status === 'running' ? 'bg-sage' : step.status === 'error' ? 'bg-red-500' : 'bg-ink/25'" aria-hidden="true" />
          <div class="flex items-start justify-between gap-3">
            <span class="text-xs font-medium" :class="step.status === 'running' ? 'text-sage' : 'text-ink/65'">{{ stepLabel(step) }}</span>
            <span class="shrink-0 text-xs tabular-nums text-ink/55">{{ step.reused ? `复用 · 上次 ${duration(step.previous_elapsed_ms ?? 0)}` : duration(step.elapsed_ms + (step.status === 'running' ? extraTime : 0)) }}</span>
          </div>
          <p v-if="step.detail" class="mt-1 break-words text-xs leading-5 text-ink/60">{{ step.detail }}</p>
        </li>
      </ol>

      <details v-if="trace.filter_stats" class="rounded-lg border border-ink/10 p-3 text-xs">
        <summary class="min-h-8 cursor-pointer font-medium leading-6 text-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy">筛选明细 · {{ trace.filter_stats.retrieved }} 本检索候选 → {{ trace.filter_stats.retained }} 本保留</summary>
        <ol class="mt-2 space-y-2">
          <li v-for="step in trace.filter_stats.steps" :key="step.id" class="flex items-start justify-between gap-3 leading-5">
            <span class="text-ink/65">{{ step.label }}<span v-if="!step.applied" class="ml-1 text-ink/50">（未启用）</span></span>
            <span class="shrink-0 tabular-nums text-ink/65">移除 {{ step.removed }} · 剩余 {{ step.remaining }}</span>
          </li>
        </ol>
        <p class="mt-3 leading-5 text-ink/55">按顺序统计，每本书只计入首次被排除的条件。{{ trace.filter_stats.compared }} 本进入重点排序<span v-if="!running">，最终入选 {{ trace.filter_stats.selected }} 本</span>。</p>
        <p v-if="trace.filter_stats.retained_from_previous" class="mt-1 leading-5 text-ink/55">最终书单中有 {{ trace.filter_stats.retained_from_previous }} 本沿用上一轮选择。</p>
      </details>

      <section v-if="trace.profile_evidence.length" aria-label="本次参考画像">
        <h4 class="text-xs font-semibold text-navy">本次参考画像</h4>
        <p class="mt-1 text-xs leading-5 text-ink/60">以下信息提供给本次推荐流程，本次明确要求优先。</p>
        <ul class="mt-3 space-y-3">
          <li v-for="fact in trace.profile_evidence" :key="fact.key" class="min-w-0">
            <p class="break-words text-xs leading-5 text-ink/75"><span class="mr-2 text-ink/60">{{ fact.label }}</span>{{ fact.value }}</p>
            <p class="mt-0.5 text-xs leading-5 text-ink/60">{{ fact.usage }}</p>
            <details class="mt-1 text-xs">
              <summary class="inline-flex min-h-8 cursor-pointer items-center gap-2 rounded text-ink/55 hover:text-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy">
                <span class="rounded bg-ink/5 px-1.5 py-0.5">{{ fact.source_label }}</span>
                <span>{{ fact.nature }}</span><span class="text-ink/50">查看来源</span>
              </summary>
              <div class="mt-1 border-l-2 border-sage/20 pl-3 text-ink/55">
                <blockquote class="whitespace-pre-wrap break-words leading-5">{{ fact.evidence || '这条信息未保留原文。' }}</blockquote>
                <p v-if="fact.updated_at" class="mt-1 text-ink/55">记录时间：{{ formatProfileDate(fact.updated_at) }}</p>
              </div>
            </details>
            <div v-if="canAct" class="mt-1 flex flex-wrap items-start gap-x-2">
              <ProfileFactEditor :fact="fact" :disabled="busy" @saved="emit('corrected')" />
              <button type="button" class="min-h-9 rounded px-2 text-xs text-ink/60 hover:bg-ink/5 hover:text-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy disabled:opacity-40" :disabled="busy" @click="emit('exclude', [...(trace.excluded_profile_keys || []), fact.key])">本次不采用并重新推荐</button>
            </div>
          </li>
        </ul>
      </section>

      <section v-if="trace.excluded_profile_evidence?.length" aria-label="本次未采用的画像">
        <h4 class="text-xs font-semibold text-navy">本次未采用的画像</h4>
        <p class="mt-1 text-xs leading-5 text-ink/60">仅影响这一轮推荐，个人画像仍保留。</p>
        <ul class="mt-2 space-y-2">
          <li v-for="fact in trace.excluded_profile_evidence" :key="fact.key" class="flex flex-wrap items-center justify-between gap-2 text-xs">
            <span class="break-words leading-5 text-ink/60">{{ fact.label }}：{{ fact.value }}</span>
            <button v-if="canAct" type="button" class="min-h-9 rounded px-2 text-navy hover:bg-ink/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy disabled:opacity-40" :disabled="busy" @click="emit('exclude', (trace.excluded_profile_keys || []).filter(key => key !== fact.key))">恢复采用并重新推荐</button>
          </li>
        </ul>
      </section>

      <section v-if="trace.comparisons.length" aria-label="重点书籍比较">
        <h4 class="text-xs font-semibold text-navy">重点书籍比较</h4>
        <p class="mt-1 text-xs leading-5 text-ink/60">按最终推荐顺序，展示前 {{ trace.comparisons.length }} 本的适配依据。</p>
        <ol class="mt-3 space-y-4">
          <li v-for="book in trace.comparisons" :key="book.book_id" class="flex min-w-0 gap-3">
            <span class="pt-0.5 text-xs font-medium tabular-nums text-sage">{{ String(book.rank).padStart(2, '0') }}</span>
            <div class="min-w-0 flex-1">
              <p class="break-words text-xs font-semibold leading-5 text-ink/80">{{ book.title }}</p>
              <p class="mt-1 break-words text-xs leading-6 text-ink/65">{{ book.reason }}</p>
              <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-ink/60"><span>{{ book.method === 'llm' ? '简介分析' : '规则初筛' }}</span><span>{{ book.available_count }} 本可借</span></div>
              <details class="mt-1 text-xs">
                <summary class="min-h-8 cursor-pointer rounded py-1.5 text-ink/60 hover:text-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy">查看书籍资料与初筛分项</summary>
                <p class="break-words leading-6 text-ink/55">简介摘录：{{ book.description_excerpt || '暂无简介，内容与先修要求尚无法确认。' }}</p>
                <dl class="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
                  <div v-for="(value, key) in book.scores" :key="key" class="flex justify-between gap-2 text-[11px] text-ink/60"><dt>{{ scoreLabels[key] || key }}</dt><dd class="tabular-nums">{{ value }}</dd></div>
                </dl>
                <p class="mt-2 text-[11px] leading-5 text-ink/55">分项为初筛参考分，不代表适配概率或最终排名。</p>
              </details>
            </div>
          </li>
        </ol>
        <p v-if="trace.comparisons.some(book => book.method === 'rule')" class="mt-3 text-xs leading-5 text-ink/60">标为“规则初筛”的书籍按规则排序，未生成简介语义比较结果。</p>
      </section>
      <CandidateComparison v-if="trace.candidates?.length" :candidates="trace.candidates" />

      <div v-if="trace.summary" class="border-t border-ink/5 pt-3">
        <h4 class="text-xs font-semibold text-navy">{{ trace.status === 'complete' ? '最终推荐依据' : '已确定的推荐依据' }}</h4>
        <p class="mt-1 break-words text-xs leading-6 text-ink/65">{{ trace.summary }}</p>
      </div>
      <div v-if="canAct && trace.retry_stages?.length" class="border-t border-ink/5 pt-3">
        <h4 class="text-xs font-semibold text-navy">按阶段重新执行</h4>
        <p class="mt-1 text-xs leading-5 text-ink/60">复用已完成的前置结果；画像变化时会重新检索。</p>
        <div class="mt-2 flex flex-wrap gap-2">
          <button v-for="stage in trace.retry_stages" :key="stage" type="button" class="min-h-10 rounded-lg border border-ink/10 bg-paper px-3 text-xs text-navy hover:bg-ink/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy disabled:opacity-40" :disabled="busy" @click="emit('retry', stage)">{{ retryLabels[stage] }}</button>
        </div>
      </div>
      <p v-else-if="!running && trace.retry_stages?.length" class="text-xs leading-5 text-ink/55">历史记录保留当时的依据；画像操作和阶段重试仅对最新一轮推荐开放。</p>
    </div>
  </details>
  <p v-if="actionError" class="mt-2 rounded-lg bg-red-50 p-3 text-xs leading-5 text-red-700" role="alert">{{ actionError }} 原推荐仍保留。</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import type { AnalysisStep, AnalysisTrace, RetryStage } from '@/types/analysis'
import { formatProfileDate } from '@/utils/profilePresentation'
import ProfileFactEditor from './ProfileFactEditor.vue'
import CandidateComparison from './CandidateComparison.vue'

const props = defineProps<{ trace: AnalysisTrace; receivedAt?: number; canAct?: boolean; busy?: boolean; actionError?: string }>()
const emit = defineEmits<{ retry: [stage: RetryStage]; exclude: [keys: string[]]; corrected: [] }>()
const expanded = ref(props.trace.status === 'running')
const now = ref(Date.now())
const running = computed(() => props.trace.status === 'running')
const extraTime = computed(() => running.value && props.receivedAt ? Math.max(0, now.value - props.receivedAt) : 0)
let timer: ReturnType<typeof setInterval> | undefined
watch(running, (value) => {
  clearInterval(timer)
  expanded.value = value
  now.value = Date.now()
  if (value) timer = setInterval(() => { now.value = Date.now() }, 200)
}, { immediate: true })
onUnmounted(() => clearInterval(timer))

const headline = computed(() => {
  if (running.value) return props.trace.steps.at(-1)?.label || '正在处理请求'
  if (props.trace.status === 'error') return '处理未完成 · 查看已完成步骤'
  if (props.trace.status === 'stopped') return '已停止 · 保留已完成步骤'
  return props.trace.comparisons.length || props.trace.summary ? '推荐过程与依据' : '处理过程'
})
const scoreLabels: Record<string, string> = { goal: '目标匹配', difficulty: '难度匹配', major: '专业相关', interest: '兴趣相关', semantic: '语义相关', availability: '可借情况' }
const retryLabels: Record<RetryStage, string> = { retrieving: '重新检索', comparing: '重新比较 · 复用检索', generating: '重写推荐语 · 复用书单' }
const completedLabels: Record<string, string> = { understanding: '已理解需求', profile: '已读取学习画像', intent: '已明确本次需求', retrieving: '已检索馆藏', filtering: '已筛选候选', comparing: '已完成适配排序', generating: '已生成回复' }
function stepLabel(step: AnalysisStep): string {
  if (step.status === 'complete') return completedLabels[step.id] || step.label.replace(/^正在/, '已完成')
  if (step.status === 'stopped') return `${step.label.replace(/^正在/, '')} · 已停止`
  if (step.status === 'error') return `${step.label.replace(/^正在/, '')} · 未完成`
  return step.label
}
function duration(ms: number): string {
  return `${(Math.max(0, ms) / 1000).toFixed(ms < 10000 ? 1 : 0)} 秒`
}
function onToggle(event: Event): void {
  expanded.value = (event.target as HTMLDetailsElement).open
}
</script>

<style scoped>
summary::-webkit-details-marker { display: none; }
.process { overflow-wrap: anywhere; }
</style>
