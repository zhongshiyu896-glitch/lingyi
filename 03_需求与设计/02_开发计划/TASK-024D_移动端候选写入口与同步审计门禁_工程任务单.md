# TASK-024D 移动端候选写入口与同步审计门禁 工程任务单

## 1. 基本信息

- 任务编号：TASK-024D
- 任务名称：移动端候选写入口与同步审计门禁
- 角色：架构师
- 优先级：P1
- 状态：通过（待执行）；C 审计意见书第229份（PASS / 高危0）；第260份维持通过
- 前置依赖：TASK-024A 审计通过（审计意见书第 216 份；第 221 份状态复核通过）；TASK-024B 任务单复核通过（审计意见书第 224 份）；TASK-024C 任务单复核通过（审计意见书第 226 份；第 227 份状态复核通过）

## 2. 任务目标

基于 `TASK-024A` 已冻结的移动端 / 小程序渠道边界，以及 `TASK-024B`、`TASK-024C` 已通过的鉴权与只读投影任务单，继续拆分第三张移动端工程子任务，范围限定为候选写入口与同步门禁收口：

1. 冻结 `message_ack`、通知已读回执、协同确认、扫码、上传、离线同步、推送绑定 / 解绑等候选写入口的统一受控语义。
2. 明确这些入口在当前阶段只能保持 `disabled_by_design / pending_design / not_enabled` 等受控失败语义，不得升级为真实写链路。
3. 明确若后续在共享前端 API 层新增封装，只能做候选入口占位与审计上下文字段收口，不得新增真实业务写请求。
4. 本任务只形成可审计工程任务边界；在 `build_release_allowed=no` 条件下，不直接放行 B 实现。

## 2.1 当前门禁状态

1. `TASK-024A` 已正式通过，移动端链路允许继续拆分 `TASK-024B ~ TASK-024D`。
2. `TASK-024B` 已由 C 第 224 份任务单复核通过；`TASK-024C` 已由 C 第 226 份任务单复核通过，第 227 份状态复核确认结论未反转。
3. 第 228 份意见书仅阻止“把已通过的 `TASK-024C` 重复派给 C”，不反转 `TASK-024C` 已通过事实。
4. 本文档需先交 C 复核边界、验收标准、允许 / 禁止范围；C 未 PASS 前不得进入 B 实现。

## 2.2 设计依据

1. `TASK-024A` 已冻结协同确认候选入口、扫码 / 上传 / 离线缓存、推送与通知绑定等渠道能力，但明确这些能力在当前阶段不进入真实实现。
2. `TASK-024A` 已要求终端请求统一进入领意受控 API 层，不得直连 ERPNext / Frappe `/api/resource`。
3. `TASK-024A` 已冻结 `message_ack`、`scan_request`、`upload_request`、`sync_queued`、`sync_completed`、`sync_failed` 等操作审计事件口径。
4. `TASK-024B` 已完成共享鉴权会话与只读入口基线收口；`TASK-024C` 已完成待办、消息与只读看板投影边界收口。
5. `Sprint3_主执行计划.md` 明确移动端实现子任务顺序为 `024B -> 024C -> 024D`。

## 3. 允许范围

> 以下为后续 B 实现候选范围；本轮 A 仅输出任务单，不修改实现。

