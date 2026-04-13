# 工程任务单：TASK-003Q 内部 Worker skipped_forbidden 兼容字段语义整改

- 任务编号：TASK-003Q
- 模块：工票/车间管理
- 优先级：P2
- 任务类型：审计整改 / API 响应契约 / 运维诊断语义
- 创建时间：2026-04-12 19:15 CST
- 作者：技术架构师
- 审计来源：TASK-003P 审计意见，内部 Worker 响应仍保留 `skipped_forbidden_count/skipped_forbidden` 兼容字段，且字段值实际等于 `forbidden_diagnostic`

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-003Q
模块：工票/车间管理
优先级：P2（低危审计整改，建议在 TASK-003 总体验收前收口）
════════════════════════════════════════════════════════════════════════════

【任务目标】
收口内部 Worker `run-once` 响应字段语义：将 `forbidden_diagnostic_count` 作为越权诊断唯一推荐字段，并废弃或明确标注 `skipped_forbidden_count/skipped_forbidden` 仅为 diagnostics-only 兼容别名，避免前端或运维误读为主处理跳过数。

【问题背景】
TASK-003H/TASK-003I 已将越权 outbox 从主处理查询中移除，默认 `run-once` 只扫描当前服务账号有权处理的 outbox；越权 outbox 只在显式诊断模式下扫描。当前响应仍保留 `skipped_forbidden_count/skipped_forbidden`，且值等于 `forbidden_diagnostic`。该字段名会让调用方误以为 Worker 主处理流程实际“跳过了越权 outbox”，与现有架构语义不一致。

【涉及文件】
修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`

测试文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_service_account_policy.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_outbox_audit_throttle.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_worker_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_audit_log.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_auth_actions.py`

【接口 / 字段清单】
| 名称 | 类型 | 当前风险 | 本任务要求 |
| --- | --- | --- | --- |
| `POST /api/workshop/internal/job-card-sync/run-once` | API | 响应字段语义易误读 | 明确主处理指标与诊断指标 |
| `forbidden_diagnostic_count` | response field | 当前是正确字段 | 作为越权诊断唯一推荐字段 |
| `forbidden_diagnostic` | response field | 旧字段但语义明确 | 可保留为短名兼容字段 |
| `skipped_forbidden_count` | response field | 容易误读为主处理跳过数 | 删除，或标注 deprecated + diagnostics-only + alias |
| `skipped_forbidden` | response field | 容易误读为主处理跳过数 | 删除，或标注 deprecated + diagnostics-only + alias |
| `forbidden_diagnostics_enabled` | response field | 当前缺少显式诊断模式标识 | 建议新增，标明本次是否执行越权诊断扫描 |

【核心设计决策】
1. 主处理不再“跳过越权 outbox”，主处理查询必须只返回当前服务账号有权处理的 outbox。
2. 越权 outbox 的统计只属于显式 diagnostics，不属于主处理 skipped。
3. 推荐字段为 `forbidden_diagnostic_count`。
4. `skipped_forbidden_count/skipped_forbidden` 不再作为新契约推荐。
5. 如果立即删除会破坏现有调用方，本阶段允许保留兼容字段。
6. 保留兼容字段时，必须在 Pydantic Field / OpenAPI schema / 接口文档中标注：`deprecated`、`diagnostics-only`、`alias of forbidden_diagnostic_count`。
7. 保留兼容字段时，其值只能等于 `forbidden_diagnostic_count`，不得另行计算。
8. 默认未启用 diagnostics 时，`forbidden_diagnostic_count/skipped_forbidden_count/skipped_forbidden` 必须全部为 0。
9. 显式启用 `include_forbidden_diagnostics=true` 时，字段含义为“诊断扫描发现的越权候选数”，不是“主处理跳过数”。
10. 操作审计 `after_data` 中允许保留兼容字段，但审计判断必须以 `forbidden_diagnostic_count` 为准。

【响应契约要求】
| 场景 | `forbidden_diagnostic_count` | `skipped_forbidden_count` | `skipped_forbidden` | 说明 |
| --- | --- | --- | --- | --- |
| 默认 `run-once`，未启用 diagnostics | 0 | 0 或字段删除 | 0 或字段删除 | 主处理不扫描越权 outbox |
| `include_forbidden_diagnostics=true`，发现 N 条 | N | N 或字段删除 | N 或字段删除 | 兼容字段仅为诊断别名 |
| dry-run + diagnostics | N | N 或字段删除 | N 或字段删除 | 不锁定、不重试、不调用 ERPNext |
| 生产 dry-run 禁用 | 不返回成功 data | 不返回成功 data | 不返回成功 data | 保持 TASK-003K 规则 |
| 权限失败 / 权限源不可用 | 不返回成功 data | 不返回成功 data | 不返回成功 data | 保持安全审计规则 |

