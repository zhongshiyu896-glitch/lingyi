# TASK-011 销售/库存只读集成设计

- 模块：销售/库存只读集成
- 版本：V1.0（设计冻结）
- 更新时间：2026-04-16
- 前置：TASK-010F 审计通过（HEAD `8575b48b8f63217c54886f2b5ac8f4bb557081bf`）
- 适用范围：TASK-011B 实现阶段与后续 TASK-012 复用

## 一、目标与边界

### 1.1 目标
冻结销售/库存只读集成的统一架构边界、API 契约、权限边界、ERPNext fail-closed 接入方式和前端只读门禁要求，作为 TASK-011B 工程实现的唯一设计基线。

### 1.2 任务边界
1. TASK-011 仅做销售/库存只读集成。
2. 不新增任何写操作、不新增 outbox 写入、不落地业务事实写入。
3. 不进入前端页面实现（前端页面归后续任务）。

### 1.3 权威来源
1. ERPNext 是销售/库存业务事实唯一权威来源。
2. FastAPI 只做只读聚合、权限过滤与错误信封归一。
3. Vue3 仅消费只读 API 并接受前端门禁约束。

## 二、系统边界与架构职责

### 2.1 系统边界
1. ERPNext：提供 Sales Order、Delivery Note、Stock Ledger Entry、Item、Warehouse、Customer 只读事实。
2. FastAPI：提供 `/api/sales-inventory/*` 聚合查询，不执行 ERPNext 写调用。
3. 前端：只读展示与导出，不暴露写动作。

### 2.2 明确禁止能力
以下能力在 TASK-011 全部禁止：
1. 创建/修改 Sales Order。
2. 提交 Delivery Note。
3. 创建/修改 Stock Entry。
4. 修改 Item/Warehouse/Customer。
5. 调用任何 ERPNext 写 API。
6. 写入任何 outbox。
7. Payment/GL/Purchase Invoice 相关逻辑。

## 三、只读接口清单（冻结）

| 接口名称 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 销售订单列表 | GET | `/api/sales-inventory/sales-orders` | 只读查询销售订单 |
| 销售订单详情 | GET | `/api/sales-inventory/sales-orders/{name}` | 只读查询销售订单明细 |
| 款式库存汇总 | GET | `/api/sales-inventory/items/{item_code}/stock-summary` | 按仓库聚合库存 |
| 库存流水 | GET | `/api/sales-inventory/items/{item_code}/stock-ledger` | 查询 SLE 流水 |
| 仓库列表 | GET | `/api/sales-inventory/warehouses` | 只读仓库资料 |
| 客户列表 | GET | `/api/sales-inventory/customers` | 只读客户资料 |

### 3.1 返回语义
1. 列表接口统一支持分页参数（`page`、`page_size`）。
2. 详情接口返回单据主体 + 行项目（如适用）。
3. 不返回 ERPNext 原始响应，必须转为本地规范结构。

## 四、权限动作与资源权限（冻结）

### 4.1 动作权限
使用 TASK-007 公共权限命名：

| 动作 | 说明 |
|---|---|
| `sales_inventory:read` | 读取销售/库存聚合数据 |
| `sales_inventory:export` | 导出销售/库存只读报表 |
| `sales_inventory:diagnostic` | 诊断 ERPNext 只读连接（普通用户禁用） |

### 4.2 资源权限字段
最小资源维度：
1. `company`
2. `item_code`
3. `warehouse`
4. `sales_order`
5. `customer`

### 4.3 校验顺序（强制）
1. 先认证（current_user）。
2. 再动作权限（`sales_inventory:*`）。
3. 再资源读取与资源权限校验。
4. 最后进入聚合逻辑。

### 4.4 防枚举规则
1. 详情接口必须先动作权限再查询资源。
2. 无权限场景不得通过 403/404 差异泄露资源存在性。
3. 权限源不可用必须 fail closed。

## 五、ERPNext Fail-Closed Adapter 接入（引用 TASK-008）

### 5.1 统一错误语义
1. timeout/连接失败/ERPNext 5xx：`EXTERNAL_SERVICE_UNAVAILABLE`。
2. ERPNext 401/403：`EXTERNAL_SERVICE_UNAVAILABLE` 或明确业务错误（禁止伪成功）。
3. malformed response：fail closed（`ERPNEXT_RESPONSE_INVALID`）。

### 5.2 单据字段校验
1. Sales Order / Delivery Note 必须校验 `docstatus`。
2. `docstatus` 缺失必须 fail closed。
3. `docstatus=0` draft 不得视为已提交流程事实。
4. `docstatus=2` cancelled 不得视为有效业务事实。

### 5.3 SLE 字段完整性校验
Stock Ledger Entry 缺少以下任一字段必须丢弃并记失败（不得纳入结果）：
1. `company`
2. `item_code`
3. `warehouse`
4. `posting_date`
5. `actual_qty`
6. `qty_after_transaction`

## 六、前端只读门禁接入（引用 TASK-010）

### 6.1 模块配置
1. 模块名：`sales_inventory`。
2. 必须接入 `frontend-contract-engine`。
3. 必须声明：
   - `fixture.positive`
   - `fixture.negative`

### 6.2 前端禁线
1. 禁止 POST/PUT/PATCH/DELETE。
2. 禁止 `/api/resource` 直连。
3. 禁止 internal API。
4. 禁止写语义按钮：`生成/同步/提交/取消/重算` 等。
5. 禁止裸 `fetch`/`axios` 绕过统一 request 封装。

## 七、错误信封规范（冻结）

### 7.1 失败信封
```json
{
  "code": "ERROR_CODE",
  "message": "可读错误信息",
  "data": null
}
```

### 7.2 成功分页信封
```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "items": [],
    "total": 0,
    "page": 1,
    "page_size": 20
  }
}
```

## 八、审计要求（冻结）

### 8.1 安全审计事件
必须覆盖：
1. 未认证。
2. 动作权限拒绝。
3. 资源越权。
4. ERPNext 权限源不可用。
5. ERPNext 依赖不可用。
6. internal diagnostic 越权访问。

### 8.2 操作审计事件
仅审计：
1. `export`
2. `diagnostic`

不要求审计普通 read 成功路径，避免审计表放大。

## 九、TASK-011B 实现边界（冻结）

### 9.1 允许项
1. 新增后端只读 router/schema/service。
2. 新增 ERPNext 只读 adapter 调用。
3. 新增后端测试。
4. 新增前端 API 类型定义（不含页面）。

### 9.2 禁止项
1. 前端页面开发。
2. ERPNext 写操作。
3. outbox 写入。
4. 本地业务事实写入。
5. 提前进入 TASK-012。

## 十、回迁与复用说明

1. 复用 TASK-007 的动作权限和资源权限校验入口。
2. 复用 TASK-008 的 fail-closed adapter 错误映射。
3. 复用 TASK-010 的前端门禁 engine 和 fixture 规范。

## 十一、实现前检查清单（给 TASK-011B）

- [ ] 只读接口与路径完全对齐本设计
- [ ] 权限动作统一使用 `sales_inventory:*`
- [ ] 资源字段最小集合完整
- [ ] ERPNext fail-closed 映射齐全
- [ ] 前端门禁模块配置 `sales_inventory` 已冻结
- [ ] 无写接口、无 outbox、无本地写事实
