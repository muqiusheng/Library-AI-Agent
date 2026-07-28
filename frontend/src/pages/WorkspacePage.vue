<template>
  <main class="flex h-screen w-full overflow-hidden bg-paper text-ink">
    <div v-if="mobileMenuOpen" class="fixed inset-0 z-30 bg-ink/35 lg:hidden" @click="mobileMenuOpen = false" />
    <aside 
      class="fixed inset-y-0 left-0 z-40 flex shrink-0 flex-col overflow-hidden bg-ink/5 p-4 lg:static lg:border-r lg:border-ink/5"
      :class="[desktopSidebarOpen ? 'lg:translate-x-0' : 'lg:-translate-x-full', mobileMenuOpen ? 'translate-x-0' : '-translate-x-full', isDragging ? '' : 'transition-all duration-300']"
      :style="{ width: mobileMenuOpen ? '280px' : (desktopSidebarOpen ? sidebarWidth + 'px' : '0px'), padding: desktopSidebarOpen || mobileMenuOpen ? '1rem' : '0', opacity: desktopSidebarOpen || mobileMenuOpen ? '1' : '0' }"
    >
      <!-- Top: Avatar & App Name (Doubao style) -->
      <div class="flex items-center gap-3 overflow-hidden px-1">
        <div class="min-w-0 flex-1">
          <h1 class="truncate text-base font-semibold">书途智引</h1>
        </div>
        <button class="grid h-8 w-8 shrink-0 place-items-center rounded-lg hover:bg-ink/5 lg:hidden" @click="mobileMenuOpen = false">×</button>
      </div>
      
      <!-- New Chat Button -->
      <button class="mt-5 flex min-h-10 w-full items-center justify-between rounded-xl bg-paper px-3 text-sm font-medium shadow-sm ring-1 ring-ink/5 hover:bg-ink/5" @click="createConversation">
        <div class="flex items-center gap-2">
          <svg class="h-4 w-4 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
          <span>新对话</span>
        </div>
        <span class="text-[10px] text-ink/35 hidden xl:inline-block">Ctrl Shift K</span>
      </button>

      <!-- History -->
      <div class="mt-6 min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
        <p class="px-2 text-xs font-semibold text-ink/40">历史对话</p>
        <div class="mt-2 space-y-0.5">
          <div v-if="conversation.loading" class="space-y-1">
            <div v-for="n in 3" :key="n" class="h-10 animate-pulse rounded-lg bg-ink/5" />
          </div>
          <button v-for="item in conversation.conversations" :key="item.id" class="group flex w-full items-center gap-2 rounded-lg px-2 py-2.5 text-left text-sm" :class="item.id === conversation.activeId ? 'bg-ink/5 font-medium' : 'text-ink/65 hover:bg-ink/5'" @click="selectConversation(item.id)">
            <svg class="h-4 w-4 shrink-0 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>
            <span class="block min-w-0 flex-1 truncate">{{ item.title }}</span>
            <span class="invisible text-ink/35 hover:text-red-500 group-hover:visible" @click.stop="conversation.removeConversation(item.id)">×</span>
          </button>
          <p v-if="!conversation.loading && !conversation.conversations.length" class="px-2 py-4 text-xs text-ink/40">
            暂无历史对话
          </p>
        </div>
      </div>

      <!-- Bottom User Section -->
      <div class="mt-4 flex flex-col gap-1 border-t border-ink/5 pt-3">
        <RouterLink class="flex items-center gap-2 rounded-lg px-2 py-2 text-sm text-ink/65 hover:bg-ink/5" to="/personal-center">
          <svg class="h-4 w-4 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
          个人中心
        </RouterLink>
        <RouterLink v-if="auth.isAdmin" class="flex items-center gap-2 rounded-lg px-2 py-2 text-sm text-ink/65 hover:bg-ink/5" to="/admin">
          <svg class="h-4 w-4 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
          数据与标签管理
        </RouterLink>
        
        <div class="mt-2 flex items-center justify-between rounded-xl px-2 py-2">
          <div class="flex min-w-0 items-center gap-2">
            <img v-if="auth.user?.avatar_url" :src="auth.user.avatar_url" class="h-8 w-8 rounded-full object-cover ring-1 ring-ink/5" />
            <div v-else class="grid h-8 w-8 place-items-center rounded-full bg-ink/5">
              <svg class="h-4 w-4 text-ink/40" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-[13px] font-medium">{{ auth.user?.display_name || auth.user?.student_no }}</p>
            </div>
          </div>
          <button class="p-1 text-ink/40 hover:text-ink" @click="signOut" title="退出登录">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
          </button>
        </div>
      </div>
    </aside>

    <!-- Resizer Handle -->
    <div 
      v-if="desktopSidebarOpen"
      class="hidden w-1 cursor-col-resize hover:bg-navy/20 active:bg-navy/40 lg:block z-50 shrink-0"
      @mousedown="startResize"
    />

    <section class="flex min-w-0 flex-1 flex-col overflow-hidden bg-paper">
      <header class="flex items-center justify-between gap-3 border-b border-ink/5 px-4 py-4 sm:px-6"><div class="flex min-w-0 items-center gap-3"><button class="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-ink/10 lg:hidden" @click="mobileMenuOpen = true">☰</button><button class="hidden h-10 w-10 shrink-0 place-items-center rounded-xl border border-ink/10 text-ink/50 hover:bg-ink/5 lg:grid" @click="desktopSidebarOpen = !desktopSidebarOpen"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" /></svg></button><div class="min-w-0"><h2 class="truncate font-semibold text-navy">{{ conversation.activeConversation?.title || '新会话' }}</h2></div></div><div class="flex items-center gap-3"><label class="hidden items-center gap-2 text-xs text-ink/50 sm:flex"><input v-model="conversation.onlyAvailable" class="accent-navy" type="checkbox" />只看在馆可借</label><button class="relative flex h-10 items-center justify-center rounded-xl border border-ink/10 px-4 text-sm font-medium text-navy" aria-label="通知" @click="notificationOpen = true">消息<span v-if="notifications.unreadCount" class="absolute -right-1 -top-1 grid min-h-5 min-w-5 place-items-center rounded-full bg-red-500 px-1 text-[10px] text-white">{{ notifications.unreadCount }}</span></button></div></header>

        <div ref="messagePane" class="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-7">
          <div v-if="!conversation.messages.length" class="mx-auto flex h-full max-w-xl flex-col items-center justify-center text-center"><p class="mt-5 text-sm text-ink/40">你好，{{ auth.user?.display_name || auth.user?.student_no }}</p><h3 class="mt-2 text-2xl font-semibold text-navy">描述你的学习目标</h3><p class="mt-3 text-sm leading-7 text-ink/55">我会从 41,774 本真实书目和 113,204 个馆藏副本中，为你筛选适合的阅读起点。</p><div class="mt-7 grid w-full gap-3 text-left sm:grid-cols-2"><button v-for="prompt in prompts" :key="prompt" class="min-h-12 rounded-2xl border border-ink/10 p-4 text-sm hover:border-navy text-ink" @click="draft = prompt">{{ prompt }}</button></div></div>
          <div v-else class="mx-auto max-w-4xl space-y-7"><div v-for="message in conversation.messages" :key="message.id" :class="message.role === 'user' ? 'flex justify-end' : ''"><div v-if="message.role === 'user'" class="max-w-[85%] rounded-2xl rounded-br-md bg-navy px-4 py-3 text-sm leading-6 text-white sm:max-w-[70%]">{{ message.content }}</div><div v-else class="space-y-4"><div class="flex items-start gap-3"><div class="min-w-0 flex-1"><div v-if="message.content" class="prose prose-sm max-w-none text-ink/80 prose-p:leading-7 prose-a:text-navy hover:prose-a:text-navy-light prose-li:my-0.5" v-html="renderMarkdown(message.content)"></div><div v-if="message.pending" class="mt-2 flex items-center gap-2 text-xs text-sage"><span class="h-2 w-2 animate-pulse rounded-full bg-sage" />{{ statusLabel }}</div><div v-if="message.failed" class="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{{ conversation.errorMessage }} <button class="ml-2 font-semibold underline" @click="conversation.retry">重试</button></div></div></div><div v-if="message.recommendation" class="grid gap-4 xl:grid-cols-2"><RecommendationCard v-for="book in message.recommendation.items" :key="book.book_id" :book="book" :set-id="message.recommendation.id" @detail="selectedBook = $event" @add-to-path="createPath(message.recommendation.id)" /><RouterLink class="rounded-2xl border border-dashed border-sage/30 p-4 text-center text-sm font-medium text-sage xl:col-span-2" :to="`/evaluate/${message.recommendation.id}`">参与匿名人工评测（1–5 分）</RouterLink></div></div></div></div>
        </div>

        <footer class="border-t border-ink/5 bg-paper px-3 py-3 sm:px-6"><div class="mx-auto max-w-4xl"><label class="mb-2 flex items-center gap-2 text-xs text-ink/45 sm:hidden"><input v-model="conversation.onlyAvailable" class="accent-navy" type="checkbox" />只看在馆可借</label><form class="flex items-end gap-2 rounded-2xl border border-ink/10 bg-ink/5 p-2 sm:p-3" @submit.prevent="send"><textarea v-model="draft" aria-label="输入消息" class="max-h-32 min-h-12 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none" @keydown.enter.exact.prevent="send" /><button v-if="conversation.isStreaming" class="min-h-11 rounded-xl border border-navy px-4 text-sm font-semibold text-navy" type="button" @click="conversation.stop">停止</button><button v-else class="min-h-11 rounded-xl bg-navy px-5 text-sm font-semibold text-white" type="submit">发送</button></form><p class="mt-2 text-center text-[11px] text-ink/35">推荐仅来自当前已发布馆藏，AI 不会编造书目和位置。</p></div></footer>
      </section>
    <BookDetailDrawer :book="selectedBook" @close="selectedBook = null" />
    <NotificationPanel v-if="notificationOpen" @close="notificationOpen = false" />
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
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
const mobileMenuOpen = ref(false); const desktopSidebarOpen = ref(true); const notificationOpen = ref(false); const draft = ref(''); const selectedBook = ref<RecommendationCardData | null>(null); const messagePane = ref<HTMLElement | null>(null)
const sidebarWidth = ref(260); const isDragging = ref(false); const startX = ref(0); const startWidth = ref(0);
const prompts = ['从零开始学习 Java', '为数据库课程找拓展阅读', '了解人工智能基础', '生成项目实践阅读路线']

