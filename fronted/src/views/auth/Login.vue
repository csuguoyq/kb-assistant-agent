<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '../../composables/useAuth'

const router = useRouter()
const route = useRoute()
const auth = useAuth()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  if (!username.value || !password.value) { error.value = '请输入用户名和密码'; return }
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push(route.query.redirect || auth.homePath())
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="card auth-card">
      <h1>🧠 公司知识库</h1>
      <p class="subtitle">AI 驱动的企业知识问答平台</p>
      <form @submit.prevent="submit">
        <input v-model="username" class="input" placeholder="用户名" />
        <input v-model="password" class="input" type="password" placeholder="密码" />
        <div v-if="error" class="error">{{ error }}</div>
        <button class="btn primary" :disabled="loading" style="width:100%">{{ loading ? '登录中...' : '登录' }}</button>
      </form>
      <p class="tip">没有账号？<router-link to="/register">立即注册</router-link></p>
      <p class="tip demo">演示账号：admin / admin123（管理员）、editor / editor123（知识编辑）</p>
    </div>
  </div>
</template>

<style scoped>
.auth-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; }
.auth-card { width: 380px; padding: 36px; }
h1 { font-size: 22px; margin-bottom: 6px; }
.subtitle { color: var(--text-light); margin-bottom: 24px; }
.input { margin-bottom: 14px; }
.error { color: #e05252; margin-bottom: 12px; font-size: 13px; }
.tip { margin-top: 14px; color: var(--text-light); font-size: 13px; }
.demo { font-size: 12px; }
</style>