【实现要求】
1. 优先方案：从响应 `data` 中删除 `skipped_forbidden_count/skipped_forbidden`，只保留 `forbidden_diagnostic_count`。
2. 兼容方案：如果测试或现有调用方依赖旧字段，则保留旧字段，但必须加 deprecated 元数据和说明。
3. Pydantic 如支持 `Field(..., deprecated=True)`，直接使用；如不支持，使用 `json_schema_extra={"deprecated": true}` 或等价 OpenAPI 元数据。
4. `WorkshopSyncRunResult.skipped_forbidden` property 如保留，docstring 必须写明 `Deprecated diagnostics-only alias of forbidden_diagnostic`。
5. `WorkshopJobCardSyncRunOnceData` 中旧字段 description 必须明确“历史兼容字段，仅诊断模式有效，不代表主处理跳过数”。
6. `run-once` 路由构造响应时，禁止把旧字段作为独立业务计数计算。
7. 推荐新增 `forbidden_diagnostics_enabled`，取值为 `include_forbidden_diagnostics or workshop_enable_forbidden_diagnostics()` 的实际结果。
8. 操作审计 `after_data` 中必须包含 `forbidden_diagnostic_count`；如包含旧字段，也必须保持 deprecated 语义一致。
9. 前端或文档如存在 `skipped_forbidden_count/skipped_forbidden` 展示，必须改为展示 `forbidden_diagnostic_count`。
10. 不得改变 outbox 主处理、诊断节流、dry-run 审计、服务账号权限等已有逻辑。

【验收标准】
□ OpenAPI schema 中 `skipped_forbidden_count` 已删除，或标注 deprecated + diagnostics-only。
□ OpenAPI schema 中 `skipped_forbidden` 已删除，或标注 deprecated + diagnostics-only。
□ `WorkshopSyncRunResult.skipped_forbidden` 如保留，docstring 明确 deprecated diagnostics-only alias。
□ `POST /api/workshop/internal/job-card-sync/run-once` 默认未启用 diagnostics 时，`forbidden_diagnostic_count=0`。
□ 默认未启用 diagnostics 时，`skipped_forbidden_count/skipped_forbidden` 如存在也必须为 0。
□ `include_forbidden_diagnostics=true` 时，`skipped_forbidden_count/skipped_forbidden` 如存在必须等于 `forbidden_diagnostic_count`。
□ 响应或文档中不得把 `skipped_forbidden_count/skipped_forbidden` 描述为主处理跳过数。
□ 操作审计 `after_data` 中包含 `forbidden_diagnostic_count`，审计判断不依赖 `skipped_forbidden*`。
□ 前端 `src` 内不得新增对 `skipped_forbidden_count/skipped_forbidden` 的业务依赖。
□ TASK-003H/TASK-003I/TASK-003J/TASK-003K/TASK-003P 回归测试继续通过。
□ 全量测试继续通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_worker_response_skipped_forbidden_fields_are_deprecated_or_removed_in_openapi`
2. `test_worker_response_documents_skipped_forbidden_as_diagnostics_only_alias`
3. `test_run_once_without_diagnostics_returns_zero_forbidden_diagnostic_count`
4. `test_run_once_without_diagnostics_returns_zero_compat_skipped_forbidden_if_present`
5. `test_run_once_with_diagnostics_uses_forbidden_diagnostic_count_as_canonical_field`
6. `test_run_once_with_diagnostics_compat_fields_equal_forbidden_diagnostic_count_if_present`
7. `test_worker_audit_after_data_contains_forbidden_diagnostic_count`
8. `test_worker_audit_after_data_does_not_require_skipped_forbidden_for_business_judgement`
9. `test_frontend_src_does_not_reference_skipped_forbidden_count`
10. `test_frontend_src_does_not_reference_skipped_forbidden`

【回归命令】
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 下执行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

如前端目录存在依赖环境，补充执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg "skipped_forbidden|skippedForbidden" src
```

【前置依赖】
- TASK-003H：Outbox 跳过行队头阻塞整改已接入
- TASK-003I：Outbox 越权诊断节流与审计去重整改已接入
- TASK-003J：内部 Worker dry-run 操作审计整改已接入
- TASK-003K：生产 dry-run 禁用判断前置整改已接入
- TASK-003P：ERPNext Item 候选查询 fail closed 已接入

【交付物】
1. 内部 Worker 响应字段语义整改。
2. OpenAPI / Pydantic 字段 deprecated 或删除结果。
3. run-once 默认模式和 diagnostics 模式响应测试。
4. 操作审计 after_data 字段测试。
5. 前端引用扫描结果。
6. 全量测试结果。

【禁止事项】
1. 禁止把 `skipped_forbidden_count/skipped_forbidden` 继续描述为主处理跳过数。
2. 禁止新增前端或运维页面对 `skipped_forbidden*` 的业务依赖。
3. 禁止为了字段整改改变 outbox 主处理查询逻辑。
4. 禁止为了字段整改关闭 forbidden diagnostics 节流或审计去重。
5. 禁止让兼容字段与 `forbidden_diagnostic_count` 出现不一致。
6. 禁止破坏 dry-run、权限拒绝、安全审计、服务账号最小权限等已通过审计的行为。

════════════════════════════════════════════════════════════════════════════
