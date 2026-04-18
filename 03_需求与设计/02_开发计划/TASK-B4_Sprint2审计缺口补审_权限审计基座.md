# 【补审任务卡】TASK-B4 Sprint2审计缺口补审 - 权限审计基座

- 任务编号：TASK-B4
- 任务名称：Sprint2 审计缺口补审（权限与审计统一基座）
- 角色：审计官
- 优先级：P0
- 前置依赖：TASK-013C 审计通过；基线参考 HEAD `384970400f7a137e8384649bd73cab5ae2d33300`

## 补审范围
- 设计文档：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-007_权限与审计统一基座设计.md`
- 实现代码：
  - `app/services/permission_service.py`
  - `app/core/permissions.py`
  - `app/main.py`
  - `app/core/error_codes.py`
  - `app/services/audit_service.py`
- 测试：`tests/test_permissions*.py`、`tests/test_audit*.py`、`tests/test_error*.py`

## 审计要点
1. resource scope 缺字段/未知字段 fail closed。
2. 权限源不可用必须 fail closed，不得伪成功。
3. 全局异常处理的安全审计 fallback 覆盖新增 code。
4. 审计脱敏完整（Authorization/Cookie/Token/Secret/password/DSN 不落盘）。
5. 错误信封统一，禁止 `200 + 空数据` 伪成功。

## 通过标准
- 高危（P1）= 0。
- 中危（P2）<= 1（若存在必须有明确整改计划）。
- P1/P2 必须整改并复审通过后方可闭环。
- 定向测试通过且与既有模块兼容。

## 执行说明
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_permissions*.py tests/test_audit*.py tests/test_error*.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```
不通过下发 `TASK-B4A`。

## 禁止事项
- 禁止修改 `06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`。
- 禁止 push / remote / PR。
- 禁止以“兼容”为由放开 fail-closed。

## 完成后回复格式
```text
TASK-B4 执行完成。
审计结论：通过 / 有条件通过 / 不通过
问题项：高 X / 中 X / 低 X
是否允许进入下一任务：是 / 否
若否，整改任务：TASK-B4A
```
