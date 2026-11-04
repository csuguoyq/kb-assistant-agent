<script setup>
import { ref, onMounted } from 'vue'
import { marked } from 'marked'
import { apiFetch } from '../../api/request'

marked.setOptions({ breaks: true })
const renderMd = (t) => marked.parse(t || '')

const records = ref([])
const detail = ref(null)

async function load() {
  records.value = await apiFetch('/api/chat/records')
}

async function open(r) {
  detail.value = await apiFetch(`/api/chat/sessions/${r.session_id}`)
}

onMounted(load)
</script>

<template>
  <div class="page-header"><h2>💬 问答记录</h2></div>
  <div class="card">
    <div v-if="records.length === 0" class="empty">暂无问答记录</div>
    <table v-else class="table">
      <thead><tr><th>问题</th><th>消息数</th><th>时间</th><th></th></tr></thead>
      <tbody>
        <tr v-for="r in records" :key="r.session_id">
          <td style="cursor:pointer" @click="open(r)">{{ r.title || '（无标题）' }}</td>
          <td>{{ r.message_count }}</td>
          <td>{{ (r.created_at || '').slice(0, 19).replace('T', ' ') }}</td>
          <td><button class="btn" @click="open(r)">查看</button></td>
        </tr>
      </tbody>
    </table>
  </div>
  <div v-if="detail" class="card" style="margin-top:16px; max-width: 900px;">
    <h3 style="margin-bottom:12px">会话详情</h3>
    <div v-for="(m, i) in detail" :key="i" style="margin-bottom:12px; line-height:1.7">
      <b>{{ m.role === 'user' ? '👤 提问' : '🤖 回答' }}：</b>
      <span v-if="m.role === 'assistant'" class="md" v-html="renderMd(m.content)"></span>
      <span v-else>{{ m.content }}</span>
      <div v-if="m.sources && m.sources.length" style="font-size:12px; color:var(--text-light); margin-top:4px">
        引用：{{ m.sources.map(s => `《${s.title}》`).join('、') }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.md { white-space: normal; }
.md :deep(h1), .md :deep(h2), .md :deep(h3) { font-size: 15px; margin: 8px 0 4px; }
.md :deep(p) { margin: 4px 0; }
.md :deep(ul), .md :deep(ol) { padding-left: 20px; margin: 4px 0; }
.md :deep(code) { background: rgba(79,110,247,.1); border-radius: 4px; padding: 1px 5px; font-size: 13px; }
.md :deep(pre) { background: #1e2433; color: #e6e9f2; border-radius: 8px; padding: 10px 12px; overflow-x: auto; }
.md :deep(pre code) { background: transparent; padding: 0; }
.md :deep(:first-child) { margin-top: 0; }
.md :deep(:last-child) { margin-bottom: 0; }
</style>
