<template>
  <div class="workshop-ticket-register">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>工票登记 / 撤销</span>
          <el-button @click="goList">返回列表</el-button>
        </div>
      </template>

      <el-tabs v-model="mode">
        <el-tab-pane label="登记工票" name="register" />
        <el-tab-pane label="撤销工票" name="reversal" />
      </el-tabs>

      <el-form label-width="120px" :model="form">
        <el-form-item label="幂等键 ticket_key">
          <el-input v-model="form.ticket_key" placeholder="扫码值或业务唯一键" />
        </el-form-item>
        <el-form-item label="Job Card">
          <el-input v-model="form.job_card" />
        </el-form-item>
        <el-form-item label="员工">
          <el-input v-model="form.employee" />
        </el-form-item>
        <el-form-item label="工序">
          <el-input v-model="form.process_name" />
        </el-form-item>
        <el-form-item label="颜色/尺码">
          <div class="inline-fields">
            <el-input v-model="form.color" placeholder="Color" />
            <el-input v-model="form.size" placeholder="Size" />
          </div>
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="form.qty" :min="0.000001" :step="1" />
        </el-form-item>
        <el-form-item label="工作日期">
          <el-date-picker v-model="form.work_date" value-format="YYYY-MM-DD" type="date" />
        </el-form-item>

        <template v-if="mode === 'register'">
          <el-form-item label="来源">
            <el-select v-model="form.source" style="width: 160px">
              <el-option label="manual" value="manual" />
              <el-option label="pda" value="pda" />
              <el-option label="mes" value="mes" />
              <el-option label="import" value="import" />
            </el-select>
          </el-form-item>
          <el-form-item label="来源单号">
            <el-input v-model="form.source_ref" />
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="原工票ID">
            <el-input-number v-model="form.original_ticket_id" :min="1" />
          </el-form-item>
          <el-form-item label="撤销原因">
            <el-input v-model="form.reason" />
          </el-form-item>
        </template>

        <el-form-item>
          <el-button
            type="primary"
            :disabled="mode === 'register' ? !canRegister : !canReversal"
            :loading="submitting"
            @click="submit"
          >
            {{ mode === 'register' ? '提交登记' : '提交撤销' }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="result"
        type="success"
        :closable="false"
        show-icon
        :title="`工票号：${result.ticket_no}，单价：${result.unit_wage}，工资：${result.wage_amount}，同步状态：${result.sync_status}${result.sync_outbox_id ? `，Outbox：${result.sync_outbox_id}` : ''}`"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  registerWorkshopTicket,
  reverseWorkshopTicket,
  type WorkshopTicketData,
} from '@/api/workshop'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const mode = ref<'register' | 'reversal'>('register')
const submitting = ref<boolean>(false)
const result = ref<WorkshopTicketData | null>(null)

const form = reactive({
  ticket_key: '',
  job_card: '',
  employee: '',
  process_name: '',
  color: '',
  size: '',
  qty: 1,
  work_date: '',
  source: 'manual',
  source_ref: '',
  original_ticket_id: undefined as number | undefined,
  reason: '',
})

const canRegister = computed<boolean>(() => permissionStore.state.buttonPermissions.ticket_register)
const canReversal = computed<boolean>(() => permissionStore.state.buttonPermissions.ticket_reversal)

const submit = async (): Promise<void> => {
  if (!form.ticket_key || !form.job_card || !form.employee || !form.process_name || !form.work_date) {
    ElMessage.warning('请完整填写关键字段')
    return
  }
  submitting.value = true
  result.value = null
  try {
    if (mode.value === 'register') {
      const resp = await registerWorkshopTicket({
        ticket_key: form.ticket_key,
        job_card: form.job_card,
        employee: form.employee,
        process_name: form.process_name,
        color: form.color || undefined,
        size: form.size || undefined,
        qty: form.qty,
        work_date: form.work_date,
        source: form.source,
        source_ref: form.source_ref || undefined,
      })
      result.value = resp.data
      ElMessage.success('登记成功')
      return
    }

    const resp = await reverseWorkshopTicket({
      ticket_key: form.ticket_key,
      job_card: form.job_card,
      employee: form.employee,
      process_name: form.process_name,
      color: form.color || undefined,
      size: form.size || undefined,
      qty: form.qty,
      work_date: form.work_date,
      original_ticket_id: form.original_ticket_id,
      reason: form.reason || 'manual reversal',
    })
    result.value = resp.data
    ElMessage.success('撤销成功')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    submitting.value = false
  }
}

const goList = (): void => {
  void router.push('/workshop/tickets')
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('workshop')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
})
</script>

<style scoped>
.workshop-ticket-register {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.inline-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  width: 100%;
}
</style>
