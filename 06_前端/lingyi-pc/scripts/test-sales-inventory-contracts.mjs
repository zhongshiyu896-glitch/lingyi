import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { checkSalesInventoryContracts } from './check-sales-inventory-contracts.mjs'

const ensureDir = (targetPath) => mkdirSync(targetPath, { recursive: true })

const write = (root, relativePath, content) => {
  const full = path.join(root, relativePath)
  ensureDir(path.dirname(full))
  writeFileSync(full, content, 'utf8')
}

const read = (root, relativePath) => readFileSync(path.join(root, relativePath), 'utf8')

const assertTrue = (condition, message) => {
  if (!condition) {
    throw new Error(message)
  }
}

const createBaseFixture = (root) => {
  write(
    root,
    'src/api/sales_inventory.ts',
    `import { request } from '@/api/request'

export const fetchSalesInventorySalesOrders = async () => request('/api/sales-inventory/sales-orders')
export const fetchSalesInventorySalesOrderDetail = async (name: string) => request('/api/sales-inventory/sales-orders/' + encodeURIComponent(name))
export const fetchSalesInventoryStockSummary = async (itemCode: string) => request('/api/sales-inventory/items/' + encodeURIComponent(itemCode) + '/stock-summary')
export const fetchSalesInventoryStockLedger = async (itemCode: string) => request('/api/sales-inventory/items/' + encodeURIComponent(itemCode) + '/stock-ledger')
export const fetchSalesInventoryWarehouses = async () => request('/api/sales-inventory/warehouses')
export const fetchSalesInventoryCustomers = async () => request('/api/sales-inventory/customers')
`,
  )

  write(
    root,
    'src/views/sales_inventory/SalesInventorySalesOrderList.vue',
    `<template><div><el-button>查询</el-button><el-button>详情</el-button></div></template>
<script setup lang="ts">
import { fetchSalesInventorySalesOrders } from '@/api/sales_inventory'
const loadRows = () => fetchSalesInventorySalesOrders()
</script>
`,
  )

  write(
    root,
    'src/views/sales_inventory/SalesInventorySalesOrderDetail.vue',
    `<template><div><el-button>返回列表</el-button></div></template>
<script setup lang="ts">
import { fetchSalesInventorySalesOrderDetail } from '@/api/sales_inventory'
const loadDetail = () => fetchSalesInventorySalesOrderDetail('SO-001')
</script>
`,
  )

  write(
    root,
    'src/views/sales_inventory/SalesInventoryStockLedger.vue',
    `<template><div><el-button>查询</el-button></div></template>
<script setup lang="ts">
import { fetchSalesInventoryStockLedger, fetchSalesInventoryStockSummary } from '@/api/sales_inventory'
const loadRows = () => Promise.all([fetchSalesInventoryStockSummary('ITEM-001'), fetchSalesInventoryStockLedger('ITEM-001')])
</script>
`,
  )

  write(
    root,
    'src/views/sales_inventory/SalesInventoryReferenceList.vue',
    `<template><div><el-button>查询客户</el-button><el-button>查询仓库</el-button></div></template>
<script setup lang="ts">
import { fetchSalesInventoryCustomers, fetchSalesInventoryWarehouses } from '@/api/sales_inventory'
const loadRefs = () => Promise.all([fetchSalesInventoryCustomers(), fetchSalesInventoryWarehouses()])
</script>
`,
  )

  write(
    root,
    'src/router/index.ts',
    `export default [
  { path: '/sales-inventory/sales-orders', meta: { module: 'sales_inventory' } },
  { path: '/sales-inventory/sales-orders/detail', meta: { module: 'sales_inventory' } },
  { path: '/sales-inventory/stock-ledger', meta: { module: 'sales_inventory' } },
  { path: '/sales-inventory/references', meta: { module: 'sales_inventory' } },
]
`,
  )

  write(
    root,
    'src/stores/permission.ts',
    `interface ButtonPermissions {
  sales_inventory_read: boolean
  sales_inventory_export: boolean
  sales_inventory_diagnostic: boolean
}
const emptyButtonPermissions = (): ButtonPermissions => ({
  sales_inventory_read: false,
  sales_inventory_export: false,
  sales_inventory_diagnostic: false,
})
const INTERNAL_NON_UI_ACTIONS = new Set<string>(['sales_inventory:diagnostic'])
const forceClearInternalButtonPermissions = (buttons: ButtonPermissions): ButtonPermissions => ({
  ...buttons,
  sales_inventory_diagnostic: false,
})
export { emptyButtonPermissions, forceClearInternalButtonPermissions, INTERNAL_NON_UI_ACTIONS }
`,
  )

  write(root, 'src/App.vue', '<template><router-view /></template>\n')
}

const runSuccessCase = () => {
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'sales-inventory-contract-fixture-'))
  try {
    createBaseFixture(fixtureRoot)
    const result = checkSalesInventoryContracts(fixtureRoot)
    assertTrue(result.ok, `合法 fixture 预期通过，实际失败:\n${result.failures.join('\n')}`)
    console.log('PASS: minimal legal sales inventory fixture')
  } finally {
    rmSync(fixtureRoot, { recursive: true, force: true })
  }
}

