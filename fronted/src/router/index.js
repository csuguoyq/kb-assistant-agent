import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const routes = [
  { path: '/', redirect: '/user/chat' },
  { path: '/login', component: () => import('../views/auth/Login.vue') },
  { path: '/register', component: () => import('../views/auth/Register.vue') },
  {
    path: '/user',
    component: () => import('../layouts/UserLayout.vue'),
    children: [
      { path: '', redirect: '/user/chat' },
      { path: 'chat', component: () => import('../views/user/Chat.vue'), meta: { title: 'AI 问答' } },
      { path: 'history', component: () => import('../views/user/History.vue'), meta: { title: '我的提问' } },
      { path: 'articles', component: () => import('../views/user/Articles.vue'), meta: { title: '知识库浏览' } },
      { path: 'profile', component: () => import('../views/user/Profile.vue'), meta: { title: '个人中心' } },
    ],
  },
  {
    path: '/admin',
    component: () => import('../layouts/AdminLayout.vue'),
    meta: { requiresEditor: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', component: () => import('../views/admin/Dashboard.vue'), meta: { title: '概览' } },
      { path: 'articles', component: () => import('../views/admin/Articles.vue'), meta: { title: '文章管理' } },
      { path: 'articles/new', component: () => import('../views/admin/ArticleEdit.vue'), meta: { title: '新建文章' } },
      { path: 'articles/:id/edit', component: () => import('../views/admin/ArticleEdit.vue'), meta: { title: '编辑文章' } },
      { path: 'categories', component: () => import('../views/admin/Categories.vue'), meta: { title: '分类管理' } },
      { path: 'records', component: () => import('../views/admin/Records.vue'), meta: { title: '问答记录' } },
      { path: 'profile', component: () => import('../views/user/Profile.vue'), meta: { title: '个人中心' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/user/chat' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  const auth = useAuth()
  if (!auth.state.ready) await auth.restoreSession()
  if (!auth.isLoggedIn()) {
    if (to.path === '/login' || to.path === '/register') return true
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' || to.path === '/register') return auth.homePath()
  if (to.meta.requiresEditor && !auth.isEditor()) return '/user/chat'
  return true
})

export default router
