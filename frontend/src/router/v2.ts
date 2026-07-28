import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    publicOnly?: boolean
    requiresAdmin?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', redirect: '/workspace' },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/pages/LoginPage.vue'),
      meta: { publicOnly: true }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/pages/RegisterPage.vue'),
      meta: { publicOnly: true }
    },
    {
      path: '/privacy',
      name: 'privacy',
      component: () => import('@/pages/PrivacyPage.vue')
    },
    {
      path: '/workspace',
      name: 'workspace',
      component: () => import('@/pages/WorkspacePage.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/personal-center',
      component: () => import('@/pages/PersonalCenterPage.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/personal-center/basic' },
        { path: 'basic', name: 'personal-basic', component: () => import('@/components/Profile/BasicInfoEditor.vue') },
        { path: 'profile', name: 'personal-profile', component: () => import('@/components/Profile/ProfileEditor.vue') },
        { path: 'paths/:id?', name: 'personal-paths', component: () => import('@/components/Profile/LearningPaths.vue') },
        { path: 'theme', name: 'personal-theme', component: () => import('@/components/Profile/ThemeEditor.vue') }
      ]
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/pages/AdminPage.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/evaluate/:setId',
      name: 'evaluation',
      component: () => import('@/pages/EvaluationPage.vue')
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/pages/NotFoundPage.vue')
    }
  ]
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.hydrate()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.publicOnly && auth.isAuthenticated) return auth.isAdmin ? '/admin' : '/workspace'
  if (to.meta.requiresAdmin && !auth.isAdmin) return '/workspace'
  if (auth.isAdmin && ['workspace', 'personal-center'].includes(String(to.name))) {
    return '/admin'
  }
  return true
})

router.onError((error) => {
  if (error.message.includes('Failed to fetch dynamically imported module') || error.message.includes('Importing a module script failed')) {
    window.location.reload()
  }
})

export default router
