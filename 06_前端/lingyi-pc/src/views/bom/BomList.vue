<template>
  <div class="bom-list-page">
    <el-card shadow="never" data-testid="bom-main-list-section">
      <el-form :inline="true" :model="query" data-testid="bom-main-list-filters">
        <el-form-item label="款式编码">
          <el-input v-model="query.item_code" clearable placeholder="Item Code" data-testid="bom-main-item-code-filter" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="query.status"
            clearable
            placeholder="请选择状态"
            aria-label="BOM状态筛选"
            style="width: 160px"
            data-testid="bom-main-status-filter"
          >
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="active" />
            <el-option label="已停用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" data-testid="bom-main-search-button" @click="runMainQuery">
            查询
          </el-button>
          <el-button :disabled="!canRead" data-testid="bom-main-reset-button" @click="resetMainQuery">重置</el-button>
          <el-button
            v-if="canCreate"
            data-action-type="write"
            data-write-guard="permission:create(v-if)"
            data-guard-state="visible_when_allowed"
            data-testid="bom-main-create-guarded-button"
            @click="goCreate"
          >
            新建 BOM
          </el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无 BOM 查看权限" />
      <template v-else>
        <el-alert
          v-if="listError"
          class="main-list-error-alert"
          title="BOM主列表加载失败"
          :description="listError"
          type="error"
          show-icon
          :closable="false"
        />

        <el-table
          :data="rows"
          v-loading="loading"
          border
          empty-text="暂无BOM数据"
          class="bom-main-table"
          data-testid="bom-main-table"
        >
          <el-table-column prop="bom_no" label="BOM编号" min-width="280" />
          <el-table-column prop="item_code" label="款式编码" min-width="140" />
          <el-table-column prop="version_no" label="版本" min-width="100" />
          <el-table-column label="状态" width="120">
            <template #default="scope">
              <el-tag :type="statusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="默认" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.is_default ? 'success' : 'info'">
                {{ scope.row.is_default ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="effective_date" label="生效日期" min-width="120" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="scope">
              <el-button link type="primary" data-testid="bom-main-detail-button" @click="goDetail(scope.row.id)">
                详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="query.page"
            :page-size="query.page_size"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onPageChange"
            @size-change="onSizeChange"
          />
        </div>

        <el-drawer
          v-model="bomDetailVisible"
          title="BOM详情（只读）"
          size="52%"
          destroy-on-close
          data-testid="bom-main-detail-drawer"
        >
          <div v-loading="bomDetailLoading" class="bom-detail-readonly-panel">
            <el-alert
              v-if="bomDetailError"
              class="bom-detail-error-alert"
              title="BOM详情加载失败"
              :description="bomDetailError"
              type="error"
              show-icon
              :closable="false"
            />
            <template v-else-if="bomDetail">
              <el-descriptions :column="2" border size="small" class="bom-detail-header">
                <el-descriptions-item label="BOM编号">{{ bomDetail.bom.bom_no }}</el-descriptions-item>
                <el-descriptions-item label="款式编码">{{ bomDetail.bom.item_code }}</el-descriptions-item>
                <el-descriptions-item label="版本">{{ bomDetail.bom.version_no }}</el-descriptions-item>
                <el-descriptions-item label="状态">
                  <el-tag :type="statusTagType(bomDetail.bom.status)">{{ bomDetail.bom.status }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="默认">
                  {{ bomDetail.bom.is_default ? '是' : '否' }}
                </el-descriptions-item>
                <el-descriptions-item label="生效日期">
                  {{ bomDetail.bom.effective_date || '-' }}
                </el-descriptions-item>
              </el-descriptions>

              <el-divider content-position="left">物料明细</el-divider>
              <el-table :data="bomDetail.items" border size="small" empty-text="暂无物料明细">
                <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
                <el-table-column prop="color" label="颜色" min-width="100" />
                <el-table-column prop="size" label="尺码" min-width="90" />
                <el-table-column prop="qty_per_piece" label="单件用量" min-width="100" />
                <el-table-column prop="loss_rate" label="损耗率" min-width="90" />
                <el-table-column prop="uom" label="单位" min-width="80" />
                <el-table-column prop="remark" label="备注" min-width="180" />
              </el-table>

              <el-divider content-position="left">工序明细</el-divider>
              <el-table :data="bomDetail.operations" border size="small" empty-text="暂无工序明细">
                <el-table-column prop="process_name" label="工序名称" min-width="150" />
                <el-table-column prop="sequence_no" label="顺序" min-width="80" />
                <el-table-column label="委外" min-width="80">
                  <template #default="scope">
                    {{ scope.row.is_subcontract ? '是' : '否' }}
                  </template>
                </el-table-column>
                <el-table-column prop="wage_rate" label="工价" min-width="100" />
                <el-table-column prop="subcontract_cost_per_piece" label="外协单价" min-width="110" />
                <el-table-column prop="remark" label="备注" min-width="180" />
              </el-table>
            </template>
            <el-empty v-else description="暂无详情数据" />
          </div>
        </el-drawer>

        <el-divider content-position="left">面料（TASK-Y27B-P1-01）</el-divider>

        <section class="fabric-section">
          <el-form :inline="true" :model="fabricQuery">
            <el-form-item label="款号">
              <el-input v-model="fabricQuery.item_code" clearable placeholder="请输入款号" />
            </el-form-item>
            <el-form-item label="面料编码">
              <el-input v-model="fabricQuery.material_item_code" clearable placeholder="请输入面料编码" />
            </el-form-item>
            <el-form-item label="面料名称">
              <el-input v-model="fabricQuery.fabric_name" clearable placeholder="请输入面料名称" />
            </el-form-item>
            <el-form-item label="颜色">
              <el-input v-model="fabricQuery.color" clearable placeholder="请输入颜色" />
            </el-form-item>
            <el-form-item label="规格">
              <el-input v-model="fabricQuery.specification" clearable placeholder="请输入规格" />
            </el-form-item>
            <el-form-item label="供应商">
              <el-input v-model="fabricQuery.supplier_name" clearable placeholder="请输入供应商" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="fabricQuery.status"
                clearable
                placeholder="请选择状态"
                style="width: 150px"
                aria-label="面料状态筛选"
              >
                <el-option label="草稿" value="草稿" />
                <el-option label="可用" value="可用" />
                <el-option label="停用" value="停用" />
              </el-select>
            </el-form-item>
            <el-form-item label="操作">
              <el-button type="primary" :disabled="!canRead" @click="loadFabrics">查询</el-button>
              <el-button :disabled="!canRead" @click="resetFabricQuery">重置</el-button>
              <el-button data-action-type="write" data-write-guard="readonly-fabric-use" @click="guardedReadonlyAction('选用')">
                选用
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-fabric-export"
                @click="guardedReadonlyAction('导出')"
              >
                导出
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="fabricError"
            class="fabric-error-alert"
            title="面料加载失败"
            :description="fabricError"
            type="error"
            show-icon
            :closable="false"
          />

          <el-table class="fabric-table" :data="fabricRows" v-loading="fabricLoading" border empty-text="暂无面料数据">
            <el-table-column prop="material_item_code" label="面料编码" min-width="160" />
            <el-table-column prop="fabric_name" label="面料名称" min-width="170" />
            <el-table-column prop="item_code" label="款号" min-width="130" />
            <el-table-column prop="color" label="颜色" min-width="100" />
            <el-table-column prop="specification" label="规格" min-width="100" />
            <el-table-column prop="supplier_name" label="供应商" min-width="150" />
            <el-table-column prop="qty_per_piece" label="单件用量" min-width="100" />
            <el-table-column prop="loss_rate" label="损耗率" min-width="90" />
            <el-table-column prop="uom" label="单位" width="80" />
            <el-table-column prop="bom_no" label="来源BOM" min-width="160" />
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <el-tag :type="fabricStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="openFabricDetail(scope.row)">查看</el-button>
                <el-button link type="warning" @click="guardedReadonlyAction('选用')">选用</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('导出')">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager fabric-pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="fabricQuery.page"
              :page-size="fabricQuery.page_size"
              :total="fabricTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onFabricPageChange"
              @size-change="onFabricSizeChange"
            />
          </div>
        </section>

        <el-divider content-position="left">辅料/包材（TASK-Y27B-P1-02）</el-divider>

        <section class="accessories-packaging-section">
          <el-form :inline="true" :model="accessoriesQuery">
            <el-form-item label="款号">
              <el-input v-model="accessoriesQuery.item_code" clearable placeholder="请输入款号" />
            </el-form-item>
            <el-form-item label="物料编码">
              <el-input v-model="accessoriesQuery.material_item_code" clearable placeholder="请输入物料编码" />
            </el-form-item>
            <el-form-item label="物料名称">
              <el-input v-model="accessoriesQuery.material_name" clearable placeholder="请输入物料名称" />
            </el-form-item>
            <el-form-item label="分类">
              <el-select
                v-model="accessoriesQuery.category"
                clearable
                placeholder="请选择分类"
                style="width: 150px"
                aria-label="辅料包材分类筛选"
              >
                <el-option label="辅料" value="辅料" />
                <el-option label="包材" value="包材" />
              </el-select>
            </el-form-item>
            <el-form-item label="供应商">
              <el-input v-model="accessoriesQuery.supplier_name" clearable placeholder="请输入供应商" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="accessoriesQuery.status"
                clearable
                placeholder="请选择状态"
                style="width: 150px"
                aria-label="辅料包材状态筛选"
              >
                <el-option label="草稿" value="草稿" />
                <el-option label="可用" value="可用" />
                <el-option label="停用" value="停用" />
              </el-select>
            </el-form-item>
            <el-form-item label="操作">
              <el-button type="primary" :disabled="!canRead" @click="loadAccessoriesPackaging">查询</el-button>
              <el-button :disabled="!canRead" @click="resetAccessoriesQuery">重置</el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-accessories-use"
                @click="guardedReadonlyAction('选用')"
              >
                选用
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-accessories-upload"
                @click="guardedReadonlyAction('上传')"
              >
                上传
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-accessories-export"
                @click="guardedReadonlyAction('导出')"
              >
                导出
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="accessoriesError"
            class="accessories-error-alert"
            title="辅料/包材加载失败"
            :description="accessoriesError"
            type="error"
            show-icon
            :closable="false"
          />

          <el-table
            class="accessories-packaging-table"
            :data="accessoriesRows"
            v-loading="accessoriesLoading"
            border
            empty-text="暂无辅料/包材数据"
          >
            <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
            <el-table-column prop="material_name" label="物料名称" min-width="170" />
            <el-table-column prop="category" label="分类" min-width="100" />
            <el-table-column prop="item_code" label="款号" min-width="120" />
            <el-table-column prop="color" label="颜色" min-width="100" />
            <el-table-column prop="specification" label="规格" min-width="100" />
            <el-table-column prop="supplier_name" label="供应商" min-width="150" />
            <el-table-column prop="qty_per_piece" label="单件用量" min-width="100" />
            <el-table-column prop="loss_rate" label="损耗率" min-width="90" />
            <el-table-column prop="uom" label="单位" width="80" />
            <el-table-column prop="bom_no" label="来源BOM" min-width="160" />
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <el-tag :type="fabricStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="260" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="openAccessoriesDetail(scope.row)">查看</el-button>
                <el-button link type="warning" @click="guardedReadonlyAction('选用')">选用</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('上传')">上传</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('导出')">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager accessories-pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="accessoriesQuery.page"
              :page-size="accessoriesQuery.page_size"
              :total="accessoriesTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onAccessoriesPageChange"
              @size-change="onAccessoriesSizeChange"
            />
          </div>
        </section>

        <el-divider content-position="left">物料加工类型（TASK-Y27B-P1-03）</el-divider>

        <section class="processing-type-section">
          <el-form :inline="true" :model="processingTypeQuery">
            <el-form-item label="款号">
              <el-input v-model="processingTypeQuery.item_code" clearable placeholder="请输入款号" />
            </el-form-item>
            <el-form-item label="加工类型">
              <el-input v-model="processingTypeQuery.process_type_name" clearable placeholder="请输入加工类型" />
            </el-form-item>
            <el-form-item label="工序名称">
              <el-input v-model="processingTypeQuery.process_name" clearable placeholder="请输入工序名称" />
            </el-form-item>
            <el-form-item label="委外类型">
              <el-select
                v-model="processingTypeQuery.subcontract_mode"
                clearable
                placeholder="请选择委外类型"
                style="width: 150px"
                aria-label="物料加工类型委外类型筛选"
              >
                <el-option label="自产" value="自产" />
                <el-option label="委外" value="委外" />
              </el-select>
            </el-form-item>
            <el-form-item label="计价方式">
              <el-select
                v-model="processingTypeQuery.pricing_mode"
                clearable
                placeholder="请选择计价方式"
                style="width: 180px"
                aria-label="物料加工类型计价方式筛选"
              >
                <el-option label="标准工序" value="标准工序" />
                <el-option label="按工价" value="按工价" />
                <el-option label="按件外协" value="按件外协" />
                <el-option label="外协待定" value="外协待定" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="processingTypeQuery.status"
                clearable
                placeholder="请选择状态"
                style="width: 150px"
                aria-label="物料加工类型状态筛选"
              >
                <el-option label="草稿" value="草稿" />
                <el-option label="可用" value="可用" />
                <el-option label="停用" value="停用" />
              </el-select>
            </el-form-item>
            <el-form-item label="操作">
              <el-button type="primary" :disabled="!canRead" @click="loadProcessingTypes">查询</el-button>
              <el-button :disabled="!canRead" @click="resetProcessingTypeQuery">重置</el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-processing-type-config"
                @click="guardedReadonlyAction('配置')"
              >
                配置
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-processing-type-toggle"
                @click="guardedReadonlyAction('启停')"
              >
                启停
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-processing-type-export"
                @click="guardedReadonlyAction('导出')"
              >
                导出
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="processingTypeError"
            class="processing-type-error-alert"
            title="物料加工类型加载失败"
            :description="processingTypeError"
            type="error"
            show-icon
            :closable="false"
          />

          <el-table
            class="processing-type-table"
            :data="processingTypeRows"
            v-loading="processingTypeLoading"
            border
            empty-text="暂无物料加工类型数据"
          >
            <el-table-column prop="process_type_code" label="加工类型编码" min-width="170" />
            <el-table-column prop="process_type_name" label="加工类型" min-width="160" />
            <el-table-column prop="process_name" label="工序名称" min-width="160" />
            <el-table-column prop="sequence_no" label="工序顺序" min-width="100" />
            <el-table-column prop="subcontract_mode" label="委外类型" min-width="100" />
            <el-table-column prop="pricing_mode" label="计价方式" min-width="110" />
            <el-table-column prop="unit_rate" label="单价/工价" min-width="110" />
            <el-table-column prop="item_code" label="款号" min-width="120" />
            <el-table-column prop="bom_no" label="来源BOM" min-width="170" />
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <el-tag :type="fabricStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="260" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="openProcessingTypeDetail(scope.row)">查看</el-button>
                <el-button link type="warning" @click="guardedReadonlyAction('配置')">配置</el-button>
                <el-button link type="danger" @click="guardedReadonlyAction('启停')">启停</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('导出')">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager processing-type-pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="processingTypeQuery.page"
              :page-size="processingTypeQuery.page_size"
              :total="processingTypeTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onProcessingTypePageChange"
              @size-change="onProcessingTypeSizeChange"
            />
          </div>
        </section>

        <el-divider content-position="left">物料加工（TASK-Y33B-P1-05）</el-divider>

        <section class="material-processing-section">
          <el-form :inline="true" :model="materialProcessingQuery">
            <el-form-item label="款号">
              <el-input v-model="materialProcessingQuery.item_code" clearable placeholder="请输入款号" />
            </el-form-item>
            <el-form-item label="工序编号">
              <el-input v-model="materialProcessingQuery.process_no" clearable placeholder="请输入工序编号" />
            </el-form-item>
            <el-form-item label="工序名称">
              <el-input v-model="materialProcessingQuery.process_name" clearable placeholder="请输入工序名称" />
            </el-form-item>
            <el-form-item label="加工供应商">
              <el-input v-model="materialProcessingQuery.processing_supplier" clearable placeholder="请输入加工供应商" />
            </el-form-item>
            <el-form-item label="加工方式">
              <el-select
                v-model="materialProcessingQuery.processing_mode"
                clearable
                placeholder="请选择加工方式"
                style="width: 160px"
                aria-label="物料加工方式筛选"
              >
                <el-option label="自产加工" value="自产加工" />
                <el-option label="协同加工" value="协同加工" />
                <el-option label="委外加工" value="委外加工" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="materialProcessingQuery.status"
                clearable
                placeholder="请选择状态"
                style="width: 150px"
                aria-label="物料加工状态筛选"
              >
                <el-option label="草稿" value="草稿" />
                <el-option label="可用" value="可用" />
                <el-option label="停用" value="停用" />
              </el-select>
            </el-form-item>
            <el-form-item label="操作">
              <el-button type="primary" :disabled="!canRead" @click="loadMaterialProcessing">查询</el-button>
              <el-button :disabled="!canRead" @click="resetMaterialProcessingQuery">重置</el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-processing-create"
                @click="guardedReadonlyAction('新增加工')"
              >
                新增加工
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-processing-edit"
                @click="guardedReadonlyAction('编辑')"
              >
                编辑
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-processing-delete"
                @click="guardedReadonlyAction('删除')"
              >
                删除
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-processing-submit"
                @click="guardedReadonlyAction('提交审核')"
              >
                提交审核
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-processing-sync"
                @click="guardedReadonlyAction('同步')"
              >
                同步
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-processing-export"
                @click="guardedReadonlyAction('导出')"
              >
                导出
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-processing-print"
                @click="guardedReadonlyAction('打印')"
              >
                打印
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="materialProcessingError"
            class="material-processing-error-alert"
            title="物料加工加载失败"
            :description="materialProcessingError"
            type="error"
            show-icon
            :closable="false"
          />

          <el-table
            class="material-processing-table"
            :data="materialProcessingRows"
            v-loading="materialProcessingLoading"
            border
            empty-text="暂无物料加工数据"
          >
            <el-table-column prop="process_no" label="工序编号" min-width="150" />
            <el-table-column prop="process_name" label="工序名称" min-width="150" />
            <el-table-column prop="processing_supplier" label="加工供应商" min-width="160" />
            <el-table-column prop="processing_mode" label="加工方式" min-width="120" />
            <el-table-column prop="planned_qty" label="计划数量" min-width="110" />
            <el-table-column prop="completed_qty" label="完成数量" min-width="110" />
            <el-table-column prop="pending_qty" label="待完成数量" min-width="120" />
            <el-table-column prop="scrap_qty" label="损耗数量" min-width="110" />
            <el-table-column prop="uom" label="单位" width="80" />
            <el-table-column prop="due_date" label="计划完成日" min-width="120" />
            <el-table-column prop="item_code" label="款号" min-width="120" />
            <el-table-column prop="bom_no" label="来源BOM" min-width="170" />
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <el-tag :type="fabricStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="280" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="openMaterialProcessingDetail(scope.row)">查看</el-button>
                <el-button link type="warning" @click="guardedReadonlyAction('编辑')">编辑</el-button>
                <el-button link type="danger" @click="guardedReadonlyAction('删除')">删除</el-button>
                <el-button link type="success" @click="guardedReadonlyAction('提交审核')">提交审核</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('导出')">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager material-processing-pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="materialProcessingQuery.page"
              :page-size="materialProcessingQuery.page_size"
              :total="materialProcessingTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onMaterialProcessingPageChange"
              @size-change="onMaterialProcessingSizeChange"
            />
          </div>
        </section>

        <el-divider content-position="left">物料加工入仓（TASK-Y39B-P1-01）</el-divider>

        <section class="material-processing-inbound-section">
          <el-form :inline="true" :model="materialProcessingInboundQuery">
            <el-form-item label="款号">
              <el-input v-model="materialProcessingInboundQuery.item_code" clearable placeholder="请输入款号" />
            </el-form-item>
            <el-form-item label="入仓单号">
              <el-input v-model="materialProcessingInboundQuery.inbound_no" clearable placeholder="请输入入仓单号" />
            </el-form-item>
            <el-form-item label="物料编码">
              <el-input
                v-model="materialProcessingInboundQuery.material_item_code"
                clearable
                placeholder="请输入物料编码"
              />
            </el-form-item>
            <el-form-item label="加工供应商">
              <el-input
                v-model="materialProcessingInboundQuery.processing_supplier"
                clearable
                placeholder="请输入加工供应商"
              />
            </el-form-item>
            <el-form-item label="入仓仓库">
              <el-select
                v-model="materialProcessingInboundQuery.warehouse_name"
                clearable
                placeholder="请选择入仓仓库"
                style="width: 170px"
                aria-label="物料加工入仓仓库筛选"
              >
                <el-option label="主料成品仓" value="主料成品仓" />
                <el-option label="委外中转仓" value="委外中转仓" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="materialProcessingInboundQuery.status"
                clearable
                placeholder="请选择状态"
                style="width: 150px"
                aria-label="物料加工入仓状态筛选"
              >
                <el-option label="待入仓" value="待入仓" />
                <el-option label="已入仓" value="已入仓" />
                <el-option label="已关闭" value="已关闭" />
              </el-select>
            </el-form-item>
            <el-form-item label="操作">
              <el-button type="primary" :disabled="!canRead" @click="loadMaterialProcessingInbound">查询</el-button>
              <el-button :disabled="!canRead" @click="resetMaterialProcessingInboundQuery">重置</el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-processing-inbound-confirm"
                @click="guardedReadonlyAction('入仓确认')"
              >
                入仓确认
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-processing-inbound-inspect"
                @click="guardedReadonlyAction('质检')"
              >
                质检
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-processing-inbound-sync"
                @click="guardedReadonlyAction('同步')"
              >
                同步
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-processing-inbound-export"
                @click="guardedReadonlyAction('导出')"
              >
                导出
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-processing-inbound-print"
                @click="guardedReadonlyAction('打印')"
              >
                打印
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="materialProcessingInboundError"
            class="material-processing-inbound-error-alert"
            title="物料加工入仓加载失败"
            :description="materialProcessingInboundError"
            type="error"
            show-icon
            :closable="false"
          />

          <el-table
            class="material-processing-inbound-table"
            :data="materialProcessingInboundRows"
            v-loading="materialProcessingInboundLoading"
            border
            empty-text="暂无物料加工入仓数据"
          >
            <el-table-column prop="inbound_no" label="入仓单号" min-width="170" />
            <el-table-column prop="process_no" label="工序编号" min-width="150" />
            <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
            <el-table-column prop="processing_supplier" label="加工供应商" min-width="160" />
            <el-table-column prop="warehouse_name" label="入仓仓库" min-width="130" />
            <el-table-column prop="inbound_qty" label="入仓数量" min-width="110" />
            <el-table-column prop="inspected_qty" label="已质检数量" min-width="120" />
            <el-table-column prop="pending_inspection_qty" label="待质检数量" min-width="120" />
            <el-table-column prop="inbound_date" label="入仓日期" min-width="120" />
            <el-table-column prop="item_code" label="款号" min-width="120" />
            <el-table-column prop="bom_no" label="来源BOM" min-width="170" />
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <el-tag :type="materialProcessingInboundStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="300" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="openMaterialProcessingInboundDetail(scope.row)">查看</el-button>
                <el-button link type="success" @click="guardedReadonlyAction('入仓确认')">入仓确认</el-button>
                <el-button link type="warning" @click="guardedReadonlyAction('质检')">质检</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('导出')">导出</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('打印')">打印</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager material-processing-inbound-pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="materialProcessingInboundQuery.page"
              :page-size="materialProcessingInboundQuery.page_size"
              :total="materialProcessingInboundTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onMaterialProcessingInboundPageChange"
              @size-change="onMaterialProcessingInboundSizeChange"
            />
          </div>
        </section>

        <el-divider content-position="left">物料扣仓（TASK-Y39B-P1-03）</el-divider>

        <section class="material-deduction-section">
          <el-form :inline="true" :model="materialDeductionQuery">
            <el-form-item label="款号">
              <el-input v-model="materialDeductionQuery.item_code" clearable placeholder="请输入款号" />
            </el-form-item>
            <el-form-item label="扣仓单号">
              <el-input v-model="materialDeductionQuery.deduction_no" clearable placeholder="请输入扣仓单号" />
            </el-form-item>
            <el-form-item label="物料编码">
              <el-input v-model="materialDeductionQuery.material_item_code" clearable placeholder="请输入物料编码" />
            </el-form-item>
            <el-form-item label="扣仓仓库">
              <el-select
                v-model="materialDeductionQuery.warehouse_name"
                clearable
                placeholder="请选择扣仓仓库"
                style="width: 170px"
                aria-label="物料扣仓仓库筛选"
              >
                <el-option label="主料成品仓" value="主料成品仓" />
                <el-option label="委外中转仓" value="委外中转仓" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="materialDeductionQuery.status"
                clearable
                placeholder="请选择状态"
                style="width: 150px"
                aria-label="物料扣仓状态筛选"
              >
                <el-option label="待扣仓" value="待扣仓" />
                <el-option label="已扣仓" value="已扣仓" />
                <el-option label="已关闭" value="已关闭" />
              </el-select>
            </el-form-item>
            <el-form-item label="操作">
              <el-button type="primary" :disabled="!canRead" @click="loadMaterialDeduction">查询</el-button>
              <el-button :disabled="!canRead" @click="resetMaterialDeductionQuery">重置</el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-deduction-confirm"
                @click="guardedReadonlyAction('扣仓确认')"
              >
                扣仓确认
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-deduction-reverse"
                @click="guardedReadonlyAction('扣仓冲销')"
              >
                扣仓冲销
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-deduction-sync"
                @click="guardedReadonlyAction('同步')"
              >
                同步
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-deduction-export"
                @click="guardedReadonlyAction('导出')"
              >
                导出
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-deduction-print"
                @click="guardedReadonlyAction('打印')"
              >
                打印
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="materialDeductionError"
            class="material-deduction-error-alert"
            title="物料扣仓加载失败"
            :description="materialDeductionError"
            type="error"
            show-icon
            :closable="false"
          />

          <el-table
            class="material-deduction-table"
            :data="materialDeductionRows"
            v-loading="materialDeductionLoading"
            border
            empty-text="暂无物料扣仓数据"
          >
            <el-table-column prop="deduction_no" label="扣仓单号" min-width="170" />
            <el-table-column prop="process_no" label="工序编号" min-width="150" />
            <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
            <el-table-column prop="warehouse_name" label="扣仓仓库" min-width="130" />
            <el-table-column prop="deduction_qty" label="应扣数量" min-width="110" />
            <el-table-column prop="deducted_qty" label="已扣数量" min-width="110" />
            <el-table-column prop="pending_deduction_qty" label="待扣数量" min-width="110" />
            <el-table-column prop="deduction_date" label="扣仓日期" min-width="120" />
            <el-table-column prop="item_code" label="款号" min-width="120" />
            <el-table-column prop="bom_no" label="来源BOM" min-width="170" />
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <el-tag :type="materialDeductionStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="300" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="openMaterialDeductionDetail(scope.row)">查看</el-button>
                <el-button link type="success" @click="guardedReadonlyAction('扣仓确认')">扣仓确认</el-button>
                <el-button link type="warning" @click="guardedReadonlyAction('扣仓冲销')">扣仓冲销</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('导出')">导出</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('打印')">打印</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager material-deduction-pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="materialDeductionQuery.page"
              :page-size="materialDeductionQuery.page_size"
              :total="materialDeductionTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onMaterialDeductionPageChange"
              @size-change="onMaterialDeductionSizeChange"
            />
          </div>
        </section>

        <el-divider content-position="left">物料销售出仓（TASK-Y39B-P1-05）</el-divider>

        <section class="material-sales-outbound-section">
          <el-form :inline="true" :model="materialSalesOutboundQuery">
            <el-form-item label="款号">
              <el-input v-model="materialSalesOutboundQuery.item_code" clearable placeholder="请输入款号" />
            </el-form-item>
            <el-form-item label="出仓单号">
              <el-input v-model="materialSalesOutboundQuery.outbound_no" clearable placeholder="请输入出仓单号" />
            </el-form-item>
            <el-form-item label="关联销售单">
              <el-input v-model="materialSalesOutboundQuery.sales_order_no" clearable placeholder="请输入关联销售单" />
            </el-form-item>
            <el-form-item label="客户">
              <el-input v-model="materialSalesOutboundQuery.customer_name" clearable placeholder="请输入客户名称" />
            </el-form-item>
            <el-form-item label="出仓仓库">
              <el-select
                v-model="materialSalesOutboundQuery.warehouse_name"
                clearable
                placeholder="请选择出仓仓库"
                style="width: 170px"
                aria-label="物料销售出仓仓库筛选"
              >
                <el-option label="主料成品仓" value="主料成品仓" />
                <el-option label="辅料中转仓" value="辅料中转仓" />
                <el-option label="包材出货仓" value="包材出货仓" />
              </el-select>
            </el-form-item>
            <el-form-item label="物料编码">
              <el-input
                v-model="materialSalesOutboundQuery.material_item_code"
                clearable
                placeholder="请输入物料编码"
              />
            </el-form-item>
            <el-form-item label="出仓状态">
              <el-select
                v-model="materialSalesOutboundQuery.status"
                clearable
                placeholder="请选择出仓状态"
                style="width: 150px"
                aria-label="物料销售出仓状态筛选"
              >
                <el-option label="待出仓" value="待出仓" />
                <el-option label="已出仓" value="已出仓" />
                <el-option label="已关闭" value="已关闭" />
              </el-select>
            </el-form-item>
            <el-form-item label="审核状态">
              <el-select
                v-model="materialSalesOutboundQuery.audit_status"
                clearable
                placeholder="请选择审核状态"
                style="width: 150px"
                aria-label="物料销售出仓审核状态筛选"
              >
                <el-option label="待审核" value="待审核" />
                <el-option label="已审核" value="已审核" />
                <el-option label="已驳回" value="已驳回" />
              </el-select>
            </el-form-item>
            <el-form-item label="操作">
              <el-button type="primary" :disabled="!canRead" @click="loadMaterialSalesOutbound">查询</el-button>
              <el-button :disabled="!canRead" @click="resetMaterialSalesOutboundQuery">重置</el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-sales-outbound-confirm"
                @click="guardedReadonlyAction('出仓确认')"
              >
                出仓确认
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-sales-outbound-audit"
                @click="guardedReadonlyAction('审核通过')"
              >
                审核通过
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-sales-outbound-sync"
                @click="guardedReadonlyAction('同步')"
              >
                同步
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-sales-outbound-export"
                @click="guardedReadonlyAction('导出')"
              >
                导出
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-sales-outbound-print"
                @click="guardedReadonlyAction('打印')"
              >
                打印
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="materialSalesOutboundError"
            class="material-sales-outbound-error-alert"
            title="物料销售出仓加载失败"
            :description="materialSalesOutboundError"
            type="error"
            show-icon
            :closable="false"
          />

          <el-table
            class="material-sales-outbound-table"
            :data="materialSalesOutboundRows"
            v-loading="materialSalesOutboundLoading"
            border
            empty-text="暂无物料销售出仓数据"
          >
            <el-table-column prop="outbound_no" label="出仓单号" min-width="170" />
            <el-table-column prop="sales_order_no" label="关联销售单" min-width="180" />
            <el-table-column prop="customer_name" label="客户" min-width="150" />
            <el-table-column prop="warehouse_name" label="出仓仓库" min-width="130" />
            <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
            <el-table-column prop="material_name" label="物料名称" min-width="150" />
            <el-table-column prop="color" label="颜色" min-width="90" />
            <el-table-column prop="size" label="尺寸" min-width="90" />
            <el-table-column prop="batch_no" label="批次" min-width="140" />
            <el-table-column prop="planned_outbound_qty" label="应出数量" min-width="110" />
            <el-table-column prop="outbound_qty" label="已出数量" min-width="110" />
            <el-table-column prop="pending_outbound_qty" label="待出数量" min-width="110" />
            <el-table-column prop="outbound_date" label="出仓日期" min-width="120" />
            <el-table-column label="出仓状态" width="110">
              <template #default="scope">
                <el-tag :type="materialSalesOutboundStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="审核状态" width="110">
              <template #default="scope">
                <el-tag :type="materialSalesOutboundAuditTagType(scope.row.audit_status)">{{ scope.row.audit_status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="applicant_name" label="申请人" min-width="120" />
            <el-table-column prop="updated_at" label="最近更新时间" min-width="170" />
            <el-table-column prop="item_code" label="款号" min-width="120" />
            <el-table-column prop="bom_no" label="来源BOM" min-width="170" />
            <el-table-column label="操作" width="320" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="openMaterialSalesOutboundDetail(scope.row)">查看</el-button>
                <el-button link type="success" @click="guardedReadonlyAction('出仓确认')">出仓确认</el-button>
                <el-button link type="warning" @click="guardedReadonlyAction('审核通过')">审核通过</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('导出')">导出</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('打印')">打印</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager material-sales-outbound-pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="materialSalesOutboundQuery.page"
              :page-size="materialSalesOutboundQuery.page_size"
              :total="materialSalesOutboundTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onMaterialSalesOutboundPageChange"
              @size-change="onMaterialSalesOutboundSizeChange"
            />
          </div>
        </section>

        <el-divider content-position="left">物料类型（TASK-Y27B-P1-04）</el-divider>

        <section class="material-type-section">
          <el-form :inline="true" :model="materialTypeQuery">
            <el-form-item label="款号">
              <el-input v-model="materialTypeQuery.item_code" clearable placeholder="请输入款号" />
            </el-form-item>
            <el-form-item label="物料编码">
              <el-input v-model="materialTypeQuery.material_item_code" clearable placeholder="请输入物料编码" />
            </el-form-item>
            <el-form-item label="物料类型">
              <el-input v-model="materialTypeQuery.material_type_name" clearable placeholder="请输入物料类型" />
            </el-form-item>
            <el-form-item label="类型分组">
              <el-select
                v-model="materialTypeQuery.material_group"
                clearable
                placeholder="请选择类型分组"
                style="width: 170px"
                aria-label="物料类型分组筛选"
              >
                <el-option label="服装主材" value="服装主材" />
                <el-option label="包装物料" value="包装物料" />
                <el-option label="工艺物料" value="工艺物料" />
                <el-option label="通用物料" value="通用物料" />
              </el-select>
            </el-form-item>
            <el-form-item label="适用场景">
              <el-select
                v-model="materialTypeQuery.applicable_scene"
                clearable
                placeholder="请选择适用场景"
                style="width: 190px"
                aria-label="物料类型适用场景筛选"
              >
                <el-option label="裁片与主面生产" value="裁片与主面生产" />
                <el-option label="车缝与后道组装" value="车缝与后道组装" />
                <el-option label="包装与出库" value="包装与出库" />
                <el-option label="染整与后整" value="染整与后整" />
                <el-option label="通用生产环节" value="通用生产环节" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="materialTypeQuery.status"
                clearable
                placeholder="请选择状态"
                style="width: 150px"
                aria-label="物料类型状态筛选"
              >
                <el-option label="草稿" value="草稿" />
                <el-option label="可用" value="可用" />
                <el-option label="停用" value="停用" />
              </el-select>
            </el-form-item>
            <el-form-item label="操作">
              <el-button type="primary" :disabled="!canRead" @click="loadMaterialTypes">查询</el-button>
              <el-button :disabled="!canRead" @click="resetMaterialTypeQuery">重置</el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-type-create"
                @click="guardedReadonlyAction('新增类型')"
              >
                新增类型
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-type-edit"
                @click="guardedReadonlyAction('编辑')"
              >
                编辑
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-type-delete"
                @click="guardedReadonlyAction('删除')"
              >
                删除
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-type-export"
                @click="guardedReadonlyAction('导出')"
              >
                导出
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="materialTypeError"
            class="material-type-error-alert"
            title="物料类型加载失败"
            :description="materialTypeError"
            type="error"
            show-icon
            :closable="false"
          />

          <el-table
            class="material-type-table"
            :data="materialTypeRows"
            v-loading="materialTypeLoading"
            border
            empty-text="暂无物料类型数据"
          >
            <el-table-column prop="material_type_code" label="类型编码" min-width="130" />
            <el-table-column prop="material_type_name" label="类型名称" min-width="130" />
            <el-table-column prop="material_group" label="类型分组" min-width="120" />
            <el-table-column prop="applicable_scene" label="适用场景" min-width="150" />
            <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
            <el-table-column prop="supplier_name" label="供应商" min-width="150" />
            <el-table-column prop="item_code" label="款号" min-width="120" />
            <el-table-column prop="bom_no" label="来源BOM" min-width="170" />
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <el-tag :type="fabricStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="250" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="openMaterialTypeDetail(scope.row)">查看</el-button>
                <el-button link type="warning" @click="guardedReadonlyAction('编辑')">编辑</el-button>
                <el-button link type="danger" @click="guardedReadonlyAction('删除')">删除</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('导出')">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager material-type-pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="materialTypeQuery.page"
              :page-size="materialTypeQuery.page_size"
              :total="materialTypeTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onMaterialTypePageChange"
              @size-change="onMaterialTypeSizeChange"
            />
          </div>
        </section>

        <el-divider content-position="left">物料单位（TASK-Y27B-P1-05）</el-divider>

        <section class="material-unit-section">
          <el-form :inline="true" :model="materialUnitQuery">
            <el-form-item label="款号">
              <el-input v-model="materialUnitQuery.item_code" clearable placeholder="请输入款号" />
            </el-form-item>
            <el-form-item label="物料编码">
              <el-input v-model="materialUnitQuery.material_item_code" clearable placeholder="请输入物料编码" />
            </el-form-item>
            <el-form-item label="单位名称">
              <el-input v-model="materialUnitQuery.unit_name" clearable placeholder="请输入单位名称" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="materialUnitQuery.status"
                clearable
                placeholder="请选择状态"
                style="width: 150px"
                aria-label="物料单位状态筛选"
              >
                <el-option label="草稿" value="草稿" />
                <el-option label="可用" value="可用" />
                <el-option label="停用" value="停用" />
              </el-select>
            </el-form-item>
            <el-form-item label="操作">
              <el-button type="primary" :disabled="!canRead" @click="loadMaterialUnits">查询</el-button>
              <el-button :disabled="!canRead" @click="resetMaterialUnitQuery">重置</el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-unit-create"
                @click="guardedReadonlyAction('新增单位')"
              >
                新增单位
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-unit-edit"
                @click="guardedReadonlyAction('编辑')"
              >
                编辑
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-unit-disable"
                @click="guardedReadonlyAction('停用')"
              >
                停用
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-material-unit-export"
                @click="guardedReadonlyAction('导出')"
              >
                导出
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="materialUnitError"
            class="material-unit-error-alert"
            title="物料单位加载失败"
            :description="materialUnitError"
            type="error"
            show-icon
            :closable="false"
          />

          <el-table
            class="material-unit-table"
            :data="materialUnitRows"
            v-loading="materialUnitLoading"
            border
            empty-text="暂无物料单位数据"
          >
            <el-table-column prop="unit_code" label="单位编码" min-width="140" />
            <el-table-column prop="unit_name" label="单位名称" min-width="120" />
            <el-table-column prop="base_unit" label="基础单位" min-width="100" />
            <el-table-column prop="conversion_text" label="换算关系" min-width="180" />
            <el-table-column prop="precision" label="精度" min-width="80" />
            <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
            <el-table-column prop="item_code" label="款号" min-width="120" />
            <el-table-column prop="bom_no" label="来源BOM" min-width="170" />
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <el-tag :type="fabricStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="250" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="openMaterialUnitDetail(scope.row)">查看</el-button>
                <el-button link type="warning" @click="guardedReadonlyAction('编辑')">编辑</el-button>
                <el-button link type="danger" @click="guardedReadonlyAction('停用')">停用</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('导出')">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager material-unit-pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="materialUnitQuery.page"
              :page-size="materialUnitQuery.page_size"
              :total="materialUnitTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onMaterialUnitPageChange"
              @size-change="onMaterialUnitSizeChange"
            />
          </div>
        </section>

        <el-divider content-position="left">物料图库（TASK-Y22B-P1-01）</el-divider>

        <section class="material-gallery-section">
          <el-form :inline="true" :model="galleryQuery">
            <el-form-item label="物料分类">
              <el-select
                v-model="galleryQuery.category"
                clearable
                placeholder="请选择分类"
                style="width: 170px"
                aria-label="物料分类筛选"
              >
                <el-option v-for="category in galleryCategoryOptions" :key="category" :label="category" :value="category" />
              </el-select>
            </el-form-item>
            <el-form-item label="款号">
              <el-input v-model="galleryQuery.item_code" clearable placeholder="请输入款号" />
            </el-form-item>
            <el-form-item label="物料编码">
              <el-input v-model="galleryQuery.material_item_code" clearable placeholder="请输入物料编码" />
            </el-form-item>
            <el-form-item label="颜色">
              <el-input v-model="galleryQuery.color" clearable placeholder="请输入颜色" />
            </el-form-item>
            <el-form-item label="规格">
              <el-input v-model="galleryQuery.size" clearable placeholder="请输入规格" />
            </el-form-item>
            <el-form-item label="操作">
              <el-button type="primary" :disabled="!canRead" @click="loadGallery">查询</el-button>
              <el-button :disabled="!canRead" @click="resetGalleryQuery">重置</el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-gallery-choose"
                @click="guardedReadonlyAction('选用')"
              >
                选用
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-gallery-upload"
                @click="guardedReadonlyAction('上传')"
              >
                上传
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-gallery-edit"
                @click="guardedReadonlyAction('编辑')"
              >
                编辑
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-gallery-delete"
                @click="guardedReadonlyAction('删除')"
              >
                删除
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="galleryError"
            class="gallery-error-alert"
            title="物料图库加载失败"
            :description="galleryError"
            type="error"
            show-icon
            :closable="false"
          />

          <el-table
            class="material-gallery-table"
            :data="galleryRows"
            v-loading="galleryLoading"
            border
            empty-text="暂无物料图库数据"
          >
            <el-table-column label="素材" width="100">
              <template #default="scope">
                <div class="gallery-thumb">
                  <span>{{ materialThumbText(scope.row.material_item_code) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="category" label="物料分类" min-width="120" />
            <el-table-column prop="item_code" label="款号" min-width="130" />
            <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
            <el-table-column prop="color" label="颜色" min-width="100" />
            <el-table-column prop="size" label="规格" min-width="100" />
            <el-table-column prop="qty_per_piece" label="单件用量" min-width="100" />
            <el-table-column prop="loss_rate" label="损耗率" min-width="90" />
            <el-table-column prop="uom" label="单位" width="80" />
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <el-tag :type="statusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="bom_no" label="来源BOM" min-width="160" />
            <el-table-column label="操作" width="240" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="openGalleryPreview(scope.row)">查看</el-button>
                <el-button link type="warning" @click="guardedReadonlyAction('选用')">选用</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('上传')">上传</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('编辑')">编辑</el-button>
                <el-button link type="danger" @click="guardedReadonlyAction('删除')">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager gallery-pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="galleryQuery.page"
              :page-size="galleryQuery.page_size"
              :total="galleryTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onGalleryPageChange"
              @size-change="onGallerySizeChange"
            />
          </div>
        </section>

        <el-divider content-position="left">物料采购单（TASK-Y22B-P1-04）</el-divider>

        <section class="purchase-order-section">
          <el-form :inline="true" :model="purchaseQuery">
            <el-form-item label="采购单号">
              <el-input v-model="purchaseQuery.purchase_no" clearable placeholder="请输入采购单号" />
            </el-form-item>
            <el-form-item label="供应商">
              <el-input v-model="purchaseQuery.supplier_name" clearable placeholder="请输入供应商" />
            </el-form-item>
            <el-form-item label="物料">
              <el-input v-model="purchaseQuery.material_keyword" clearable placeholder="请输入物料编码/名称" />
            </el-form-item>
            <el-form-item label="交期">
              <el-date-picker
                v-model="purchaseQuery.delivery_date_range"
                type="daterange"
                unlink-panels
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="purchaseQuery.status"
                clearable
                placeholder="请选择状态"
                style="width: 150px"
                aria-label="采购单状态筛选"
              >
                <el-option label="草稿" value="草稿" />
                <el-option label="待确认" value="待确认" />
                <el-option label="已确认" value="已确认" />
                <el-option label="已取消" value="已取消" />
              </el-select>
            </el-form-item>
            <el-form-item label="数量区间">
              <el-input-number v-model="purchaseQuery.min_qty" :min="0" :controls="false" placeholder="最小数量" />
              <span class="range-sep">-</span>
              <el-input-number v-model="purchaseQuery.max_qty" :min="0" :controls="false" placeholder="最大数量" />
            </el-form-item>
            <el-form-item label="金额区间">
              <el-input-number v-model="purchaseQuery.min_amount" :min="0" :controls="false" placeholder="最小金额" />
              <span class="range-sep">-</span>
              <el-input-number v-model="purchaseQuery.max_amount" :min="0" :controls="false" placeholder="最大金额" />
            </el-form-item>
            <el-form-item label="操作">
              <el-button type="primary" :disabled="!canRead" @click="loadPurchaseOrders">查询</el-button>
              <el-button :disabled="!canRead" @click="resetPurchaseQuery">重置</el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-purchase-generate"
                @click="guardedReadonlyAction('生成采购')"
              >
                生成采购
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-purchase-confirm"
                @click="guardedReadonlyAction('确认')"
              >
                确认
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-purchase-cancel"
                @click="guardedReadonlyAction('取消')"
              >
                取消
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-purchase-export"
                @click="guardedReadonlyAction('导出')"
              >
                导出
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="purchaseError"
            class="purchase-error-alert"
            title="物料采购单加载失败"
            :description="purchaseError"
            type="error"
            show-icon
            :closable="false"
          />

          <el-table
            class="purchase-order-table"
            :data="purchaseRows"
            v-loading="purchaseLoading"
            border
            empty-text="暂无物料采购单数据"
          >
            <el-table-column prop="purchase_no" label="采购单号" min-width="220" />
            <el-table-column prop="supplier_name" label="供应商" min-width="160" />
            <el-table-column prop="item_code" label="款号" min-width="120" />
            <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
            <el-table-column prop="material_name" label="物料名称" min-width="150" />
            <el-table-column prop="qty" label="数量" min-width="100" />
            <el-table-column prop="uom" label="单位" width="80" />
            <el-table-column prop="unit_price" label="单价" min-width="110" />
            <el-table-column prop="total_amount" label="金额" min-width="120" />
            <el-table-column prop="expected_delivery_date" label="交期" min-width="120" />
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <el-tag :type="purchaseStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="270" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="openPurchaseDetail(scope.row)">查看</el-button>
                <el-button link type="warning" @click="guardedReadonlyAction('生成采购')">生成采购</el-button>
                <el-button link type="success" @click="guardedReadonlyAction('确认')">确认</el-button>
                <el-button link type="danger" @click="guardedReadonlyAction('取消')">取消</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('导出')">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager purchase-pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="purchaseQuery.page"
              :page-size="purchaseQuery.page_size"
              :total="purchaseTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onPurchasePageChange"
              @size-change="onPurchaseSizeChange"
            />
          </div>
        </section>
      </template>
    </el-card>

    <el-dialog v-model="previewVisible" title="物料图库预览" width="520px">
      <template v-if="previewRow">
        <div class="preview-grid">
          <div class="preview-thumb">{{ materialThumbText(previewRow.material_item_code) }}</div>
          <div class="preview-meta">
            <p>款号：{{ previewRow.item_code }}</p>
            <p>物料编码：{{ previewRow.material_item_code }}</p>
            <p>物料分类：{{ previewRow.category }}</p>
            <p>颜色/规格：{{ previewRow.color || '-' }} / {{ previewRow.size || '-' }}</p>
            <p>单件用量：{{ previewRow.qty_per_piece }} {{ previewRow.uom }}</p>
            <p>损耗率：{{ previewRow.loss_rate }}</p>
            <p>来源BOM：{{ previewRow.bom_no }}</p>
          </div>
        </div>
      </template>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchBomAccessoriesPackaging,
  fetchBomDetail,
  fetchBomFabrics,
  fetchBomList,
  fetchBomMaterialDeduction,
  fetchBomMaterialGallery,
  fetchBomMaterialProcessing,
  fetchBomMaterialProcessingInbound,
  fetchBomMaterialSalesOutbound,
  fetchBomMaterialTypes,
  fetchBomMaterialUnits,
  fetchBomProcessingTypes,
  fetchBomPurchaseOrders,
  type BomAccessoriesPackagingItem,
  type BomDetailData,
  type BomFabricItem,
  type BomListItem,
  type BomMaterialGalleryItem,
  type BomMaterialDeductionItem,
  type BomMaterialProcessingItem,
  type BomMaterialProcessingInboundItem,
  type BomMaterialSalesOutboundItem,
  type BomMaterialTypeItem,
  type BomMaterialUnitItem,
  type BomProcessingTypeItem,
  type BomPurchaseOrderItem,
} from '@/api/bom'
import { usePermissionStore } from '@/stores/permission'

const loading = ref<boolean>(false)
const rows = ref<BomListItem[]>([])
const total = ref<number>(0)
const listError = ref<string>('')
const bomDetailVisible = ref<boolean>(false)
const bomDetailLoading = ref<boolean>(false)
const bomDetailError = ref<string>('')
const bomDetail = ref<BomDetailData | null>(null)
const fabricLoading = ref<boolean>(false)
const fabricRows = ref<BomFabricItem[]>([])
const fabricTotal = ref<number>(0)
const fabricError = ref<string>('')
const accessoriesLoading = ref<boolean>(false)
const accessoriesRows = ref<BomAccessoriesPackagingItem[]>([])
const accessoriesTotal = ref<number>(0)
const accessoriesError = ref<string>('')
const processingTypeLoading = ref<boolean>(false)
const processingTypeRows = ref<BomProcessingTypeItem[]>([])
const processingTypeTotal = ref<number>(0)
const processingTypeError = ref<string>('')
const materialProcessingLoading = ref<boolean>(false)
const materialProcessingRows = ref<BomMaterialProcessingItem[]>([])
const materialProcessingTotal = ref<number>(0)
const materialProcessingError = ref<string>('')
const materialProcessingInboundLoading = ref<boolean>(false)
const materialProcessingInboundRows = ref<BomMaterialProcessingInboundItem[]>([])
const materialProcessingInboundTotal = ref<number>(0)
const materialProcessingInboundError = ref<string>('')
const materialDeductionLoading = ref<boolean>(false)
const materialDeductionRows = ref<BomMaterialDeductionItem[]>([])
const materialDeductionTotal = ref<number>(0)
const materialDeductionError = ref<string>('')
const materialSalesOutboundLoading = ref<boolean>(false)
const materialSalesOutboundRows = ref<BomMaterialSalesOutboundItem[]>([])
const materialSalesOutboundTotal = ref<number>(0)
const materialSalesOutboundError = ref<string>('')
const materialTypeLoading = ref<boolean>(false)
const materialTypeRows = ref<BomMaterialTypeItem[]>([])
const materialTypeTotal = ref<number>(0)
const materialTypeError = ref<string>('')
const materialUnitLoading = ref<boolean>(false)
const materialUnitRows = ref<BomMaterialUnitItem[]>([])
const materialUnitTotal = ref<number>(0)
const materialUnitError = ref<string>('')
const galleryLoading = ref<boolean>(false)
const galleryRows = ref<BomMaterialGalleryItem[]>([])
const galleryTotal = ref<number>(0)
const galleryError = ref<string>('')
const galleryCategoryOptions = ref<string[]>([])
const purchaseLoading = ref<boolean>(false)
const purchaseRows = ref<BomPurchaseOrderItem[]>([])
const purchaseTotal = ref<number>(0)
const purchaseError = ref<string>('')
const previewVisible = ref<boolean>(false)
const previewRow = ref<BomMaterialGalleryItem | null>(null)
const permissionStore = usePermissionStore()
const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const canCreate = computed<boolean>(() => permissionStore.state.buttonPermissions.create)

const query = reactive({
  item_code: '',
  status: '',
  page: 1,
  page_size: 20,
})

const fabricQuery = reactive({
  item_code: '',
  material_item_code: '',
  fabric_name: '',
  color: '',
  specification: '',
  supplier_name: '',
  status: '',
  page: 1,
  page_size: 20,
})

const accessoriesQuery = reactive({
  item_code: '',
  material_item_code: '',
  material_name: '',
  category: '',
  supplier_name: '',
  status: '',
  page: 1,
  page_size: 20,
})

const processingTypeQuery = reactive({
  item_code: '',
  process_type_name: '',
  process_name: '',
  subcontract_mode: '',
  pricing_mode: '',
  status: '',
  page: 1,
  page_size: 20,
})

const materialProcessingQuery = reactive({
  item_code: '',
  process_no: '',
  process_name: '',
  processing_supplier: '',
  processing_mode: '',
  status: '',
  page: 1,
  page_size: 20,
})

const materialProcessingInboundQuery = reactive({
  item_code: '',
  inbound_no: '',
  material_item_code: '',
  processing_supplier: '',
  warehouse_name: '',
  status: '',
  page: 1,
  page_size: 20,
})

const materialDeductionQuery = reactive({
  item_code: '',
  deduction_no: '',
  material_item_code: '',
  warehouse_name: '',
  status: '',
  page: 1,
  page_size: 20,
})

const materialSalesOutboundQuery = reactive({
  item_code: '',
  outbound_no: '',
  sales_order_no: '',
  customer_name: '',
  warehouse_name: '',
  material_item_code: '',
  status: '',
  audit_status: '',
  page: 1,
  page_size: 20,
})

const materialTypeQuery = reactive({
  item_code: '',
  material_item_code: '',
  material_type_name: '',
  material_group: '',
  applicable_scene: '',
  status: '',
  page: 1,
  page_size: 20,
})

const materialUnitQuery = reactive({
  item_code: '',
  material_item_code: '',
  unit_name: '',
  status: '',
  page: 1,
  page_size: 20,
})

const galleryQuery = reactive({
  item_code: '',
  material_item_code: '',
  color: '',
  size: '',
  category: '',
  status: '',
  page: 1,
  page_size: 20,
})

const purchaseQuery = reactive({
  purchase_no: '',
  supplier_name: '',
  material_keyword: '',
  status: '',
  delivery_date_range: [] as string[],
  min_qty: undefined as number | undefined,
  max_qty: undefined as number | undefined,
  min_amount: undefined as number | undefined,
  max_amount: undefined as number | undefined,
  page: 1,
  page_size: 20,
})

const loadList = async (): Promise<void> => {
  if (!canRead.value) {
    rows.value = []
    total.value = 0
    listError.value = ''
    return
  }
  loading.value = true
  listError.value = ''
  try {
    const result = await fetchBomList(query)
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    rows.value = []
    total.value = 0
    listError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const runMainQuery = (): void => {
  query.page = 1
  loadList()
}

const resetMainQuery = (): void => {
  query.item_code = ''
  query.status = ''
  query.page = 1
  query.page_size = 20
  loadList()
}

const onPageChange = (page: number): void => {
  query.page = page
  loadList()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  loadList()
}

const loadFabrics = async (): Promise<void> => {
  if (!canRead.value) {
    fabricRows.value = []
    fabricTotal.value = 0
    fabricError.value = ''
    return
  }
  fabricLoading.value = true
  fabricError.value = ''
  try {
    const result = await fetchBomFabrics(fabricQuery)
    fabricRows.value = result.data.items
    fabricTotal.value = result.data.total
  } catch (error) {
    fabricRows.value = []
    fabricTotal.value = 0
    fabricError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    fabricLoading.value = false
  }
}

const resetFabricQuery = (): void => {
  fabricQuery.item_code = ''
  fabricQuery.material_item_code = ''
  fabricQuery.fabric_name = ''
  fabricQuery.color = ''
  fabricQuery.specification = ''
  fabricQuery.supplier_name = ''
  fabricQuery.status = ''
  fabricQuery.page = 1
  fabricQuery.page_size = 20
  loadFabrics()
}

const onFabricPageChange = (page: number): void => {
  fabricQuery.page = page
  loadFabrics()
}

const onFabricSizeChange = (size: number): void => {
  fabricQuery.page_size = size
  fabricQuery.page = 1
  loadFabrics()
}

const fabricStatusTagType = (status: string): 'success' | 'warning' | 'info' => {
  if (status === '可用') return 'success'
  if (status === '停用') return 'warning'
  return 'info'
}

const loadAccessoriesPackaging = async (): Promise<void> => {
  if (!canRead.value) {
    accessoriesRows.value = []
    accessoriesTotal.value = 0
    accessoriesError.value = ''
    return
  }
  accessoriesLoading.value = true
  accessoriesError.value = ''
  try {
    const result = await fetchBomAccessoriesPackaging(accessoriesQuery)
    accessoriesRows.value = result.data.items
    accessoriesTotal.value = result.data.total
  } catch (error) {
    accessoriesRows.value = []
    accessoriesTotal.value = 0
    accessoriesError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    accessoriesLoading.value = false
  }
}

const resetAccessoriesQuery = (): void => {
  accessoriesQuery.item_code = ''
  accessoriesQuery.material_item_code = ''
  accessoriesQuery.material_name = ''
  accessoriesQuery.category = ''
  accessoriesQuery.supplier_name = ''
  accessoriesQuery.status = ''
  accessoriesQuery.page = 1
  accessoriesQuery.page_size = 20
  loadAccessoriesPackaging()
}

const onAccessoriesPageChange = (page: number): void => {
  accessoriesQuery.page = page
  loadAccessoriesPackaging()
}

const onAccessoriesSizeChange = (size: number): void => {
  accessoriesQuery.page_size = size
  accessoriesQuery.page = 1
  loadAccessoriesPackaging()
}

const loadProcessingTypes = async (): Promise<void> => {
  if (!canRead.value) {
    processingTypeRows.value = []
    processingTypeTotal.value = 0
    processingTypeError.value = ''
    return
  }
  processingTypeLoading.value = true
  processingTypeError.value = ''
  try {
    const result = await fetchBomProcessingTypes(processingTypeQuery)
    processingTypeRows.value = result.data.items
    processingTypeTotal.value = result.data.total
  } catch (error) {
    processingTypeRows.value = []
    processingTypeTotal.value = 0
    processingTypeError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    processingTypeLoading.value = false
  }
}

const resetProcessingTypeQuery = (): void => {
  processingTypeQuery.item_code = ''
  processingTypeQuery.process_type_name = ''
  processingTypeQuery.process_name = ''
  processingTypeQuery.subcontract_mode = ''
  processingTypeQuery.pricing_mode = ''
  processingTypeQuery.status = ''
  processingTypeQuery.page = 1
  processingTypeQuery.page_size = 20
  loadProcessingTypes()
}

const onProcessingTypePageChange = (page: number): void => {
  processingTypeQuery.page = page
  loadProcessingTypes()
}

const onProcessingTypeSizeChange = (size: number): void => {
  processingTypeQuery.page_size = size
  processingTypeQuery.page = 1
  loadProcessingTypes()
}

const loadMaterialProcessing = async (): Promise<void> => {
  if (!canRead.value) {
    materialProcessingRows.value = []
    materialProcessingTotal.value = 0
    materialProcessingError.value = ''
    return
  }
  materialProcessingLoading.value = true
  materialProcessingError.value = ''
  try {
    const result = await fetchBomMaterialProcessing(materialProcessingQuery)
    materialProcessingRows.value = result.data.items
    materialProcessingTotal.value = result.data.total
  } catch (error) {
    materialProcessingRows.value = []
    materialProcessingTotal.value = 0
    materialProcessingError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    materialProcessingLoading.value = false
  }
}

const resetMaterialProcessingQuery = (): void => {
  materialProcessingQuery.item_code = ''
  materialProcessingQuery.process_no = ''
  materialProcessingQuery.process_name = ''
  materialProcessingQuery.processing_supplier = ''
  materialProcessingQuery.processing_mode = ''
  materialProcessingQuery.status = ''
  materialProcessingQuery.page = 1
  materialProcessingQuery.page_size = 20
  loadMaterialProcessing()
}

const onMaterialProcessingPageChange = (page: number): void => {
  materialProcessingQuery.page = page
  loadMaterialProcessing()
}

const onMaterialProcessingSizeChange = (size: number): void => {
  materialProcessingQuery.page_size = size
  materialProcessingQuery.page = 1
  loadMaterialProcessing()
}

const loadMaterialProcessingInbound = async (): Promise<void> => {
  if (!canRead.value) {
    materialProcessingInboundRows.value = []
    materialProcessingInboundTotal.value = 0
    materialProcessingInboundError.value = ''
    return
  }
  materialProcessingInboundLoading.value = true
  materialProcessingInboundError.value = ''
  try {
    const result = await fetchBomMaterialProcessingInbound(materialProcessingInboundQuery)
    materialProcessingInboundRows.value = result.data.items
    materialProcessingInboundTotal.value = result.data.total
  } catch (error) {
    materialProcessingInboundRows.value = []
    materialProcessingInboundTotal.value = 0
    materialProcessingInboundError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    materialProcessingInboundLoading.value = false
  }
}

const resetMaterialProcessingInboundQuery = (): void => {
  materialProcessingInboundQuery.item_code = ''
  materialProcessingInboundQuery.inbound_no = ''
  materialProcessingInboundQuery.material_item_code = ''
  materialProcessingInboundQuery.processing_supplier = ''
  materialProcessingInboundQuery.warehouse_name = ''
  materialProcessingInboundQuery.status = ''
  materialProcessingInboundQuery.page = 1
  materialProcessingInboundQuery.page_size = 20
  loadMaterialProcessingInbound()
}

const onMaterialProcessingInboundPageChange = (page: number): void => {
  materialProcessingInboundQuery.page = page
  loadMaterialProcessingInbound()
}

const onMaterialProcessingInboundSizeChange = (size: number): void => {
  materialProcessingInboundQuery.page_size = size
  materialProcessingInboundQuery.page = 1
  loadMaterialProcessingInbound()
}

const materialProcessingInboundStatusTagType = (status: string): 'success' | 'warning' | 'info' => {
  if (status === '已入仓') return 'success'
  if (status === '已关闭') return 'warning'
  return 'info'
}

const loadMaterialDeduction = async (): Promise<void> => {
  if (!canRead.value) {
    materialDeductionRows.value = []
    materialDeductionTotal.value = 0
    materialDeductionError.value = ''
    return
  }
  materialDeductionLoading.value = true
  materialDeductionError.value = ''
  try {
    const result = await fetchBomMaterialDeduction(materialDeductionQuery)
    materialDeductionRows.value = result.data.items
    materialDeductionTotal.value = result.data.total
  } catch (error) {
    materialDeductionRows.value = []
    materialDeductionTotal.value = 0
    materialDeductionError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    materialDeductionLoading.value = false
  }
}

const resetMaterialDeductionQuery = (): void => {
  materialDeductionQuery.item_code = ''
  materialDeductionQuery.deduction_no = ''
  materialDeductionQuery.material_item_code = ''
  materialDeductionQuery.warehouse_name = ''
  materialDeductionQuery.status = ''
  materialDeductionQuery.page = 1
  materialDeductionQuery.page_size = 20
  loadMaterialDeduction()
}

const onMaterialDeductionPageChange = (page: number): void => {
  materialDeductionQuery.page = page
  loadMaterialDeduction()
}

const onMaterialDeductionSizeChange = (size: number): void => {
  materialDeductionQuery.page_size = size
  materialDeductionQuery.page = 1
  loadMaterialDeduction()
}

const materialDeductionStatusTagType = (status: string): 'success' | 'warning' | 'info' => {
  if (status === '已扣仓') return 'success'
  if (status === '已关闭') return 'warning'
  return 'info'
}

const loadMaterialSalesOutbound = async (): Promise<void> => {
  if (!canRead.value) {
    materialSalesOutboundRows.value = []
    materialSalesOutboundTotal.value = 0
    materialSalesOutboundError.value = ''
    return
  }
  materialSalesOutboundLoading.value = true
  materialSalesOutboundError.value = ''
  try {
    const result = await fetchBomMaterialSalesOutbound(materialSalesOutboundQuery)
    materialSalesOutboundRows.value = result.data.items
    materialSalesOutboundTotal.value = result.data.total
  } catch (error) {
    materialSalesOutboundRows.value = []
    materialSalesOutboundTotal.value = 0
    materialSalesOutboundError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    materialSalesOutboundLoading.value = false
  }
}

const resetMaterialSalesOutboundQuery = (): void => {
  materialSalesOutboundQuery.item_code = ''
  materialSalesOutboundQuery.outbound_no = ''
  materialSalesOutboundQuery.sales_order_no = ''
  materialSalesOutboundQuery.customer_name = ''
  materialSalesOutboundQuery.warehouse_name = ''
  materialSalesOutboundQuery.material_item_code = ''
  materialSalesOutboundQuery.status = ''
  materialSalesOutboundQuery.audit_status = ''
  materialSalesOutboundQuery.page = 1
  materialSalesOutboundQuery.page_size = 20
  loadMaterialSalesOutbound()
}

const onMaterialSalesOutboundPageChange = (page: number): void => {
  materialSalesOutboundQuery.page = page
  loadMaterialSalesOutbound()
}

const onMaterialSalesOutboundSizeChange = (size: number): void => {
  materialSalesOutboundQuery.page_size = size
  materialSalesOutboundQuery.page = 1
  loadMaterialSalesOutbound()
}

const materialSalesOutboundStatusTagType = (status: string): 'success' | 'warning' | 'info' => {
  if (status === '已出仓') return 'success'
  if (status === '已关闭') return 'warning'
  return 'info'
}

const materialSalesOutboundAuditTagType = (status: string): 'success' | 'warning' | 'info' => {
  if (status === '已审核') return 'success'
  if (status === '已驳回') return 'warning'
  return 'info'
}

const loadMaterialTypes = async (): Promise<void> => {
  if (!canRead.value) {
    materialTypeRows.value = []
    materialTypeTotal.value = 0
    materialTypeError.value = ''
    return
  }
  materialTypeLoading.value = true
  materialTypeError.value = ''
  try {
    const result = await fetchBomMaterialTypes(materialTypeQuery)
    materialTypeRows.value = result.data.items
    materialTypeTotal.value = result.data.total
  } catch (error) {
    materialTypeRows.value = []
    materialTypeTotal.value = 0
    materialTypeError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    materialTypeLoading.value = false
  }
}

const resetMaterialTypeQuery = (): void => {
  materialTypeQuery.item_code = ''
  materialTypeQuery.material_item_code = ''
  materialTypeQuery.material_type_name = ''
  materialTypeQuery.material_group = ''
  materialTypeQuery.applicable_scene = ''
  materialTypeQuery.status = ''
  materialTypeQuery.page = 1
  materialTypeQuery.page_size = 20
  loadMaterialTypes()
}

const onMaterialTypePageChange = (page: number): void => {
  materialTypeQuery.page = page
  loadMaterialTypes()
}

const onMaterialTypeSizeChange = (size: number): void => {
  materialTypeQuery.page_size = size
  materialTypeQuery.page = 1
  loadMaterialTypes()
}

const loadMaterialUnits = async (): Promise<void> => {
  if (!canRead.value) {
    materialUnitRows.value = []
    materialUnitTotal.value = 0
    materialUnitError.value = ''
    return
  }
  materialUnitLoading.value = true
  materialUnitError.value = ''
  try {
    const result = await fetchBomMaterialUnits(materialUnitQuery)
    materialUnitRows.value = result.data.items
    materialUnitTotal.value = result.data.total
  } catch (error) {
    materialUnitRows.value = []
    materialUnitTotal.value = 0
    materialUnitError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    materialUnitLoading.value = false
  }
}

const resetMaterialUnitQuery = (): void => {
  materialUnitQuery.item_code = ''
  materialUnitQuery.material_item_code = ''
  materialUnitQuery.unit_name = ''
  materialUnitQuery.status = ''
  materialUnitQuery.page = 1
  materialUnitQuery.page_size = 20
  loadMaterialUnits()
}

const onMaterialUnitPageChange = (page: number): void => {
  materialUnitQuery.page = page
  loadMaterialUnits()
}

const onMaterialUnitSizeChange = (size: number): void => {
  materialUnitQuery.page_size = size
  materialUnitQuery.page = 1
  loadMaterialUnits()
}

const loadGallery = async (): Promise<void> => {
  if (!canRead.value) {
    galleryRows.value = []
    galleryTotal.value = 0
    galleryError.value = ''
    return
  }
  galleryLoading.value = true
  galleryError.value = ''
  try {
    const result = await fetchBomMaterialGallery(galleryQuery)
    galleryRows.value = result.data.items
    galleryTotal.value = result.data.total
    galleryCategoryOptions.value = Array.from(
      new Set(result.data.items.map((item) => item.category).filter((category) => category)),
    )
  } catch (error) {
    galleryRows.value = []
    galleryTotal.value = 0
    galleryError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    galleryLoading.value = false
  }
}

const onGalleryPageChange = (page: number): void => {
  galleryQuery.page = page
  loadGallery()
}

const onGallerySizeChange = (size: number): void => {
  galleryQuery.page_size = size
  galleryQuery.page = 1
  loadGallery()
}

const loadPurchaseOrders = async (): Promise<void> => {
  if (!canRead.value) {
    purchaseRows.value = []
    purchaseTotal.value = 0
    purchaseError.value = ''
    return
  }
  purchaseLoading.value = true
  purchaseError.value = ''
  try {
    const [deliveryDateFrom, deliveryDateTo] = purchaseQuery.delivery_date_range
    const result = await fetchBomPurchaseOrders({
      purchase_no: purchaseQuery.purchase_no,
      supplier_name: purchaseQuery.supplier_name,
      material_keyword: purchaseQuery.material_keyword,
      status: purchaseQuery.status,
      delivery_date_from: deliveryDateFrom || undefined,
      delivery_date_to: deliveryDateTo || undefined,
      min_qty: purchaseQuery.min_qty,
      max_qty: purchaseQuery.max_qty,
      min_amount: purchaseQuery.min_amount,
      max_amount: purchaseQuery.max_amount,
      page: purchaseQuery.page,
      page_size: purchaseQuery.page_size,
    })
    purchaseRows.value = result.data.items
    purchaseTotal.value = result.data.total
  } catch (error) {
    purchaseRows.value = []
    purchaseTotal.value = 0
    purchaseError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    purchaseLoading.value = false
  }
}

const resetPurchaseQuery = (): void => {
  purchaseQuery.purchase_no = ''
  purchaseQuery.supplier_name = ''
  purchaseQuery.material_keyword = ''
  purchaseQuery.status = ''
  purchaseQuery.delivery_date_range = []
  purchaseQuery.min_qty = undefined
  purchaseQuery.max_qty = undefined
  purchaseQuery.min_amount = undefined
  purchaseQuery.max_amount = undefined
  purchaseQuery.page = 1
  purchaseQuery.page_size = 20
  loadPurchaseOrders()
}

const onPurchasePageChange = (page: number): void => {
  purchaseQuery.page = page
  loadPurchaseOrders()
}

const onPurchaseSizeChange = (size: number): void => {
  purchaseQuery.page_size = size
  purchaseQuery.page = 1
  loadPurchaseOrders()
}

const purchaseStatusTagType = (status: string): 'success' | 'warning' | 'info' => {
  if (status === '已确认') return 'success'
  if (status === '已取消') return 'warning'
  return 'info'
}

const resetGalleryQuery = (): void => {
  galleryQuery.item_code = ''
  galleryQuery.material_item_code = ''
  galleryQuery.color = ''
  galleryQuery.size = ''
  galleryQuery.category = ''
  galleryQuery.status = ''
  galleryQuery.page = 1
  galleryQuery.page_size = 20
  loadGallery()
}

const statusTagType = (status: string): 'success' | 'info' | 'warning' => {
  if (status === 'active') return 'success'
  if (status === 'inactive') return 'warning'
  return 'info'
}

const materialThumbText = (materialItemCode: string): string => {
  const tokens = materialItemCode.split(/[-_]/).filter(Boolean)
  return (tokens[0] || 'IMG').slice(0, 3).toUpperCase()
}

const openGalleryPreview = (row: BomMaterialGalleryItem): void => {
  previewRow.value = row
  previewVisible.value = true
}

const guardedReadonlyAction = (action: string): void => {
  ElMessage.warning(`${action}功能受控：当前仅开放只读演示`)
}

const openBomDetail = async (id: number): Promise<void> => {
  if (!canRead.value) {
    ElMessage.warning('无 BOM 查看权限')
    return
  }
  bomDetailVisible.value = true
  bomDetailLoading.value = true
  bomDetailError.value = ''
  bomDetail.value = null
  try {
    const result = await fetchBomDetail(id)
    bomDetail.value = result.data
  } catch (error) {
    bomDetailError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    bomDetailLoading.value = false
  }
}

const goDetail = (id: number): void => {
  void openBomDetail(id)
}

const goCreate = (): void => {
  if (!canCreate.value) {
    ElMessage.warning('无新建 BOM 权限')
    return
  }
  guardedReadonlyAction('新建 BOM')
}

const openFabricDetail = (row: BomFabricItem): void => {
  goDetail(row.bom_id)
}

const openAccessoriesDetail = (row: BomAccessoriesPackagingItem): void => {
  goDetail(row.bom_id)
}

const openProcessingTypeDetail = (row: BomProcessingTypeItem): void => {
  goDetail(row.bom_id)
}

const openMaterialProcessingDetail = (row: BomMaterialProcessingItem): void => {
  goDetail(row.bom_id)
}

const openMaterialProcessingInboundDetail = (row: BomMaterialProcessingInboundItem): void => {
  goDetail(row.bom_id)
}

const openMaterialDeductionDetail = (row: BomMaterialDeductionItem): void => {
  goDetail(row.bom_id)
}

const openMaterialSalesOutboundDetail = (row: BomMaterialSalesOutboundItem): void => {
  goDetail(row.bom_id)
}

const openMaterialTypeDetail = (row: BomMaterialTypeItem): void => {
  goDetail(row.bom_id)
}

const openMaterialUnitDetail = (row: BomMaterialUnitItem): void => {
  goDetail(row.bom_id)
}

const openPurchaseDetail = (row: BomPurchaseOrderItem): void => {
  goDetail(row.bom_id)
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('bom')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
  await loadList()
  await loadFabrics()
  await loadAccessoriesPackaging()
  await loadProcessingTypes()
  await loadMaterialProcessing()
  await loadMaterialProcessingInbound()
  await loadMaterialDeduction()
  await loadMaterialSalesOutbound()
  await loadMaterialTypes()
  await loadMaterialUnits()
  await loadGallery()
  await loadPurchaseOrders()
})
</script>

<style scoped>
.bom-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.main-list-error-alert {
  margin-bottom: 12px;
}

.fabric-section {
  margin-top: 8px;
}

.accessories-packaging-section {
  margin-top: 8px;
}

.processing-type-section {
  margin-top: 8px;
}

.material-processing-section {
  margin-top: 8px;
}

.material-processing-inbound-section {
  margin-top: 8px;
}

.material-deduction-section {
  margin-top: 8px;
}

.material-sales-outbound-section {
  margin-top: 8px;
}

.material-type-section {
  margin-top: 8px;
}

.material-unit-section {
  margin-top: 8px;
}

.material-gallery-section {
  margin-top: 8px;
}

.purchase-order-section {
  margin-top: 8px;
}

.gallery-pager {
  margin-top: 10px;
}

.fabric-pager {
  margin-top: 10px;
}

.accessories-pager {
  margin-top: 10px;
}

.processing-type-pager {
  margin-top: 10px;
}

.material-processing-pager {
  margin-top: 10px;
}

.material-processing-inbound-pager {
  margin-top: 10px;
}

.material-deduction-pager {
  margin-top: 10px;
}

.material-sales-outbound-pager {
  margin-top: 10px;
}

.material-type-pager {
  margin-top: 10px;
}

.material-unit-pager {
  margin-top: 10px;
}

.purchase-pager {
  margin-top: 10px;
}

.range-sep {
  margin: 0 6px;
  color: var(--el-text-color-secondary);
}

.gallery-thumb {
  width: 52px;
  height: 52px;
  border-radius: 8px;
  border: 1px solid var(--el-border-color);
  background: var(--el-fill-color-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.gallery-error-alert {
  margin-bottom: 12px;
}

.fabric-error-alert {
  margin-bottom: 12px;
}

.accessories-error-alert {
  margin-bottom: 12px;
}

.processing-type-error-alert {
  margin-bottom: 12px;
}

.material-processing-error-alert {
  margin-bottom: 12px;
}

.material-processing-inbound-error-alert {
  margin-bottom: 12px;
}

.material-deduction-error-alert {
  margin-bottom: 12px;
}

.material-sales-outbound-error-alert {
  margin-bottom: 12px;
}

.material-type-error-alert {
  margin-bottom: 12px;
}

.material-unit-error-alert {
  margin-bottom: 12px;
}

.purchase-error-alert {
  margin-bottom: 12px;
}

.bom-detail-readonly-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bom-detail-header {
  margin-bottom: 4px;
}

.bom-detail-error-alert {
  margin-bottom: 4px;
}

.preview-grid {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 12px;
  align-items: start;
}

.preview-thumb {
  width: 120px;
  height: 120px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-fill-color-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: var(--el-text-color-secondary);
}

.preview-meta p {
  margin: 0 0 6px;
}
</style>
