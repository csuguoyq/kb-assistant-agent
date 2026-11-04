import { reactive } from 'vue'
import { apiFetch } from '../api/request'

// 模块级单例：路由切换导致 Chat 组件销毁重建时，会话内容不丢失
const state = reactive({
  sessionId: '',
  messages: [], // { role, content, sources }
})

function newChat() {
  state.sessionId = ''
  state.messages = []
}

async function restoreLatest() {
  if (state.messages.length) return
  const sessions = await apiFetch('/api/chat/sessions')
  if (sessions.length) {
    const detail = await apiFetch(`/api/chat/sessions/${sessions[0].id}`)
    state.sessionId = sessions[0].id
    state.messages = detail.map((m) => ({ role: m.role, content: m.content, sources: m.sources }))
  }
}

export function useChatStore() {
  return { state, newChat, restoreLatest }
}
