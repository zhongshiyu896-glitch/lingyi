# TASK-005E2 款式利润 API 审计阻断整改工程任务单

## 任务编号

TASK-005E2

## 任务名称

款式利润 API 审计阻断整改

## 任务目标

修复审计意见书第 99 份指出的 `TASK-005E1` 阻断问题：服务端来源采集器空实现、权限矩阵偏离冻结口径、鉴权顺序不正确、早期失败操作审计缺失。修复后才能再次提交 TASK-005E API 复审。

## 审计来源

审计意见书第 99 份，结论：不通过。

必须修复问题：

1. P1：`StyleProfitApiSourceCollector` 空实现导致创建零值/不完整快照。
2. P1：权限矩阵偏离冻结口径，`Production Manager` 被授予创建权限，`Finance Manager / Sales Manager` 权限缺失。
3. P2：列表/创建接口鉴权顺序不正确，无动作权限用户可能先拿到 400 业务错误。
4. P2：列表失败、创建早期失败操作审计覆盖不完整。

## 严格边界

允许做：

1. 修复款式利润 API router。
2. 修复款式利润权限动作映射。
3. 修复 `StyleProfitApiSourceCollector` fail closed 语义。
4. 增加或修正 API 测试。
5. 增加或修正 PostgreSQL 测试门禁。

禁止做：

1. 禁止修改利润计算公式。
2. 禁止修改 D 系列已通过审计的利润计算口径。
3. 禁止新增或修改 migrations。
4. 禁止修改前端。
5. 禁止修改 `.github`。
6. 禁止修改 `02_源码`。
7. 禁止进入 `TASK-006`。
8. 禁止实现导出、打印、加工厂对账。
9. 禁止为了测试绕过鉴权、审计或资源权限。

## 涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_api_source_collector.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_errors.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_postgresql.py`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006*`

## P1-1：来源采集器空实现整改

### 当前问题

`StyleProfitApiSourceCollector` 中 `_load_*` 方法直接 `return []`，导致 `POST /api/reports/style-profit/snapshots` 在没有可信来源事实时仍能创建零值或不完整快照。

### 架构决策

TASK-005E2 阶段采用 fail closed 最低可验收口径：

1. 真实来源采集未就绪时，不允许创建快照。
2. 来源采集失败，不允许创建快照。
3. 服务端无法区分“真实无数据”和“采集未实现/不可用”时，必须按不可用处理。
4. 禁止把空数组默认解释成“业务无成本/无收入”。
5. 测试可以注入 fake collector 返回可信来源 rows，但生产默认 collector 不得空实现成功。

### 实现要求

1. `StyleProfitApiSourceCollector.collect()` 必须返回明确结果或抛出标准异常。
2. 默认 collector 不得通过空 `_load_*` 生成空快照。
3. 如果 ERPNext / 服务端事实来源未实现或不可用，必须抛出 `STYLE_PROFIT_SOURCE_UNAVAILABLE`。
4. 如果本地 FastAPI 来源读取失败，必须抛出 `DATABASE_READ_FAILED`。
5. 如果来源采集结果没有任何可信收入来源，必须返回 `STYLE_PROFIT_SOURCE_UNAVAILABLE` 或 `STYLE_PROFIT_TRUSTED_SOURCE_REQUIRED`，不得落库。
6. 如果来源采集结果没有任何可信成本来源，但收入来源存在，允许生成 incomplete 快照的前提是 source_map 写明 unresolved；否则 fail closed。
7. 真实 collector 与测试 fake collector 必须分离，测试注入不得污染生产默认路径。
8. `POST /snapshots` 在 collector fail closed 时不得调用 `StyleProfitService.create_snapshot()`。
9. collector fail closed 后不得写 snapshot/detail/source_map。
10. collector fail closed 必须写创建失败操作审计。

### 必测用例

- 默认 collector 未配置真实来源时，`POST /snapshots` 返回 `503 + STYLE_PROFIT_SOURCE_UNAVAILABLE`。
- 默认 collector 未配置真实来源时，不创建 snapshot。
- collector 抛 `DATABASE_READ_FAILED` 时，不创建 snapshot。
- fake collector 返回可信 rows 时，创建接口可正常调用 `StyleProfitService.create_snapshot()`。
- fake collector 返回空 rows 时，创建接口 fail closed，不创建零值快照。

