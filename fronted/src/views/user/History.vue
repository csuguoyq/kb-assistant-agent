<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../api/request'

const sessions = ref([])
const detail = ref([])
const error = ref('')

async function load() {
  try { sessions.value = await apiFetch('/api/chat/sessions') } catch (e) { error.value = e.message }
}

async function open(s) {
  detail.value = await apiFetch(`/api/chat/sessions/${s.id}`)
}

async function remove(s) {
  if (!confirm('确定删除该会话？')) return
  await apiFetch(`/api/chat/sessions/${s.id}`, { method: 'DELETE' })
  load()
  detail.value = []
}

onMounted(load)
</script>

<template>
  <div style="max-width: 900px; margin: 0 auto;">
    <div class="page-header"><h2>🕘 我的提问</h2></div>
    <div class="card" style="margin-bottom: 16px;">
      <div v-if="sessions.length === 0" class="empty">还没有提问记录，去 <router-link to="/user/chat">AI 问答</router-link> 提个问题吧</div>
      <table v-else class="table">
        <thead><tr><th>问题</th><th>轮数</th><th>时间</th><th></th></tr></thead>
        <tbody>
          <tr v-for="s in sessions" :key="s.id">
            <td style="cursor:pointer" @click="open(s)">{{ s.title || '（无标题）' }}</td>
            <td>{{ Math.floor(s.message_count / 2) }}</td>
            <td>{{ (s.created_at || '').slice(0, 19).replace('T', ' ') }}</td>
            <td><button class="btn danger" @click="remove(s)">删除</button></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="detail.length" class="card">
      <h3 style="margin-bottom:12px">会话详情</h3>
      <div v-for="(m, i) in detail" :key="i" :class="['msg', m.role]">
        <b>{{ m.role === 'user' ? '👤 我' : '🤖 小知' }}：</b>
        <span style="white-space: pre-wrap;">{{ m.content }}</span>
      </div>
    </div>
    <div v-if="error" class="empty">{{ error }}</div>
  </div>
</template>

<style scoped>
.msg { margin-bottom: 12px; line-height: 1.7; }
</style>
