<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiFetch } from '../../api/request'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id)

const form = ref({ title: '', content: '', category_id: null, tags: '', status: 'draft' })
const categories = ref([])
const message = ref('')

onMounted(async () => {
  categories.value = await apiFetch('/api/categories')
  if (id.value) {
    const a = await apiFetch(`/api/articles/${id.value}`)
    form.value = { title: a.title, content: a.content, category_id: a.category_id, tags: a.tags || '', status: a.status }
  }
})

async function save(publish = false) {
  message.value = ''
  const payload = { ...form.value, category_id: form.value.category_id || null }
  if (publish) payload.status = 'published'
  try {
    if (id.value) {
      await apiFetch(`/api/articles/${id.value}`, { method: 'PUT', body: payload })
    } else {
      const a = await apiFetch('/api/articles', { method: 'POST', body: payload })
      router.replace(`/admin/articles/${a.id}/edit`)
    }
    message.value = publish ? '✅ 已保存并发布，文章已同步至 AI 知识库' : '✅ 已保存草稿'
  } catch (e) {
    message.value = `❌ ${e.message}`
  }
}
</script>

<template>
  <div class="page-header">
    <h2>{{ id ? '编辑文章' : '新建文章' }}</h2>
    <button class="btn" @click="router.push('/admin/articles')">返回列表</button>
  </div>

  <div class="card">
    <input v-model="form.title" class="input" placeholder="文章标题" style="margin-bottom:14px" />
    <div style="display:flex; gap:10px; margin-bottom:14px">
      <select v-model="form.category_id" class="input" style="width:200px">
        <option :value="null">未分类</option>
        <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <input v-model="form.tags" class="input" placeholder="标签，逗号分隔（如：考勤,制度）" />
    </div>
    <textarea v-model="form.content" class="input" rows="16" placeholder="正文内容（发布后将分块向量化供 AI 检索）"></textarea>
    <div style="display:flex; gap:10px; margin-top:14px; align-items:center">
      <button class="btn" @click="save(false)">保存草稿</button>
      <button class="btn primary" @click="save(true)">保存并发布</button>
      <span v-if="message">{{ message }}</span>
    </div>
  </div>
</template>
