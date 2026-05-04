<template>
  <div class="bom-list-page">
    <el-card shadow="never">
      <el-form :inline="true" :model="query">
        <el-form-item label="款式编码">
          <el-input v-model="query.item_code" clearable placeholder="Item Code" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="query.status"
            clearable
            placeholder="请选择状态"
            aria-label="BOM状态筛选"
            style="width: 160px"
          >
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="active" />
            <el-option label="已停用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadList">查询</el-button>
          <el-button
            v-if="canCreate"
            data-action-type="write"
            data-write-guard="permission:create(v-if)"
            data-guard-state="visible_when_allowed"
            @click="goCreate"
          >
            新建 BOM
          </el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无 BOM 查看权限" />
      <template v-else>
        <el-table :data="rows" v-loading="loading" border empty-text="暂无BOM数据" class="bom-main-table">
          <el-table-column prop="bom_no" label="BOM编号" min-width="280" />
          <el-table-column prop="item_code" label="款式编码" min-width="140" />
          <el-table-column prop="version_no" label="版本" min-width="100" />
          <el-table-column prop="status" label="状态" width="120" />
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
              <el-button link type="primary" @click="goDetail(scope.row.id)">详情</el-button>
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
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchBomAccessoriesPackaging,
  fetchBomFabrics,
  fetchBomList,
  fetchBomMaterialGallery,
  fetchBomMaterialTypes,
  fetchBomMaterialUnits,
  fetchBomProcessingTypes,
  fetchBomPurchaseOrders,
  type BomAccessoriesPackagingItem,
  type BomFabricItem,
  type BomListItem,
  type BomMaterialGalleryItem,
  type BomMaterialTypeItem,
  type BomMaterialUnitItem,
  type BomProcessingTypeItem,
  type BomPurchaseOrderItem,
} from '@/api/bom'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const loading = ref<boolean>(false)
const rows = ref<BomListItem[]>([])
const total = ref<number>(0)
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
    return
  }
  loading.value = true
  try {
    const result = await fetchBomList(query)
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
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

const goDetail = (id: number): void => {
  router.push({ path: '/bom/detail', query: { id: String(id) } })
}

const goCreate = (): void => {
  if (!canCreate.value) {
    ElMessage.warning('无新建 BOM 权限')
    return
  }
  router.push('/bom/detail')
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

.fabric-section {
  margin-top: 8px;
}

.accessories-packaging-section {
  margin-top: 8px;
}

.processing-type-section {
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

.material-type-error-alert {
  margin-bottom: 12px;
}

.material-unit-error-alert {
  margin-bottom: 12px;
}

.purchase-error-alert {
  margin-bottom: 12px;
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
