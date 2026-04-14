# TASK-005E3 款式利润详情接口鉴权前置整改工程任务单

## 任务编号

TASK-005E3

## 任务名称

款式利润详情接口鉴权前置整改

## 任务目标

修复 `GET /api/reports/style-profit/snapshots/{snapshot_id}` 先查询 snapshot 再校验 `style_profit:read` 的信息枚举风险。无读权限用户请求任意 snapshot_id，无论该 ID 是否存在，都必须优先返回 `403 + AUTH_FORBIDDEN`，不得通过 `403/404` 差异探测利润快照是否存在。

## 审计来源

TASK-005E2 复审结论：有条件通过，保留 1 个中危问题。

最需要优先处理的问题：详情接口仍然先查快照再做 `style_profit:read` 动作权限，导致无读权限用户可以通过“存在 ID 返回 403、不存在 ID 返回 404”探测利润快照是否存在。

## 严格边界

本任务只允许修复详情接口鉴权顺序与对应测试。

允许做：

1. 调整 `GET /api/reports/style-profit/snapshots/{snapshot_id}` 的动作权限校验顺序。
2. 补充无读权限用户访问存在 ID / 不存在 ID 均返回 403 的测试。
3. 补充授权用户访问不存在 ID 返回 404 的测试。
4. 保持详情接口资源权限和操作审计不回退。

禁止做：

1. 禁止修改利润计算公式。
2. 禁止修改来源采集器口径。
3. 禁止修改权限矩阵。
4. 禁止新增或修改 migrations。
5. 禁止修改前端。
6. 禁止修改 `.github`。
7. 禁止修改 `02_源码`。
8. 禁止进入 `TASK-006`。
9. 禁止实现导出、打印、加工厂对账。
10. 禁止扩大到前端联调。

## 允许修改文件

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_errors.py`

## 禁止修改文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006*`

## 具体实现要求

### 1. 动作权限前置

详情接口必须调整为以下顺序：

1. 登录鉴权。
2. 立即校验 `style_profit:read` 动作权限。
3. 动作权限失败，返回 `403 + AUTH_FORBIDDEN`，并写安全审计。
4. 动作权限通过后，查询 snapshot。
5. snapshot 不存在，返回 `404 + STYLE_PROFIT_NOT_FOUND`。
6. snapshot 存在后，按 `snapshot.company + snapshot.item_code` 做资源权限校验。
7. 资源权限通过后，读取 detail/source_map。
8. 详情读取成功写操作审计。
9. 详情读取失败写操作失败审计。

### 2. 禁止存在性枚举

无 `style_profit:read` 动作权限用户：

| 请求对象 | 返回 |
| --- | --- |
| 已存在 snapshot_id | `403 + AUTH_FORBIDDEN` |
| 不存在 snapshot_id | `403 + AUTH_FORBIDDEN` |

授权用户：

| 请求对象 | 返回 |
| --- | --- |
| 不存在 snapshot_id | `404 + STYLE_PROFIT_NOT_FOUND` |
| 存在但无资源权限 | `403 + AUTH_FORBIDDEN` |
| 存在且有资源权限 | `200 + code=0` |

### 3. 审计要求

1. 无动作权限返回 403 时必须写安全审计。
2. 不存在 snapshot 的授权用户 404，可以写操作失败审计；如现有规范已要求详情失败审计，则必须写。
3. 存在但无资源权限返回 403 时必须写安全审计。
4. 详情成功操作审计不得回退。
5. 详情操作审计失败不得返回详情，必须返回 `AUDIT_WRITE_FAILED`。

## 必测用例

- [ ] 无 `style_profit:read` 用户访问已存在 snapshot_id，返回 `403 + AUTH_FORBIDDEN`。
- [ ] 无 `style_profit:read` 用户访问不存在 snapshot_id，返回 `403 + AUTH_FORBIDDEN`。
- [ ] 上述两个 403 响应的错误信封一致，不暴露 ID 是否存在。
- [ ] 上述两个 403 均写安全审计。
- [ ] 有 `style_profit:read` 用户访问不存在 snapshot_id，返回 `404 + STYLE_PROFIT_NOT_FOUND`。
- [ ] 有 `style_profit:read` 但无 item/company 资源权限用户访问存在 snapshot_id，返回 `403 + AUTH_FORBIDDEN`。
- [ ] 详情接口仍然在资源权限通过后才读取 detail/source_map。
- [ ] 详情成功操作审计不回退。
- [ ] 详情操作审计失败返回 `AUDIT_WRITE_FAILED`。

## 测试命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q \
  tests/test_style_profit_api.py \
  tests/test_style_profit_api_permissions.py \
  tests/test_style_profit_api_audit.py \
  tests/test_style_profit_api_errors.py

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

- [ ] 详情接口 `style_profit:read` 动作权限已前置到 snapshot 查询之前。
- [ ] 无读权限访问存在 ID 返回 403。
- [ ] 无读权限访问不存在 ID 返回 403。
- [ ] 无读权限无法通过 403/404 差异探测快照存在性。
- [ ] 授权用户访问不存在 ID 返回 404。
- [ ] 授权但无资源权限访问存在 ID 返回 403。
- [ ] 403 权限拒绝写安全审计。
- [ ] 详情成功操作审计不回退。
- [ ] 详情操作审计失败返回 `AUDIT_WRITE_FAILED`。
- [ ] 定向 pytest 通过。
- [ ] 全量 pytest 通过。
- [ ] unittest discover 通过。
- [ ] py_compile 通过。
- [ ] 未修改前端。
- [ ] 未修改 `.github`。
- [ ] 未修改 `02_源码`。
- [ ] 未修改 migrations。
- [ ] 未进入 TASK-006。

## 交付回报格式

```text
TASK-005E3 已完成。

修复内容：
- 详情接口动作权限前置：[已修复/未修复]
- 存在性枚举风险：[已关闭/未关闭]
- 详情安全审计：[已覆盖/未覆盖]
- 详情操作审计：[已覆盖/未覆盖]

验证结果：
- API 定向 pytest：[结果]
- 全量 pytest：[结果]
- unittest discover：[结果]
- py_compile：[结果]
- 禁改扫描：[通过/不通过]

关键证明：
- 无读权限 + 已存在 ID 返回 403：[证明]
- 无读权限 + 不存在 ID 返回 403：[证明]
- 有读权限 + 不存在 ID 返回 404：[证明]

确认：
- 未修改前端
- 未修改 .github
- 未修改 02_源码
- 未修改 migrations
- 未进入 TASK-006
```
