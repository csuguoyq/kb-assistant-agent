<script setup>
import { useRoute } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const auth = useAuth()

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

const adminNav = [
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

const isAdmin = route.path.startsWith('/admin')
const navs = isAdmin ? adminNav : userNav
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="logo">🧠 公司知识库</div>
      <div class="side-banner">{{ isAdmin ? '🛠️ 管理端 · 管理知识库' : '💬 问答端 · 使用知识库' }}</div>
      <nav v-for="group in navs" :key="group.label">
        <div class="group-label">{{ group.label }}</div>
        <router-link v-for="item in group.items" :key="item.path" :to="item.path" class="nav-item">
          <span>{{ item.icon }}</span>{{ item.label }}
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <router-link to="/user/profile" class="nav-item"><span>👤</span>个人中心</router-link>
        <a v-if="auth.isEditor()" class="nav-item" @click.prevent="$router.push(isAdmin ? '/user/chat' : '/admin/dashboard')">
          <span>{{ isAdmin ? '💬' : '🛠️' }}</span>{{ isAdmin ? '切换到问答端' : '切换到管理端' }}
        </a>
        <a class="nav-item" @click.prevent="auth.logout(); $router.push('/login')"><span>🚪</span>退出登录</a>
        <div class="role-badge">{{ auth.state.user?.name || auth.state.user?.username }}（{{ auth.role() }}）</div>
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
.logo { font-size: 17px; font-weight: 600; color: #fff; padding: 8px 12px 10px; }
.side-banner {
  font-size: 12px; color: #fff; background: #2a3245; border-radius: 8px;
  padding: 8px 12px; margin: 0 0 6px; text-align: center;
}
.group-label { font-size: 12px; color: #6a7288; padding: 14px 12px 6px; }
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 8px; color: #c8cede; margin-bottom: 2px; cursor: pointer;
}
.nav-item:hover { background: #2a3245; color: #fff; }
.nav-item.router-link-active { background: var(--primary); color: #fff; }
.sidebar-footer { margin-top: auto; }
.role-badge { font-size: 12px; color: #6a7288; padding: 10px 12px; }
.main { flex: 1; padding: 24px; min-width: 0; }
</style>
