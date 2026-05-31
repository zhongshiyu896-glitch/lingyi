<template>
  <div class="production-plan-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>生产计划列表（本地联动回看）</h2>
            <p class="sub-title">MVP-CAND-004 / sales-order local draft linkage</p>
          </div>
          <el-button @click="goSalesOrders">返回销售订单</el-button>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        title="本页只回看 local-dev 生产计划草稿摘要，不连接生产服务。"
        class="scope-alert"
      />

      <el-form :model="query" inline class="query-panel">
        <el-form-item label="关键字">
          <el-input v-model="query.keyword" clearable placeholder="计划号/订单号/款号" />
        </el-form-item>
        <el-form-item label="订单号">
          <el-input v-model="query.orderNo" clearable placeholder="订单号" />
        </el-form-item>
        <el-form-item label="款号">
          <el-input v-model="query.styleCode" clearable placeholder="款号" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width: 160px">
            <el-option label="全部" value="" />
            <el-option label="draft" value="draft" />
            <el-option label="saved" value="saved" />
            <el-option label="cancelled" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="scenario_tag">
          <el-input v-model="query.scenarioTag" clearable placeholder="MVP-CAND004-..." />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="refreshPlans">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <section data-testid="mvp-production-plan-summary">
        <el-table :data="plans" border v-loading="loading" class="result-table">
          <el-table-column prop="planNo" label="计划号" min-width="170" />
          <el-table-column prop="orderNo" label="订单号" min-width="170" />
          <el-table-column prop="styleCode" label="款号" min-width="140" />
          <el-table-column prop="plannedQty" label="计划数量" min-width="120" />
          <el-table-column prop="planDate" label="计划日期" min-width="130" />
          <el-table-column prop="status" label="计划状态" min-width="110">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" effect="plain">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="scenarioTag" label="scenario_tag" min-width="220" />
        </el-table>
      </section>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { request } from '@/api/request'

interface ProductionPlanDraftData {
  draft_id: number
  scenario_tag: string
  order_no: string
  style_code: string
  plan_no: string
  planned_qty: number
  plan_date: string
  status: string
}

interface ProductionPlanListResponse {
  items: ProductionPlanDraftData[]
  total: number
}

interface PlanRow {
  draftId: number
  scenarioTag: string
  planNo: string
  orderNo: string
  styleCode: string
  plannedQty: number
  planDate: string
  status: string
}

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const plans = ref<PlanRow[]>([])

const query = reactive({
  keyword: '',
  orderNo: '',
  styleCode: '',
  status: '',
  scenarioTag: '',
})

const statusTagType = (status: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (status === 'saved' || status === 'active') return 'success'
  if (status === 'cancelled') return 'danger'
  if (status === 'draft') return 'warning'
  return 'info'
}

const refreshPlans = async (): Promise<void> => {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (query.keyword.trim()) params.set('keyword', query.keyword.trim())
    if (query.orderNo.trim()) params.set('order_no', query.orderNo.trim())
    if (query.styleCode.trim()) params.set('style_code', query.styleCode.trim())
    if (query.status.trim()) params.set('status', query.status.trim())
    if (query.scenarioTag.trim()) params.set('scenario_tag', query.scenarioTag.trim())
    const queryString = params.toString()
    const url = queryString ? `/api/local-dev/production-plan-drafts?${queryString}` : '/api/local-dev/production-plan-drafts'
    const response = await request<ProductionPlanListResponse>(url)
    plans.value = response.data.items.map((item) => ({
      draftId: item.draft_id,
      scenarioTag: item.scenario_tag,
      planNo: item.plan_no,
      orderNo: item.order_no,
      styleCode: item.style_code,
      plannedQty: Number(item.planned_qty || 0),
      planDate: item.plan_date,
      status: item.status || 'draft',
    }))
  } catch (error) {
    ElMessage.error(`查询失败：${(error as Error).message}`)
  } finally {
    loading.value = false
  }
}

const resetQuery = (): void => {
  query.keyword = ''
  query.orderNo = ''
  query.styleCode = ''
  query.status = ''
  query.scenarioTag = ''
  void refreshPlans()
}

const goSalesOrders = (): void => {
  router.push('/sales-inventory/sales-orders')
}

onMounted(() => {
  const scenario = Array.isArray(route.query.scenario_tag) ? route.query.scenario_tag[0] : route.query.scenario_tag
  if (typeof scenario === 'string' && scenario.trim()) {
    query.scenarioTag = scenario.trim()
  }
  const orderNo = Array.isArray(route.query.order_no) ? route.query.order_no[0] : route.query.order_no
  if (typeof orderNo === 'string' && orderNo.trim()) {
    query.orderNo = orderNo.trim()
  }
  const styleCode = Array.isArray(route.query.style_code) ? route.query.style_code[0] : route.query.style_code
  if (typeof styleCode === 'string' && styleCode.trim()) {
    query.styleCode = styleCode.trim()
  }
  void refreshPlans()
})
</script>

<style scoped>
.production-plan-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-row h2 {
  margin: 0;
  font-size: 18px;
  line-height: 1.4;
}

.sub-title {
  margin: 2px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.scope-alert {
  margin-bottom: 12px;
}

.query-panel {
  margin-bottom: 8px;
}

.result-table {
  width: 100%;
}
</style>