const runFailureCase = (caseName, mutateFixture, expectedKeyword) => {
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'sales-inventory-contract-fixture-'))
  try {
    createBaseFixture(fixtureRoot)
    mutateFixture(fixtureRoot)
    const result = checkSalesInventoryContracts(fixtureRoot)
    assertTrue(!result.ok, `[${caseName}] 预期失败，但返回成功`)
    const output = result.failures.join('\n')
    assertTrue(
      output.includes(expectedKeyword),
      `[${caseName}] 失败关键词不匹配，期望包含: ${expectedKeyword}\n实际输出:\n${output}`,
    )
    console.log(`PASS: ${caseName}`)
  } finally {
    rmSync(fixtureRoot, { recursive: true, force: true })
  }
}

const failureCases = [
  {
    name: 'api POST method should fail closed',
    expectedKeyword: '禁止未授权 POST 写入口',
    mutate: (root) => {
      const content = read(root, 'src/api/sales_inventory.ts')
      write(root, 'src/api/sales_inventory.ts', `${content}\nexport const bad = () => request('/api/sales-inventory/sales-orders', { method: 'POST' })\n`)
    },
  },
  {
    name: 'ERPNext direct resource should fail closed',
    expectedKeyword: '禁止 ERPNext /api/resource 直连',
    mutate: (root) => {
      const content = read(root, 'src/api/sales_inventory.ts')
      write(root, 'src/api/sales_inventory.ts', `${content}\nconst bad = '/api/resource/Sales Order'\n`)
    },
  },
  {
    name: 'internal endpoint should fail closed',
    expectedKeyword: '禁止前端调用 internal 接口',
    mutate: (root) => {
      const content = read(root, 'src/api/sales_inventory.ts')
      write(root, 'src/api/sales_inventory.ts', `${content}\nconst bad = '/api/sales-inventory/internal/worker'\n`)
    },
  },
  {
    name: 'run-once should fail closed',
    expectedKeyword: '禁止在前端页面或路由暴露 run-once 动作',
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(root, 'src/router/index.ts', `${content}\n// run-once\n`)
    },
  },
  {
    name: 'diagnostic page endpoint should fail closed',
    expectedKeyword: '禁止调用 diagnostic 接口',
    mutate: (root) => {
      const content = read(root, 'src/views/sales_inventory/SalesInventoryReferenceList.vue')
      write(root, 'src/views/sales_inventory/SalesInventoryReferenceList.vue', `${content}\nconst bad = '/api/sales-inventory/diagnostic'\n`)
    },
  },
  {
    name: 'Chinese write wording should fail closed',
    expectedKeyword: '禁止写动作中文语义',
    mutate: (root) => {
      const content = read(root, 'src/views/sales_inventory/SalesInventorySalesOrderList.vue')
      write(root, 'src/views/sales_inventory/SalesInventorySalesOrderList.vue', content.replace('查询</el-button>', '同步库存</el-button>'))
    },
  },
  {
    name: 'English write wording should fail closed',
    expectedKeyword: '禁止写动作英文语义',
    mutate: (root) => {
      const content = read(root, 'src/views/sales_inventory/SalesInventorySalesOrderList.vue')
      write(root, 'src/views/sales_inventory/SalesInventorySalesOrderList.vue', `${content}\nconst submitSalesInventory = () => undefined\n`)
    },
  },
  {
    name: 'missing required API function should fail closed',
    expectedKeyword: '缺少只读方法: fetchSalesInventoryCustomers',
    mutate: (root) => {
      const content = read(root, 'src/api/sales_inventory.ts')
      write(root, 'src/api/sales_inventory.ts', content.replace('fetchSalesInventoryCustomers', 'fetchSalesInventoryClientList'))
    },
  },
  {
    name: 'missing route should fail closed',
    expectedKeyword: '缺少销售库存只读路径: /sales-inventory/references',
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(root, 'src/router/index.ts', content.replace("  { path: '/sales-inventory/references', meta: { module: 'sales_inventory' } },\n", ''))
    },
  },
  {
    name: 'diagnostic route should fail closed',
    expectedKeyword: '路由禁止暴露非只读路径',
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(root, 'src/router/index.ts', `${content}\nexport const badRoute = '/sales-inventory/diagnostic'\n`)
    },
  },
  {
    name: 'missing diagnostic denylist should fail closed',
    expectedKeyword: '缺少销售库存 diagnostic denylist',
    mutate: (root) => {
      const content = read(root, 'src/stores/permission.ts')
      write(root, 'src/stores/permission.ts', content.replace("'sales_inventory:diagnostic'", "'sales_inventory:read'"))
    },
  },
  {
    name: 'missing diagnostic force clear should fail closed',
    expectedKeyword: '强制清零 sales_inventory_diagnostic',
    mutate: (root) => {
      const content = read(root, 'src/stores/permission.ts')
      write(root, 'src/stores/permission.ts', content.replace('  sales_inventory_diagnostic: false,\n})\nexport {', '})\nexport {'))
    },
  },
]

runSuccessCase()
for (const item of failureCases) {
  runFailureCase(item.name, item.mutate, item.expectedKeyword)
}

console.log(`Sales inventory contract reverse tests passed. scenarios=${failureCases.length + 1}`)
