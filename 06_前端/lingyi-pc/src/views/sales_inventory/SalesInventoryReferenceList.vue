<template>
  <div class="reference-page" data-testid="w001a05-reference-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row" data-testid="w001a05-reference-toolbar">
          <div class="title-group">
            <span class="title">基础资料本地维护</span>
            <span class="sub-title">/sales-inventory/references · customer / supplier local draft write closure</span>
          </div>
          <div class="header-tags">
            <el-tag type="success" effect="plain">local-dev only</el-tag>
            <el-tag type="warning" effect="plain">ERPNext / worker / production write disabled</el-tag>
          </div>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        title="当前页面仅开放客户/供应商本地草稿新增与停用。非 local-dev、非法 request_id、重复写入、非法状态均 fail-closed。"
      />

      <section class="summary-grid" data-testid="w001a05-reference-summary">
        <el-card shadow="never" class="summary-card">
          <span class="summary-label">当前标签</span>
          <strong class="summary-value">{{ activeTabLabel }}</strong>
        </el-card>
        <el-card shadow="never" class="summary-card">
          <span class="summary-label">草稿总数</span>
          <strong class="summary-value">{{ filteredRows.length }}</strong>
        </el-card>
        <el-card shadow="never" class="summary-card">
          <span class="summary-label">启用草稿</span>
          <strong class="summary-value">{{ activeCount }}</strong>
        </el-card>
        <el-card shadow="never" class="summary-card">
          <span class="summary-label">停用草稿</span>
          <strong class="summary-value">{{ inactiveCount }}</strong>
        </el-card>
      </section>

      <el-tabs
        v-model="activeTab"
        class="reference-tabs"
        data-testid="w001a05-reference-tabs"
        @tab-change="handleTabChange"
      >
        <el-tab-pane label="客户草稿" name="customers" />
        <el-tab-pane label="供应商草稿" name="suppliers" />
      </el-tabs>

      <section class="create-panel" data-testid="w001a05-reference-create-panel">
        <el-form :inline="true" :model="createForm" label-width="96px">
          <el-form-item label="company">
            <el-input v-model="createForm.company" style="width: 180px" data-testid="w001a05-company-input" />
          </el-form-item>
          <el-form-item :label="activeTab === 'customers' ? '客户编码' : '供应商编码'">
            <el-input v-model="createForm.referenceNo" style="width: 220px" data-testid="w001a05-reference-no-input" />
          </el-form-item>
          <el-form-item :label="activeTab === 'customers' ? '客户名称' : '供应商名称'">
            <el-input v-model="createForm.referenceName" style="width: 220px" data-testid="w001a05-reference-name-input" />
          </el-form-item>
          <el-form-item label="scenario_tag">
            <el-input v-model="createForm.scenarioTag" style="width: 240px" data-testid="w001a05-scenario-tag-input" />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="writing"
              data-action-type="write"
              data-testid="w001a05-create-button"
              @click="handleCreateDraft"
            >
              {{ activeTab === 'customers' ? '新增客户草稿' : '新增供应商草稿' }}
            </el-button>
          </el-form-item>
        </el-form>

        <el-descriptions border :column="2" data-testid="w001a05-reference-request-context">
          <el-descriptions-item label="request_id">{{ requestIdPreview }}</el-descriptions-item>
          <el-descriptions-item label="idempotency_key">{{ idempotencyKeyPreview }}</el-descriptions-item>
          <el-descriptions-item label="readback">
            {{ activeTab === 'customers' ? 'GET /api/sales-inventory/customers + /reference-drafts/customers' : 'GET /api/sales-inventory/suppliers + /reference-drafts/suppliers' }}
          </el-descriptions-item>
          <el-descriptions-item label="write_boundary">
            create / deactivate only; ERPNext / worker / internal run-once / production write disabled
          </el-descriptions-item>
        </el-descriptions>
      </section>

      <section class="filter-panel" data-testid="w001a05-reference-filter">
        <el-form :inline="true" :model="query">
          <el-form-item label="关键字">
            <el-input v-model="query.keyword" clearable style="width: 240px" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="query.status" clearable placeholder="全部" style="width: 140px">
              <el-option label="全部" value="" />
              <el-option label="active" value="active" />
              <el-option label="inactive" value="inactive" />
            </el-select>
          </el-form-item>
          <el-form-item label="来源">
            <el-select v-model="query.source" clearable placeholder="全部" style="width: 160px">
              <el-option label="全部" value="" />
              <el-option label="erpnext" value="erpnext" />
              <el-option label="local-draft" value="local-draft" />
            </el-select>
          </el-form-item>
          <el-form-item label="停用原因">
            <el-input v-model="deactivateReason" style="width: 220px" data-testid="w001a05-deactivate-reason-input" />
          </el-form-item>
          <el-form-item>
            <el-button :loading="loading" @click="refreshReferences(true)">刷新</el-button>
          </el-form-item>
        </el-form>
      </section>

      <el-alert
        v-if="feedbackMessage"
        :type="feedbackType"
        :closable="false"
        show-icon
        class="feedback-alert"
        data-testid="w001a05-feedback"
        :title="feedbackMessage"
      />

      <section class="table-panel" data-testid="w001a05-reference-table">
        <el-table :data="filteredRows" border v-loading="loading">
          <el-table-column prop="code" label="编码" min-width="180" />
          <el-table-column prop="name" label="名称" min-width="220" />
          <el-table-column prop="company" label="Company" min-width="160" />
          <el-table-column label="类型" width="120">
            <template #default="{ row }">
              <el-tag :type="row.referenceType === 'customers' ? 'primary' : 'warning'" effect="plain">
                {{ row.referenceType === 'customers' ? '客户' : '供应商' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="来源" width="140">
            <template #default="{ row }">
              <el-tag :type="row.source === 'local-draft' ? 'success' : 'info'" effect="plain">
                {{ row.source }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'" effect="plain">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="scenarioTag" label="scenario_tag" min-width="220" />
          <el-table-column prop="createdAt" label="创建时间" min-width="200" />
          <el-table-column label="说明" min-width="220">
            <template #default="{ row }">
              <span>{{ row.disabledReason || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="动作" width="180" align="center">
            <template #default="{ row }">
              <el-button
                text
                type="danger"
                :disabled="row.source !== 'local-draft' || row.status !== 'active' || writing"
                data-action-type="write"
                :data-testid="`w001a05-deactivate-${row.referenceType}-${row.code}`"
                @click="handleDeactivate(row)"
              >
                停用草稿
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="disabled-reasons" data-testid="w001a05-disabled-reasons">
        <h3>禁区链路</h3>
        <ul>
          <li>ERPNext 生产写：disabled</li>
          <li>worker / internal run-once：disabled</li>
          <li>production write / export remediation：disabled</li>
        </ul>
      </section>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  buildSalesInventoryReferenceRequestId,
  buildSalesInventoryReferenceScenarioTag,
  createSalesInventoryReferenceDraft,
  deactivateSalesInventoryReferenceDraft,
  ensureSalesInventoryReferenceScenarioTag,
  type SalesInventoryReferenceDraftType,
} from '@/api/sales_inventory'
import {
  filterReferenceRows,
  loadSalesInventoryReferenceRows,
  resolveReferenceTab,
  type SalesInventoryReferenceQuery,
  type SalesInventoryReferenceRow,
  type SalesInventoryReferenceTab,
} from '@/api/sales_inventory_references'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const writing = ref(false)
const rows = ref<SalesInventoryReferenceRow[]>([])
const activeTab = ref<SalesInventoryReferenceTab>(resolveReferenceTab(route.query.tab, route.query.parity))
const feedbackMessage = ref('')
const feedbackType = ref<'success' | 'warning' | 'error'>('success')
const deactivateReason = ref('local-dev deactivate')

const query = reactive<SalesInventoryReferenceQuery>({
  keyword: '',
  status: '',
  source: '',
})

const createForm = reactive({
  company: 'COMP-A',
  referenceNo: '',
  referenceName: '',
  scenarioTag: buildSalesInventoryReferenceScenarioTag(),
})

const activeTabLabel = computed(() => (activeTab.value === 'customers' ? 'customer' : 'supplier'))
const filteredRows = computed(() => filterReferenceRows(rows.value, query))
const activeCount = computed(() => filteredRows.value.filter((row) => row.status === 'active').length)
const inactiveCount = computed(() => filteredRows.value.filter((row) => row.status === 'inactive').length)

const currentReferenceType = computed<SalesInventoryReferenceDraftType>(() => (
  activeTab.value === 'customers' ? 'customer' : 'supplier'
))

const idempotencyKeyPreview = computed(() => {
  const scenarioTag = ensureSalesInventoryReferenceScenarioTag(createForm.scenarioTag)
  const referenceSuffix = createForm.referenceNo.trim() || 'draft'
  return `IDEMP-${scenarioTag}-${currentReferenceType.value}-${referenceSuffix}`
})

const requestIdPreview = computed(() =>
  buildSalesInventoryReferenceRequestId({
    scenarioTag: createForm.scenarioTag,
    operation: 'create_draft',
    referenceType: currentReferenceType.value,
    idempotencyKey: idempotencyKeyPreview.value,
    referenceNo: createForm.referenceNo.trim() || 'draft',
    company: createForm.company.trim() || 'COMP-A',
  }),
)

const setFeedback = (type: 'success' | 'warning' | 'error', message: string): void => {
  feedbackType.value = type
  feedbackMessage.value = message
}

const syncTabFromRoute = (): void => {
  activeTab.value = resolveReferenceTab(route.query.tab, route.query.parity)
}

const refreshReferences = async (showToast = false): Promise<void> => {
  loading.value = true
  try {
    const result = await loadSalesInventoryReferenceRows(activeTab.value, String(route.query.parity || ''))
    rows.value = result.rows
    if (showToast) {
      ElMessage.success(`${activeTab.value === 'customers' ? '客户' : '供应商'}草稿已刷新`)
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : '刷新失败'
    setFeedback('error', message)
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const handleCreateDraft = async (): Promise<void> => {
  const company = createForm.company.trim()
  const referenceNo = createForm.referenceNo.trim()
  const referenceName = createForm.referenceName.trim()
  if (!company || !referenceNo || !referenceName) {
    setFeedback('warning', 'company / 编码 / 名称不能为空')
    return
  }
  const scenarioTag = ensureSalesInventoryReferenceScenarioTag(createForm.scenarioTag)
  createForm.scenarioTag = scenarioTag
  const payload = {
    operation: 'create_draft' as const,
    scenario_tag: scenarioTag,
    company,
    reference_no: referenceNo,
    reference_name: referenceName,
    idempotency_key: idempotencyKeyPreview.value,
  }
  writing.value = true
  try {
    const response = await createSalesInventoryReferenceDraft(currentReferenceType.value, payload, {
      requestId: requestIdPreview.value,
    })
    setFeedback(
      'success',
      `${currentReferenceType.value === 'customer' ? '客户' : '供应商'}草稿创建成功：${response.data.reference_no} / status=${response.data.status}`,
    )
    createForm.referenceNo = ''
    createForm.referenceName = ''
    createForm.scenarioTag = buildSalesInventoryReferenceScenarioTag()
    await refreshReferences(false)
  } catch (error) {
    const message = error instanceof Error ? error.message : '创建失败'
    setFeedback('error', message)
  } finally {
    writing.value = false
  }
}

const handleDeactivate = async (row: SalesInventoryReferenceRow): Promise<void> => {
  if (!row.draftId) {
    setFeedback('warning', '仅本地草稿支持停用')
    return
  }
  const scenarioTag = buildSalesInventoryReferenceScenarioTag()
  const payload = {
    operation: 'deactivate_draft' as const,
    scenario_tag: scenarioTag,
    company: row.company,
    idempotency_key: `IDEMP-${scenarioTag}-${currentReferenceType.value}-${row.code}-deactivate`,
    reason: deactivateReason.value.trim() || 'local-dev deactivate',
  }
  const requestId = buildSalesInventoryReferenceRequestId({
    scenarioTag,
    operation: 'deactivate_draft',
    referenceType: currentReferenceType.value,
    idempotencyKey: payload.idempotency_key,
    referenceNo: row.code,
    company: row.company,
  })
  writing.value = true
  try {
    const response = await deactivateSalesInventoryReferenceDraft(currentReferenceType.value, row.draftId, payload, {
      requestId,
    })
    setFeedback(
      'success',
      `${currentReferenceType.value === 'customer' ? '客户' : '供应商'}草稿已停用：${response.data.reference_no} / status=${response.data.status}`,
    )
    await refreshReferences(false)
  } catch (error) {
    const message = error instanceof Error ? error.message : '停用失败'
    setFeedback('error', message)
  } finally {
    writing.value = false
  }
}

const handleTabChange = async (tabName: string | number): Promise<void> => {
  const nextTab: SalesInventoryReferenceTab = tabName === 'suppliers' ? 'suppliers' : 'customers'
  await router.replace({
    path: '/sales-inventory/references',
    query: { tab: nextTab },
  })
}

watch(
  () => [route.query.tab, route.query.parity],
  () => {
    syncTabFromRoute()
    void refreshReferences(false)
  },
)

onMounted(() => {
  syncTabFromRoute()
  void refreshReferences(false)
})
</script>

<style scoped>
.reference-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title {
  font-size: 16px;
  font-weight: 600;
}

.sub-title,
.summary-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.header-tags,
.summary-grid {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  margin-top: 12px;
}

.summary-card {
  min-height: 84px;
}

.summary-value {
  font-size: 20px;
  line-height: 1;
}

.create-panel,
.filter-panel,
.feedback-alert,
.table-panel,
.disabled-reasons {
  margin-top: 12px;
}

.disabled-reasons ul {
  margin: 8px 0 0;
  padding-left: 18px;
}
</style>