## P1-2：权限矩阵整改

### 冻结口径

| 角色 | style_profit:read | style_profit:snapshot_create |
| --- | --- | --- |
| System Manager | 是 | 是 |
| Finance Manager | 是 | 是 |
| Production Manager | 是 | 否 |
| Sales Manager | 是 | 否 |
| Viewer | 否 | 否 |

### 实现要求

1. `DEFAULT_STATIC_ROLE_ACTIONS` 按冻结口径修正。
2. `ERP_ROLE_ACTIONS` 按冻结口径修正。
3. 移除 `Production Manager` 的 `style_profit:snapshot_create`。
4. 补齐 `Finance Manager` 的 `style_profit:read` 和 `style_profit:snapshot_create`。
5. 补齐 `Sales Manager` 的 `style_profit:read`。
6. `Viewer` 不得默认拥有款式利润权限。
7. `/api/auth/actions?module=style_profit` 返回结果必须与矩阵一致。

### 必测用例

- `System Manager` 可读、可创建。
- `Finance Manager` 可读、可创建。
- `Production Manager` 可读、不可创建。
- `Sales Manager` 可读、不可创建。
- `Viewer` 不可读、不可创建。
- static 权限源覆盖上述矩阵。
- ERP role 聚合覆盖上述矩阵。

## P2-1：鉴权顺序整改

### 当前问题

列表接口先校验 `company/item_code` 再做动作权限；创建接口先拒绝客户端来源字段或做参数校验，再做 `style_profit:snapshot_create` 权限。无动作权限用户可拿到 400 业务错误，而不是 403 权限错误。

### 实现要求

1. 登录后必须先做动作权限校验。
2. 列表接口：先校验 `style_profit:read`，再校验 company/item_code 必填，再做资源权限。
3. 详情接口：读取 snapshot 是否存在后，先校验 `style_profit:read`，再按 snapshot.company/snapshot.item_code 做资源权限，再读 detail/source_map。
4. 创建接口：允许先做最小 body 解析以便取得请求对象，但在任何业务字段校验、客户端来源字段拒绝、idempotency 校验前，必须先校验 `style_profit:snapshot_create`。
5. 无动作权限用户无论 payload 是否缺字段、是否有客户端来源字段、是否 idempotency 非法，都必须稳定返回 `403 + AUTH_FORBIDDEN`。
6. 403 必须写安全审计。

### 必测用例

- 无 `style_profit:read` 用户请求列表且缺 company/item_code，返回 403，不返回 400。
- 无 `style_profit:snapshot_create` 用户创建且携带客户端来源字段，返回 403，不返回 400。
- 无 `style_profit:snapshot_create` 用户创建且 idempotency_key 非法，返回 403，不返回 400。
- 有 `style_profit:snapshot_create` 用户携带客户端来源字段，返回 400 + `STYLE_PROFIT_CLIENT_SOURCE_FORBIDDEN`。
- 有 `style_profit:snapshot_create` 用户 idempotency_key 非法，返回 400 + `STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY`。

## P2-2：操作审计覆盖整改

### 当前问题

列表失败路径没有操作审计；创建接口的客户端来源字段拒绝、参数校验拒绝发生在 `_record_failure_safely` 前，导致创建失败操作审计缺口。

### 实现要求

1. 列表接口在动作权限通过后，业务校验失败、数据库读取失败必须写操作失败审计。
2. 创建接口在动作权限通过后，客户端来源字段拒绝必须写创建失败操作审计。
3. 创建接口在动作权限通过后，参数校验失败必须写创建失败操作审计。
4. 创建接口 collector fail closed 必须写创建失败操作审计。
5. 创建接口 service 业务异常必须写创建失败操作审计。
6. 详情接口保持成功/失败操作审计，不得回退。
7. 必需操作审计写入失败必须返回 `AUDIT_WRITE_FAILED`。
8. 权限拒绝场景必须写安全审计；是否额外写操作审计由实现统一，但不得漏安全审计。