function startResize(e: MouseEvent) {
  isDragging.value = true
  startX.value = e.clientX
  startWidth.value = sidebarWidth.value
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function onResize(e: MouseEvent) {
  if (!isDragging.value) return
  const dx = e.clientX - startX.value
  sidebarWidth.value = Math.max(200, Math.min(480, startWidth.value + dx))
}

function stopResize() {
  isDragging.value = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

function renderMarkdown(content: string | undefined) {
  if (!content) return ''
  return DOMPurify.sanitize(marked.parse(content, { breaks: true, gfm: true }) as string)
}

const statusLabel = computed(() => {
  const labels: Partial<Record<StreamStatus, string>> = {
    understanding: '正在理解你的需求…',
    retrieving: '正在检索真实馆藏…',
    organizing: '正在组织推荐…'
  }
  return labels[conversation.streamStatus] ?? '正在连接…'
})
onMounted(async () => { 
  await Promise.all([conversation.loadConversations(), notifications.refresh()]); 
  if (conversation.activeId && conversation.conversations.find(c => c.id === conversation.activeId)) {
    await conversation.selectConversation(conversation.activeId)
  } else {
    const emptyConv = conversation.conversations.find(c => c.title === '新会话')
    if (emptyConv) {
      await conversation.selectConversation(emptyConv.id)
    } else {
      await conversation.newConversation()
    }
  }
})
watch(() => conversation.messages, async () => { await nextTick(); if (messagePane.value) messagePane.value.scrollTop = messagePane.value.scrollHeight }, { deep: true })
async function createConversation() { 
  const emptyConv = conversation.conversations.find(c => c.title === '新会话')
  if (emptyConv) await conversation.selectConversation(emptyConv.id)
  else await conversation.newConversation()
  mobileMenuOpen.value = false 
}
async function selectConversation(id: string) { await conversation.selectConversation(id); mobileMenuOpen.value = false }
async function send() { const value = draft.value; if (!value.trim()) return; draft.value = ''; await conversation.send(value) }
async function createPath(setId: string) { const path = await createLearningPath(setId); await router.push(`/personal-center/paths/${path.id}`) }
async function signOut() { 
  if (conversation.activeId && conversation.messages.length === 0) {
    await conversation.removeConversation(conversation.activeId).catch(() => {})
  }
  await auth.logout(); 
  sessionStorage.removeItem('bookpath_active_conversation_id');
  await router.replace('/login') 
}
</script>
