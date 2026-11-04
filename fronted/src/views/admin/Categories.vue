<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../api/request'

const categories = ref([])
const name = ref('')
const description = ref('')

async function load() {
  categories.value = await apiFetch('/api/categories')
}

async function create() {
  if (!name.value.trim()) return
  await apiFetch('/api/categories', { method: 'POST', body: { name: name.value, description: description.value } })
  name.value = ''
  description.value = ''
  load()
}

async function remove(c) {
  if (!confirm(`确定删除分类「${c.name}」？`)) return
  try {
    await apiFetch(`/api/categories/${c.id}`, { method: 'DELETE' })
    load()
  } catch (e) {
    alert(e.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="page-header"><h2>🗂️ 分类管理</h2></div>
  <div class="card" style="max-width: 640px; margin-bottom: 16px;">
    <div style="display:flex; gap:10px">
      <input v-model="name" class="input" placeholder="分类名称" />
      <input v-model="description" class="input" placeholder="描述（可选）" />
      <button class="btn primary" @click="create">新增</button>
    </div>
  </div>
  <div class="card" style="max-width: 640px;">
    <div v-if="categories.length === 0" class="empty">暂无分类</div>
    <table v-else class="table">
      <thead><tr><th>名称</th><th>描述</th><th></th></tr></thead>
      <tbody>
        <tr v-for="c in categories" :key="c.id">
          <td><span class="tag">{{ c.name }}</span></td>
          <td>{{ c.description || '-' }}</td>
          <td><button class="btn danger" @click="remove(c)">删除</button></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
