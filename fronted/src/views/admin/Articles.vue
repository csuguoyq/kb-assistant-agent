<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../api/request'

const router = useRouter()
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const search = ref('')
const status = ref('')

async function load() {
  const data = await apiFetch(
    `/api/articles?page=${page.value}&page_size=${pageSize}&search=${encodeURIComponent(search.value)}&status=${status.value}`
  )
  items.value = data.items
  total.value = data.total
}

async function togglePublish(a) {
  await apiFetch(`/api/articles/${a.id}/${a.status === 'published' ? 'unpublish' : 'publish'}`, { method: 'POST' })
  load()
}

async function remove(a) {
  if (!confirm(`确定删除文章「${a.title}」？将同时从 AI 知识库移除。`)) return
  await apiFetch(`/api/articles/${a.id}`, { method: 'DELETE' })
  load()
}

onMounted(load)
</script>

<template>
  <div class="page-header">
    <h2>📝 文章管理</h2>
    <button class="btn primary" @click="router.push('/admin/articles/new')">＋ 新建文章</button>
  </div>

  <div class="card">
    <div style="display:flex; gap:10px; margin-bottom:14px">
      <input v-model="search" class="input" style="width:240px" placeholder="搜索标题/标签" @input="page = 1; load()" />
      <select v-model="status" class="input" style="width:140px" @change="page = 1; load()">
        <option value="">全部状态</option>
        <option value="published">已发布</option>
        <option value="draft">草稿</option>
      </select>
    </div>

    <div v-if="items.length === 0" class="empty">暂无文章，点击右上角新建</div>
    <table v-else class="table">
      <thead><tr><th>标题</th><th>状态</th><th>标签</th><th>更新时间</th><th style="width:230px">操作</th></tr></thead>
      <tbody>
        <tr v-for="a in items" :key="a.id">
          <td>{{ a.title }}</td>
          <td><span :class="['tag', a.status === 'published' ? 'green' : 'gray']">{{ a.status === 'published' ? '已发布' : '草稿' }}</span></td>
          <td>{{ a.tags || '-' }}</td>
          <td>{{ (a.updated_at || '').slice(0, 10) }}</td>
          <td>
            <button class="btn" @click="router.push(`/admin/articles/${a.id}/edit`)">编辑</button>
            <button class="btn" style="margin-left:6px" @click="togglePublish(a)">{{ a.status === 'published' ? '撤销发布' : '发布' }}</button>
            <button class="btn danger" style="margin-left:6px" @click="remove(a)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div class="pagination">
      <button class="btn" :disabled="page <= 1" @click="page--; load()">上一页</button>
      <span>{{ page }} / {{ Math.ceil(total / pageSize) || 1 }}</span>
      <button class="btn" :disabled="page >= Math.ceil(total / pageSize)" @click="page++; load()">下一页</button>
    </div>
  </div>
</template>
