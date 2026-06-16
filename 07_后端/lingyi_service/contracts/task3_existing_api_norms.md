# 任务3 既有后端接口规范

范围：本文件只固化当前真实 FastAPI 后端已经采用的接口口径。任务3不创建新规范、不迁移错误码、不改变生产权限源、不实现库存/财务写闭环。

## 响应信封

- 成功固定为 `{"code":"0","message":"success","data":...}`。
- 失败固定为 `{"code":错误码,"message":错误说明,"data":{} 或 null}`。
- FastAPI `HTTPException` 已由 `app/main.py` 统一补 `data:{}`；业务代码不得改成 `success/data/error` 自创结构。

## 错误码

- 沿用 `app/core/error_codes.py` 与 `app/core/permissions.py` 的既有错误码。
- 未登录：`AUTH_UNAUTHORIZED` 或既有兼容的 `AUTH_UNAUTHENTICATED`，HTTP 401。
- 无权限：`AUTH_FORBIDDEN`，HTTP 403。
- 生产权限源不可用等场景沿用既有 `PERMISSION_SOURCE_UNAVAILABLE`、`ERPNEXT_*`、模块级错误码。
- 任务3不引入任何新命名错误码。

## 鉴权

- dev/test/local 联调用既有头：`X-LY-Dev-User` 与 `X-LY-Dev-Roles`。
- 全权限联调角色使用 `X-LY-Dev-Roles: System Manager`。
- dev header 只在 development/test/local 且显式允许时生效；生产不得依赖 dev header。
- 生产权限源是否脱 ERPNext：PARKED。当前 `app/main.py` 要求 `APP_ENV=production` 时 `LINGYI_PERMISSION_SOURCE=erpnext`，任务2/3不修改。

## 查询参数

- 分页参数沿用 `page`、`page_size`。
- 日期区间沿用 `from_date`、`to_date`，不新增 `startDate/endDate`。
- 关键词沿用 `keyword`，不新增 `searchText/q`。
- 公司过滤沿用既有 `company`；dev 兜底只用于已确认的 dev/test 场景。
- 其它筛选参数必须以现有 router 函数签名为准，不为前端单独创造别名。

## 分页

- 标准列表结构：`{"items":[],"total":0,"page":1,"page_size":20}`。
- 默认 `page=1`、`page_size=20`。
- 新增或 readiness 列表上限为 100；非法、空值或超上限按现有 helper 回落，不扩大返回量。
- 不允许用 404 表示空列表；空数据返回标准分页空列表。

## 前端接入分级

- A 类：真实业务接口；GET 只读可进入前端候选，写接口仍需单独任务验落库、权限、审计、幂等。
- B 类：dev/test readiness 只读接口；仅用于临时联调，生产默认关闭。
- C 类：readiness flow 回执桩；不能作为真实写接口。
- D 类：内部、诊断、worker 接口；不允许页面直连。

## 暂停项

- ERPNext 权限源 PARKED：任务2/3只记录现状，不实现脱 ERPNext。
- 库存/财务内核 PARKED：任务2/3只做页面只读接入对表，不自建库存台账、应收应付或总账写闭环。
