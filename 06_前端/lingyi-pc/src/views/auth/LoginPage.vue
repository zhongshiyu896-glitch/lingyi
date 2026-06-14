<template>
  <main class="login-shell" data-testid="m1-login-page">
    <section class="login-card" data-testid="m1-login-card">
      <header class="login-card__header">
        <h1>领意登录</h1>
        <p>{{ loginDescription }}</p>
      </header>

      <el-form label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="用户名">
          <el-input
            v-model="username"
            data-testid="m1-login-username"
            maxlength="64"
            autocomplete="username"
            placeholder="输入 ERPNext 用户名"
          />
        </el-form-item>

        <el-form-item label="密码">
          <el-input
            v-model="password"
            autocomplete="current-password"
            data-testid="m1-login-password"
            maxlength="256"
            placeholder="输入 ERPNext 密码"
            show-password
            type="password"
          />
        </el-form-item>

        <el-form-item v-if="!isProductionLogin" label="角色配置">
          <el-select
            v-model="profile"
            data-testid="m1-login-profile"
            placeholder="选择本地角色配置"
            style="width: 100%"
          >
            <el-option
              v-for="option in roleOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>

        <el-alert
          v-if="errorMessage"
          :closable="false"
          :title="errorMessage"
          data-testid="m1-login-error"
          type="error"
        />

        <div class="login-card__actions">
          <el-button
            :disabled="!canSubmit"
            :loading="submitting"
            data-testid="m1-login-submit"
            type="primary"
            @click="handleSubmit"
          >
            登录
          </el-button>
          <span class="login-card__hint">{{ loginHint }}</span>
        </div>
      </el-form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { type LocalLoginPayload, type LocalLoginProfile } from '@/api/auth'
import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const route = useRoute()
const router = useRouter()

const isProductionLogin = import.meta.env.PROD || import.meta.env.MODE === 'production'
const username = ref(isProductionLogin ? '' : 'w003a.local')
const password = ref('')
const profile = ref<LocalLoginProfile>('system_manager')
const submitting = ref(false)
const errorMessage = ref('')

const roleOptions: Array<{ label: string; value: LocalLoginProfile }> = [
  { label: '系统管理员', value: 'system_manager' },
  { label: 'BOM 编辑', value: 'bom_editor' },
  { label: '生产经理', value: 'production_manager' },
  { label: '外发经理', value: 'subcontract_manager' },
  { label: '质检经理', value: 'quality_manager' },
  { label: '仓库经理', value: 'warehouse_manager' },
  { label: '销售经理', value: 'sales_manager' },
]

const loginDescription = computed(() =>
  isProductionLogin ? '使用 ERPNext 账号登录，成功后复用 ERPNext 会话。' : '本地开发可使用 profile 会话；生产构建不会显示角色配置。',
)

const loginHint = computed(() =>
  isProductionLogin ? '成功后会跳转到业务路由并复用 ERPNext cookie 会话。' : '成功后会跳转到业务路由并复用本地 cookie 会话。',
)

const canSubmit = computed(() => {
  if (!username.value.trim()) return false
  if (isProductionLogin && !password.value.trim()) return false
  return true
})

const redirectPath = computed(() => {
  const raw = route.query.redirect
  return typeof raw === 'string' && raw.startsWith('/') ? raw : '/home'
})

const handleSubmit = async (): Promise<void> => {
  errorMessage.value = ''
  if (!canSubmit.value) {
    errorMessage.value = isProductionLogin ? '请输入用户名和密码' : '请输入用户名'
    return
  }
  submitting.value = true
  try {
    const payload: LocalLoginPayload = {
      username: username.value.trim(),
      password: password.value,
    }
    if (!isProductionLogin) {
      payload.profile = profile.value
    }
    await permissionStore.login(payload)
    await router.replace(redirectPath.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '登录失败'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.login-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px 16px;
  background: #f4f7fb;
  box-sizing: border-box;
}

.login-card {
  width: min(440px, 100%);
  padding: 24px;
  border: 1px solid #d7dce5;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
}

.login-card__header {
  margin-bottom: 20px;
}

.login-card__header h1 {
  margin: 0 0 8px;
  font-size: 24px;
  line-height: 1.2;
  color: #182233;
}

.login-card__header p {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: #52637a;
}

.login-card__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 20px;
  flex-wrap: wrap;
}

.login-card__hint {
  font-size: 13px;
  line-height: 1.5;
  color: #52637a;
}
</style>
