# TASK-005A 款式利润报表开发前基线盘点工程任务单

- 任务编号：TASK-005A
- 模块：款式利润报表 / 开发前基线盘点
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 23:14 CST
- 作者：技术架构师
- 前置状态：TASK-004C13 GitHub 平台闭环仍等待无凭据 GitHub 仓库 URL，TASK-005/TASK-006 工程实现继续阻塞
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V0.1；`ADR-076`
- 任务边界：只做开发前基线盘点和设计缺口报告，不写后端代码，不写前端代码，不建迁移，不新增接口，不进入 TASK-005B 实现

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005A
模块：款式利润报表开发前基线盘点
优先级：P0（实现前强制盘点）
════════════════════════════════════════════════════════════════════════════

【任务目标】
盘点款式利润报表所依赖的 ERPNext、BOM、外发、工票、生产计划数据源和现有代码基础，输出可审计的基线报告，为后续 TASK-005B 设计冻结和工程实现做准备。

【当前限制】
1. TASK-004C13 GitHub 平台闭环未完成，不能启动 TASK-005 工程实现。
2. 本任务只允许读代码、读文档、输出盘点报告。
3. 本任务不得创建 `style_profit` 后端模型、接口、迁移或前端页面。
4. 本任务不得修改 `06_前端/`、`07_后端/`、`.github/workflows/`、`02_源码/`。
5. 本任务不得进入 TASK-006。

【必须读取】
- /Users/hh/Desktop/领意服装管理系统/README.md
- /Users/hh/Desktop/领意服装管理系统/00_交接与日志/HANDOVER_STATUS.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/00_总体架构概览.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/01_模块设计_BOM管理.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/02_模块设计_外发加工管理.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/04_模块设计_工票车间管理.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md

【必须盘点的代码范围】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/alembic/ 或迁移目录实际位置
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/

【输出文件】
新建：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-005_款式利润报表_开发前基线盘点.md

可追加：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

【报告必须包含】

## 1. 现有实现扫描结果
| 范围 | 是否存在利润相关实现 | 文件路径 | 可复用性 | 风险 |
| --- | --- | --- | --- | --- |

必须搜索关键字：
- `style_profit`
- `profit`
- `gross_margin`
- `cost_allocation`
- `snapshot`
- `Sales Order`
- `Stock Ledger Entry`
- `Purchase Receipt`

## 2. 上游依赖状态
| 依赖模块 | 当前状态 | 可用数据 | 缺口 | 是否阻塞 TASK-005B |
| --- | --- | --- | --- | --- |

必须覆盖：
1. TASK-001 BOM 管理。
2. TASK-002 外发加工管理。
3. TASK-003 工票/车间管理。
4. TASK-004 生产计划集成。
5. ERPNext Sales Order。
6. ERPNext Purchase Receipt。
7. ERPNext Stock Ledger Entry。

## 3. 利润口径候选
| 成本/收入项 | 候选公式 | 数据来源 | 精度风险 | 是否需要架构决策 |
| --- | --- | --- | --- | --- |

必须至少覆盖：
1. 销售收入。
2. 标准材料成本。
3. 标准工序成本。
4. 实际材料成本。
5. 实际工票成本。
6. 实际外发加工费。
7. 扣款金额。
8. 制造费用或其他费用分摊。
9. 利润金额。
10. 利润率。

参考候选公式：
1. 标准材料成本 = BOM 展开用量 × 标准采购单价。
2. 标准工序成本 = BOM 工序单价 × 订单数量。
3. 实际工票成本 = 工票净数量 × 实际工价。
4. 实际外发加工费 = 外发验货合格数量 × 外发单价 - 扣款金额。
5. 利润金额 = 销售收入 - 标准材料成本 - 实际工票成本 - 实际外发加工费 - 其他分摊费用。
6. 利润率 = 利润金额 / 销售收入。

## 4. 数据模型草案
只输出草案，不建表。