### 必测用例

- 授权用户列表缺 company/item_code，返回 400 且写操作失败审计。
- 授权用户列表数据库读取失败，返回 `DATABASE_READ_FAILED` 且写操作失败审计。
- 授权用户创建携带客户端来源字段，返回 `STYLE_PROFIT_CLIENT_SOURCE_FORBIDDEN` 且写操作失败审计。
- 授权用户创建参数非法，返回对应错误码且写操作失败审计。
- 授权用户创建 collector fail closed，返回 `STYLE_PROFIT_SOURCE_UNAVAILABLE` 且写操作失败审计。
- 上述必需审计写入失败时返回 `AUDIT_WRITE_FAILED`。

## PostgreSQL 门禁补强

当前 PostgreSQL 测试可以 skip，但必须保持安全门禁。

新增或修正测试：

1. 默认无 `POSTGRES_TEST_DSN` 时明确 skip。
2. 有 DSN 但无 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true` 时明确 skip。
3. 数据库名不匹配 `_test` 或 `lingyi_test_` 时必须拒绝执行 destructive 操作。
4. 后续进入前端联调或发布前，必须补真实 PostgreSQL 非 skip 证据。

## 测试命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q \
  tests/test_style_profit_api.py \
  tests/test_style_profit_api_permissions.py \
  tests/test_style_profit_api_audit.py \
  tests/test_style_profit_api_errors.py \
  tests/test_style_profit_api_postgresql.py

.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

禁改扫描：

```bash
cd /Users/hh/Desktop/领意服装管理系统

git diff --name-only -- 06_前端 .github 02_源码
git diff --name-only -- 07_后端/lingyi_service/migrations
git diff --name-only -- '03_需求与设计/02_开发计划' | grep 'TASK-006' || true
```

## 验收标准

- [ ] 默认 collector 未配置真实来源时 fail closed。
- [ ] 默认 collector 不再用空数组创建零值快照。
- [ ] collector 不可用时不调用 `StyleProfitService.create_snapshot()`。
- [ ] collector 不可用时不落 snapshot/detail/source_map。
- [ ] fake collector 返回可信 rows 时创建接口可走通。
- [ ] 权限矩阵符合 System Manager / Finance Manager / Production Manager / Sales Manager / Viewer 冻结口径。
- [ ] static 权限源测试通过。
- [ ] ERP role 聚合测试通过。
- [ ] 无权限用户在非法 payload 下优先返回 403。
- [ ] 403 写安全审计。
- [ ] 列表业务失败写操作失败审计。
- [ ] 创建早期业务失败写操作失败审计。
- [ ] 必需操作审计失败返回 `AUDIT_WRITE_FAILED`。
- [ ] 定向 pytest 通过。
- [ ] 全量 pytest 通过。
- [ ] unittest discover 通过。
- [ ] py_compile 通过。
- [ ] PostgreSQL 测试安全门禁保留。
- [ ] 未修改前端。
- [ ] 未修改 `.github`。
- [ ] 未修改 `02_源码`。
- [ ] 未修改 migrations。
- [ ] 未进入 TASK-006。

## 交付回报格式

```text
TASK-005E2 已完成。

修复内容：
- P1 来源采集 fail closed：[已修复/未修复]
- P1 权限矩阵：[已修复/未修复]
- P2 鉴权顺序：[已修复/未修复]
- P2 操作审计覆盖：[已修复/未修复]

验证结果：
- API 定向 pytest：[结果]
- 全量 pytest：[结果]
- unittest discover：[结果]
- py_compile：[结果]
- PostgreSQL 测试：[非 skip 结果或 skip 原因]
- 禁改扫描：[通过/不通过]

关键证明：
- 默认 collector 不创建空来源快照：[证明]
- Production Manager 不可创建：[证明]
- Finance Manager 可创建：[证明]
- 无权限 + 非法 payload 优先 403：[证明]
- 创建早期失败写操作审计：[证明]

确认：
- 未修改前端
- 未修改 .github
- 未修改 02_源码
- 未修改 migrations
- 未进入 TASK-006
```
