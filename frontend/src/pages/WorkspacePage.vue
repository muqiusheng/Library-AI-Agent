<template>
  <main class="min-h-screen bg-paper px-3 py-3 sm:px-5 lg:px-7">
    <div class="mx-auto grid max-w-[1580px] gap-4 lg:grid-cols-[270px_minmax(0,1fr)]">
      <div v-if="mobileMenuOpen" class="fixed inset-0 z-30 bg-black/35 lg:hidden" @click="mobileMenuOpen = false" />
      <aside class="fixed inset-y-3 left-3 z-40 flex w-[min(286px,calc(100vw-24px))] flex-col rounded-3xl bg-navy p-5 text-white shadow-card transition-transform lg:static lg:z-auto lg:w-auto lg:translate-x-0" :class="mobileMenuOpen ? 'translate-x-0' : '-translate-x-[110%]'">
        <div class="flex items-start justify-between"><div><p class="text-xs font-semibold uppercase tracking-[0.22em] text-amber">BookPath AI</p><h1 class="mt-2 text-2xl font-semibold">书途智引</h1></div><button class="grid h-10 w-10 place-items-center rounded-xl bg-white/10 lg:hidden" @click="mobileMenuOpen = false">×</button></div>
        <button class="mt-6 min-h-11 w-full rounded-xl bg-white px-4 text-sm font-semibold text-navy" @click="createConversation">＋ 新建会话</button>
        <div class="mt-6 min-h-0 flex-1 overflow-y-auto"><p class="px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-white/35">最近会话</p><div class="mt-2 space-y-1"><div v-if="conversation.loading" class="space-y-2"><div v-for="n in 3" :key="n" class="h-11 animate-pulse rounded-xl bg-white/5" /></div><button v-for="item in conversation.conversations" :key="item.id" class="group flex w-full items-center gap-2 rounded-xl px-3 py-3 text-left text-sm" :class="item.id === conversation.activeId ? 'bg-white/12 text-white' : 'text-white/60 hover:bg-white/5'" @click="selectConversation(item.id)"><span class="min-w-0 flex-1 truncate">{{ item.title }}</span><span class="invisible text-white/35 group-hover:visible" @click.stop="conversation.removeConversation(item.id)">×</span></button><p v-if="!conversation.loading && !conversation.conversations.length" class="px-3 py-6 text-center text-xs leading-5 text-white/40">还没有会话，从一个学习目标开始吧。</p></div></div>
        <nav class="border-t border-white/10 pt-3 text-sm"><RouterLink class="block rounded-xl px-3 py-2.5 text-white/55" to="/paths">我的学习路径</RouterLink><RouterLink class="block rounded-xl px-3 py-2.5 text-white/55" to="/profile">我的画像</RouterLink><RouterLink v-if="auth.isAdmin" class="block rounded-xl px-3 py-2.5 text-white/55" to="/admin">数据与标签管理</RouterLink></nav>
        <div class="mt-3 border-t border-white/10 pt-4"><p class="truncate text-sm font-medium">{{ auth.user?.display_name || auth.user?.student_no }}</p><p class="mt-1 text-xs text-white/40">{{ auth.user?.student_no }} · {{ auth.isAdmin ? '管理员' : '学生' }}</p><button class="mt-3 min-h-10 w-full rounded-xl border border-white/15 text-sm text-white/65" @click="signOut">退出登录</button></div>
      </aside>

      <section class="flex h-[calc(100vh-24px)] min-w-0 flex-col overflow-hidden rounded-3xl bg-white shadow-card sm:h-[calc(100vh-40px)]">
        <header class="flex items-center justify-between gap-3 border-b border-black/5 px-4 py-4 sm:px-6"><div class="flex min-w-0 items-center gap-3"><button class="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-black/10 lg:hidden" @click="mobileMenuOpen = true">☰</button><div class="min-w-0"><p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-sage">AI 学习工作台</p><h2 class="mt-1 truncate font-semibold text-navy">{{ conversation.activeConversation?.title || '新会话' }}</h2></div></div><div class="flex items-center gap-3"><label class="hidden items-center gap-2 text-xs text-black/50 sm:flex"><input v-model="conversation.onlyAvailable" class="accent-navy" type="checkbox" />只看在馆可借</label><button class="relative grid h-10 w-10 place-items-center rounded-xl border border-black/10 text-navy" aria-label="通知" @click="notificationOpen = true">铃<span v-if="notifications.unreadCount" class="absolute -right-1 -top-1 grid min-h-5 min-w-5 place-items-center rounded-full bg-red-500 px-1 text-[10px] text-white">{{ notifications.unreadCount }}</span></button></div></header>

        <div ref="messagePane" class="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-7">
          <div v-if="!conversation.messages.length" class="mx-auto flex h-full max-w-xl flex-col items-center justify-center text-center"><div class="grid h-14 w-14 place-items-center rounded-2xl bg-amber/15 text-2xl text-navy">路</div><p class="mt-5 text-sm text-black/40">你好，{{ auth.user?.display_name || auth.user?.student_no }}</p><h3 class="mt-2 text-2xl font-semibold text-navy">描述你的学习目标</h3><p class="mt-3 text-sm leading-7 text-black/55">我会从 41,774 本真实书目和 113,204 个馆藏副本中，为你筛选适合的阅读起点。</p><div class="mt-7 grid w-full gap-3 text-left sm:grid-cols-2"><button v-for="prompt in prompts" :key="prompt" class="min-h-12 rounded-2xl border border-black/10 p-4 text-sm hover:border-navy" @click="draft = prompt">{{ prompt }}</button></div></div>
          <div v-else class="mx-auto max-w-4xl space-y-7"><div v-for="message in conversation.messages" :key="message.id" :class="message.role === 'user' ? 'flex justify-end' : ''"><div v-if="message.role === 'user'" class="max-w-[85%] rounded-2xl rounded-br-md bg-navy px-4 py-3 text-sm leading-6 text-white sm:max-w-[70%]">{{ message.content }}</div><div v-else class="space-y-4"><div class="flex items-start gap-3"><div class="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-amber/15 text-sm text-navy">路</div><div class="min-w-0 flex-1"><p v-if="message.content" class="text-sm leading-7 text-black/65">{{ message.content }}</p><div v-if="message.pending" class="mt-2 flex items-center gap-2 text-xs text-sage"><span class="h-2 w-2 animate-pulse rounded-full bg-sage" />{{ statusLabel }}</div><div v-if="message.failed" class="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{{ conversation.errorMessage }} <button class="ml-2 font-semibold underline" @click="conversation.retry">重试</button></div></div></div><div v-if="message.recommendation" class="grid gap-4 xl:grid-cols-2"><RecommendationCard v-for="book in message.recommendation.items" :key="book.book_id" :book="book" :set-id="message.recommendation.id" @detail="selectedBook = $event" @add-to-path="createPath(message.recommendation.id)" /><RouterLink class="rounded-2xl border border-dashed border-sage/30 p-4 text-center text-sm font-medium text-sage xl:col-span-2" :to="`/evaluate/${message.recommendation.id}`">参与匿名人工评测（1–5 分）</RouterLink></div></div></div></div>
        </div>

        <footer class="border-t border-black/5 bg-white px-3 py-3 sm:px-6"><div class="mx-auto max-w-4xl"><label class="mb-2 flex items-center gap-2 text-xs text-black/45 sm:hidden"><input v-model="conversation.onlyAvailable" class="accent-navy" type="checkbox" />只看在馆可借</label><form class="flex items-end gap-2 rounded-2xl border border-black/10 bg-paper p-2 sm:p-3" @submit.prevent="send"><textarea v-model="draft" aria-label="输入消息" class="max-h-32 min-h-12 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none" @keydown.enter.exact.prevent="send" /><button v-if="conversation.isStreaming" class="min-h-11 rounded-xl border border-navy px-4 text-sm font-semibold text-navy" type="button" @click="conversation.stop">停止</button><button v-else class="min-h-11 rounded-xl bg-navy px-5 text-sm font-semibold text-white" type="submit">发送</button></form><p class="mt-2 text-center text-[11px] text-black/35">推荐仅来自当前已发布馆藏，AI 不会编造书目和位置。</p></div></footer>
      </section>
    </div>
    <BookDetailDrawer :book="selectedBook" @close="selectedBook = null" />
    <NotificationPanel v-if="notificationOpen" @close="notificationOpen = false" />
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { createLearningPath } from '@/api/learningPaths'
import NotificationPanel from '@/components/notification/NotificationPanel.vue'
import BookDetailDrawer from '@/components/recommendation/BookDetailDrawer.vue'
import RecommendationCard from '@/components/recommendation/RecommendationCard.vue'
import { useAuthStore } from '@/stores/auth'
import { useConversationStore } from '@/stores/conversation'
import { useNotificationStore } from '@/stores/notifications'
import type { StreamStatus } from '@/types/conversation'
import type { RecommendationCardData } from '@/types/recommendation'

