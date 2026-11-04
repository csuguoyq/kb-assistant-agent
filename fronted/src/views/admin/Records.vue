<script setup>
import { ref, onMounted } from 'vue'
import { marked } from 'marked'
import { apiFetch } from '../../api/request'

marked.setOptions({ breaks: true })
const renderMd = (t) => marked.parse(t || '')

const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const detail = ref(null)

async function load() {
  const data = await apiFetch(`/api/chat/records?page=${page.value}&page_size=${pageSize}`)
  records.value = data.items
  total.value = data.total
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
          <td><button class="btn" @click="open(r)">查看详情</button></td>
        </tr>
      </tbody>
    </table>
    <div class="pagination">
      <button class="btn" :disabled="page <= 1" @click="page--; load()">上一页</button>
      <span>{{ page }} / {{ Math.ceil(total / pageSize) || 1 }}（共 {{ total }} 条）</span>
      <button class="btn" :disabled="page >= Math.ceil(total / pageSize)" @click="page++; load()">下一页</button>
    </div>
  </div>

  <div v-if="detail" class="modal-mask" @click.self="detail = null">
    <div class="card modal">
      <div class="page-header">
        <h3>会话详情</h3>
        <button class="btn" @click="detail = null">关闭</button>
      </div>
      <div class="detail-body">
        <div v-for="(m, i) in detail" :key="i" class="msg">
          <div class="msg-role">{{ m.role === 'user' ? '👤 提问' : '🤖 回答' }}</div>
          <div class="msg-content">
            <span v-if="m.role === 'assistant'" class="md" v-html="renderMd(m.content)"></span>
            <span v-else>{{ m.content }}</span>
            <div v-if="m.sources && m.sources.length" class="sources-line">
              引用：{{ m.sources.map(s => `《${s.title}》`).join('、') }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center; z-index: 10; }
.modal { width: min(760px, 92vw); max-height: 82vh; display: flex; flex-direction: column; }
.detail-body { overflow-y: auto; }
.msg { margin-bottom: 16px; }
.msg-role { font-weight: 600; margin-bottom: 4px; }
.msg-content { line-height: 1.7; padding-left: 2px; }
.sources-line { font-size: 12px; color: var(--text-light); margin-top: 4px; }

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
