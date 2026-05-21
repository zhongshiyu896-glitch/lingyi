<template>
  <div class="system-management-page" data-testid="system-management-page">
    <el-alert
      data-testid="system-management-parity-hint"
      data-route-parity="/system/management"
      data-runtime-mode="READONLY_GET_ONLY"
      type="info"
      :closable="false"
      title="系统管理只读交互：/system/management｜READONLY_GET_ONLY｜系统配置 / 用户角色菜单 / 审计日志 / 同步导出下载入口均按本地只读 guard 验证"
    />

    <div class="readonly-strip" data-testid="system-management-readonly-status">
      <el-tag effect="plain" data-testid="system-management-get-only">GET-only</el-tag>
      <el-tag
        effect="plain"
        type="warning"
        data-testid="system-management-write-guard"
        data-write-guard="readonly:system-save-submit"
        data-guard-state="guarded_readonly"
        data-side-effect-guard="write-disabled"
      >
        写入动作 guarded_readonly
      </el-tag>
      <el-tag
        effect="plain"
        type="warning"
        data-testid="system-management-export-download-guard"
        data-write-guard="readonly:system-export-download-sync"
        data-guard-state="guarded_readonly"
        data-side-effect-guard="download-sync-disabled"
      >
        导出 / 下载 / 同步不触发
      </el-tag>
    </div>

    <el-card shadow="never" data-testid="approval-flow-section">
      <template #header>
        <div class="header-row">
          <span>审核流程（TASK-Y3B-09，只读）</span>
          <el-button type="primary" :loading="approvalFlowLoading" @click="loadApprovalFlows">查询</el-button>
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
        title="当前账号无 system:config_read 权限（审核流程只读目录不可见）"
        style="margin-bottom: 12px"
      />

      <template v-else>
        <el-alert
          type="info"
          :closable="false"
          style="margin-bottom: 12px"
          title="共享路由边界：本任务仅实现审核流程，保留 Y3B-10 用户管理未实现语义。"
        />

        <el-form :inline="true" :model="approvalFlowQuery" class="query-form" data-testid="approval-flow-query-form">
          <el-form-item label="审核类型">
            <el-select
              v-model="approvalFlowQuery.audit_type"
              clearable
              placeholder="请选择"
              style="width: 180px"
            >
              <el-option v-for="option in approvalFlowAuditTypeOptions" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="approvalFlowQuery.status" clearable placeholder="全部" style="width: 160px">
              <el-option label="启用" value="启用" />
              <el-option label="草稿" value="草稿" />
              <el-option label="停用" value="停用" />
            </el-select>
          </el-form-item>
          <el-form-item label="关键词">
            <el-input
              v-model="approvalFlowQuery.keyword"
              clearable
              placeholder="请输入"
              style="width: 200px"
            />
          </el-form-item>
          <el-form-item label="开始时间">
            <el-input v-model="approvalFlowQuery.start_date" clearable placeholder="开始时间" style="width: 160px" />
          </el-form-item>
          <el-form-item label="结束时间">
            <el-input v-model="approvalFlowQuery.end_date" clearable placeholder="结束时间" style="width: 160px" />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="approvalFlowLoading"
              data-testid="approval-flow-search"
              @click="loadApprovalFlows"
            >
              搜索
            </el-button>
            <el-button data-testid="approval-flow-reset" @click="resetApprovalFlowFilters">重置</el-button>
            <el-button data-testid="approval-flow-clear" @click="clearApprovalFlowSelection">清空</el-button>
          </el-form-item>
        </el-form>

        <div class="meta-row">
          <span>最后修改人：{{ activeApprovalFlow?.last_modified_by ?? '-' }}</span>
          <span>最后修改时间：{{ activeApprovalFlow?.last_modified_at ?? '-' }}</span>
        </div>

        <el-alert
          v-if="approvalFlowErrorMessage"
          type="error"
          :closable="false"
          :title="approvalFlowErrorMessage"
          style="margin-bottom: 12px"
        />

        <el-table
          :data="approvalFlowItems"
          border
          row-key="flow_key"
          empty-text="暂无审核流程目录数据"
          data-testid="approval-flow-table"
        >
          <el-table-column prop="title" label="标题" min-width="180" />
          <el-table-column prop="sent_at" label="发送时间" min-width="180" />
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag :type="approvalStatusTagType(scope.row.status)" effect="plain">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="sender" label="发送人" width="120" />
          <el-table-column prop="created_by" label="创建人" width="120" />
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
          <el-table-column label="操作" min-width="360">
            <template #default="scope">
              <div class="action-group">
                <el-button type="primary" link @click="openApprovalFlowDiagram(scope.row)">示意图</el-button>
                <el-button
                  v-for="action in scope.row.actions"
                  :key="`${scope.row.flow_key}-${action.action_key}`"
                  type="primary"
                  link
                  :disabled="action.guarded"
                  :data-write-guard="systemGuardKey(action.action_key)"
                  :data-guard-state="action.guarded ? 'guarded_readonly' : 'readonly_view'"
                  :data-side-effect-guard="systemSideEffectGuard(action.action_key)"
                  @click="onGuardedActionClick(action)"
                >
                  {{ action.label }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!approvalFlowItems.length" description="暂无审核流程目录数据" data-testid="approval-flow-empty" />

        <el-alert
          type="warning"
          :closable="false"
          style="margin-top: 12px"
          title="Y3B-10 preserved check：当前仅实现审核流程语义，用户管理功能未实现。"
        />
      </template>
    </el-card>

    <el-card shadow="never" data-testid="organization-framework-section">
      <template #header>
        <div class="header-row">
          <span>组织框架（TASK-Y74B-P1-03，只读）</span>
          <el-button type="primary" :loading="organizationFrameworkLoading" @click="loadOrganizationFrameworks">
            查询
          </el-button>
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
        title="当前账号无 system:config_read 权限（组织框架只读目录不可见）"
        style="margin-bottom: 12px"
      />

      <template v-else>
        <el-alert
          type="info"
          :closable="false"
          style="margin-bottom: 12px"
          title="共享路由边界：本任务仅新增组织框架只读语义，不覆盖审批流程、用户目录、配置目录、字典目录与系统健康摘要。"
        />

        <el-form
          :inline="true"
          :model="organizationFrameworkQuery"
          class="query-form"
          data-testid="organization-framework-query-form"
        >
          <el-form-item label="组织层级">
            <el-select v-model="organizationFrameworkQuery.org_level" clearable placeholder="全部" style="width: 180px">
              <el-option
                v-for="option in organizationFrameworkLevelOptions"
                :key="option"
                :label="option"
                :value="option"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="organizationFrameworkQuery.status" clearable placeholder="全部" style="width: 160px">
              <el-option v-for="option in organizationFrameworkStatusTags" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item label="关键词">
            <el-input
              v-model="organizationFrameworkQuery.keyword"
              clearable
              placeholder="请输入组织编码/组织名称/负责人"
              style="width: 260px"
            />
          </el-form-item>
          <el-form-item label="生效开始">
            <el-input
              v-model="organizationFrameworkQuery.effective_start_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item label="生效结束">
            <el-input
              v-model="organizationFrameworkQuery.effective_end_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="organizationFrameworkLoading"
              data-testid="organization-framework-search"
              @click="loadOrganizationFrameworks"
            >
              搜索
            </el-button>
            <el-button data-testid="organization-framework-reset" @click="resetOrganizationFrameworkFilters">
              重置
            </el-button>
            <el-button data-testid="organization-framework-clear" @click="clearOrganizationFrameworkSelection">
              清空
            </el-button>
          </el-form-item>
        </el-form>

        <div class="meta-row">
          <span>最近更新：{{ activeOrganizationFrameworkItem?.updated_at ?? '-' }}</span>
          <span>最近生效日期：{{ activeOrganizationFrameworkItem?.effective_date ?? '-' }}</span>
          <span>guarded 按钮：{{ organizationFrameworkUiButtons.join(' / ') || '-' }}</span>
        </div>

        <el-alert
          v-if="organizationFrameworkErrorMessage"
          type="error"
          :closable="false"
          :title="organizationFrameworkErrorMessage"
          style="margin-bottom: 12px"
        />

        <el-table
          :data="organizationFrameworkItems"
          border
          row-key="org_code"
          empty-text="暂无组织框架数据"
          data-testid="organization-framework-table"
        >
          <el-table-column prop="org_code" label="组织编码" min-width="140" />
          <el-table-column prop="org_name" label="组织名称" min-width="180" />
          <el-table-column prop="parent_org_name" label="上级组织" min-width="180" />
          <el-table-column prop="manager_name" label="负责人" width="120" />
          <el-table-column prop="org_level" label="组织层级" width="120" />
          <el-table-column prop="headcount_planned" label="编制人数" width="110" />
          <el-table-column prop="headcount_on_duty" label="在岗人数" width="110" />
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag :type="organizationFrameworkStatusTagType(scope.row.status)" effect="plain">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="effective_date" label="生效日期" width="120" />
          <el-table-column prop="updated_at" label="更新时间" min-width="180" />
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" min-width="360">
            <template #default="scope">
              <div class="action-group">
                <el-button
                  v-for="action in scope.row.actions"
                  :key="`${scope.row.org_code}-${action.action_key}`"
                  type="primary"
                  link
                  :disabled="action.guarded"
                  :data-write-guard="systemGuardKey(action.action_key)"
                  :data-guard-state="action.guarded ? 'guarded_readonly' : 'readonly_view'"
                  :data-side-effect-guard="systemSideEffectGuard(action.action_key)"
                  @click="onOrganizationFrameworkActionClick(scope.row, action)"
                >
                  {{ action.label }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="!organizationFrameworkItems.length"
          description="暂无组织框架数据"
          data-testid="organization-framework-empty"
        />

        <el-alert
          type="warning"
          :closable="false"
          style="margin-top: 12px"
          title="写动作、上传/下载/导出/打印均为 guarded/disabled，仅允许只读查看。"
        />
      </template>
    </el-card>

    <el-card shadow="never" data-testid="integration-platform-section">
      <template #header>
        <div class="header-row">
          <span>对接平台（TASK-Y74B-P1-05，只读）</span>
          <el-button type="primary" :loading="integrationPlatformLoading" @click="loadIntegrationPlatforms">
            查询
          </el-button>
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
        title="当前账号无 system:config_read 权限（对接平台只读目录不可见）"
        style="margin-bottom: 12px"
      />

      <template v-else>
        <el-alert
          type="info"
          :closable="false"
          style="margin-bottom: 12px"
          title="共享路由边界：本任务仅新增对接平台只读语义，不覆盖审批流程、用户目录、组织框架、配置目录、字典目录与系统健康摘要。"
        />

        <el-form
          :inline="true"
          :model="integrationPlatformQuery"
          class="query-form"
          data-testid="integration-platform-query-form"
        >
          <el-form-item label="平台类型">
            <el-select v-model="integrationPlatformQuery.platform_type" clearable placeholder="全部" style="width: 180px">
              <el-option
                v-for="option in integrationPlatformTypeOptions"
                :key="option"
                :label="option"
                :value="option"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="integrationPlatformQuery.status" clearable placeholder="全部" style="width: 160px">
              <el-option v-for="option in integrationPlatformStatusTags" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item label="接入模式">
            <el-select v-model="integrationPlatformQuery.endpoint_mode" clearable placeholder="全部" style="width: 180px">
              <el-option
                v-for="option in integrationPlatformModeOptions"
                :key="option"
                :label="option"
                :value="option"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="关键词">
            <el-input
              v-model="integrationPlatformQuery.keyword"
              clearable
              placeholder="请输入平台编码/平台名称/连接器/同步方向"
              style="width: 320px"
            />
          </el-form-item>
          <el-form-item label="更新开始">
            <el-input
              v-model="integrationPlatformQuery.updated_start_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item label="更新结束">
            <el-input
              v-model="integrationPlatformQuery.updated_end_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="integrationPlatformLoading"
              data-testid="integration-platform-search"
              @click="loadIntegrationPlatforms"
            >
              搜索
            </el-button>
            <el-button data-testid="integration-platform-reset" @click="resetIntegrationPlatformFilters">重置</el-button>
            <el-button data-testid="integration-platform-clear" @click="clearIntegrationPlatformSelection">清空</el-button>
          </el-form-item>
        </el-form>

        <div class="meta-row">
          <span>最近更新：{{ activeIntegrationPlatformItem?.updated_at ?? '-' }}</span>
          <span>最近同步：{{ activeIntegrationPlatformItem?.last_sync_at ?? '-' }}</span>
          <span>guarded 按钮：{{ integrationPlatformUiButtons.join(' / ') || '-' }}</span>
        </div>

        <el-alert
          v-if="integrationPlatformErrorMessage"
          type="error"
          :closable="false"
          :title="integrationPlatformErrorMessage"
          style="margin-bottom: 12px"
        />

        <el-table
          :data="integrationPlatformItems"
          border
          row-key="platform_code"
          empty-text="暂无对接平台数据"
          data-testid="integration-platform-table"
        >
          <el-table-column prop="platform_code" label="平台编码" min-width="140" />
          <el-table-column prop="platform_name" label="平台名称" min-width="180" />
          <el-table-column prop="platform_type" label="平台类型" width="120" />
          <el-table-column prop="endpoint_mode" label="接入模式" width="120" />
          <el-table-column prop="connector" label="连接器" min-width="180" />
          <el-table-column prop="webhook_url_masked" label="Webhook（脱敏）" min-width="220" />
          <el-table-column prop="sync_direction" label="同步方向" min-width="160" />
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag :type="integrationPlatformStatusTagType(scope.row.status)" effect="plain">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="last_sync_at" label="最近同步" min-width="180" />
          <el-table-column prop="retry_policy" label="重试策略" min-width="160" />
          <el-table-column prop="updated_at" label="更新时间" min-width="180" />
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" min-width="360">
            <template #default="scope">
              <div class="action-group">
                <el-button
                  v-for="action in scope.row.actions"
                  :key="`${scope.row.platform_code}-${action.action_key}`"
                  type="primary"
                  link
                  :disabled="action.guarded"
                  :data-write-guard="systemGuardKey(action.action_key)"
                  :data-guard-state="action.guarded ? 'guarded_readonly' : 'readonly_view'"
                  :data-side-effect-guard="systemSideEffectGuard(action.action_key)"
                  @click="onIntegrationPlatformActionClick(scope.row, action)"
                >
                  {{ action.label }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="!integrationPlatformItems.length"
          description="暂无对接平台数据"
          data-testid="integration-platform-empty"
        />

        <el-alert
          type="warning"
          :closable="false"
          style="margin-top: 12px"
          title="同步、测试连接、启停、导出、打印均为 guarded/disabled，仅允许只读查看。"
        />
      </template>
    </el-card>

    <el-card shadow="never" data-testid="system-announcement-section">
      <template #header>
        <div class="header-row">
          <span>系统公告（TASK-Y79B-P1-02，只读）</span>
          <el-button type="primary" :loading="systemAnnouncementLoading" @click="loadSystemAnnouncements">
            查询
          </el-button>
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
        title="当前账号无 system:config_read 权限（系统公告只读目录不可见）"
        style="margin-bottom: 12px"
      />

      <template v-else>
        <el-alert
          type="info"
          :closable="false"
          style="margin-bottom: 12px"
          title="共享路由边界：本任务仅新增系统公告只读语义，不覆盖审批流程、用户目录、组织框架、对接平台、配置目录、字典目录与系统健康摘要。"
        />

        <el-form
          :inline="true"
          :model="systemAnnouncementQuery"
          class="query-form"
          data-testid="system-announcement-query-form"
        >
          <el-form-item label="分类">
            <el-select v-model="systemAnnouncementQuery.category" clearable placeholder="全部" style="width: 180px">
              <el-option
                v-for="option in systemAnnouncementCategoryOptions"
                :key="option"
                :label="option"
                :value="option"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="发布状态">
            <el-select v-model="systemAnnouncementQuery.status" clearable placeholder="全部" style="width: 160px">
              <el-option v-for="option in systemAnnouncementStatusTags" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item label="目标范围">
            <el-input
              v-model="systemAnnouncementQuery.target_scope"
              clearable
              placeholder="请输入目标范围"
              style="width: 180px"
            />
          </el-form-item>
          <el-form-item label="关键词">
            <el-input
              v-model="systemAnnouncementQuery.keyword"
              clearable
              placeholder="请输入公告编号/标题/负责人"
              style="width: 280px"
            />
          </el-form-item>
          <el-form-item label="发布开始">
            <el-input
              v-model="systemAnnouncementQuery.published_start_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item label="发布结束">
            <el-input
              v-model="systemAnnouncementQuery.published_end_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="systemAnnouncementLoading"
              data-testid="system-announcement-search"
              @click="loadSystemAnnouncements"
            >
              搜索
            </el-button>
            <el-button data-testid="system-announcement-reset" @click="resetSystemAnnouncementFilters">重置</el-button>
            <el-button data-testid="system-announcement-clear" @click="clearSystemAnnouncementSelection">清空</el-button>
          </el-form-item>
        </el-form>

        <div class="meta-row">
          <span>最近发布：{{ activeSystemAnnouncementItem?.published_at ?? '-' }}</span>
          <span>最近更新：{{ activeSystemAnnouncementItem?.updated_at ?? '-' }}</span>
          <span>guarded 按钮：{{ systemAnnouncementUiButtons.join(' / ') || '-' }}</span>
        </div>

        <el-alert
          v-if="systemAnnouncementErrorMessage"
          type="error"
          :closable="false"
          :title="systemAnnouncementErrorMessage"
          style="margin-bottom: 12px"
        />

        <el-table
          :data="systemAnnouncementItems"
          border
          row-key="announcement_code"
          empty-text="暂无系统公告数据"
          data-testid="system-announcement-table"
        >
          <el-table-column prop="announcement_code" label="公告编号" min-width="140" />
          <el-table-column prop="title" label="标题" min-width="220" />
          <el-table-column prop="category" label="分类" width="130" />
          <el-table-column prop="target_scope" label="目标范围" min-width="140" />
          <el-table-column label="发布状态" width="110">
            <template #default="scope">
              <el-tag :type="systemAnnouncementStatusTagType(scope.row.publish_status)" effect="plain">
                {{ scope.row.publish_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="published_at" label="发布时间" min-width="180" />
          <el-table-column prop="expires_at" label="失效时间" min-width="180" />
          <el-table-column prop="priority" label="优先级" width="100" />
          <el-table-column prop="owner" label="负责人" width="120" />
          <el-table-column prop="updated_at" label="更新时间" min-width="180" />
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" min-width="360">
            <template #default="scope">
              <div class="action-group">
                <el-button
                  v-for="action in scope.row.actions"
                  :key="`${scope.row.announcement_code}-${action.action_key}`"
                  type="primary"
                  link
                  :disabled="action.guarded"
                  :data-write-guard="systemGuardKey(action.action_key)"
                  :data-guard-state="action.guarded ? 'guarded_readonly' : 'readonly_view'"
                  :data-side-effect-guard="systemSideEffectGuard(action.action_key)"
                  @click="onSystemAnnouncementActionClick(scope.row, action)"
                >
                  {{ action.label }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="!systemAnnouncementItems.length"
          description="暂无系统公告数据"
          data-testid="system-announcement-empty"
        />

        <el-alert
          type="warning"
          :closable="false"
          style="margin-top: 12px"
          title="发布、撤回、置顶、导出、打印均为 guarded/disabled，仅允许只读查看。"
        />
      </template>
    </el-card>

    <el-card shadow="never" data-testid="operation-log-section">
      <template #header>
        <div class="header-row">
          <span>操作日志（TASK-Y79B-P1-03，只读）</span>
          <el-button type="primary" :loading="operationLogLoading" @click="loadOperationLogs">查询</el-button>
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
        title="当前账号无 system:config_read 权限（操作日志只读目录不可见）"
        style="margin-bottom: 12px"
      />

      <template v-else>
        <el-alert
          type="info"
          :closable="false"
          style="margin-bottom: 12px"
          title="共享路由边界：本任务仅新增操作日志只读语义，不覆盖审批流程、用户目录、组织框架、对接平台、系统公告、配置目录、字典目录与系统健康摘要。"
        />

        <el-form :inline="true" :model="operationLogQuery" class="query-form" data-testid="operation-log-query-form">
          <el-form-item label="模块">
            <el-select v-model="operationLogQuery.module" clearable placeholder="全部" style="width: 180px">
              <el-option v-for="option in operationLogModuleOptions" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item label="操作类型">
            <el-select v-model="operationLogQuery.operation_type" clearable placeholder="全部" style="width: 180px">
              <el-option v-for="option in operationLogTypeOptions" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item label="结果状态">
            <el-select v-model="operationLogQuery.result_status" clearable placeholder="全部" style="width: 160px">
              <el-option v-for="option in operationLogStatusTags" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item label="操作人">
            <el-input v-model="operationLogQuery.operator" clearable placeholder="请输入操作人" style="width: 180px" />
          </el-form-item>
          <el-form-item label="关键词">
            <el-input
              v-model="operationLogQuery.keyword"
              clearable
              placeholder="请输入日志编号/操作名称/详情关键词"
              style="width: 300px"
            />
          </el-form-item>
          <el-form-item label="操作开始">
            <el-input
              v-model="operationLogQuery.operated_start_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item label="操作结束">
            <el-input
              v-model="operationLogQuery.operated_end_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="operationLogLoading"
              data-testid="operation-log-search"
              @click="loadOperationLogs"
            >
              搜索
            </el-button>
            <el-button data-testid="operation-log-reset" @click="resetOperationLogFilters">重置</el-button>
            <el-button data-testid="operation-log-clear" @click="clearOperationLogSelection">清空</el-button>
          </el-form-item>
        </el-form>

        <div class="meta-row">
          <span>最近操作：{{ activeOperationLogItem?.operated_at ?? '-' }}</span>
          <span>最近追踪ID：{{ activeOperationLogItem?.trace_id ?? '-' }}</span>
          <span>guarded 按钮：{{ operationLogUiButtons.join(' / ') || '-' }}</span>
        </div>

        <el-alert
          v-if="operationLogErrorMessage"
          type="error"
          :closable="false"
          :title="operationLogErrorMessage"
          style="margin-bottom: 12px"
        />

        <el-table
          :data="operationLogItems"
          border
          row-key="log_id"
          empty-text="暂无操作日志数据"
          data-testid="operation-log-table"
        >
          <el-table-column prop="log_id" label="日志编号" min-width="140" />
          <el-table-column prop="module" label="模块" min-width="160" />
          <el-table-column prop="operation_type" label="操作类型" width="120" />
          <el-table-column prop="operation_name" label="操作名称" min-width="180" />
          <el-table-column prop="info" label="详情摘要" min-width="220" />
          <el-table-column prop="operator" label="操作人" width="120" />
          <el-table-column label="结果状态" width="110">
            <template #default="scope">
              <el-tag :type="operationLogResultTagType(scope.row.result_status)" effect="plain">
                {{ scope.row.result_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="operated_at" label="操作时间" min-width="180" />
          <el-table-column prop="client_ip" label="客户端IP" min-width="140" />
          <el-table-column prop="trace_id" label="追踪ID" min-width="180" />
          <el-table-column prop="remark" label="备注" min-width="200" />
          <el-table-column label="操作" min-width="320">
            <template #default="scope">
              <div class="action-group">
                <el-button
                  v-for="action in scope.row.actions"
                  :key="`${scope.row.log_id}-${action.action_key}`"
                  type="primary"
                  link
                  :disabled="action.guarded"
                  :data-write-guard="systemGuardKey(action.action_key)"
                  :data-guard-state="action.guarded ? 'guarded_readonly' : 'readonly_view'"
                  :data-side-effect-guard="systemSideEffectGuard(action.action_key)"
                  @click="onOperationLogActionClick(scope.row, action)"
                >
                  {{ action.label }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!operationLogItems.length" description="暂无操作日志数据" data-testid="operation-log-empty" />

        <el-alert
          type="warning"
          :closable="false"
          style="margin-top: 12px"
          title="查看详情、筛选、导出、打印、清理日志、归档均为 guarded/disabled，仅允许只读查看。"
        />
      </template>
    </el-card>

    <el-card shadow="never" data-testid="document-code-section">
      <template #header>
        <div class="header-row">
          <span>单据编码（TASK-Y79B-P1-04，只读）</span>
          <el-button type="primary" :loading="documentCodeLoading" @click="loadDocumentCodes">查询</el-button>
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
        title="当前账号无 system:config_read 权限（单据编码只读目录不可见）"
        style="margin-bottom: 12px"
      />

      <template v-else>
        <el-alert
          type="info"
          :closable="false"
          style="margin-bottom: 12px"
          title="共享路由边界：本任务仅新增单据编码只读语义，不覆盖审批流程、用户目录、组织框架、对接平台、系统公告、操作日志、配置目录、字典目录与系统健康摘要。"
        />

        <el-form :inline="true" :model="documentCodeQuery" class="query-form" data-testid="document-code-query-form">
          <el-form-item label="单据类型">
            <el-select v-model="documentCodeQuery.document_type" clearable placeholder="全部" style="width: 180px">
              <el-option v-for="option in documentCodeTypeOptions" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="documentCodeQuery.status" clearable placeholder="全部" style="width: 160px">
              <el-option v-for="option in documentCodeStatusTags" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item label="关键词">
            <el-input
              v-model="documentCodeQuery.keyword"
              clearable
              placeholder="请输入编码编号/单据名称/前缀关键词"
              style="width: 300px"
            />
          </el-form-item>
          <el-form-item label="更新开始">
            <el-input
              v-model="documentCodeQuery.updated_start_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item label="更新结束">
            <el-input
              v-model="documentCodeQuery.updated_end_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="documentCodeLoading"
              data-testid="document-code-search"
              @click="loadDocumentCodes"
            >
              搜索
            </el-button>
            <el-button data-testid="document-code-reset" @click="resetDocumentCodeFilters">重置</el-button>
            <el-button data-testid="document-code-clear" @click="clearDocumentCodeSelection">清空</el-button>
          </el-form-item>
        </el-form>

        <div class="meta-row">
          <span>最近更新：{{ activeDocumentCodeItem?.updated_at ?? '-' }}</span>
          <span>最近流水号：{{ activeDocumentCodeItem?.current_sequence ?? '-' }}</span>
          <span>guarded 按钮：{{ documentCodeUiButtons.join(' / ') || '-' }}</span>
        </div>

        <el-alert
          v-if="documentCodeErrorMessage"
          type="error"
          :closable="false"
          :title="documentCodeErrorMessage"
          style="margin-bottom: 12px"
        />

        <el-table
          :data="documentCodeItems"
          border
          row-key="document_code_id"
          empty-text="暂无单据编码数据"
          data-testid="document-code-table"
        >
          <el-table-column prop="document_code_id" label="编码编号" min-width="140" />
          <el-table-column prop="document_name" label="单据名称" min-width="170" />
          <el-table-column prop="document_type" label="单据类型" min-width="140" />
          <el-table-column prop="prefix" label="编码前缀" width="120" />
          <el-table-column prop="serial_rule" label="流水规则" min-width="180" />
          <el-table-column prop="current_sequence" label="当前流水号" width="120" />
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag :type="documentCodeStatusTagType(scope.row.status)" effect="plain">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reset_cycle" label="重置周期" width="120" />
          <el-table-column prop="owner" label="负责人" width="120" />
          <el-table-column prop="updated_at" label="更新时间" min-width="180" />
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" min-width="420">
            <template #default="scope">
              <div class="action-group">
                <el-button
                  v-for="action in scope.row.actions"
                  :key="`${scope.row.document_code_id}-${action.action_key}`"
                  type="primary"
                  link
                  :disabled="action.guarded"
                  :data-write-guard="systemGuardKey(action.action_key)"
                  :data-guard-state="action.guarded ? 'guarded_readonly' : 'readonly_view'"
                  :data-side-effect-guard="systemSideEffectGuard(action.action_key)"
                  @click="onDocumentCodeActionClick(scope.row, action)"
                >
                  {{ action.label }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!documentCodeItems.length" description="暂无单据编码数据" data-testid="document-code-empty" />

        <el-alert
          type="warning"
          :closable="false"
          style="margin-top: 12px"
          title="新增、编辑、启停、预览、重置、导出、打印均为 guarded/disabled，仅允许只读查看。"
        />
      </template>
    </el-card>

    <el-card shadow="never" data-testid="message-notification-settings-section">
      <template #header>
        <div class="header-row">
          <span>消息通知设置（TASK-Y84B-P1-02，只读）</span>
          <el-button
            type="primary"
            :loading="messageNotificationSettingLoading"
            @click="loadMessageNotificationSettings"
          >
            查询
          </el-button>
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
        title="当前账号无 system:config_read 权限（消息通知设置只读目录不可见）"
        style="margin-bottom: 12px"
      />

      <template v-else>
        <el-alert
          type="info"
          :closable="false"
          style="margin-bottom: 12px"
          title="共享路由边界：本任务仅新增消息通知设置只读语义，不覆盖审批流程、用户目录、组织框架、对接平台、系统公告、操作日志、单据编码、配置目录、字典目录与系统健康摘要。"
        />

        <el-form
          :inline="true"
          :model="messageNotificationSettingQuery"
          class="query-form"
          data-testid="message-notification-settings-query-form"
        >
          <el-form-item label="通知渠道">
            <el-select
              v-model="messageNotificationSettingQuery.channel"
              clearable
              placeholder="全部"
              style="width: 180px"
            >
              <el-option
                v-for="option in messageNotificationSettingChannelOptions"
                :key="option"
                :label="option"
                :value="option"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="messageNotificationSettingQuery.status"
              clearable
              placeholder="全部"
              style="width: 160px"
            >
              <el-option
                v-for="option in messageNotificationSettingStatusTags"
                :key="option"
                :label="option"
                :value="option"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="目标范围">
            <el-input
              v-model="messageNotificationSettingQuery.target_scope"
              clearable
              placeholder="请输入目标范围"
              style="width: 180px"
            />
          </el-form-item>
          <el-form-item label="关键词">
            <el-input
              v-model="messageNotificationSettingQuery.keyword"
              clearable
              placeholder="请输入设置编号/设置名称/事件关键词"
              style="width: 300px"
            />
          </el-form-item>
          <el-form-item label="更新开始">
            <el-input
              v-model="messageNotificationSettingQuery.updated_start_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item label="更新结束">
            <el-input
              v-model="messageNotificationSettingQuery.updated_end_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="messageNotificationSettingLoading"
              data-testid="message-notification-settings-search"
              @click="loadMessageNotificationSettings"
            >
              搜索
            </el-button>
            <el-button data-testid="message-notification-settings-reset" @click="resetMessageNotificationSettingFilters">
              重置
            </el-button>
            <el-button data-testid="message-notification-settings-clear" @click="clearMessageNotificationSettingSelection">
              清空
            </el-button>
          </el-form-item>
        </el-form>

        <div class="meta-row">
          <span>最近更新：{{ activeMessageNotificationSettingItem?.updated_at ?? '-' }}</span>
          <span>默认渠道：{{ activeMessageNotificationSettingItem?.channel ?? '-' }}</span>
          <span>guarded 按钮：{{ messageNotificationSettingUiButtons.join(' / ') || '-' }}</span>
        </div>

        <el-alert
          v-if="messageNotificationSettingErrorMessage"
          type="error"
          :closable="false"
          :title="messageNotificationSettingErrorMessage"
          style="margin-bottom: 12px"
        />

        <el-table
          :data="messageNotificationSettingItems"
          border
          row-key="setting_code"
          empty-text="暂无消息通知设置数据"
          data-testid="message-notification-settings-table"
        >
          <el-table-column prop="setting_code" label="设置编号" min-width="140" />
          <el-table-column prop="setting_name" label="设置名称" min-width="200" />
          <el-table-column prop="channel" label="通知渠道" min-width="120" />
          <el-table-column prop="target_scope" label="目标范围" min-width="140" />
          <el-table-column prop="digest_mode" label="推送模式" min-width="140" />
          <el-table-column prop="trigger_events" label="触发事件" min-width="220" />
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag :type="messageNotificationSettingStatusTagType(scope.row.status)" effect="plain">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="owner" label="负责人" width="120" />
          <el-table-column prop="updated_at" label="更新时间" min-width="180" />
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" min-width="400">
            <template #default="scope">
              <div class="action-group">
                <el-button
                  v-for="action in scope.row.actions"
                  :key="`${scope.row.setting_code}-${action.action_key}`"
                  type="primary"
                  link
                  :disabled="action.guarded"
                  :data-write-guard="systemGuardKey(action.action_key)"
                  :data-guard-state="action.guarded ? 'guarded_readonly' : 'readonly_view'"
                  :data-side-effect-guard="systemSideEffectGuard(action.action_key)"
                  @click="onMessageNotificationSettingActionClick(scope.row, action)"
                >
                  {{ action.label }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="!messageNotificationSettingItems.length"
          description="暂无消息通知设置数据"
          data-testid="message-notification-settings-empty"
        />

        <el-alert
          type="warning"
          :closable="false"
          style="margin-top: 12px"
          title="编辑、启停、测试发送、导出、打印均为 guarded/disabled，仅允许只读查看。"
        />
      </template>
    </el-card>

    <el-card shadow="never" data-testid="preference-settings-section">
      <template #header>
        <div class="header-row">
          <span>偏好设置（TASK-Y84B-P1-03，只读）</span>
          <el-button type="primary" :loading="preferenceSettingLoading" @click="loadPreferenceSettings">
            查询
          </el-button>
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
        title="当前账号无 system:config_read 权限（偏好设置只读目录不可见）"
        style="margin-bottom: 12px"
      />

      <template v-else>
        <el-alert
          type="info"
          :closable="false"
          style="margin-bottom: 12px"
          title="共享路由边界：本任务仅新增偏好设置只读语义，不覆盖审批流程、用户目录、组织框架、对接平台、系统公告、操作日志、单据编码、消息通知设置、配置目录、字典目录与系统健康摘要。"
        />

        <el-form
          :inline="true"
          :model="preferenceSettingQuery"
          class="query-form"
          data-testid="preference-settings-query-form"
        >
          <el-form-item label="适用范围">
            <el-select
              v-model="preferenceSettingQuery.preference_scope"
              clearable
              placeholder="全部"
              style="width: 180px"
            >
              <el-option
                v-for="option in preferenceSettingScopeOptions"
                :key="option"
                :label="option"
                :value="option"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="preferenceSettingQuery.status"
              clearable
              placeholder="全部"
              style="width: 160px"
            >
              <el-option v-for="option in preferenceSettingStatusTags" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item label="关键词">
            <el-input
              v-model="preferenceSettingQuery.keyword"
              clearable
              placeholder="请输入设置编号/设置名称/参数类型"
              style="width: 280px"
            />
          </el-form-item>
          <el-form-item label="更新开始">
            <el-input
              v-model="preferenceSettingQuery.updated_start_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item label="更新结束">
            <el-input
              v-model="preferenceSettingQuery.updated_end_date"
              clearable
              placeholder="YYYY-MM-DD"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="preferenceSettingLoading"
              data-testid="preference-settings-search"
              @click="loadPreferenceSettings"
            >
              搜索
            </el-button>
            <el-button data-testid="preference-settings-reset" @click="resetPreferenceSettingFilters">重置</el-button>
            <el-button data-testid="preference-settings-clear" @click="clearPreferenceSettingSelection">清空</el-button>
          </el-form-item>
        </el-form>

        <div class="meta-row">
          <span>最近更新：{{ activePreferenceSettingItem?.updated_at ?? '-' }}</span>
          <span>生效层级：{{ activePreferenceSettingItem?.effective_level ?? '-' }}</span>
          <span>guarded 按钮：{{ preferenceSettingUiButtons.join(' / ') || '-' }}</span>
        </div>

        <el-alert
          v-if="preferenceSettingErrorMessage"
          type="error"
          :closable="false"
          :title="preferenceSettingErrorMessage"
          style="margin-bottom: 12px"
        />

        <el-table
          :data="preferenceSettingItems"
          border
          row-key="setting_code"
          empty-text="暂无偏好设置数据"
          data-testid="preference-settings-table"
        >
          <el-table-column prop="setting_code" label="设置编号" min-width="140" />
          <el-table-column prop="setting_name" label="设置名称" min-width="180" />
          <el-table-column prop="preference_scope" label="适用范围" min-width="140" />
          <el-table-column prop="value_type" label="参数类型" min-width="140" />
          <el-table-column prop="current_value_masked" label="当前值（脱敏）" min-width="170" />
          <el-table-column prop="effective_level" label="生效层级" min-width="120" />
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag :type="preferenceSettingStatusTagType(scope.row.status)" effect="plain">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="owner" label="负责人" width="120" />
          <el-table-column prop="updated_at" label="更新时间" min-width="180" />
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" min-width="400">
            <template #default="scope">
              <div class="action-group">
                <el-button
                  v-for="action in scope.row.actions"
                  :key="`${scope.row.setting_code}-${action.action_key}`"
                  type="primary"
                  link
                  :disabled="action.guarded"
                  :data-write-guard="systemGuardKey(action.action_key)"
                  :data-guard-state="action.guarded ? 'guarded_readonly' : 'readonly_view'"
                  :data-side-effect-guard="systemSideEffectGuard(action.action_key)"
                  @click="onPreferenceSettingActionClick(scope.row, action)"
                >
                  {{ action.label }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="!preferenceSettingItems.length"
          description="暂无偏好设置数据"
          data-testid="preference-settings-empty"
        />

        <el-alert
          type="warning"
          :closable="false"
          style="margin-top: 12px"
          title="编辑、启停、同步、导出、打印均为 guarded/disabled，仅允许只读查看。"
        />
      </template>
    </el-card>

    <el-card shadow="never" data-testid="user-role-menu-section">
      <template #header>
        <div class="header-row">
          <span>用户管理（TASK-Y3B-10，只读）</span>
          <el-button type="primary" :loading="userCatalogLoading" @click="loadUserCatalog">查询</el-button>
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
        title="当前账号无 system:config_read 权限（用户目录只读数据不可见）"
        style="margin-bottom: 12px"
      />

      <template v-else>
        <el-alert
          type="info"
          :closable="false"
          style="margin-bottom: 12px"
          title="共享路由边界：本任务仅实现用户管理语义，保留 Y3B-09 审核流程区块。"
        />

        <el-form :inline="true" :model="userCatalogQuery" class="query-form" data-testid="user-role-menu-query-form">
          <el-form-item label="角色">
            <el-select v-model="userCatalogQuery.role" clearable placeholder="全部" style="width: 180px">
              <el-option v-for="option in userRoleOptions" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="userCatalogQuery.status" clearable placeholder="全部" style="width: 160px">
              <el-option v-for="option in userStatusOptions" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item label="关键词">
            <el-input
              v-model="userCatalogQuery.keyword"
              clearable
              placeholder="请输入用户名/姓名/部门"
              style="width: 240px"
            />
          </el-form-item>
          <el-form-item label="开始时间">
            <el-input v-model="userCatalogQuery.start_date" clearable placeholder="开始时间" style="width: 160px" />
          </el-form-item>
          <el-form-item label="结束时间">
            <el-input v-model="userCatalogQuery.end_date" clearable placeholder="结束时间" style="width: 160px" />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="userCatalogLoading"
              data-testid="user-role-menu-search"
              @click="loadUserCatalog"
            >
              搜索
            </el-button>
            <el-button data-testid="user-role-menu-reset" @click="resetUserCatalogFilters">重置</el-button>
            <el-button data-testid="user-role-menu-clear" @click="clearUserCatalogSelection">清空</el-button>
          </el-form-item>
        </el-form>

        <div class="meta-row">
          <span>最近更新时间：{{ activeUserCatalogItem?.updated_at ?? '-' }}</span>
          <span>最近登录：{{ activeUserCatalogItem?.last_login_at ?? '-' }}</span>
        </div>

        <el-alert
          v-if="userCatalogErrorMessage"
          type="error"
          :closable="false"
          :title="userCatalogErrorMessage"
          style="margin-bottom: 12px"
        />

        <el-table
          :data="userCatalogItems"
          border
          row-key="user_id"
          empty-text="暂无用户目录数据"
          data-testid="user-role-menu-table"
        >
          <el-table-column prop="username" label="用户名" min-width="140" />
          <el-table-column prop="display_name" label="姓名" min-width="140" />
          <el-table-column prop="role" label="角色" min-width="150" />
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag :type="userStatusTagType(scope.row.status)" effect="plain">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="department" label="部门" min-width="140" />
          <el-table-column prop="last_login_at" label="最近登录" min-width="180" />
          <el-table-column prop="updated_at" label="更新时间" min-width="180" />
          <el-table-column label="操作" min-width="360">
            <template #default="scope">
              <div class="action-group">
                <el-button
                  v-for="action in scope.row.actions"
                  :key="`${scope.row.user_id}-${action.action_key}`"
                  type="primary"
                  link
                  :disabled="action.guarded"
                  :data-write-guard="systemGuardKey(action.action_key)"
                  :data-guard-state="action.guarded ? 'guarded_readonly' : 'readonly_view'"
                  :data-side-effect-guard="systemSideEffectGuard(action.action_key)"
                  @click="onUserCatalogActionClick(scope.row, action)"
                >
                  {{ action.label }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!userCatalogItems.length" description="暂无用户目录数据" data-testid="user-role-menu-empty" />

        <el-alert
          type="warning"
          :closable="false"
          style="margin-top: 12px"
          title="Y3B-09 preserved check：审核流程（TASK-Y3B-09，只读）区块保留且未覆盖。"
        />
      </template>
    </el-card>

    <el-card shadow="never" data-testid="system-config-section">
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
        <el-form :inline="true" :model="configQuery" class="query-form" data-testid="system-config-query-form">
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

        <el-table :data="configItems" border empty-text="暂无配置目录数据" data-testid="system-config-table">
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

        <el-empty v-if="!configItems.length" description="暂无配置目录数据" data-testid="system-config-empty" />
      </template>
    </el-card>

    <el-card shadow="never" data-testid="system-dictionary-section">
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
        <el-form :inline="true" :model="dictionaryQuery" class="query-form" data-testid="system-dictionary-query-form">
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

        <el-table :data="dictionaryItems" border empty-text="暂无字典目录数据" data-testid="system-dictionary-table">
          <el-table-column prop="dict_type" label="dict_type" min-width="180" />
          <el-table-column prop="dict_code" label="dict_code" min-width="180" />
          <el-table-column prop="dict_name" label="dict_name" min-width="180" />
          <el-table-column prop="status" label="status" width="120" />
          <el-table-column prop="source" label="source" width="170" />
          <el-table-column prop="updated_at" label="updated_at" min-width="190" />
        </el-table>

        <el-empty v-if="!dictionaryItems.length" description="暂无字典目录数据" data-testid="system-dictionary-empty" />
      </template>
    </el-card>

    <el-card shadow="never" data-testid="system-health-section">
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
        <el-table :data="healthItems" border empty-text="暂无系统健康摘要数据" data-testid="system-health-table">
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

        <el-empty v-if="!healthItems.length" description="暂无系统健康摘要数据" data-testid="system-health-empty" />
      </template>
    </el-card>

    <el-dialog v-model="approvalFlowDiagramVisible" title="审核流程示意图（只读）" width="680px">
      <template v-if="activeApprovalFlow">
        <el-descriptions :column="2" border size="small" style="margin-bottom: 12px">
          <el-descriptions-item label="审核类型">{{ activeApprovalFlow.audit_type }}</el-descriptions-item>
          <el-descriptions-item label="流程状态">{{ activeApprovalFlow.status }}</el-descriptions-item>
          <el-descriptions-item label="标题">{{ activeApprovalFlow.title }}</el-descriptions-item>
          <el-descriptions-item label="最后修改人">{{ activeApprovalFlow.last_modified_by }}</el-descriptions-item>
        </el-descriptions>
        <el-table :data="activeApprovalFlow.nodes" border empty-text="暂无流程节点">
          <el-table-column prop="node_name" label="节点" min-width="140" />
          <el-table-column prop="approver_rule" label="审批规则" min-width="220" />
          <el-table-column label="状态" width="120">
            <template #default="scope">
              <el-tag :type="approvalNodeTagType(scope.row.status)" effect="plain">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </template>
      <template #footer>
        <el-button @click="approvalFlowDiagramVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="userCatalogDetailVisible" title="用户详情（只读）" width="640px">
      <template v-if="activeUserCatalogItem">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="用户ID">{{ activeUserCatalogItem.user_id }}</el-descriptions-item>
          <el-descriptions-item label="用户名">{{ activeUserCatalogItem.username }}</el-descriptions-item>
          <el-descriptions-item label="姓名">{{ activeUserCatalogItem.display_name }}</el-descriptions-item>
          <el-descriptions-item label="角色">{{ activeUserCatalogItem.role }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ activeUserCatalogItem.status }}</el-descriptions-item>
          <el-descriptions-item label="部门">{{ activeUserCatalogItem.department }}</el-descriptions-item>
          <el-descriptions-item label="最近登录">{{ activeUserCatalogItem.last_login_at }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ activeUserCatalogItem.updated_at }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <template #footer>
        <el-button @click="userCatalogDetailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import systemManagementApi, {
  type SystemAnnouncementAction,
  type SystemAnnouncementItem,
  type SystemDocumentCodeAction,
  type SystemDocumentCodeItem,
  type SystemMessageNotificationSettingAction,
  type SystemMessageNotificationSettingItem,
  type SystemPreferenceSettingAction,
  type SystemPreferenceSettingItem,
  type SystemOperationLogAction,
  type SystemOperationLogItem,
  type SystemApprovalFlowAction,
  type SystemApprovalFlowItem,
  type SystemConfigCatalogItem,
  type SystemDictionaryCatalogItem,
  type SystemHealthSummaryItem,
  type SystemIntegrationPlatformAction,
  type SystemIntegrationPlatformItem,
  type SystemOrganizationFrameworkAction,
  type SystemOrganizationFrameworkItem,
  type SystemUserCatalogAction,
  type SystemUserCatalogItem,
} from '@/api/system_management'
import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const configLoading = ref<boolean>(false)
const dictionaryLoading = ref<boolean>(false)
const healthLoading = ref<boolean>(false)
const approvalFlowLoading = ref<boolean>(false)
const userCatalogLoading = ref<boolean>(false)
const organizationFrameworkLoading = ref<boolean>(false)
const integrationPlatformLoading = ref<boolean>(false)
const systemAnnouncementLoading = ref<boolean>(false)
const operationLogLoading = ref<boolean>(false)
const documentCodeLoading = ref<boolean>(false)
const messageNotificationSettingLoading = ref<boolean>(false)
const preferenceSettingLoading = ref<boolean>(false)
const configItems = ref<SystemConfigCatalogItem[]>([])
const dictionaryItems = ref<SystemDictionaryCatalogItem[]>([])
const healthItems = ref<SystemHealthSummaryItem[]>([])
const approvalFlowItems = ref<SystemApprovalFlowItem[]>([])
const approvalFlowAuditTypeOptions = ref<string[]>([])
const userCatalogItems = ref<SystemUserCatalogItem[]>([])
const organizationFrameworkItems = ref<SystemOrganizationFrameworkItem[]>([])
const integrationPlatformItems = ref<SystemIntegrationPlatformItem[]>([])
const systemAnnouncementItems = ref<SystemAnnouncementItem[]>([])
const operationLogItems = ref<SystemOperationLogItem[]>([])
const documentCodeItems = ref<SystemDocumentCodeItem[]>([])
const messageNotificationSettingItems = ref<SystemMessageNotificationSettingItem[]>([])
const preferenceSettingItems = ref<SystemPreferenceSettingItem[]>([])
const userRoleOptions = ref<string[]>([])
const userStatusOptions = ref<string[]>([])
const organizationFrameworkLevelOptions = ref<string[]>([])
const organizationFrameworkStatusTags = ref<string[]>([])
const organizationFrameworkUiButtons = ref<string[]>([])
const integrationPlatformTypeOptions = ref<string[]>([])
const integrationPlatformModeOptions = ref<string[]>([])
const integrationPlatformStatusTags = ref<string[]>([])
const integrationPlatformUiButtons = ref<string[]>([])
const systemAnnouncementCategoryOptions = ref<string[]>([])
const systemAnnouncementStatusTags = ref<string[]>([])
const systemAnnouncementUiButtons = ref<string[]>([])
const operationLogModuleOptions = ref<string[]>([])
const operationLogTypeOptions = ref<string[]>([])
const operationLogStatusTags = ref<string[]>([])
const operationLogUiButtons = ref<string[]>([])
const documentCodeTypeOptions = ref<string[]>([])
const documentCodeStatusTags = ref<string[]>([])
const documentCodeUiButtons = ref<string[]>([])
const messageNotificationSettingChannelOptions = ref<string[]>([])
const messageNotificationSettingStatusTags = ref<string[]>([])
const messageNotificationSettingUiButtons = ref<string[]>([])
const preferenceSettingScopeOptions = ref<string[]>([])
const preferenceSettingStatusTags = ref<string[]>([])
const preferenceSettingUiButtons = ref<string[]>([])
const approvalFlowDiagramVisible = ref<boolean>(false)
const activeApprovalFlow = ref<SystemApprovalFlowItem | null>(null)
const approvalFlowErrorMessage = ref<string>('')
const userCatalogDetailVisible = ref<boolean>(false)
const activeUserCatalogItem = ref<SystemUserCatalogItem | null>(null)
const userCatalogErrorMessage = ref<string>('')
const activeOrganizationFrameworkItem = ref<SystemOrganizationFrameworkItem | null>(null)
const organizationFrameworkErrorMessage = ref<string>('')
const activeIntegrationPlatformItem = ref<SystemIntegrationPlatformItem | null>(null)
const integrationPlatformErrorMessage = ref<string>('')
const activeSystemAnnouncementItem = ref<SystemAnnouncementItem | null>(null)
const systemAnnouncementErrorMessage = ref<string>('')
const activeOperationLogItem = ref<SystemOperationLogItem | null>(null)
const operationLogErrorMessage = ref<string>('')
const activeDocumentCodeItem = ref<SystemDocumentCodeItem | null>(null)
const documentCodeErrorMessage = ref<string>('')
const activeMessageNotificationSettingItem = ref<SystemMessageNotificationSettingItem | null>(null)
const messageNotificationSettingErrorMessage = ref<string>('')
const activePreferenceSettingItem = ref<SystemPreferenceSettingItem | null>(null)
const preferenceSettingErrorMessage = ref<string>('')

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

const approvalFlowQuery = reactive({
  audit_type: '样板单',
  status: '' as '' | '启用' | '草稿' | '停用',
  keyword: '',
  start_date: '',
  end_date: '',
})

const userCatalogQuery = reactive({
  role: '',
  status: '' as '' | '启用' | '停用' | '锁定',
  keyword: '',
  start_date: '',
  end_date: '',
})

const organizationFrameworkQuery = reactive({
  org_level: '',
  status: '' as '' | '生效' | '待生效' | '停用',
  keyword: '',
  effective_start_date: '',
  effective_end_date: '',
})

const integrationPlatformQuery = reactive({
  platform_type: '',
  status: '' as '' | '运行中' | '告警' | '停用',
  endpoint_mode: '',
  keyword: '',
  updated_start_date: '',
  updated_end_date: '',
})

const systemAnnouncementQuery = reactive({
  category: '',
  status: '' as '' | '已发布' | '草稿' | '已撤回',
  target_scope: '',
  keyword: '',
  published_start_date: '',
  published_end_date: '',
})

const operationLogQuery = reactive({
  module: '',
  operation_type: '',
  result_status: '' as '' | '成功' | '失败' | '部分成功',
  operator: '',
  keyword: '',
  operated_start_date: '',
  operated_end_date: '',
})

const documentCodeQuery = reactive({
  document_type: '',
  status: '' as '' | '启用' | '停用' | '草稿',
  keyword: '',
  updated_start_date: '',
  updated_end_date: '',
})

const messageNotificationSettingQuery = reactive({
  channel: '',
  status: '' as '' | '启用' | '停用' | '草稿',
  target_scope: '',
  keyword: '',
  updated_start_date: '',
  updated_end_date: '',
})

const preferenceSettingQuery = reactive({
  preference_scope: '',
  status: '' as '' | '启用' | '停用' | '草稿',
  keyword: '',
  updated_start_date: '',
  updated_end_date: '',
})

const canSystemRead = computed<boolean>(() => permissionStore.state.actions.includes('system:read'))
const canConfigRead = computed<boolean>(() => permissionStore.state.actions.includes('system:config_read'))
const canDictionaryRead = computed<boolean>(() => permissionStore.state.actions.includes('system:dictionary_read'))
const canDiagnosticRead = computed<boolean>(() => permissionStore.state.actions.includes('system:diagnostic'))
const canReadConfig = computed<boolean>(() => canSystemRead.value && canConfigRead.value)
const canReadDictionary = computed<boolean>(() => canSystemRead.value && canDictionaryRead.value)
const canReadHealthSummary = computed<boolean>(() => canSystemRead.value && canDiagnosticRead.value)
const canReadApprovalFlows = computed<boolean>(() => canSystemRead.value && canConfigRead.value)
const canReadUserCatalog = computed<boolean>(() => canSystemRead.value && canConfigRead.value)
const canReadOrganizationFramework = computed<boolean>(() => canSystemRead.value && canConfigRead.value)
const canReadIntegrationPlatforms = computed<boolean>(() => canSystemRead.value && canConfigRead.value)
const canReadSystemAnnouncements = computed<boolean>(() => canSystemRead.value && canConfigRead.value)
const canReadOperationLogs = computed<boolean>(() => canSystemRead.value && canConfigRead.value)
const canReadDocumentCodes = computed<boolean>(() => canSystemRead.value && canConfigRead.value)
const canReadMessageNotificationSettings = computed<boolean>(() => canSystemRead.value && canConfigRead.value)
const canReadPreferenceSettings = computed<boolean>(() => canSystemRead.value && canConfigRead.value)

const systemGuardKey = (actionKey: string): string => {
  const normalized = actionKey.replace(/_/g, '-')
  if (normalized === 'view') {
    return 'readonly:system-view'
  }
  return `readonly:system-${normalized}`
}

const systemSideEffectGuard = (actionKey: string): string => {
  const normalized = actionKey.toLowerCase()
  if (normalized.includes('export') || normalized.includes('download') || normalized.includes('print')) {
    return 'download-disabled'
  }
  if (normalized.includes('sync') || normalized.includes('retry') || normalized.includes('test')) {
    return 'sync-disabled'
  }
  if (normalized === 'view') {
    return 'view-only'
  }
  return 'write-disabled'
}

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

const loadApprovalFlows = async (): Promise<void> => {
  if (!canReadApprovalFlows.value) {
    approvalFlowItems.value = []
    approvalFlowAuditTypeOptions.value = []
    approvalFlowErrorMessage.value = ''
    activeApprovalFlow.value = null
    return
  }

  approvalFlowLoading.value = true
  approvalFlowErrorMessage.value = ''
  try {
    const result = await systemManagementApi.fetchSystemApprovalFlows({
      audit_type: approvalFlowQuery.audit_type || undefined,
      status: approvalFlowQuery.status || undefined,
      keyword: approvalFlowQuery.keyword.trim() || undefined,
      start_date: approvalFlowQuery.start_date.trim() || undefined,
      end_date: approvalFlowQuery.end_date.trim() || undefined,
    })
    approvalFlowItems.value = result.data.items
    approvalFlowAuditTypeOptions.value = result.data.audit_type_options
    activeApprovalFlow.value = result.data.items[0] ?? null
  } catch (error: unknown) {
    approvalFlowItems.value = []
    activeApprovalFlow.value = null
    approvalFlowErrorMessage.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    approvalFlowLoading.value = false
  }
}

const loadUserCatalog = async (): Promise<void> => {
  if (!canReadUserCatalog.value) {
    userCatalogItems.value = []
    userRoleOptions.value = []
    userStatusOptions.value = []
    userCatalogErrorMessage.value = ''
    activeUserCatalogItem.value = null
    return
  }

  userCatalogLoading.value = true
  userCatalogErrorMessage.value = ''
  try {
    const result = await systemManagementApi.fetchSystemUserCatalog({
      role: userCatalogQuery.role || undefined,
      status: userCatalogQuery.status || undefined,
      keyword: userCatalogQuery.keyword.trim() || undefined,
      start_date: userCatalogQuery.start_date.trim() || undefined,
      end_date: userCatalogQuery.end_date.trim() || undefined,
    })
    userCatalogItems.value = result.data.items
    userRoleOptions.value = result.data.role_options
    userStatusOptions.value = result.data.status_options
    activeUserCatalogItem.value = result.data.items[0] ?? null
  } catch (error: unknown) {
    userCatalogItems.value = []
    activeUserCatalogItem.value = null
    userCatalogErrorMessage.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    userCatalogLoading.value = false
  }
}

const loadOrganizationFrameworks = async (): Promise<void> => {
  if (!canReadOrganizationFramework.value) {
    organizationFrameworkItems.value = []
    organizationFrameworkLevelOptions.value = []
    organizationFrameworkStatusTags.value = []
    organizationFrameworkUiButtons.value = []
    organizationFrameworkErrorMessage.value = ''
    activeOrganizationFrameworkItem.value = null
    return
  }

  organizationFrameworkLoading.value = true
  organizationFrameworkErrorMessage.value = ''
  try {
    const result = await systemManagementApi.fetchSystemOrganizationFrameworks({
      org_level: organizationFrameworkQuery.org_level || undefined,
      status: organizationFrameworkQuery.status || undefined,
      keyword: organizationFrameworkQuery.keyword.trim() || undefined,
      effective_start_date: organizationFrameworkQuery.effective_start_date.trim() || undefined,
      effective_end_date: organizationFrameworkQuery.effective_end_date.trim() || undefined,
    })
    organizationFrameworkItems.value = result.data.items
    organizationFrameworkLevelOptions.value = result.data.org_level_options
    organizationFrameworkStatusTags.value = result.data.status_tags
    organizationFrameworkUiButtons.value = result.data.ui_buttons
    activeOrganizationFrameworkItem.value = result.data.items[0] ?? null
  } catch (error: unknown) {
    organizationFrameworkItems.value = []
    activeOrganizationFrameworkItem.value = null
    organizationFrameworkErrorMessage.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    organizationFrameworkLoading.value = false
  }
}

const loadIntegrationPlatforms = async (): Promise<void> => {
  if (!canReadIntegrationPlatforms.value) {
    integrationPlatformItems.value = []
    integrationPlatformTypeOptions.value = []
    integrationPlatformModeOptions.value = []
    integrationPlatformStatusTags.value = []
    integrationPlatformUiButtons.value = []
    integrationPlatformErrorMessage.value = ''
    activeIntegrationPlatformItem.value = null
    return
  }

  integrationPlatformLoading.value = true
  integrationPlatformErrorMessage.value = ''
  try {
    const result = await systemManagementApi.fetchSystemIntegrationPlatforms({
      platform_type: integrationPlatformQuery.platform_type || undefined,
      status: integrationPlatformQuery.status || undefined,
      endpoint_mode: integrationPlatformQuery.endpoint_mode || undefined,
      keyword: integrationPlatformQuery.keyword.trim() || undefined,
      updated_start_date: integrationPlatformQuery.updated_start_date.trim() || undefined,
      updated_end_date: integrationPlatformQuery.updated_end_date.trim() || undefined,
    })
    integrationPlatformItems.value = result.data.items
    integrationPlatformTypeOptions.value = result.data.platform_type_options
    integrationPlatformModeOptions.value = result.data.endpoint_mode_options
    integrationPlatformStatusTags.value = result.data.status_tags
    integrationPlatformUiButtons.value = result.data.ui_buttons
    activeIntegrationPlatformItem.value = result.data.items[0] ?? null
  } catch (error: unknown) {
    integrationPlatformItems.value = []
    activeIntegrationPlatformItem.value = null
    integrationPlatformErrorMessage.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    integrationPlatformLoading.value = false
  }
}

const loadSystemAnnouncements = async (): Promise<void> => {
  if (!canReadSystemAnnouncements.value) {
    systemAnnouncementItems.value = []
    systemAnnouncementCategoryOptions.value = []
    systemAnnouncementStatusTags.value = []
    systemAnnouncementUiButtons.value = []
    systemAnnouncementErrorMessage.value = ''
    activeSystemAnnouncementItem.value = null
    return
  }

  systemAnnouncementLoading.value = true
  systemAnnouncementErrorMessage.value = ''
  try {
    const result = await systemManagementApi.fetchSystemAnnouncements({
      category: systemAnnouncementQuery.category || undefined,
      status: systemAnnouncementQuery.status || undefined,
      target_scope: systemAnnouncementQuery.target_scope.trim() || undefined,
      keyword: systemAnnouncementQuery.keyword.trim() || undefined,
      published_start_date: systemAnnouncementQuery.published_start_date.trim() || undefined,
      published_end_date: systemAnnouncementQuery.published_end_date.trim() || undefined,
    })
    systemAnnouncementItems.value = result.data.items
    systemAnnouncementCategoryOptions.value = result.data.category_options
    systemAnnouncementStatusTags.value = result.data.status_tags
    systemAnnouncementUiButtons.value = result.data.ui_buttons
    activeSystemAnnouncementItem.value = result.data.items[0] ?? null
  } catch (error: unknown) {
    systemAnnouncementItems.value = []
    activeSystemAnnouncementItem.value = null
    systemAnnouncementErrorMessage.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    systemAnnouncementLoading.value = false
  }
}

const loadOperationLogs = async (): Promise<void> => {
  if (!canReadOperationLogs.value) {
    operationLogItems.value = []
    operationLogModuleOptions.value = []
    operationLogTypeOptions.value = []
    operationLogStatusTags.value = []
    operationLogUiButtons.value = []
    operationLogErrorMessage.value = ''
    activeOperationLogItem.value = null
    return
  }

  operationLogLoading.value = true
  operationLogErrorMessage.value = ''
  try {
    const result = await systemManagementApi.fetchSystemOperationLogs({
      module: operationLogQuery.module || undefined,
      operation_type: operationLogQuery.operation_type || undefined,
      result_status: operationLogQuery.result_status || undefined,
      operator: operationLogQuery.operator.trim() || undefined,
      keyword: operationLogQuery.keyword.trim() || undefined,
      operated_start_date: operationLogQuery.operated_start_date.trim() || undefined,
      operated_end_date: operationLogQuery.operated_end_date.trim() || undefined,
    })
    operationLogItems.value = result.data.items
    operationLogModuleOptions.value = result.data.module_options
    operationLogTypeOptions.value = result.data.operation_type_options
    operationLogStatusTags.value = result.data.status_tags
    operationLogUiButtons.value = result.data.ui_buttons
    activeOperationLogItem.value = result.data.items[0] ?? null
  } catch (error: unknown) {
    operationLogItems.value = []
    activeOperationLogItem.value = null
    operationLogErrorMessage.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    operationLogLoading.value = false
  }
}

const loadDocumentCodes = async (): Promise<void> => {
  if (!canReadDocumentCodes.value) {
    documentCodeItems.value = []
    documentCodeTypeOptions.value = []
    documentCodeStatusTags.value = []
    documentCodeUiButtons.value = []
    documentCodeErrorMessage.value = ''
    activeDocumentCodeItem.value = null
    return
  }

  documentCodeLoading.value = true
  documentCodeErrorMessage.value = ''
  try {
    const result = await systemManagementApi.fetchSystemDocumentCodes({
      document_type: documentCodeQuery.document_type || undefined,
      status: documentCodeQuery.status || undefined,
      keyword: documentCodeQuery.keyword.trim() || undefined,
      updated_start_date: documentCodeQuery.updated_start_date.trim() || undefined,
      updated_end_date: documentCodeQuery.updated_end_date.trim() || undefined,
    })
    documentCodeItems.value = result.data.items
    documentCodeTypeOptions.value = result.data.document_type_options
    documentCodeStatusTags.value = result.data.status_tags
    documentCodeUiButtons.value = result.data.ui_buttons
    activeDocumentCodeItem.value = result.data.items[0] ?? null
  } catch (error: unknown) {
    documentCodeItems.value = []
    activeDocumentCodeItem.value = null
    documentCodeErrorMessage.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    documentCodeLoading.value = false
  }
}

const loadMessageNotificationSettings = async (): Promise<void> => {
  if (!canReadMessageNotificationSettings.value) {
    messageNotificationSettingItems.value = []
    messageNotificationSettingChannelOptions.value = []
    messageNotificationSettingStatusTags.value = []
    messageNotificationSettingUiButtons.value = []
    messageNotificationSettingErrorMessage.value = ''
    activeMessageNotificationSettingItem.value = null
    return
  }

  messageNotificationSettingLoading.value = true
  messageNotificationSettingErrorMessage.value = ''
  try {
    const result = await systemManagementApi.fetchSystemMessageNotificationSettings({
      channel: messageNotificationSettingQuery.channel || undefined,
      status: messageNotificationSettingQuery.status || undefined,
      target_scope: messageNotificationSettingQuery.target_scope.trim() || undefined,
      keyword: messageNotificationSettingQuery.keyword.trim() || undefined,
      updated_start_date: messageNotificationSettingQuery.updated_start_date.trim() || undefined,
      updated_end_date: messageNotificationSettingQuery.updated_end_date.trim() || undefined,
    })
    messageNotificationSettingItems.value = result.data.items
    messageNotificationSettingChannelOptions.value = result.data.channel_options
    messageNotificationSettingStatusTags.value = result.data.status_tags
    messageNotificationSettingUiButtons.value = result.data.ui_buttons
    activeMessageNotificationSettingItem.value = result.data.items[0] ?? null
  } catch (error: unknown) {
    messageNotificationSettingItems.value = []
    activeMessageNotificationSettingItem.value = null
    messageNotificationSettingErrorMessage.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    messageNotificationSettingLoading.value = false
  }
}

const loadPreferenceSettings = async (): Promise<void> => {
  if (!canReadPreferenceSettings.value) {
    preferenceSettingItems.value = []
    preferenceSettingScopeOptions.value = []
    preferenceSettingStatusTags.value = []
    preferenceSettingUiButtons.value = []
    preferenceSettingErrorMessage.value = ''
    activePreferenceSettingItem.value = null
    return
  }

  preferenceSettingLoading.value = true
  preferenceSettingErrorMessage.value = ''
  try {
    const result = await systemManagementApi.fetchSystemPreferenceSettings({
      preference_scope: preferenceSettingQuery.preference_scope || undefined,
      status: preferenceSettingQuery.status || undefined,
      keyword: preferenceSettingQuery.keyword.trim() || undefined,
      updated_start_date: preferenceSettingQuery.updated_start_date.trim() || undefined,
      updated_end_date: preferenceSettingQuery.updated_end_date.trim() || undefined,
    })
    preferenceSettingItems.value = result.data.items
    preferenceSettingScopeOptions.value = result.data.preference_scope_options
    preferenceSettingStatusTags.value = result.data.status_tags
    preferenceSettingUiButtons.value = result.data.ui_buttons
    activePreferenceSettingItem.value = result.data.items[0] ?? null
  } catch (error: unknown) {
    preferenceSettingItems.value = []
    activePreferenceSettingItem.value = null
    preferenceSettingErrorMessage.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    preferenceSettingLoading.value = false
  }
}

const resetApprovalFlowFilters = (): void => {
  approvalFlowQuery.audit_type = '样板单'
  approvalFlowQuery.status = ''
  approvalFlowQuery.keyword = ''
  approvalFlowQuery.start_date = ''
  approvalFlowQuery.end_date = ''
  void loadApprovalFlows()
}

const clearApprovalFlowSelection = (): void => {
  approvalFlowItems.value = []
  activeApprovalFlow.value = null
  approvalFlowErrorMessage.value = ''
}

const resetUserCatalogFilters = (): void => {
  userCatalogQuery.role = ''
  userCatalogQuery.status = ''
  userCatalogQuery.keyword = ''
  userCatalogQuery.start_date = ''
  userCatalogQuery.end_date = ''
  void loadUserCatalog()
}

const clearUserCatalogSelection = (): void => {
  userCatalogItems.value = []
  activeUserCatalogItem.value = null
  userCatalogErrorMessage.value = ''
}

const resetOrganizationFrameworkFilters = (): void => {
  organizationFrameworkQuery.org_level = ''
  organizationFrameworkQuery.status = ''
  organizationFrameworkQuery.keyword = ''
  organizationFrameworkQuery.effective_start_date = ''
  organizationFrameworkQuery.effective_end_date = ''
  void loadOrganizationFrameworks()
}

const clearOrganizationFrameworkSelection = (): void => {
  organizationFrameworkItems.value = []
  activeOrganizationFrameworkItem.value = null
  organizationFrameworkErrorMessage.value = ''
}

const resetIntegrationPlatformFilters = (): void => {
  integrationPlatformQuery.platform_type = ''
  integrationPlatformQuery.status = ''
  integrationPlatformQuery.endpoint_mode = ''
  integrationPlatformQuery.keyword = ''
  integrationPlatformQuery.updated_start_date = ''
  integrationPlatformQuery.updated_end_date = ''
  void loadIntegrationPlatforms()
}

const clearIntegrationPlatformSelection = (): void => {
  integrationPlatformItems.value = []
  activeIntegrationPlatformItem.value = null
  integrationPlatformErrorMessage.value = ''
}

const resetSystemAnnouncementFilters = (): void => {
  systemAnnouncementQuery.category = ''
  systemAnnouncementQuery.status = ''
  systemAnnouncementQuery.target_scope = ''
  systemAnnouncementQuery.keyword = ''
  systemAnnouncementQuery.published_start_date = ''
  systemAnnouncementQuery.published_end_date = ''
  void loadSystemAnnouncements()
}

const clearSystemAnnouncementSelection = (): void => {
  systemAnnouncementItems.value = []
  activeSystemAnnouncementItem.value = null
  systemAnnouncementErrorMessage.value = ''
}

const resetOperationLogFilters = (): void => {
  operationLogQuery.module = ''
  operationLogQuery.operation_type = ''
  operationLogQuery.result_status = ''
  operationLogQuery.operator = ''
  operationLogQuery.keyword = ''
  operationLogQuery.operated_start_date = ''
  operationLogQuery.operated_end_date = ''
  void loadOperationLogs()
}

const clearOperationLogSelection = (): void => {
  operationLogItems.value = []
  activeOperationLogItem.value = null
  operationLogErrorMessage.value = ''
}

const resetDocumentCodeFilters = (): void => {
  documentCodeQuery.document_type = ''
  documentCodeQuery.status = ''
  documentCodeQuery.keyword = ''
  documentCodeQuery.updated_start_date = ''
  documentCodeQuery.updated_end_date = ''
  void loadDocumentCodes()
}

const clearDocumentCodeSelection = (): void => {
  documentCodeItems.value = []
  activeDocumentCodeItem.value = null
  documentCodeErrorMessage.value = ''
}

const resetMessageNotificationSettingFilters = (): void => {
  messageNotificationSettingQuery.channel = ''
  messageNotificationSettingQuery.status = ''
  messageNotificationSettingQuery.target_scope = ''
  messageNotificationSettingQuery.keyword = ''
  messageNotificationSettingQuery.updated_start_date = ''
  messageNotificationSettingQuery.updated_end_date = ''
  void loadMessageNotificationSettings()
}

const clearMessageNotificationSettingSelection = (): void => {
  messageNotificationSettingItems.value = []
  activeMessageNotificationSettingItem.value = null
  messageNotificationSettingErrorMessage.value = ''
}

const resetPreferenceSettingFilters = (): void => {
  preferenceSettingQuery.preference_scope = ''
  preferenceSettingQuery.status = ''
  preferenceSettingQuery.keyword = ''
  preferenceSettingQuery.updated_start_date = ''
  preferenceSettingQuery.updated_end_date = ''
  void loadPreferenceSettings()
}

const clearPreferenceSettingSelection = (): void => {
  preferenceSettingItems.value = []
  activePreferenceSettingItem.value = null
  preferenceSettingErrorMessage.value = ''
}

const openApprovalFlowDiagram = (flow: SystemApprovalFlowItem): void => {
  activeApprovalFlow.value = flow
  approvalFlowDiagramVisible.value = true
}

const onGuardedActionClick = (action: SystemApprovalFlowAction): void => {
  ElMessage.info(action.disabled_reason)
}

const onUserCatalogActionClick = (
  item: SystemUserCatalogItem,
  action: SystemUserCatalogAction,
): void => {
  if (action.action_key === 'view' && !action.guarded) {
    activeUserCatalogItem.value = item
    userCatalogDetailVisible.value = true
    return
  }
  ElMessage.info(action.disabled_reason)
}

const onOrganizationFrameworkActionClick = (
  item: SystemOrganizationFrameworkItem,
  action: SystemOrganizationFrameworkAction,
): void => {
  if (action.action_key === 'view' && !action.guarded) {
    activeOrganizationFrameworkItem.value = item
    ElMessage.info(`只读查看：${item.org_name}`)
    return
  }
  ElMessage.info(action.disabled_reason)
}

const onIntegrationPlatformActionClick = (
  item: SystemIntegrationPlatformItem,
  action: SystemIntegrationPlatformAction,
): void => {
  if (action.action_key === 'view' && !action.guarded) {
    activeIntegrationPlatformItem.value = item
    ElMessage.info(`只读查看：${item.platform_name}`)
    return
  }
  ElMessage.info(action.disabled_reason)
}

const onSystemAnnouncementActionClick = (
  item: SystemAnnouncementItem,
  action: SystemAnnouncementAction,
): void => {
  if (action.action_key === 'view' && !action.guarded) {
    activeSystemAnnouncementItem.value = item
    ElMessage.info(`只读查看：${item.title}`)
    return
  }
  ElMessage.info(action.disabled_reason)
}

const onOperationLogActionClick = (
  item: SystemOperationLogItem,
  action: SystemOperationLogAction,
): void => {
  if (action.action_key === 'view' && !action.guarded) {
    activeOperationLogItem.value = item
    ElMessage.info(`只读查看：${item.operation_name}`)
    return
  }
  ElMessage.info(action.disabled_reason)
}

const onDocumentCodeActionClick = (
  item: SystemDocumentCodeItem,
  action: SystemDocumentCodeAction,
): void => {
  if (action.action_key === 'view' && !action.guarded) {
    activeDocumentCodeItem.value = item
    ElMessage.info(`只读查看：${item.document_name}`)
    return
  }
  ElMessage.info(action.disabled_reason)
}

const onMessageNotificationSettingActionClick = (
  item: SystemMessageNotificationSettingItem,
  action: SystemMessageNotificationSettingAction,
): void => {
  if (action.action_key === 'view' && !action.guarded) {
    activeMessageNotificationSettingItem.value = item
    ElMessage.info(`只读查看：${item.setting_name}`)
    return
  }
  ElMessage.info(action.disabled_reason)
}

const onPreferenceSettingActionClick = (
  item: SystemPreferenceSettingItem,
  action: SystemPreferenceSettingAction,
): void => {
  if (action.action_key === 'view' && !action.guarded) {
    activePreferenceSettingItem.value = item
    ElMessage.info(`只读查看：${item.setting_name}`)
    return
  }
  ElMessage.info(action.disabled_reason)
}

const approvalStatusTagType = (status: string): 'success' | 'warning' | 'danger' => {
  if (status === '启用') {
    return 'success'
  }
  if (status === '草稿') {
    return 'warning'
  }
  return 'danger'
}

const approvalNodeTagType = (status: string): 'success' | 'warning' | 'danger' => {
  if (status === 'done') {
    return 'success'
  }
  if (status === 'todo') {
    return 'warning'
  }
  return 'danger'
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

const userStatusTagType = (status: string): 'success' | 'warning' | 'danger' => {
  if (status === '启用') {
    return 'success'
  }
  if (status === '锁定') {
    return 'warning'
  }
  return 'danger'
}

const organizationFrameworkStatusTagType = (status: string): 'success' | 'warning' | 'danger' => {
  if (status === '生效') {
    return 'success'
  }
  if (status === '待生效') {
    return 'warning'
  }
  return 'danger'
}

const integrationPlatformStatusTagType = (status: string): 'success' | 'warning' | 'danger' => {
  if (status === '运行中') {
    return 'success'
  }
  if (status === '告警') {
    return 'warning'
  }
  return 'danger'
}

const systemAnnouncementStatusTagType = (status: string): 'success' | 'warning' | 'danger' => {
  if (status === '已发布') {
    return 'success'
  }
  if (status === '草稿') {
    return 'warning'
  }
  return 'danger'
}

const operationLogResultTagType = (status: string): 'success' | 'warning' | 'danger' => {
  if (status === '成功') {
    return 'success'
  }
  if (status === '部分成功') {
    return 'warning'
  }
  return 'danger'
}

const documentCodeStatusTagType = (status: string): 'success' | 'warning' | 'danger' => {
  if (status === '启用') {
    return 'success'
  }
  if (status === '草稿') {
    return 'warning'
  }
  return 'danger'
}

const messageNotificationSettingStatusTagType = (status: string): 'success' | 'warning' | 'danger' => {
  if (status === '启用') {
    return 'success'
  }
  if (status === '草稿') {
    return 'warning'
  }
  return 'danger'
}

const preferenceSettingStatusTagType = (status: string): 'success' | 'warning' | 'danger' => {
  if (status === '启用') {
    return 'success'
  }
  if (status === '草稿') {
    return 'warning'
  }
  return 'danger'
}

onMounted(() => {
  permissionStore
    .loadCurrentUser()
    .then(() => permissionStore.loadModuleActions('system'))
    .then(() =>
      Promise.all([
        loadApprovalFlows(),
        loadUserCatalog(),
        loadOrganizationFrameworks(),
        loadIntegrationPlatforms(),
        loadSystemAnnouncements(),
        loadOperationLogs(),
        loadDocumentCodes(),
        loadMessageNotificationSettings(),
        loadPreferenceSettings(),
        loadConfigCatalog(),
        loadDictionaryCatalog(),
        loadHealthSummary(),
      ]),
    )
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

.readonly-strip {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.header-row > .el-button {
  flex-shrink: 0;
}

.query-form {
  margin-bottom: 12px;
}

.query-form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.query-form :deep(.el-input),
.query-form :deep(.el-select),
.query-form :deep(.el-date-editor) {
  max-width: 260px;
}

.meta-row {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.action-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

:deep(.el-card__header) {
  padding: 14px 16px;
}

:deep(.el-card__body) {
  padding: 14px 16px;
}

@media (max-width: 768px) {
  .header-row {
    align-items: flex-start;
  }

  .query-form :deep(.el-form-item) {
    width: 100%;
    margin-right: 0;
  }

  .query-form :deep(.el-input),
  .query-form :deep(.el-select),
  .query-form :deep(.el-date-editor) {
    width: 100% !important;
    max-width: 100%;
  }
}
</style>
