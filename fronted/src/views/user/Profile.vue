<script setup>
import { useAuth } from '../../composables/useAuth'

const auth = useAuth()
</script>

<template>
  <div style="max-width: 600px; margin: 0 auto;">
    <div class="page-header"><h2>👤 个人中心</h2></div>
    <div class="card" v-if="auth.state.user">
      <table class="table">
        <tr><th>用户名</th><td>{{ auth.state.user.username }}</td></tr>
        <tr><th>姓名</th><td>{{ auth.state.user.name || '未设置' }}</td></tr>
        <tr><th>邮箱</th><td>{{ auth.state.user.email }}</td></tr>
        <tr><th>角色</th><td><span class="tag">{{ auth.state.user.role }}</span></td></tr>
        <tr><th>注册时间</th><td>{{ (auth.state.user.created_at || '').slice(0, 10) }}</td></tr>
      </table>
    </div>
  </div>
</template>
