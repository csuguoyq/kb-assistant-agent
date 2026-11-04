<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../api/request'

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const search = ref('')
const current = ref(null)

async function load() {
  const data = await apiFetch(`/api/articles/public?page=${page.value}&page_size=${pageSize}&search=${encodeURIComponent(search.value)}`)
  items.value = data.items
  total.value = data.total
}

function openArticle(id) {
  apiFetch(`/api/articles/public/${id}`).then((a) => { current.value = a })
}

onMounted(load)
</script>

<template>
  <div style="max-width: 900px; margin: 0 auto;">
    <div class="page-header">
      <h2>📚 知识库浏览</h2>
      <input v-model="search" class="input" style="width: 240px" placeholder="搜索文章标题/标签" @input="page = 1; load()" />
    </div>

    <div class="card">
      <div v-if="items.length === 0" class="empty">暂无已发布的知识文章</div>
      <table v-else class="table">
        <thead><tr><th>标题</th><th>标签</th><th>更新时间</th><th></th></tr></thead>
        <tbody>
          <tr v-for="a in items" :key="a.id">
            <td>{{ a.title }}</td>
            <td><span v-for="t in (a.tags || '').split(',').filter(Boolean)" :key="t" class="tag gray" style="margin-right:4px">{{ t }}</span></td>
            <td>{{ (a.updated_at || '').slice(0, 10) }}</td>
            <td><button class="btn" @click="openArticle(a.id)">查看</button></td>
          </tr>
        </tbody>
      </table>
      <div class="pagination">
        <button class="btn" :disabled="page <= 1" @click="page--; load()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / pageSize) || 1 }}</span>
        <button class="btn" :disabled="page >= Math.ceil(total / pageSize)" @click="page++; load()">下一页</button>
      </div>
    </div>

    <div v-if="current" class="modal-mask" @click.self="current = null">
      <div class="card modal">
        <div class="page-header">
          <h3>{{ current.title }}</h3>
          <button class="btn" @click="current = null">关闭</button>
        </div>
        <div style="white-space: pre-wrap; line-height: 1.8">{{ current.content }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center; z-index: 10; }
.modal { width: 720px; max-height: 80vh; overflow-y: auto; }
</style>
