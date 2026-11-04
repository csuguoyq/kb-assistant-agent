<script setup>
import { ref, nextTick, onMounted, computed } from 'vue'
import { marked } from 'marked'
import { streamChat, apiFetch } from '../../api/request'
import { useAuth } from '../../composables/useAuth'
import { useChatStore } from '../../composables/useChat'

marked.setOptions({ breaks: true })

function renderMd(text) {
  return marked.parse(text || '')
}

const auth = useAuth()
const store = useChatStore()

const question = ref('')
const sending = ref(false)
const messages = store.state.messages  // 数组引用安全；sessionId 是原始值，禁止拷贝，须读 store
const listEl = ref(null)
const inputEl = ref(null)

const suggestions = ['年假有几天？怎么申请？', '出差报销标准是什么？', 'VPN 怎么申请？', '迟到会怎么处理？']

function scrollBottom() {
  nextTick(() => listEl.value && (listEl.value.scrollTop = listEl.value.scrollHeight))
}

async function send(text) {
  const q = (text ?? question.value).trim()
  if (!q || sending.value) return
  question.value = ''
  sending.value = true
  // 等待历史恢复完成再确定会话 ID，避免恢复期间提问导致一问一会话
  await store.restoreLatest()
  // 首问立即确定会话 ID：后续提问/刷新都复用它，避免一问一会话的碎片
  if (!store.state.sessionId) {
    store.state.sessionId = crypto.randomUUID().replaceAll('-', '')
  }
  const startedAt = Date.now()
  const assistant = { role: 'assistant', content: '', sources: [], status: '', elapsed: '' }
  messages.push({ role: 'user', content: q })
  messages.push(assistant)
  scrollBottom()

  await streamChat({
    question: q,
    sessionId: store.state.sessionId,
    onChunk: (t) => {
      if (!assistant.content) assistant.elapsed = `${((Date.now() - startedAt) / 1000).toFixed(1)}s 首字`
      assistant.status = ''
      assistant.content += t
      scrollBottom()
    },
    onTool: (name) => { assistant.status = `🔍 正在调用工具：${name}…`; scrollBottom() },
    onSources: (items) => { assistant.sources = items },
    onDone: (sid) => {
      store.state.sessionId = sid
      assistant.elapsed = `${((Date.now() - startedAt) / 1000).toFixed(1)}s`
    },
    onError: (msg) => {
      assistant.elapsed = `${((Date.now() - startedAt) / 1000).toFixed(1)}s`
      if (!assistant.content) assistant.content = `⚠️ ${msg}`
    },
  })
  sending.value = false
  scrollBottom()
  // 等 Vue 把 disabled 属性移除后再聚焦，否则 focus 会静默失败
  nextTick(() => inputEl.value?.focus())
}

async function openSession(session) {
  const detail = await apiFetch(`/api/chat/sessions/${session.id}`)
  store.state.sessionId = session.id
  messages.splice(0, messages.length, ...detail.map((m) => ({ role: m.role, content: m.content, sources: m.sources })))
  scrollBottom()
}

function newChat() {
  store.newChat()
}

// 点击引用来源：弹框显示文章全文，不再跳转页面
const sourceArticle = ref(null)
const loadingSource = ref(false)

async function openSource(s) {
  loadingSource.value = true
  try {
    sourceArticle.value = await apiFetch(`/api/articles/public/${s.article_id}`)
  } catch (e) {
    alert(`无法打开文章：${e.message}`)
  } finally {
    loadingSource.value = false
  }
}

onMounted(async () => {
  if (!messages.length) {
    try { await store.restoreLatest(); scrollBottom() } catch { /* 忽略恢复失败 */ }
  }
})
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
            <div v-if="m.role === 'assistant'" class="content md" v-html="renderMd(m.content)"></div>
            <div v-else class="content">{{ m.content }}<span v-if="sending && i === messages.length - 1" class="cursor">▍</span></div>
            <div v-if="m.role === 'assistant' && !m.content" class="content typing">{{ m.status || '正在思考…' }}</div>
            <div v-if="m.role === 'assistant' && m.elapsed && m.content" class="meta">⏱ {{ m.elapsed }}</div>
            <div v-if="m.sources && m.sources.length" class="sources">
              <div class="sources-title">📎 引用来源（点击查看原文）</div>
              <div v-for="s in m.sources" :key="s.article_id" class="source-item" @click="openSource(s)">
                《{{ s.title }}》
              </div>
            </div>
          </div>
        </div>
      </div>

      <form class="chat-input" @submit.prevent="send()">
        <input ref="inputEl" v-model="question" class="input" placeholder="输入你的问题，例如：年假有几天？" :disabled="sending" />
        <button class="btn primary" :disabled="sending || !question.trim()">{{ sending ? '思考中...' : '发送' }}</button>
      </form>
    </div>

    <div v-if="sourceArticle || loadingSource" class="modal-mask" @click.self="sourceArticle = null">
      <div class="card modal">
        <div class="page-header">
          <h3>{{ loadingSource ? '加载中…' : sourceArticle.title }}</h3>
          <button class="btn" @click="sourceArticle = null">关闭</button>
        </div>
        <div class="modal-body" style="white-space: pre-wrap; line-height: 1.8">{{ sourceArticle?.content }}</div>
      </div>
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
.typing { color: var(--text-light); }
.content.md { white-space: normal; }
.content.md >>> :first-child { margin-top: 0; }
.content.md >>> :last-child { margin-bottom: 0; }
.content.md >>> h1, .content.md >>> h2, .content.md >>> h3, .content.md >>> h4 {
  font-size: 15px; margin: 10px 0 6px;
}
.content.md >>> p { margin: 6px 0; }
.content.md >>> ul, .content.md >>> ol { padding-left: 20px; margin: 6px 0; }
.content.md >>> li { margin: 3px 0; }
.content.md >>> code {
  background: rgba(79,110,247,.1); border-radius: 4px; padding: 1px 5px; font-size: 13px;
}
.content.md >>> pre {
  background: #1e2433; color: #e6e9f2; border-radius: 8px; padding: 10px 12px;
  overflow-x: auto; margin: 8px 0;
}
.content.md >>> pre code { background: transparent; padding: 0; }
.content.md >>> table { border-collapse: collapse; margin: 8px 0; }
.content.md >>> th, .content.md >>> td { border: 1px solid var(--border); padding: 4px 10px; font-size: 13px; }
.content.md >>> blockquote {
  border-left: 3px solid var(--primary); color: var(--text-light);
  padding-left: 10px; margin: 6px 0;
}
@keyframes blink { 50% { opacity: 0; } }

.sources { margin-top: 10px; border-top: 1px dashed var(--border); padding-top: 8px; }
.meta { margin-top: 6px; font-size: 12px; color: var(--text-light); text-align: right; }
.sources-title { font-size: 12px; color: var(--text-light); margin-bottom: 4px; }
.source-item { font-size: 13px; color: var(--primary); cursor: pointer; padding: 2px 0; }
.source-item:hover { text-decoration: underline; }

.chat-input { display: flex; gap: 10px; padding: 16px 20px; border-top: 1px solid var(--border); }

.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center; z-index: 10; }
.modal { width: min(760px, 92vw); max-height: 82vh; display: flex; flex-direction: column; }
.modal-body { overflow-y: auto; }
</style>
