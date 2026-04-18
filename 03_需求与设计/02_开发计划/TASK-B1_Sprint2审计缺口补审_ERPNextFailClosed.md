# 【补审任务卡】TASK-B1 Sprint2审计缺口补审 - ERPNext Fail-Closed Adapter

- 任务编号：TASK-B1
- 任务名称：Sprint2 审计缺口补审（ERPNext Fail-Closed Adapter）
- 角色：审计官
- 优先级：P0
- 前置依赖：TASK-013C 审计通过；基线参考 HEAD `384970400f7a137e8384649bd73cab5ae2d33300`

## 补审范围
- 设计文档：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-008_ERPNext集成FailClosed规范.md`
- 实现代码：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_fail_closed_adapter.py`
- 相关契约：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`、`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py`
- 测试：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_erpnext_fail_closed_adapter.py`
- 交付证据：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-008B_ERPNextFailClosedAdapter公共实现_交付证据.md`、`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-008B1_ERPNextDocstatus类型FailClosed整改_交付证据.md`

## 审计要点
1. timeout / connection / 5xx 必须 fail closed，不得伪成功。
2. 401/403 必须映射授权失败语义，不得吞错。
3. 404 / malformed response 必须结构化失败。
4. docstatus 只允许 `0/1/2` 与字符串 `"0"/"1"/"2"`，非法类型必须拒绝。
5. 错误信息不得泄露 token/cookie/authorization/DSN/password。
6. 不得出现 `200 + 空数据` 伪成功。

## 通过标准
- 高危（P1）= 0。
- 中危（P2）<= 1（若存在必须有明确整改计划）。
- P1/P2 必须整改并复审通过后方可闭环。
- 关键测试通过：`test_erpnext_fail_closed_adapter.py`。
- 结论必须明确“是否允许进入下一任务”。

## 执行说明
1. 先读设计，再读实现，再读测试，最后核对交付证据一致性。
2. 必跑：
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_erpnext_fail_closed_adapter.py
.venv/bin/python -m py_compile app/services/erpnext_fail_closed_adapter.py tests/test_erpnext_fail_closed_adapter.py
```
3. 输出审计意见书，若不通过必须指向整改编号 `TASK-B1A`。

## 禁止事项
- 禁止修改 `06_前端/**`。
- 禁止修改 `07_后端/**`。
- 禁止修改 `.github/**`。
- 禁止修改 `02_源码/**`。
- 禁止 push / 禁止配置 remote / 禁止创建 PR。
- 禁止将本地验证表述为 hosted runner 或 required check 平台闭环。

## 完成后回复格式
```text
TASK-B1 执行完成。
审计结论：通过 / 有条件通过 / 不通过
问题项：高 X / 中 X / 低 X
是否允许进入下一任务：是 / 否
若否，整改任务：TASK-B1A
```
