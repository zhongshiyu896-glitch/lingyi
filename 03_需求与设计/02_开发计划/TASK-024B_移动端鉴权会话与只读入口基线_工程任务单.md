# TASK-024B 移动端鉴权会话与只读入口基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-024B
- 任务名称：移动端鉴权会话与只读入口基线
- 角色：架构师
- 优先级：P1
- 状态：审计通过（审计意见书第 224 份）
- 前置依赖：TASK-024A 审计通过（审计意见书第 216 份；第 221 份状态复核通过）

## 2. 任务目标

基于 `TASK-024A` 已冻结的移动端 / 小程序渠道边界，输出第一张可执行工程子任务，范围限定为共享鉴权会话与只读入口基线收口：

1. 清理终端共享请求层对本地持久化敏感凭据的依赖。
2. 统一终端侧鉴权入口继续走受控 API 与 `credentials: 'include'` 路径。
3. 保持当前只读入口语义，不放开真实写链路，不创建移动端 / 小程序新代码仓或新应用骨架。

## 2.1 当前门禁状态

1. `TASK-024A` 已正式通过，A 允许拆分 `TASK-024B`。
2. 本文档已完成 C 正式复核并通过，允许 A 保留 `TASK-024B` 为后续候选实现任务。
3. 在 `build_release_allowed=no` 条件下，当前仍不得直接放行 B 进入实现。

## 2.2 已确认的现状差异

当前共享前端请求层仍存在终端本地持久化敏感凭据依赖，与 `TASK-024A` 的渠道安全边界冲突：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/auth.ts:59`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/request.ts:10`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/bom.ts:119`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts:150`

上述位置都直接读取 `window.localStorage.getItem('LY_AUTH_TOKEN')` 或 `window.localStorage.getItem('token')`。

## 3. 允许范围

1. 允许修改以下共享前端文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/auth.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/request.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/bom.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts`
2. 允许只在必要时补充以下测试或验证文件：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_auth_actions.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_error_envelope.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_request_id_sanitization.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_security_audit.py`
3. 允许同步更新当前任务单与 C 复核指令。

## 4. 禁止范围

1. 禁止新建移动端 App、小程序、H5 独立工程目录。
2. 禁止修改 `06_前端/lingyi-pc/src/views/**`、`06_前端/lingyi-pc/src/router/**`、`07_后端/lingyi_service/app/routers/**`（除非 C 复核后另行放行）。
3. 禁止修改 `07_后端/**` 业务实现、`.github/**`、`02_源码/**`。
4. 禁止引入终端直连 ERPNext / Frappe `/api/resource`。
5. 禁止新增本地持久化 `Authorization`、`Cookie`、`Token`、`Secret`、明文 DSN。
6. 禁止放开真实写链路；扫码、上传、推送绑定、协同确认等候选写入继续冻结。
7. 禁止声明移动端 / 小程序已实现完成、已联调完成、已发布完成。
8. 禁止 push / remote / PR / 生产发布。

## 5. 必须输出

1. 共享请求层不再从 `localStorage` 读取 `LY_AUTH_TOKEN` 或 `token`。
2. 终端鉴权继续走受控 API 与 `credentials: 'include'`，不得引入新的持久化敏感凭据方案。
3. 401 / 403 / 503 失败语义保持 fail-closed，不得返回伪成功。
4. 现有只读入口不被放宽，不得借本任务开放真实写入。
5. 若需要补测试，只能补与鉴权、请求头、审计脱敏、request_id 安全相关的最小验证。

## 6. 验收标准

1. `06_前端/lingyi-pc/src/api/*.ts` 中不再存在 `localStorage.getItem('LY_AUTH_TOKEN')` 或 `localStorage.getItem('token')`。
2. 共享请求层仍保留 `credentials: 'include'`，且未新增裸 `fetch/axios` 绕过现有受控封装。
3. `TASK-024A` 的以下设计约束未被破坏：
   - 终端本地不得持久化敏感凭据。
   - 资源存在但越权 / 资源不存在继续对外收口为受控语义。
   - 不开放 ERPNext 直连。
   - 不放开候选写链路。
4. 产出仍限定在允许范围文件内。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
rg -n "localStorage\.getItem\('LY_AUTH_TOKEN'\)|localStorage\.getItem\('token'\)" \
  '06_前端/lingyi-pc/src/api'
npm --prefix '06_前端/lingyi-pc' run typecheck
npm --prefix '06_前端/lingyi-pc' run build
git diff --name-only -- '06_前端/lingyi-pc/src/api' '07_后端/lingyi_service/tests' '.github' '02_源码'
```

## 8. 完成回报

```text
TASK-024B 执行完成。
结论：待审计
是否移除 localStorage 敏感凭据读取：是 / 否
是否新增移动端/小程序独立工程：否
是否放开真实写链路：否
是否修改前端视图/后端业务实现/.github/02_源码：否
是否 push/remote/PR：否
```
