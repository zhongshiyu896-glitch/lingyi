<template>
  <div class="workshop-ticket-batch">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>工票批量导入</span>
          <el-button @click="goList">返回列表</el-button>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="请粘贴 JSON 数组，每行对象包含 ticket_key/job_card/employee/process_name/qty/work_date 等字段。"
      />

      <el-input
        v-model="rawJson"
        class="json-editor"
        type="textarea"
        :rows="16"
        placeholder='[
  {"operation_type":"register","ticket_key":"BATCH-001","job_card":"JC-001","employee":"EMP-001","process_name":"sew","qty":10,"work_date":"2026-04-12","source":"import"}
]'
      />

      <div class="actions">
        <el-button type="primary" :disabled="!canBatch" :loading="submitting" @click="submitBatch">
          开始导入
        </el-button>
      </div>

      <el-descriptions v-if="result" :column="3" border>
        <el-descriptions-item label="成功">{{ result.success_count }}</el-descriptions-item>
        <el-descriptions-item label="失败">{{ result.failed_count }}</el-descriptions-item>
        <el-descriptions-item label="总计">{{ result.success_count + result.failed_count }}</el-descriptions-item>
      </el-descriptions>

      <el-table v-if="result && result.failed_items.length > 0" :data="result.failed_items" border style="margin-top: 12px">
        <el-table-column prop="row_index" label="行号" width="90" />
        <el-table-column prop="ticket_key" label="ticket_key" min-width="150" />
        <el-table-column label="错误码" min-width="180">
          <template #default="scope">
            {{ scope.row.error_code || scope.row.code }}
          </template>
        </el-table-column>
        <el-table-column prop="message" label="错误信息" min-width="220" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { batchWorkshopTickets } from '@/api/workshop'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const rawJson = ref<string>('')
const submitting = ref<boolean>(false)
const result = ref<{
  success_count: number
  failed_count: number
  success_items: Array<{ ticket_no: string }>
  failed_items: Array<{ row_index: number; index?: number; code: string; error_code?: string; message: string; ticket_key: string }>
} | null>(null)

const canBatch = computed<boolean>(() => permissionStore.state.buttonPermissions.ticket_batch)

const submitBatch = async (): Promise<void> => {
  let rows: Array<Record<string, unknown>> = []
  try {
    const parsed = JSON.parse(rawJson.value || '[]')
    if (!Array.isArray(parsed)) {
      throw new Error('导入内容必须是 JSON 数组')
    }
    rows = parsed
  } catch (error) {
    ElMessage.error(`JSON 解析失败：${(error as Error).message}`)
    return
  }
  if (rows.length === 0) {
    ElMessage.warning('请先输入导入数据')
    return
  }

  submitting.value = true
  result.value = null
  try {
    const resp = await batchWorkshopTickets(rows as never)
    result.value = resp.data
    ElMessage.success('批量导入完成')
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
.workshop-ticket-batch {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.json-editor {
  margin-top: 12px;
}

.actions {
  margin-top: 12px;
}
</style>
