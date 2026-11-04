const API_BASE = 'http://127.0.0.1:8001'

export { API_BASE }

export async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('token')
  const headers = { ...(options.headers || {}) }
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.body && typeof options.body !== 'string') {
    options = { ...options, body: JSON.stringify(options.body) }
    headers['Content-Type'] = 'application/json'
  }

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (resp.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('登录已过期，请重新登录')
  }
  const json = await resp.json().catch(() => null)
  if (!resp.ok || (json && json.code !== 200)) {
    throw new Error((json && json.message) || `请求失败（${resp.status}）`)
  }
  return json.data
}

/**
 * SSE 流式问答：POST /api/chat/ask
 * onChunk(text) / onSources(items) / onDone(sessionId) / onError(message)
 */
export async function streamChat({ question, sessionId, onChunk, onSources, onDone, onError }) {
  const token = localStorage.getItem('token')
  try {
    const resp = await fetch(`${API_BASE}/api/chat/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: token ? `Bearer ${token}` : '',
      },
      body: JSON.stringify({ question, session_id: sessionId }),
    })
    if (!resp.ok) throw new Error('请求失败')

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split('\n\n')
      buffer = events.pop()
      for (const event of events) {
        const line = event.trim()
        if (!line.startsWith('data:')) continue
        const payload = JSON.parse(line.slice(5).trim())
        if (payload.type === 'chunk') onChunk?.(payload.content)
        else if (payload.type === 'sources') onSources?.(payload.items || [])
        else if (payload.type === 'done') onDone?.(payload.session_id)
        else if (payload.type === 'error') onError?.(payload.message)
      }
    }
  } catch (e) {
    onError?.(e.message || '网络异常')
  }
}
