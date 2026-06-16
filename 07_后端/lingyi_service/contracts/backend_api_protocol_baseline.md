# 后端统一协议与权限基础规范

本文件对应 `FastAPI后端长期开发单_20260616` 任务3，记录当前后端统一口径和后续硬门禁。

## 响应信封

- 成功：`{"code":"0","message":"success","data":...}`。
- 失败：`{"code":错误码,"message":错误说明,"data":{} 或 null}`；可附带 `request_id`，但不得替换既有信封。
- 当前仓库仍使用既有错误码，如 `AUTH_UNAUTHORIZED` / `AUTH_FORBIDDEN`；开发单建议的新错误码需要单独迁移任务，不能在本轮破坏既有前端/测试。

## 分页

- 标准列表：`{"items":[],"total":0,"page":1,"page_size":20}`。
- 默认 `page=1`，`page_size=20`；readiness 端口上限 100，非法或超上限回落默认值。

## 权限

- 开发/测试联调用 `X-LY-Dev-User` 与 `X-LY-Dev-Roles`，生产必须关闭 dev header。
- 业务接口必须后端鉴权，前端隐藏按钮不能替代接口权限。
- readiness/stub 只能在 development/dev/local/test 挂载，生产 route table 不应出现对应路径。

## 接入规则

- A 类真实 GET 接口可进入前端只读接入候选。
- A 类写接口必须经单独任务验证真实落库、权限、审计、幂等/冲突处理后才可接。
- B 类 readiness 只读接口只作为临时联调辅助。
- C 类 readiness flow 回执桩不得当作真实写接口。
- D 类内部/诊断接口不得给页面直连。
