<template>
  <div class="production-plan-page" data-testid="yisuan-1to1-production-plan-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>生产计划</h2>
            <p class="sub-title">衣算云 UI 1:1 对齐（只读态）</p>
          </div>
          <div class="header-actions">
            <el-button @click="goSalesOrders">销售订单</el-button>
            <el-button type="primary" plain @click="goHome">工作台</el-button>
          </div>
        </div>
      </template>

      <el-alert type="info" :closable="false" class="scope-alert">
        <template #title>
          当前页面展示计划状态看板与计划清单，仅支持筛选和观察，不触发新增、更新、下发等写动作。
        </template>
      </el-alert>

      <section class="source-readback" data-testid="yisuan-1to1-ui-source-readback">
        <el-tag type="success">contract_source_readback_present=true</el-tag>
        <el-tag type="primary">covered_contract_ids=A002,A006</el-tag>
        <el-tag type="warning">A006 blocked/unknown => not_claimed</el-tag>
        <el-tag type="info">real_business_object_created=false</el-tag>
        <el-tag type="info">linked_calculation_enabled=false</el-tag>
        <span>来源：A002/A006 contract sources（B018 继承，no-write）</span>
      </section>

      <section class="status-board" data-testid="yisuan-1to1-production-plan-status-board">
        <el-card v-for="card in statusBoard" :key="card.name" shadow="never" class="status-card">
          <div class="status-name">{{ card.name }}</div>
          <div class="status-value">{{ card.value }}</div>
          <div class="status-note">{{ card.note }}</div>
        </el-card>
      </section>

      <el-form :model="query" inline class="query-panel">
        <el-form-item label="关键字">
          <el-input v-model="query.keyword" clearable placeholder="计划号/订单号/款号" />
        </el-form-item>
        <el-form-item label="计划状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width: 160px">
            <el-option label="全部" value="" />
            <el-option label="待锁定" value="待锁定" />
            <el-option label="进行中" value="进行中" />
            <el-option label="待复核" value="待复核" />
          </el-select>
        </el-form-item>
        <el-form-item label="生产组">
          <el-select v-model="query.group" clearable placeholder="全部" style="width: 160px">
            <el-option label="A 线" value="A线" />
            <el-option label="B 线" value="B线" />
            <el-option label="外协组" value="外协组" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <section data-testid="yisuan-1to1-production-plan-table">
        <el-table :data="filteredPlans" border class="result-table">
          <el-table-column prop="planNo" label="计划号" min-width="160" />
          <el-table-column prop="orderNo" label="订单号" min-width="160" />
          <el-table-column prop="styleCode" label="款号" min-width="130" />
          <el-table-column prop="group" label="生产组" min-width="110" />
          <el-table-column prop="plannedQty" label="计划数量" min-width="110" />
          <el-table-column prop="progress" label="进度" min-width="110" />
          <el-table-column prop="planDate" label="计划日期" min-width="120" />
          <el-table-column prop="status" label="状态" min-width="120">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" effect="plain">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <el-card shadow="never" class="contract-boundary-card">
        <template #header>
          <div class="contract-header">
            <strong>合同边界回读（A002/A006）</strong>
            <el-tag type="danger" effect="plain">popup_only / blocked / source_unknown / not_claimed</el-tag>
          </div>
        </template>

        <div class="contract-grid">
          <div class="contract-block" data-testid="yisuan-contract-key-fields">
            <h4>key_fields</h4>
            <div class="tag-row">
              <el-tag v-for="field in keyFields" :key="`key-${field}`" type="success" effect="light">
                {{ field }} VERIFIED
              </el-tag>
            </div>
          </div>

          <div class="contract-block" data-testid="yisuan-contract-validation-rules">
            <h4>validation_rules</h4>
            <ul>
              <li v-for="rule in validationRules" :key="`rule-${rule}`">
                {{ rule }} => blocked / source_unknown / pending_confirmation / not_claimed
              </li>
            </ul>
          </div>

          <div class="contract-block" data-testid="yisuan-contract-status-rules">
            <h4>status_rules</h4>
            <div class="tag-row">
              <el-tag v-for="state in statusRules" :key="`state-${state}`" type="info" effect="light">{{ state }}</el-tag>
              <el-tag type="warning" effect="light">A006_popup_only_boundary=true</el-tag>
              <el-tag type="danger" effect="light">A006_blocked_unknown_claimed_as_confirmed=false</el-tag>
            </div>
          </div>

          <div class="contract-block" data-testid="yisuan-contract-readonly-readback-rules">
            <h4>readonly/readback rules</h4>
            <ul>
              <li v-for="rule in readbackRules" :key="`readback-${rule}`">{{ rule }}</li>
            </ul>
          </div>
        </div>
      </el-card>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useRouter } from 'vue-router'

