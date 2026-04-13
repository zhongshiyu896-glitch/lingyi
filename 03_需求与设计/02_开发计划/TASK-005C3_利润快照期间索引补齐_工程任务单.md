# TASK-005C3 利润快照期间索引补齐工程任务单

- 任务编号：TASK-005C3
- 模块：款式利润报表 / 快照查询索引整改
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 06:58 CST
- 作者：技术架构师
- 审计来源：TASK-005C2 审计结论有条件通过，中危 1
- 前置依赖：TASK-005C2 已交付并完成审计；ADR-082 生效
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V0.7；`ADR-083`
- 任务边界：只补利润快照期间查询索引和测试；不得进入 TASK-005D 利润快照计算服务；不得注册 API；不得修改前端；不得进入 TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005C3
模块：利润快照期间索引补齐
优先级：P0（审计阻断整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
补齐 `ly_style_profit_snapshot` 的期间查询索引 `idx_ly_style_profit_snapshot_company_item_period(company, item_code, from_date, to_date)`，关闭 TASK-005C2 审计剩余 P2 问题，然后再申请 TASK-005D 放行复审。

【允许修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_005c_create_style_profit_tables.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/[timestamp]_add_style_profit_snapshot_period_index.py（如不能原地修改迁移时使用）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_models.py
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

【禁止修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py（除非测试导入路径必须调整，不得改业务逻辑）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py（除非测试导入路径必须调整，不得改 DTO 契约）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/**
- /Users/hh/Desktop/领意服装管理系统/.github/**
- /Users/hh/Desktop/领意服装管理系统/02_源码/**
- 任意 TASK-005D / TASK-006 文件

【必须整改】

## 1. 模型索引

在 `LyStyleProfitSnapshot.__table_args__` 中补齐索引：

```python
Index(
    "idx_ly_style_profit_snapshot_company_item_period",
    "company",
    "item_code",
    "from_date",
    "to_date",
)
```

规则：
1. 索引名称必须固定为 `idx_ly_style_profit_snapshot_company_item_period`。
2. 字段顺序必须固定为 `company, item_code, from_date, to_date`。
3. 不得用 `sales_order` 替代 `from_date/to_date`。
4. 不得删除现有 `company + item_code + sales_order` 索引；订单查询和期间查询是两个不同访问路径。

## 2. 迁移索引

迁移中必须创建同名索引。

规则：
1. 如果 `task_005c_create_style_profit_tables.py` 尚未被正式应用，可在该迁移中补索引。
2. 如果该迁移已经被应用或存在审计要求保留迁移历史，必须新增增量迁移 `[timestamp]_add_style_profit_snapshot_period_index.py`。
3. 增量迁移必须支持 upgrade 创建索引、downgrade 删除索引。
4. PostgreSQL schema 必须指向 `ly_schema`。
5. 不允许 drop/recreate 利润快照表。

## 3. 测试

必须补模型测试，确认索引存在且字段顺序正确。

测试要求：
1. 从 `LyStyleProfitSnapshot.__table__.indexes` 中查找 `idx_ly_style_profit_snapshot_company_item_period`。
2. 断言字段顺序等于 `['company', 'item_code', 'from_date', 'to_date']`。
3. 如项目已有迁移文本检查，增加迁移索引存在性断言。
4. 保持 TASK-005C1/C2 既有测试全部通过。

【禁止事项】
- 禁止修改利润计算逻辑。
- 禁止新增 `/api/reports/style-profit/` 路由。
- 禁止实现 `POST /api/reports/style-profit/snapshot`。
- 禁止修改前端。
- 禁止进入 TASK-005D/TASK-006。
- 禁止借本任务重构 source mapping 状态白名单或 source_map 字段契约。

【验证命令】

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_models.py tests/test_style_profit_source_mapping.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

静态边界检查：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- 06_前端 .github 02_源码
git diff --name-only -- 07_后端/lingyi_service/app/main.py 07_后端/lingyi_service/app/routers
```

【验收标准】
□ `LyStyleProfitSnapshot` 已包含 `idx_ly_style_profit_snapshot_company_item_period`。
□ 索引字段顺序为 `company, item_code, from_date, to_date`。
□ 迁移已创建同名索引，且 schema 为 `ly_schema`。
□ 测试覆盖索引存在性和字段顺序。
□ 定向测试、全量 pytest、unittest、py_compile 通过。
□ 未注册利润 API，未修改前端，未进入 TASK-005D/TASK-006。

【预计工时】
0.25-0.5 天

════════════════════════════════════════════════════════════════════════════
