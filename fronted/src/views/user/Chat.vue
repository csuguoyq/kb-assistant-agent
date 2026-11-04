<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { streamChat, apiFetch } from '../../api/request'
import { useAuth } from '../../composables/useAuth'

const router = useRouter()
const auth = useAuth()

const question = ref('')
const sending = ref(false)
const sessionId = ref('')
const messages = ref([])   // { role, content, sources }
const listEl = ref(null)

const suggestions = ['年假有几天？怎么申请？', '出差报销标准是什么？', 'VPN 怎么申请？', '迟到会怎么处理？']

function scrollBottom() {
  nextTick(() => listEl.value && (listEl.value.scrollTop = listEl.value.scrollHeight))
}

async function send(text) {
  const q = (text ?? question.value).trim()
  if (!q || sending.value) return
  question.value = ''
  sending.value = true
  const assistant = ref({ role: 'assistant', content: '', sources: [] })
  messages.value.push({ role: 'user', content: q })
  messages.value.push(assistant.value)
  scrollBottom()

  await streamChat({
    question: q,
    sessionId: sessionId.value,
    onChunk: (t) => { assistant.value.content += t; scrollBottom() },
    onSources: (items) => { assistant.value.sources = items },
    onDone: (sid) => { sessionId.value = sid },
    onError: (msg) => {
      if (!assistant.value.content) assistant.value.content = `⚠️ ${msg}`
    },
  })
  sending.value = false
  scrollBottom()
}

async function openSession(session) {
  const detail = await apiFetch(`/api/chat/sessions/${session.id}`)
  sessionId.value = session.id
  messages.value = detail.map((m) => ({ role: m.role, content: m.content, sources: m.sources }))
  scrollBottom()
}

function newChat() {
  sessionId.value = ''
  messages.value = []
}

function goArticle(id) {
  window.open(`${location.origin}/user/articles?id=${id}`, '_blank')
}

onMounted(newChat)
</script>

<template>
  <div class="chat-page">
    <div class="card chat-box">
      <div class="chat-header">
        <h2>🤖 AI 知识问答</h2>
        <button class="btn" @click="newChat">＋ 新会话</button>
      </div>

      <div ref="listEl" class="chat-list">
        <div v-if="messages.length === 0" class="chat-welcome">
          <div class="hello">你好，{{ auth.state.user?.name || auth.state.user?.username }}！我是知识库助手「小知」</div>
          <div class="hello-sub">关于公司制度、IT 服务、产品知识的问题都可以直接问我</div>
          <div class="suggestions">
            <button v-for="s in suggestions" :key="s" class="btn" @click="send(s)">{{ s }}</button>
          </div>
        </div>

        <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
          <div class="avatar">{{ m.role === 'user' ? '👤' : '🤖' }}</div>
          <div class="bubble">
            <div class="content">{{ m.content }}<span v-if="sending && i === messages.length - 1 && m.role === 'assistant'" class="cursor">▍</span></div>
            <div v-if="m.sources && m.sources.length" class="sources">
              <div class="sources-title">📎 引用来源</div>
              <div v-for="s in m.sources" :key="s.article_id" class="source-item" @click="goArticle(s.article_id)">
                《{{ s.title }}》
              </div>
            </div>
          </div>
        </div>
      </div>

      <form class="chat-input" @submit.prevent="send()">
        <input v-model="question" class="input" placeholder="输入你的问题，例如：年假有几天？" :disabled="sending" />
        <button class="btn primary" :disabled="sending || !question.trim()">{{ sending ? '思考中...' : '发送' }}</button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.chat-page { max-width: 900px; margin: 0 auto; }
.chat-box { display: flex; flex-direction: column; height: calc(100vh - 48px); padding: 0; overflow: hidden; }
.chat-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--border); }
.chat-list { flex: 1; overflow-y: auto; padding: 20px; }
.chat-welcome { text-align: center; padding-top: 60px; }
.hello { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
.hello-sub { color: var(--text-light); margin-bottom: 24px; }
.suggestions { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }

.msg { display: flex; gap: 10px; margin-bottom: 18px; }
.msg.user { flex-direction: row-reverse; }
.avatar { width: 36px; height: 36px; border-radius: 50%; background: #eef1fe; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.bubble { max-width: 72%; background: var(--bg); border-radius: 12px; padding: 12px 16px; line-height: 1.7; white-space: pre-wrap; }
.msg.user .bubble { background: #eef1fe; }
.cursor { animation: blink 1s infinite; color: var(--primary); }
@keyframes blink { 50% { opacity: 0; } }

.sources { margin-top: 10px; border-top: 1px dashed var(--border); padding-top: 8px; }
.sources-title { font-size: 12px; color: var(--text-light); margin-bottom: 4px; }
.source-item { font-size: 13px; color: var(--primary); cursor: pointer; padding: 2px 0; }
.source-item:hover { text-decoration: underline; }

.chat-input { display: flex; gap: 10px; padding: 16px 20px; border-top: 1px solid var(--border); }
</style>
