# TASK-005C4 利润模型本地仓库基线提交证据

- 任务编号：TASK-005C4
- 记录时间：2026-04-14 07:46:28 CST
- 仓库根：/Users/hh/Desktop/领意服装管理系统
- 当前分支：main
- 提交前 HEAD：9ed0bab
- remote 状态：未配置 remote（`git remote -v` 无输出）

## 验证结果

| 验证项 | 结果 |
| --- | --- |
| 定向 pytest | `43 passed, 1 warning` |
| 全量 pytest | `503 passed, 5 skipped, 903 warnings` |
| unittest discover | `Ran 492 tests ... OK` |
| py_compile | 通过，无输出 |

## 禁改边界扫描

| 命令 | 结果 |
| --- | --- |
| `git diff --name-only -- 06_前端 .github 02_源码` | 无输出 |
| `git diff --name-only -- 07_后端/lingyi_service/app/main.py 07_后端/lingyi_service/app/routers` | 无输出 |

## staged 白名单复核

`git diff --cached --name-only` 结果在白名单 stage 后记录：

```text
03_需求与设计/01_架构设计/03_技术决策记录.md
03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md
03_需求与设计/01_架构设计/架构师会话日志.md
03_需求与设计/02_开发计划/TASK-005C1_利润来源映射审计字段与状态FailClosed整改_工程任务单.md
03_需求与设计/02_开发计划/TASK-005C2_利润来源默认不纳入与字段契约收口整改_工程任务单.md
03_需求与设计/02_开发计划/TASK-005C3_利润快照期间索引补齐_工程任务单.md
03_需求与设计/02_开发计划/TASK-005C4_利润模型本地仓库基线提交_工程任务单.md
03_需求与设计/02_开发计划/TASK-005C4_利润模型本地仓库基线提交证据.md
03_需求与设计/02_开发计划/TASK-005C_利润模型迁移与来源映射设计_工程任务单.md
03_需求与设计/02_开发计划/当前 sprint 任务清单.md
03_需求与设计/05_审计记录.md
03_需求与设计/05_审计记录/审计官会话日志.md
07_后端/lingyi_service/app/models/__init__.py
07_后端/lingyi_service/app/models/style_profit.py
07_后端/lingyi_service/app/schemas/style_profit.py
07_后端/lingyi_service/app/services/style_profit_source_service.py
07_后端/lingyi_service/migrations/versions/task_005c_create_style_profit_tables.py
07_后端/lingyi_service/tests/test_style_profit_models.py
07_后端/lingyi_service/tests/test_style_profit_source_mapping.py
```

`git diff --cached --check` 结果：

```text
通过，无输出
```

## 提交记录

- 提交信息：`feat: add style profit model source mapping baseline`
- 提交后 HEAD：提交完成后由 `git rev-parse --short HEAD` 确认；该 SHA 无法预先写入同一个 commit 的文件内容中，最终值以交付回报为准。

## 边界声明

- 未 push。
- 未配置 remote。
- 未进入 TASK-005D。
- 未进入 TASK-006。
- 未注册利润 API。
- 未修改前端。