1. 允许在 C 复核通过且后续 `build_release_allowed=yes` 后，最小修改以下共享前端 API 文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/request.ts`
2. 允许在 C 复核通过且确有必要时新增一个共享前端 API 候选动作封装文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/mobile_candidate_actions.ts`
3. 允许只在必要时补充与受控失败语义、request_id / device_id 透传、审计脱敏相关的最小验证文件：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_error_envelope.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_request_id_sanitization.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_security_audit.py`
4. 允许同步更新当前任务单与 C 复核指令。

## 4. 禁止范围

1. 禁止新建移动端 App、小程序、H5 独立工程目录。
2. 禁止修改 `06_前端/lingyi-pc/src/views/**`、`06_前端/lingyi-pc/src/router/**`。
3. 禁止修改 `07_后端/**` 业务实现、`.github/**`、`02_源码/**`。
4. 禁止引入终端直连 ERPNext / Frappe `/api/resource`。
5. 禁止新增 `POST`、`PUT`、`PATCH`、`DELETE` 真实业务写请求。
6. 禁止把 `message_ack`、通知已读回执、协同确认、扫码、上传、离线同步、推送绑定 / 解绑从候选语义升级为真实写入。
7. 禁止新增本地持久化 `Authorization`、`Cookie`、`Token`、`Secret`、明文 DSN。
8. 禁止声明移动端 / 小程序已实现完成、已联调完成、已发布完成。
9. 禁止设置 `build_release_allowed=yes`、禁止放行 B、禁止 push / remote / PR / 生产发布。

## 5. 必须输出

1. 候选写入口必须统一进入受控前端 API 封装，不得出现绕过 `request.ts` 的裸 `fetch/axios`。
2. 当前阶段所有候选写入口只能返回 `disabled_by_design / pending_design / not_enabled` 等受控失败语义，不得返回伪成功。
3. 若新增 `mobile_candidate_actions.ts`，其职责只能是归并候选动作占位与审计上下文字段，不得定义真实业务写流程。
4. 必须明确最小上下文字段：`request_id`、`device_id`、`user_id`、`company`；缺字段默认 fail-closed。
5. 不得记录推送密钥、小程序密钥、Outbox 内部事件键、敏感凭据原文。
6. 本任务完成后，移动端链路仍保持“可继续规划 / 待后续放行”，不自动等同于允许实现。

## 6. 验收标准

1. 任务实现候选范围不包含 `views/**`、`router/**`、后端业务实现、`.github/**`、`02_源码/**`。
2. 新增或调整的移动端候选动作封装中，不存在 `POST`、`PUT`、`PATCH`、`DELETE` 真实业务写语义。
3. 不存在 ERPNext / Frappe `/api/resource` 直连。
4. 不存在 `localStorage.getItem('LY_AUTH_TOKEN')` 或 `localStorage.getItem('token')` 敏感凭据读取新增或残留。
5. `message_ack`、通知已读回执、协同确认、扫码、上传、离线同步、推送绑定 / 解绑仍保持候选冻结，不进入真实写入。
6. C 对本任务单出具正式复核结论前，不得放行 B。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
rg -n "(/api/resource|localStorage\.getItem\('LY_AUTH_TOKEN'\)|localStorage\.getItem\('token'\))" \
  '06_前端/lingyi-pc/src/api'
CHECK_FILES=(
  '06_前端/lingyi-pc/src/api/request.ts'
)
if [ -f '06_前端/lingyi-pc/src/api/mobile_candidate_actions.ts' ]; then
  CHECK_FILES+=('06_前端/lingyi-pc/src/api/mobile_candidate_actions.ts')
  rg -n "message_ack|ack|scan|upload|sync|bind|unbind|disabled_by_design|pending_design|not_enabled" \
    '06_前端/lingyi-pc/src/api/mobile_candidate_actions.ts'
  rg -n "method:\s*['\"](POST|PUT|PATCH|DELETE)['\"]|\.post\(|\.put\(|\.patch\(|\.delete\(" \
    '06_前端/lingyi-pc/src/api/mobile_candidate_actions.ts'
fi
git diff --name-only -- '06_前端/lingyi-pc/src/api' '06_前端/lingyi-pc/src/views' '06_前端/lingyi-pc/src/router' '07_后端' '.github' '02_源码'
```

## 8. 完成回报

```text
TASK-024D 执行完成。
结论：待审计
是否仅涉及候选写入口占位与同步门禁：是 / 否
是否新增移动端/小程序独立工程：否
是否放开 message_ack/扫码/上传/通知已读/推送绑定等真实写链路：否
是否直连 ERPNext/Frappe：否
是否修改前端视图/路由/后端业务实现/.github/02_源码：否
是否 push/remote/PR：否
```

## 8.1 审计回执

- 审计意见书第229份：2026-04-18 15:36 | 通过 | 高危0
- 审计意见书第260份：2026-04-18 21:34 | 通过（维持第229份）| 高危0
- C Auditor 确认：本任务单边界完整、可审计、未越权
