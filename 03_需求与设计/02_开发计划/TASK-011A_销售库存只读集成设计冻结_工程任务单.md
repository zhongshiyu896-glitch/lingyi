# TASK-011A 销售/库存只读集成设计冻结工程任务单

- 任务编号：TASK-011A
- 角色：工程师
- 优先级：P1
- 前置依赖：TASK-010F 审计通过（HEAD `8575b48b8f63217c54886f2b5ac8f4bb557081bf`）
- 任务类型：设计冻结（仅文档）

## 一、任务目标

冻结销售/库存只读集成的系统边界、API 契约、权限边界、ERPNext fail-closed 接入方式与前端只读门禁要求，形成 TASK-011B 的唯一实现前置。

## 二、任务边界

### 2.1 允许输出
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-011_销售库存只读集成设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-011A_销售库存只读集成设计冻结_工程任务单.md`

### 2.2 禁止修改
- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`

### 2.3 禁止实现
1. 创建/修改 Sales Order。
2. 提交 Delivery Note。
3. 创建/修改 Stock Entry。
4. 修改 Item/Warehouse/Customer。
5. 任何 ERPNext 写 API。
6. 任何 outbox 写入。
7. Payment/GL/Purchase Invoice 逻辑。

## 三、必须冻结内容

### 3.1 系统边界
文档必须明确：
1. ERPNext 是销售/库存权威来源。
2. FastAPI 仅做聚合查询与权限过滤。
3. Vue3 仅做只读展示。
4. 本任务不写 ERPNext、不写本地业务事实。

### 3.2 只读接口清单（至少）
1. `GET /api/sales-inventory/sales-orders`
2. `GET /api/sales-inventory/sales-orders/{name}`
3. `GET /api/sales-inventory/items/{item_code}/stock-summary`
4. `GET /api/sales-inventory/items/{item_code}/stock-ledger`
5. `GET /api/sales-inventory/warehouses`
6. `GET /api/sales-inventory/customers`

### 3.3 权限动作（引用 TASK-007）
1. `sales_inventory:read`
2. `sales_inventory:export`
3. `sales_inventory:diagnostic`

### 3.4 资源权限字段
至少覆盖：
1. `company`
2. `item_code`
3. `warehouse`
4. `sales_order`
5. `customer`

并明确：
1. 列表先动作权限再资源过滤。
2. 详情先动作权限再资源读取再资源校验。
3. 无权限不得通过 403/404 差异泄露存在性。
4. 权限源不可用 fail closed。

### 3.5 ERPNext Fail-Closed 接入（引用 TASK-008）
必须冻结：
1. timeout / 连接失败 / 5xx → `EXTERNAL_SERVICE_UNAVAILABLE`。
2. 401/403 不得伪成功。
3. malformed response fail closed。
4. Sales Order / Delivery Note 强制 `docstatus` 校验。
5. SLE 必填字段缺失不得纳入结果。

### 3.6 前端只读门禁接入（引用 TASK-010）
必须冻结：
1. 模块名：`sales_inventory`。
2. 公共 engine 接入。
3. `fixture.positive` 与 `fixture.negative` 必填。
4. 禁止写方法、`/api/resource`、internal API、写语义按钮。

### 3.7 错误信封
必须冻结统一失败信封与分页成功信封示例。

### 3.8 审计要求
1. 安全审计：未认证、动作拒绝、资源越权、权限源不可用、依赖不可用、internal diagnostic 越权。
2. 操作审计：仅 `export`、`diagnostic`。
3. 普通 read 成功不写操作审计（防放大）。

### 3.9 TASK-011B 实现边界
允许：后端只读 router/schema/service、ERPNext 只读 adapter 调用、测试、前端 API 类型。

禁止：前端页面开发、ERPNext 写操作、outbox、本地写事实、进入 TASK-012。

## 四、审计前置要求

审计官必须确认：
1. 文档未要求写操作。
2. 文档明确 ERPNext fail-closed 路径。
3. 文档明确权限与资源校验顺序。
4. 文档明确前端只读门禁接入。
5. 文档明确 TASK-011B 允许/禁止边界。

## 五、验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
test -f "03_需求与设计/01_架构设计/TASK-011_销售库存只读集成设计.md"
test -f "03_需求与设计/02_开发计划/TASK-011A_销售库存只读集成设计冻结_工程任务单.md"
git diff --name-only -- "06_前端" "07_后端" ".github" "02_源码"
git diff --cached --name-only
```

## 六、验收标准

- [ ] TASK-011 设计文档已输出
- [ ] TASK-011A 工程任务单已输出
- [ ] 明确 ERPNext 为销售/库存权威来源
- [ ] 明确只读接口清单
- [ ] 明确权限动作与资源字段
- [ ] 明确 ERPNext fail-closed 接入方式
- [ ] 明确前端只读门禁接入方式
- [ ] 明确 TASK-011B 实现边界
- [ ] 未修改前端代码
- [ ] 未修改后端代码
- [ ] 未修改 `.github`
- [ ] 未修改 `02_源码`
- [ ] 未暂存、未提交、未 push

## 七、执行约束

1. 本任务仅输出文档。
2. 不改业务代码。
3. 不暂存、不提交、不 push。
4. 不进入 TASK-011B 实现。

## 八、交付回报格式

```text
TASK-011A 执行完成。
结论：待审计

已输出：
- /03_需求与设计/01_架构设计/TASK-011_销售库存只读集成设计.md
- /03_需求与设计/02_开发计划/TASK-011A_销售库存只读集成设计冻结_工程任务单.md

本次只输出文档。
未修改前端/后端/.github/02_源码。
未暂存、未提交、未 push。
```