必须给出候选表：
- `ly_schema.ly_style_profit_snapshot`
- `ly_schema.ly_style_profit_detail`
- `ly_schema.ly_cost_allocation_rule`

每张表必须列出：
- 用途
- 关键字段
- 唯一约束
- 索引建议
- 数据来源
- 是否需要快照不可变

## 5. API 草案
只输出草案，不实现。

必须覆盖候选接口：
| 接口 | 方法 | 路径 | 用途 | 幂等要求 | 权限动作 |
| --- | --- | --- | --- | --- | --- |

候选路径：
- `GET /api/reports/style-profit/`
- `POST /api/reports/style-profit/snapshot`
- `GET /api/reports/style-profit/{snapshot_id}`
- `GET /api/reports/style-profit/compare`

必须判断 `POST /snapshot` 是否需要 `idempotency_key`。

## 6. 权限与审计缺口
必须明确：
1. 读取利润报表需要的动作权限。
2. 生成利润快照需要的动作权限。
3. 是否需要按 `company / item_code / sales_order` 做资源级权限。
4. 权限来源必须沿用 ERPNext Role / User Permission 聚合，不允许静态权限作为生产权威源。
5. 权限源不可用时必须 fail closed。
6. 401/403/503 是否需要安全审计。
7. 生成快照是否需要操作审计。
8. 错误日志是否需要脱敏。

## 7. 前端页面缺口
必须盘点：
1. 是否已有利润报表页面。
2. 是否已有报表路由。
3. 是否已有 API client。
4. 是否接入统一请求客户端。
5. 是否需要新增筛选项：日期、款式、销售订单、客户、公司。
6. 是否需要导出、打印、明细钻取。

## 8. 风险清单
按 P1/P2/P3 输出：
| 风险等级 | 风险 | 影响 | 建议处理 |
| --- | --- | --- | --- |

至少评估：
1. 销售收入取 Sales Order 还是 Sales Invoice。
2. 实际材料成本取 Purchase Receipt 还是 Stock Ledger Entry。
3. 外发扣款是否以验货事实还是对账锁定事实为准。
4. 工票撤销和日薪补数是否影响历史快照。
5. 快照重算是否覆盖旧快照。
6. 多公司权限和跨公司订单风险。
7. 平台闭环未完成对 TASK-005 实现的阻塞。

## 9. TASK-005B 拆分建议
只给建议，不实现。

必须拆出候选任务：
1. TASK-005B 利润口径设计冻结。
2. TASK-005C 后端数据模型与迁移。
3. TASK-005D 利润快照计算服务。
4. TASK-005E 权限、审计和错误信封。
5. TASK-005F 前端利润报表页面。
6. TASK-005G 报表导出与打印。
7. TASK-005H 回归测试与审计封版。

【禁止事项】
- 禁止新增或修改 `style_profit.py` 后端代码。
- 禁止新增或修改 `style_profit.ts` 前端代码。
- 禁止新增 Alembic 迁移。
- 禁止注册新路由。
- 禁止修改数据库模型。
- 禁止调用 ERPNext 写接口。
- 禁止改 TASK-004C13 平台闭环相关配置。
- 禁止进入 TASK-006。

【验收标准】
□ `/03_需求与设计/01_架构设计/TASK-005_款式利润报表_开发前基线盘点.md` 已创建。
□ 报告包含现有实现扫描、上游依赖状态、利润口径候选、数据模型草案、API 草案、权限审计缺口、前端缺口、风险清单、TASK-005B 拆分建议。
□ 报告明确 TASK-004C13 平台闭环未完成前，TASK-005B 工程实现不得启动。
□ `git diff --name-only -- 06_前端 07_后端 .github 02_源码` 无业务代码变更。
□ 未新增迁移文件。
□ 未新增后端路由、模型、schema、service。
□ 未新增前端 api、view、router、store。
□ 工程师会话日志已追加完成记录。

【预计工时】
0.5-1 天

════════════════════════════════════════════════════════════════════════════
