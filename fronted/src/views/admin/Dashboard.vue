<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../api/request'

const stats = ref({ articles: 0, published: 0, categories: 0, sessions: 0 })
const recent = ref([])

onMounted(async () => {
  const [articles, categories, sessions] = await Promise.all([
    apiFetch('/api/articles?page=1&page_size=5'),
    apiFetch('/api/categories'),
    apiFetch('/api/chat/records'),
  ])
  stats.value.articles = articles.total
  recent.value = articles.items
  stats.value.categories = categories.length
  stats.value.sessions = sessions.length
  const all = await apiFetch('/api/articles?page=1&page_size=5&status=published')
  stats.value.published = all.total
})
</script>

<template>
  <div class="page-header"><h2>📊 知识库概览</h2></div>
  <div class="stats">
    <div class="card stat"><div class="num">{{ stats.articles }}</div><div>文章总数</div></div>
    <div class="card stat"><div class="num">{{ stats.published }}</div><div>已发布（AI 可检索）</div></div>
    <div class="card stat"><div class="num">{{ stats.categories }}</div><div>知识分类</div></div>
    <div class="card stat"><div class="num">{{ stats.sessions }}</div><div>AI 问答会话</div></div>
  </div>
  <div class="card">
    <h3 style="margin-bottom: 12px">最近更新的文章</h3>
    <table class="table">
      <thead><tr><th>标题</th><th>状态</th><th>更新时间</th></tr></thead>
      <tbody>
        <tr v-for="a in recent" :key="a.id">
          <td>{{ a.title }}</td>
          <td><span :class="['tag', a.status === 'published' ? 'green' : 'gray']">{{ a.status === 'published' ? '已发布' : '草稿' }}</span></td>
          <td>{{ (a.updated_at || '').slice(0, 19).replace('T', ' ') }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
@media (max-width: 768px) { .stats { grid-template-columns: repeat(2, 1fr); } }
.stat { text-align: center; color: var(--text-light); }
.num { font-size: 28px; font-weight: 700; color: var(--primary); margin-bottom: 4px; }
</style>
