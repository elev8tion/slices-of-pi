<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isRegister = ref(false)
const username = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)

async function submit() {
  loading.value = true
  try {
    let ok: boolean
    if (isRegister.value) {
      ok = await auth.register(username.value, email.value, password.value)
    } else {
      ok = await auth.login(username.value, password.value)
    }
    if (ok) {
      const redirect = (route.query.redirect as string) || '/'
      router.push(redirect)
    }
  } finally {
    loading.value = false
  }
}

function toggleMode() {
  isRegister.value = !isRegister.value
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <!-- Logo -->
      <div class="login-logo">
        <img src="/logo-login.png" alt="Slice of Pi" class="login-logo-img" />
      </div>

      <h1 class="login-title">{{ isRegister ? 'Create Account' : 'Sign In' }}</h1>
      <p class="login-subtitle">
        {{ isRegister ? 'Register to manage your pi agents' : 'Sign in to your dashboard' }}
      </p>

      <form @submit.prevent="submit" class="login-form">
        <div class="login-field">
          <label>Username</label>
          <input
            v-model="username"
            type="text"
            placeholder="username"
            required
            autocomplete="username"
          />
        </div>

        <div v-if="isRegister" class="login-field">
          <label>Email</label>
          <input
            v-model="email"
            type="email"
            placeholder="you@example.com"
            required
            autocomplete="email"
          />
        </div>

        <div class="login-field">
          <label>Password</label>
          <input
            v-model="password"
            type="password"
            placeholder="••••••••"
            required
            autocomplete="current-password"
          />
        </div>

        <button type="submit" class="login-btn" :disabled="loading">
          {{ loading ? 'Please wait...' : isRegister ? 'Create Account' : 'Sign In' }}
        </button>
      </form>

      <div class="login-toggle">
        {{ isRegister ? 'Already have an account?' : "Don't have an account?" }}
        <button class="login-toggle-btn" @click="toggleMode">
          {{ isRegister ? 'Sign In' : 'Create One' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #08080C;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: #0C0C10;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 24px;
  padding: 40px 32px;
  box-shadow: 0 24px 80px rgba(0,0,0,0.8);
}

.login-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 28px;
}
.login-logo-img {
  width: 180px;
  height: 180px;
}

.login-title {
  text-align: center;
  font-size: 20px;
  font-weight: 600;
  color: #F0F0F2;
  margin-bottom: 4px;
}
.login-subtitle {
  text-align: center;
  font-size: 13px;
  color: rgba(255,255,255,0.3);
  margin-bottom: 28px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.login-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.login-field label {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255,255,255,0.4);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.login-field input {
  background: transparent;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  border: 1px solid rgba(233,236,224,0.15);
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 14px;
  color: #E9ECE0;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
}
.login-field input:focus {
  border-color: #9DD522;
}
.login-field input::placeholder {
  color: rgba(233,236,224,0.20);
}

.login-btn {
  margin-top: 8px;
  background: #9DD522;
  color: #fff;
  border: none;
  border-radius: 12px;
  padding: 12px;
  font-size: 14px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 12px rgba(157,213,34,0.25);
}
.login-btn:hover:not(:disabled) {
  background: #8BC01E;
}
.login-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.login-toggle {
  text-align: center;
  margin-top: 20px;
  font-size: 13px;
  color: rgba(255,255,255,0.3);
}
.login-toggle-btn {
  background: none;
  border: none;
  color: #9DD522;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  padding: 0;
  margin-left: 4px;
}
.login-toggle-btn:hover {
  color: #A5B4FC;
}
</style>
