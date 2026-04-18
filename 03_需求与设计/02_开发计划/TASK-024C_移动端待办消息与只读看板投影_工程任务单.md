# TASK-024C 移动端待办消息与只读看板投影 工程任务单

## 1. 基本信息

- 任务编号：TASK-024C
- 任务名称：移动端待办消息与只读看板投影
- 角色：架构师
- 优先级：P1
- 状态：审计通过（审计意见书第 226 份）
- 前置依赖：TASK-024A 审计通过（审计意见书第 216 份；第 221 份状态复核通过）；TASK-024B 任务单复核通过（审计意见书第 224 份）

## 2. 任务目标

基于 `TASK-024A` 已冻结的移动端 / 小程序渠道边界，以及 `TASK-024B` 已通过的鉴权会话与只读入口基线任务单，继续拆分第二张移动端工程子任务：

1. 冻结移动端 / 小程序侧待办、消息、提醒、生产 / 成本 / 供应链 / 质量轻量看板的只读投影入口。
2. 明确所有读取继续进入领意受控 API 层，不直连 ERPNext / Frappe `/api/resource`。
3. 明确 `message_ack`、通知已读回执、协同确认、扫码、上传、离线缓存等候选写入仍保持冻结，本任务不开放真实写链路。
4. 本任务只形成可审计工程任务边界；在 `build_release_allowed=no` 条件下，不直接放行 B 实现。

## 2.1 当前门禁状态

1. `TASK-024A` 已正式通过，移动端链路允许继续拆分 `TASK-024B ~ TASK-024D`。
2. `TASK-024B` 已由 C 第 224 份任务单复核通过，但当前没有 `build_release_allowed=yes`。
3. 本文档需先交 C 复核边界、验收标准、允许 / 禁止范围；C 未 PASS 前不得进入 B 实现。

## 2.2 设计依据

1. `TASK-024A` 第 37~42 行冻结了登录会话、待办消息、轻量看板、协同确认候选入口、扫码 / 上传 / 离线缓存、推送通知绑定等渠道能力。
2. `TASK-024A` 第 69~81 行要求终端请求统一进入领意受控 API 层、不得直连 ERPNext，候选写入默认冻结。
3. `TASK-024A` 第 149~154 行要求继承前端门禁，禁止裸 `fetch/axios`、禁止客户端持久化敏感凭据，终端上传 / 扫码 / 推送绑定涉及写入时必须后续单独放行。
4. `Sprint3_主执行计划.md` 明确移动端实现子任务顺序为 `024B -> 024C -> 024D`。

## 3. 允许范围

> 以下为后续 B 实现候选范围；本轮 A 仅输出任务单，不修改实现。

1. 允许在 C 复核通过且后续 `build_release_allowed=yes` 后，最小修改以下共享前端 API 文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/request.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/style_profit.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/subcontract.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/sales_inventory.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts`
2. 允许在 C 复核通过且确有必要时新增一个共享前端 API 聚合文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/mobile_readonly.ts`
3. 允许只在必要时补充与只读投影、权限拒绝、请求封装、脱敏审计相关的最小测试或验证说明。
4. 允许同步更新当前任务单与 C 复核指令。

## 4. 禁止范围

1. 禁止新建移动端 App、小程序、H5 独立工程目录。
2. 禁止修改 `06_前端/lingyi-pc/src/views/**`、`06_前端/lingyi-pc/src/router/**`。
3. 禁止修改 `07_后端/**` 业务实现、`.github/**`、`02_源码/**`。
4. 禁止引入终端直连 ERPNext / Frappe `/api/resource`。
5. 禁止新增本地持久化 `Authorization`、`Cookie`、`Token`、`Secret`、明文 DSN。
6. 禁止新增真实写接口、真实写按钮、真实写 worker、Outbox 写入执行路径。
7. 禁止把 `message_ack`、通知已读回执、协同确认、扫码、上传、离线缓存从候选语义升级为真实写入。
8. 禁止声明移动端 / 小程序已实现完成、已联调完成、已发布完成。
9. 禁止 push / remote / PR / 生产发布。

## 5. 必须输出

1. 只读投影入口必须复用现有受控 API client，不得绕过 `request.ts` 或现有受控封装。
2. 待办、消息、提醒、生产 / 成本 / 供应链 / 质量轻量看板只能返回只读数据投影，不得触发写入。
3. 权限不足、资源不存在、上游不可用必须保持受控失败语义，不得返回伪成功。
4. 不得记录敏感凭据、推送密钥、小程序密钥、Outbox 内部事件键。
5. 如新增 `mobile_readonly.ts`，其职责只能是组合现有只读 API，不得定义新业务域或绕过模块权限。

## 6. 验收标准

1. 任务实现候选范围不包含 `views/**`、`router/**`、后端业务实现、`.github/**`、`02_源码/**`。
2. 新增或调整的移动端只读投影 API 不包含 `POST`、`PUT`、`PATCH`、`DELETE` 写语义。
3. 不存在 ERPNext / Frappe `/api/resource` 直连。
4. 不存在 `localStorage.getItem('LY_AUTH_TOKEN')` 或 `localStorage.getItem('token')` 敏感凭据读取新增或残留。
5. `message_ack`、通知已读回执、协同确认、扫码、上传、离线缓存仍保持候选冻结，不进入真实写入。
6. C 对本任务单出具正式复核结论前，不得放行 B。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
rg -n "(/api/resource|localStorage\.getItem\('LY_AUTH_TOKEN'\)|localStorage\.getItem\('token'\))" \
  '06_前端/lingyi-pc/src/api'
CHECK_FILES=(
  '06_前端/lingyi-pc/src/api/production.ts'
  '06_前端/lingyi-pc/src/api/style_profit.ts'
  '06_前端/lingyi-pc/src/api/subcontract.ts'
  '06_前端/lingyi-pc/src/api/sales_inventory.ts'
  '06_前端/lingyi-pc/src/api/quality.ts'
)
if [ -f '06_前端/lingyi-pc/src/api/mobile_readonly.ts' ]; then
  CHECK_FILES+=('06_前端/lingyi-pc/src/api/mobile_readonly.ts')
fi
rg -n "method:\s*['\"](POST|PUT|PATCH|DELETE)['\"]|\.post\(|\.put\(|\.patch\(|\.delete\(" \
  "${CHECK_FILES[@]}"
npm --prefix '06_前端/lingyi-pc' run typecheck
npm --prefix '06_前端/lingyi-pc' run build
git diff --name-only -- '06_前端/lingyi-pc/src/api' '06_前端/lingyi-pc/src/views' '06_前端/lingyi-pc/src/router' '07_后端' '.github' '02_源码'
```

## 8. 完成回报

```text
TASK-024C 执行完成。
结论：待审计
是否仅涉及只读投影：是 / 否
是否新增移动端/小程序独立工程：否
是否放开 message_ack/扫码/上传/通知已读等真实写链路：否
是否直连 ERPNext/Frappe：否
是否修改前端视图/路由/后端业务实现/.github/02_源码：否
是否 push/remote/PR：否
```
