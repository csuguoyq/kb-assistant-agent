<script setup>
import { ref, onMounted } from 'vue'
import { marked } from 'marked'
import { apiFetch } from '../../api/request'

marked.setOptions({ breaks: true })
const renderMd = (t) => marked.parse(t || '')

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
        <span v-if="m.role === 'assistant'" class="md" v-html="renderMd(m.content)"></span>
        <span v-else>{{ m.content }}</span>
      </div>
    </div>
    <div v-if="error" class="empty">{{ error }}</div>
  </div>
</template>

<style scoped>
.msg { margin-bottom: 12px; line-height: 1.7; }
.msg .md { white-space: normal; }
.msg .md :deep(h1), .msg .md :deep(h2), .msg .md :deep(h3) { font-size: 15px; margin: 8px 0 4px; }
.msg .md :deep(p) { margin: 4px 0; }
.msg .md :deep(ul), .msg .md :deep(ol) { padding-left: 20px; margin: 4px 0; }
.msg .md :deep(code) { background: rgba(79,110,247,.1); border-radius: 4px; padding: 1px 5px; font-size: 13px; }
.msg .md :deep(pre) { background: #1e2433; color: #e6e9f2; border-radius: 8px; padding: 10px 12px; overflow-x: auto; }
.msg .md :deep(pre code) { background: transparent; padding: 0; }
.msg .md :deep(table) { border-collapse: collapse; }
.msg .md :deep(th), .msg .md :deep(td) { border: 1px solid var(--border); padding: 4px 10px; font-size: 13px; }
.msg .md :deep(:first-child) { margin-top: 0; }
.msg .md :deep(:last-child) { margin-bottom: 0; }
</style>
