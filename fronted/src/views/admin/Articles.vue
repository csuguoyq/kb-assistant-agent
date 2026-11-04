<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch, uploadFile } from '../../api/request'

const router = useRouter()
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const search = ref('')
const status = ref('')
const importing = ref(false)
const fileInput = ref(null)
const categories = ref([])
const importModal = ref(false)   // { file, category_id, status }

async function load() {
  const data = await apiFetch(
    `/api/articles?page=${page.value}&page_size=${pageSize}&search=${encodeURIComponent(search.value)}&status=${status.value}`
  )
  items.value = data.items
  total.value = data.total
}

function onImportFile(e) {
  const file = e.target.files[0]
  e.target.value = ''
  if (!file) return
  importModal.value = { file, category_id: null, status: 'published' }
}

async function confirmImport() {
  const m = importModal.value
  if (!m) return
  importing.value = true
  try {
    const fields = { status: m.status }
    if (m.category_id) fields.category_id = m.category_id
    const res = await uploadFile('/api/articles/import', m.file, fields)
    importModal.value = false
    alert(res.message)
    load()
  } catch (err) {
    alert(`导入失败：${err.message}`)
  } finally {
    importing.value = false
  }
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

onMounted(() => {
  load()
  apiFetch('/api/categories').then((c) => { categories.value = c })
})
</script>

<template>
  <div class="page-header">
    <h2>📝 文章管理</h2>
    <div style="display:flex; gap:10px">
      <button class="btn" :disabled="importing" @click="fileInput.click()">
        {{ importing ? '导入中...' : '📥 导入文档' }}
      </button>
      <input ref="fileInput" type="file" hidden accept=".pdf,.docx,.txt,.md,.markdown" @change="onImportFile" />
      <button class="btn primary" @click="router.push('/admin/articles/new')">＋ 新建文章</button>
    </div>
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
      <thead><tr><th>标题</th><th>分类</th><th>状态</th><th>标签</th><th>更新时间</th><th style="width:280px; white-space:nowrap">操作</th></tr></thead>
      <tbody>
        <tr v-for="a in items" :key="a.id">
          <td>{{ a.title }}</td>
          <td><span v-if="a.category_name" class="tag">{{ a.category_name }}</span><span v-else class="tag gray">未分类</span></td>
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

  <div v-if="importModal" class="modal-mask" @click.self="importModal = false">
    <div class="card modal">
      <div class="page-header"><h3>导入文档</h3><button class="btn" @click="importModal = false">取消</button></div>
      <p style="margin-bottom:12px">📄 {{ importModal.file.name }}（{{ Math.ceil(importModal.file.size / 1024) }} KB）</p>
      <label style="display:block; margin-bottom:8px; color:var(--text-light)">所属分类</label>
      <select v-model="importModal.category_id" class="input" style="margin-bottom:14px">
        <option :value="null">未分类</option>
        <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <label style="display:block; margin-bottom:8px; color:var(--text-light)">导入后状态</label>
      <select v-model="importModal.status" class="input" style="margin-bottom:18px">
        <option value="published">发布（立即向量化入库，AI 可检索）</option>
        <option value="draft">草稿（仅保存，不入库）</option>
      </select>
      <button class="btn primary" style="width:100%" :disabled="importing" @click="confirmImport">
        {{ importing ? '导入中...' : '确认导入' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center; z-index: 10; }
.modal { width: min(480px, 92vw); }
</style>
