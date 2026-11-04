<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../api/request'

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
      <span style="white-space: pre-wrap;">{{ m.content }}</span>
      <div v-if="m.sources && m.sources.length" style="font-size:12px; color:var(--text-light); margin-top:4px">
        引用：{{ m.sources.map(s => `《${s.title}》`).join('、') }}
      </div>
    </div>
  </div>
</template>
