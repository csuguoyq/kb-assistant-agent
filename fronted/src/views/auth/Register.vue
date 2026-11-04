<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../../composables/useAuth'

const router = useRouter()
const auth = useAuth()

const form = ref({ username: '', email: '', password: '', name: '', role: 'user' })
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.register(form.value)
    await auth.login(form.value.username, form.value.password)
    router.push(auth.homePath())
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="card auth-card">
      <h1>注册账号</h1>
      <form @submit.prevent="submit">
        <input v-model="form.username" class="input" placeholder="用户名（3-50 字符）" />
        <input v-model="form.name" class="input" placeholder="姓名（可选）" />
        <input v-model="form.email" class="input" placeholder="邮箱" />
        <input v-model="form.password" class="input" type="password" placeholder="密码（至少 6 位）" />
        <select v-model="form.role" class="input">
          <option value="user">普通用户（提问）</option>
          <option value="editor">知识编辑（管理知识库）</option>
        </select>
        <div v-if="error" class="error">{{ error }}</div>
        <button class="btn primary" style="width:100%">注册</button>
      </form>
      <p class="tip">已有账号？<router-link to="/login">去登录</router-link></p>
    </div>
  </div>
</template>

<style scoped>
.auth-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; }
.auth-card { width: 380px; padding: 36px; }
h1 { font-size: 22px; margin-bottom: 20px; }
.input { margin-bottom: 14px; }
.error { color: #e05252; margin-bottom: 12px; font-size: 13px; }
.tip { margin-top: 14px; color: var(--text-light); font-size: 13px; }
</style>
