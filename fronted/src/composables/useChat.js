import { reactive } from 'vue'
import { apiFetch } from '../api/request'

// 模块级单例：路由切换导致 Chat 组件销毁重建时，会话内容不丢失
const state = reactive({
  sessionId: '',
  messages: [], // { role, content, sources }
})

function newChat() {
  state.sessionId = ''
  state.messages.splice(0, state.messages.length)  // 原地清空，保持引用不变
}

let restorePromise = null

function restoreLatest() {
  // 只触发一次，后续调用复用同一个 Promise：提问前能等待恢复完成，避免竞态开新会话
  if (!restorePromise) {
    restorePromise = (async () => {
      if (state.messages.length) return
      const sessions = await apiFetch('/api/chat/sessions')
      if (sessions.length) await loadSessionById(sessions[0].id)
    })()
  }
  return restorePromise
}

async function loadSessionById(id) {
  const detail = await apiFetch(`/api/chat/sessions/${id}`)
  state.sessionId = id
  // 原地填充：聊天页持有的是该数组的引用，整体赋值会导致界面不更新
  state.messages.splice(0, state.messages.length,
    ...detail.map((m) => ({ role: m.role, content: m.content, sources: m.sources })))
}

export function useChatStore() {
  return { state, newChat, restoreLatest, loadSessionById }
}