const auth = useAuthStore(); const conversation = useConversationStore(); const notifications = useNotificationStore(); const router = useRouter()
const mobileMenuOpen = ref(false); const notificationOpen = ref(false); const draft = ref(''); const selectedBook = ref<RecommendationCardData | null>(null); const messagePane = ref<HTMLElement | null>(null)
const prompts = ['从零开始学习 Java', '为数据库课程找拓展阅读', '了解人工智能基础', '生成项目实践阅读路线']
const statusLabel = computed(() => {
  const labels: Partial<Record<StreamStatus, string>> = {
    understanding: '正在理解你的需求…',
    retrieving: '正在检索真实馆藏…',
    organizing: '正在组织推荐…'
  }
  return labels[conversation.streamStatus] ?? '正在连接…'
})
onMounted(async () => { await Promise.all([conversation.loadConversations(), notifications.refresh()]); await conversation.newConversation() })
watch(() => conversation.messages, async () => { await nextTick(); if (messagePane.value) messagePane.value.scrollTop = messagePane.value.scrollHeight }, { deep: true })
async function createConversation() { await conversation.newConversation(); mobileMenuOpen.value = false }
async function selectConversation(id: string) { await conversation.selectConversation(id); mobileMenuOpen.value = false }
async function send() { const value = draft.value; if (!value.trim()) return; draft.value = ''; await conversation.send(value) }
async function createPath(setId: string) { const path = await createLearningPath(setId); await router.push(`/paths/${path.id}`) }
async function signOut() { await auth.logout(); await router.replace('/login') }
</script>
