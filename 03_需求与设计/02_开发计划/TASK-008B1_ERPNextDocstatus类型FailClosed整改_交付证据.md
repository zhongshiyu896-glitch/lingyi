# TASK-008B1 ERPNext docstatus 类型 Fail-Closed 整改交付证据

## 1. 修复说明
- 修复文件：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_fail_closed_adapter.py`
- 问题根因：`_coerce_docstatus()` 使用 `int(raw_docstatus)` 强转，导致 `bool/float/非精确字符串` 被误接收。
- 本次修复：
  - 仅接受 `int` 且值为 `0/1/2`
  - 仅接受字符串精确值：`"0"/"1"/"2"`
  - 显式拒绝 `bool`
  - 非法类型/非法值统一抛 `ERPNEXT_DOCSTATUS_INVALID`
  - 缺失 `docstatus` 保持 `ERPNEXT_DOCSTATUS_REQUIRED`
- 同时在 `normalize_erpnext_response()` 中区分“字段缺失”和“字段存在但值非法”：
  - `docstatus` 字段不存在 -> 走缺失分支（后续 `ERPNEXT_DOCSTATUS_REQUIRED`）
  - `docstatus` 字段存在但值非法（含 `None`）-> 立即 `ERPNEXT_DOCSTATUS_INVALID`

## 2. 合法 docstatus 输入清单
- `0`
- `1`
- `2`
- `"0"`
- `"1"`
- `"2"`

## 3. 非法 docstatus 输入清单
- `True`
- `False`
- `1.2`
- `0.0`
- `""`
- `" "`
- `"01"`
- `"1.0"`
- `"submitted"`
- `None`（字段存在但值为 `None`）
- `[]`
- `{}`

处理结果：上述非法输入全部 fail closed，错误码为 `ERPNEXT_DOCSTATUS_INVALID`。

## 4. 测试结果
执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. `.venv/bin/python -m pytest -q tests/test_erpnext_fail_closed_adapter.py`
- 结果：`19 passed`

2. `.venv/bin/python -m py_compile app/services/erpnext_fail_closed_adapter.py tests/test_erpnext_fail_closed_adapter.py`
- 结果：通过

新增覆盖点：
- `test_normalize_accepts_exact_docstatus_literals`
- `test_normalize_rejects_malformed_docstatus_literals`
- 缺失字段场景继续由 `test_missing_docstatus_fail_closed` 验证 `ERPNEXT_DOCSTATUS_REQUIRED`

## 5. 禁改扫描结果
执行目录：`/Users/hh/Desktop/领意服装管理系统`

1. `git diff --name-only -- 06_前端 .github 02_源码`
- 结果：空输出

2. `git diff --name-only -- 07_后端/lingyi_service/migrations`
- 结果：空输出

3. `git diff --cached --name-only`
- 结果：空输出（未暂存、未提交）

## 6. 剩余风险
- 仍存在历史 `datetime.utcnow()` deprecation warnings（非本任务范围）。
- 本次仅修复公共 docstatus 类型判定，旧业务 adapter 仍有后续分批接入公共基座空间。
