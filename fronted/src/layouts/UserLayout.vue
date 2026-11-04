<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { useChatStore } from '../composables/useChat'
import { apiFetch } from '../api/request'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const chat = useChatStore()
const menuOpen = ref(false)

const recentSessions = ref([])

async function loadRecent() {
  try {
    const sessions = await apiFetch('/api/chat/sessions')
    recentSessions.value = sessions.slice(0, 5)
  } catch {
    recentSessions.value = []
  }
}

async function openSession(s) {
  await chat.loadSessionById(s.id)
  router.push('/user/chat')
  closeMenu()
}

// 进入问答页后刷新最近会话列表（新提问会出现在最上面）
watch(() => route.path, (p) => { if (p === '/user/chat') loadRecent() }, { immediate: true })

// 普通用户（user）：只能使用知识库
const userNav = [
  {
    label: '使用知识库',
    items: [
      { path: '/user/chat', icon: '🤖', label: 'AI 问答' },
      { path: '/user/history', icon: '🕘', label: '我的提问' },
      { path: '/user/articles', icon: '📚', label: '知识库浏览' },
    ],
  },
]

// 知识编辑 / 管理员：使用 + 管理（admin 额外有用户管理）
const staffNav = [
  {
    label: '使用知识库',
    items: [
      { path: '/user/chat', icon: '🤖', label: 'AI 问答' },
      { path: '/user/history', icon: '🕘', label: '我的提问' },
    ],
  },
  {
    label: '管理知识库',
    items: [
      { path: '/admin/dashboard', icon: '📊', label: '概览' },
      { path: '/admin/articles', icon: '📝', label: '文章管理' },
      { path: '/admin/categories', icon: '🗂️', label: '分类管理' },
      { path: '/admin/records', icon: '💬', label: '问答记录' },
    ],
  },
]

const navs = auth.isEditor() ? staffNav : userNav

function closeMenu() {
  menuOpen.value = false
}
</script>

<template>
  <div class="layout">
    <div class="mobile-topbar">
      <span class="logo-mini">🧠 知识库</span>
      <button class="btn menu-btn" @click="menuOpen = !menuOpen">☰</button>
    </div>
    <div v-if="menuOpen" class="mask" @click="menuOpen = false"></div>
    <aside class="sidebar" :class="{ open: menuOpen }">
      <div class="logo">🧠 公司知识库</div>
      <nav v-for="group in navs" :key="group.label">
        <div class="group-label">{{ group.label }}</div>
        <router-link v-for="item in group.items" :key="item.path" :to="item.path" class="nav-item" @click="closeMenu">
          <span>{{ item.icon }}</span>{{ item.label }}
        </router-link>
        <template v-if="group.label === '使用知识库' && recentSessions.length">
          <div class="group-label" style="margin-top: 6px">🕘 最近会话</div>
          <a v-for="s in recentSessions" :key="s.id" class="nav-item session-item" :title="s.title" @click="openSession(s)">
            {{ s.title || '（无标题）' }}
          </a>
        </template>
      </nav>
      <div class="sidebar-footer">
        <router-link to="/user/profile" class="nav-item" @click="closeMenu"><span>👤</span>个人中心</router-link>
        <a class="nav-item" @click.prevent="auth.logout(); $router.push('/login')"><span>🚪</span>退出登录</a>
        <div class="role-badge">{{ auth.state.user?.name || auth.state.user?.username }}（{{ auth.role() === 'admin' ? '管理员' : auth.role() === 'editor' ? '知识编辑' : '用户' }}）</div>
      </div>
    </aside>
    <main class="main"><router-view /></main>
  </div>
</template>

<style scoped>
.layout { display: flex; min-height: 100vh; }
.sidebar {
  width: 220px; background: #1e2433; color: #c8cede;
  display: flex; flex-direction: column; padding: 16px 12px; position: sticky; top: 0; height: 100vh;
}
.logo { font-size: 17px; font-weight: 600; color: #fff; padding: 8px 12px 14px; }
.group-label { font-size: 12px; color: #6a7288; padding: 14px 12px 6px; }
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 8px; color: #c8cede; margin-bottom: 2px; cursor: pointer;
}
.nav-item:hover { background: #2a3245; color: #fff; }
.nav-item.router-link-active { background: var(--primary); color: #fff; }
.session-item {
  font-size: 12px; color: #9aa2b8;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block;
}
.session-item:hover { color: #fff; }
.sidebar-footer { margin-top: auto; }
.role-badge { font-size: 12px; color: #6a7288; padding: 10px 12px; }
.main { flex: 1; padding: 24px; min-width: 0; }

.mobile-topbar, .mask { display: none; }

@media (max-width: 768px) {
  .mobile-topbar {
    display: flex; align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 20;
    background: #1e2433; color: #fff; padding: 10px 14px;
  }
  .logo-mini { font-weight: 600; }
  .menu-btn { background: transparent; border-color: #3a4358; color: #fff; padding: 5px 12px; }
  .mask { display: block; position: fixed; inset: 0; background: rgba(0,0,0,.4); z-index: 14; }
  .sidebar {
    position: fixed; left: 0; top: 0; bottom: 0; z-index: 15;
    transform: translateX(-100%); transition: transform .2s; height: 100vh;
  }
  .sidebar.open { transform: translateX(0); box-shadow: 4px 0 16px rgba(0,0,0,.3); }
  .main { padding: 14px; }
}
</style>
