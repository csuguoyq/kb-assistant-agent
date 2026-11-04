import { reactive } from 'vue'
import { apiFetch } from '../api/request'

const state = reactive({
  user: null,
  ready: false,
})

async function login(username, password) {
  const data = await apiFetch('/api/auth/login', {
    method: 'POST',
    body: { username, password },
  })
  localStorage.setItem('token', data.access_token)
  await fetchMe()
}

async function register(payload) {
  await apiFetch('/api/auth/register', { method: 'POST', body: payload })
}

async function fetchMe() {
  try {
    state.user = await apiFetch('/api/users/me')
  } catch {
    state.user = null
  }
}

async function restoreSession() {
  if (localStorage.getItem('token')) await fetchMe()
  state.ready = true
}

function logout() {
  localStorage.removeItem('token')
  state.user = null
}

const isLoggedIn = () => !!state.user
const role = () => state.user?.role || ''
const isEditor = () => ['editor', 'admin'].includes(role())
const homePath = () => (isEditor() ? '/admin/dashboard' : '/user/chat')

export function useAuth() {
  return { state, login, register, fetchMe, restoreSession, logout, isLoggedIn, role, isEditor, homePath }
}
