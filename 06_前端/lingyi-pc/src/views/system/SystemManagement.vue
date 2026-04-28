<template>
  <div class="system-management-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>系统配置目录（只读）</span>
          <el-button type="primary" :loading="configLoading" @click="loadConfigCatalog">查询</el-button>
        </div>
      </template>

      <el-alert
        v-if="!canSystemRead"
        type="warning"
        :closable="false"
        title="当前账号无 system:read 权限"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-else-if="!canConfigRead"
        type="warning"
        :closable="false"
        title="当前账号无 system:config_read 权限"
        style="margin-bottom: 12px"
      />

      <template v-else>
        <el-form :inline="true" :model="configQuery" class="query-form">
          <el-form-item label="模块">
            <el-input v-model="configQuery.module" clearable placeholder="module（可选）" />
          </el-form-item>
          <el-form-item label="分组">
            <el-select v-model="configQuery.config_group" clearable placeholder="全部" style="width: 180px">
              <el-option label="ui" value="ui" />
              <el-option label="security" value="security" />
              <el-option label="audit" value="audit" />
              <el-option label="integration" value="integration" />
            </el-select>
          </el-form-item>
          <el-form-item label="来源">
            <el-select v-model="configQuery.source" clearable placeholder="全部" style="width: 180px">
              <el-option label="static_registry" value="static_registry" />
              <el-option label="policy_registry" value="policy_registry" />
              <el-option label="env_registry" value="env_registry" />
            </el-select>
          </el-form-item>
          <el-form-item label="敏感标记">
            <el-select v-model="configQuery.is_sensitive" clearable placeholder="全部" style="width: 160px">
              <el-option label="true" value="true" />
              <el-option label="false" value="false" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-table :data="configItems" border empty-text="暂无配置目录数据">
          <el-table-column prop="module" label="模块" width="130" />
          <el-table-column prop="config_key" label="配置键" min-width="220" />
          <el-table-column prop="config_group" label="分组" width="140" />
          <el-table-column prop="description" label="说明" min-width="220" />
          <el-table-column prop="source" label="来源" width="170" />
          <el-table-column label="敏感" width="120">
            <template #default="scope">
              <el-tag v-if="scope.row.is_sensitive" type="danger" effect="plain">敏感配置</el-tag>
              <el-tag v-else type="success" effect="plain">普通配置</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" min-width="190" />
        </el-table>

        <el-empty v-if="!configItems.length" description="暂无配置目录数据" />
      </template>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>数据字典目录（只读）</span>
          <el-button type="primary" :loading="dictionaryLoading" @click="loadDictionaryCatalog">查询</el-button>
        </div>
      </template>

      <el-alert
        v-if="!canSystemRead"
        type="warning"
        :closable="false"
        title="当前账号无 system:read 权限"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-else-if="!canDictionaryRead"
        type="warning"
        :closable="false"
        title="当前账号无 system:dictionary_read 权限"
        style="margin-bottom: 12px"
      />

      <template v-else>
        <el-form :inline="true" :model="dictionaryQuery" class="query-form">
          <el-form-item label="字典类型">
            <el-input v-model="dictionaryQuery.dict_type" clearable placeholder="dict_type（可选）" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="dictionaryQuery.status" clearable placeholder="全部" style="width: 180px">
              <el-option label="active" value="active" />
              <el-option label="inactive" value="inactive" />
              <el-option label="deprecated" value="deprecated" />
            </el-select>
          </el-form-item>
          <el-form-item label="来源">
            <el-select v-model="dictionaryQuery.source" clearable placeholder="全部" style="width: 180px">
              <el-option label="static_registry" value="static_registry" />
              <el-option label="policy_registry" value="policy_registry" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-table :data="dictionaryItems" border empty-text="暂无字典目录数据">
          <el-table-column prop="dict_type" label="dict_type" min-width="180" />
          <el-table-column prop="dict_code" label="dict_code" min-width="180" />
          <el-table-column prop="dict_name" label="dict_name" min-width="180" />
          <el-table-column prop="status" label="status" width="120" />
          <el-table-column prop="source" label="source" width="170" />
          <el-table-column prop="updated_at" label="updated_at" min-width="190" />
        </el-table>

        <el-empty v-if="!dictionaryItems.length" description="暂无字典目录数据" />
      </template>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>系统健康诊断摘要（只读）</span>
          <el-button type="primary" :loading="healthLoading" @click="loadHealthSummary">查询</el-button>
        </div>
      </template>

      <el-alert
        v-if="!canSystemRead"
        type="warning"
        :closable="false"
        title="当前账号无 system:read 权限"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-else-if="!canDiagnosticRead"
        type="warning"
        :closable="false"
        title="当前账号无 system:diagnostic 权限"
        style="margin-bottom: 12px"
      />

      <template v-else>
        <el-table :data="healthItems" border empty-text="暂无系统健康摘要数据">
          <el-table-column prop="module" label="模块" width="140" />
          <el-table-column label="状态" width="130">
            <template #default="scope">
              <el-tag :type="statusTagType(scope.row.status)" effect="plain">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="check_name" label="检查项" min-width="220" />
          <el-table-column prop="check_result" label="结果摘要" min-width="220" />
          <el-table-column prop="generated_at" label="生成时间" min-width="190" />
        </el-table>

        <el-empty v-if="!healthItems.length" description="暂无系统健康摘要数据" />
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import systemManagementApi, {
  type SystemConfigCatalogItem,
  type SystemDictionaryCatalogItem,
  type SystemHealthSummaryItem,
} from '@/api/system_management'
import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const configLoading = ref<boolean>(false)
const dictionaryLoading = ref<boolean>(false)
const healthLoading = ref<boolean>(false)
const configItems = ref<SystemConfigCatalogItem[]>([])
const dictionaryItems = ref<SystemDictionaryCatalogItem[]>([])
const healthItems = ref<SystemHealthSummaryItem[]>([])