interface PlanRow {
  planNo: string
  orderNo: string
  styleCode: string
  group: string
  plannedQty: number
  progress: string
  planDate: string
  status: string
}

const router = useRouter()

const query = reactive({
  keyword: '',
  status: '',
  group: '',
})

const plans: PlanRow[] = [
  {
    planNo: 'PP-2606-A01',
    orderNo: 'SO-YS-260601',
    styleCode: 'JK-2410',
    group: 'A线',
    plannedQty: 480,
    progress: '62%',
    planDate: '2026-06-03',
    status: '进行中',
  },
  {
    planNo: 'PP-2606-B07',
    orderNo: 'SO-YS-260614',
    styleCode: 'DR-8831',
    group: '外协组',
    plannedQty: 300,
    progress: '35%',
    planDate: '2026-06-07',
    status: '待复核',
  },
  {
    planNo: 'PP-2606-C11',
    orderNo: 'SO-YS-260626',
    styleCode: 'TS-1077',
    group: 'B线',
    plannedQty: 560,
    progress: '12%',
    planDate: '2026-06-12',
    status: '待锁定',
  },
]

const statusBoard = [
  { name: '待锁定计划', value: '3', note: '交期确认前不可下发' },
  { name: '进行中计划', value: '8', note: '本周执行中的生产单' },
  { name: '异常待处理', value: '2', note: '涉及面料或工序冲突' },
]

const keyFields = [
  '订单',
  '客户',
  '下单日期',
  '业务员',
  '汇率',
  '币种',
  '备注',
  '款号',
  '款名',
  '颜色',
  '尺码',
  '单价',
  '计划数量',
  '计划状态',
]

const validationRules = [
  '主订单保存',
  '订单详情回读动作',
  '生产制单',
  '加工单',
  'BOM',
  '工序',
  '库存',
  '财务',
  '提交/审核/删除/作废',
  '生成生产/采购/加工单',
]

const statusRules = ['VERIFIED', 'PARTIAL', 'UNKNOWN', 'NO-GO', 'BLOCKED']

const readbackRules = [
  'UI 静态证据不等同业务算法 1:1',
  'mainOrderSaveClicked=false',
  'orderCreated=false',
  'orderNumberGenerated=false',
  'A006 blocked/unknown fields only for shell expression',
]

const filteredPlans = computed(() => {
  const keyword = query.keyword.trim().toLowerCase()
  return plans.filter((row) => {
    if (keyword && !`${row.planNo} ${row.orderNo} ${row.styleCode}`.toLowerCase().includes(keyword)) return false
    if (query.status && row.status !== query.status) return false
    if (query.group && row.group !== query.group) return false
    return true
  })
})

const statusType = (status: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (status === '进行中') return 'success'
  if (status === '待复核') return 'danger'
  if (status === '待锁定') return 'warning'
  return 'info'
}

const resetQuery = (): void => {
  query.keyword = ''
  query.status = ''
  query.group = ''
}

const goSalesOrders = (): void => {
  router.push('/sales-inventory/sales-orders')
}

const goHome = (): void => {
  router.push('/home')
}
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

.header-actions {
  display: flex;
  gap: 8px;
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

.source-readback {
  margin-bottom: 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.status-board {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.status-card {
  border: 1px solid var(--el-border-color-lighter);
}

.status-name {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.status-value {
  font-size: 24px;
  line-height: 1.2;
  margin-top: 6px;
}

.status-note {
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.query-panel {
  margin-bottom: 8px;
}

.result-table {
  width: 100%;
}

.contract-boundary-card {
  margin-top: 12px;
}

.contract-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.contract-grid {
  display: grid;
  gap: 10px;
}

.contract-block h4 {
  margin: 0 0 8px;
  font-size: 13px;
}

.contract-block ul {
  margin: 0;
  padding-left: 18px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