const configQuery = reactive({
  module: '',
  config_group: '',
  source: '',
  is_sensitive: '' as '' | 'true' | 'false',
})

const dictionaryQuery = reactive({
  dict_type: '',
  status: '' as '' | 'active' | 'inactive' | 'deprecated',
  source: '',
})

const canSystemRead = computed<boolean>(() => permissionStore.state.actions.includes('system:read'))
const canConfigRead = computed<boolean>(() => permissionStore.state.actions.includes('system:config_read'))
const canDictionaryRead = computed<boolean>(() => permissionStore.state.actions.includes('system:dictionary_read'))
const canDiagnosticRead = computed<boolean>(() => permissionStore.state.actions.includes('system:diagnostic'))
const canReadConfig = computed<boolean>(() => canSystemRead.value && canConfigRead.value)
const canReadDictionary = computed<boolean>(() => canSystemRead.value && canDictionaryRead.value)
const canReadHealthSummary = computed<boolean>(() => canSystemRead.value && canDiagnosticRead.value)

const loadConfigCatalog = async (): Promise<void> => {
  if (!canReadConfig.value) {
    configItems.value = []
    return
  }

  configLoading.value = true
  try {
    const result = await systemManagementApi.fetchSystemConfigCatalog({
      module: configQuery.module.trim() || undefined,
      config_group: configQuery.config_group || undefined,
      source: configQuery.source || undefined,
      is_sensitive: configQuery.is_sensitive || undefined,
    })
    configItems.value = result.data.items
  } catch (error: unknown) {
    configItems.value = []
    ElMessage.error((error as Error).message)
  } finally {
    configLoading.value = false
  }
}

const loadDictionaryCatalog = async (): Promise<void> => {
  if (!canReadDictionary.value) {
    dictionaryItems.value = []
    return
  }

  dictionaryLoading.value = true
  try {
    const result = await systemManagementApi.fetchSystemDictionaryCatalog({
      dict_type: dictionaryQuery.dict_type.trim() || undefined,
      status: dictionaryQuery.status || undefined,
      source: dictionaryQuery.source || undefined,
    })
    dictionaryItems.value = result.data.items
  } catch (error: unknown) {
    dictionaryItems.value = []
    ElMessage.error((error as Error).message)
  } finally {
    dictionaryLoading.value = false
  }
}

const loadHealthSummary = async (): Promise<void> => {
  if (!canReadHealthSummary.value) {
    healthItems.value = []
    return
  }

  healthLoading.value = true
  try {
    const result = await systemManagementApi.fetchSystemHealthSummary()
    healthItems.value = result.data.items
  } catch (error: unknown) {
    healthItems.value = []
    ElMessage.error((error as Error).message)
  } finally {
    healthLoading.value = false
  }
}

const statusTagType = (status: string): 'success' | 'warning' | 'danger' => {
  if (status === 'ok') {
    return 'success'
  }
  if (status === 'warn') {
    return 'warning'
  }
  return 'danger'
}

onMounted(() => {
  permissionStore
    .loadCurrentUser()
    .then(() => permissionStore.loadModuleActions('system'))
    .then(() => Promise.all([loadConfigCatalog(), loadDictionaryCatalog(), loadHealthSummary()]))
    .catch((error: unknown) => {
      ElMessage.error((error as Error).message)
    })
})
</script>

<style scoped>
.system-management-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.query-form {
  margin-bottom: 12px;
}
</style>
