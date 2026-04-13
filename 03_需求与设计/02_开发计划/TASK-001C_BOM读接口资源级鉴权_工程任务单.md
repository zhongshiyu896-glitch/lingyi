# TASK-001C BOM 读接口与展开接口资源级鉴权任务单

- 任务编号：TASK-001C
- 关联任务：TASK-001B 权限来源升级 ERPNext
- 优先级：P0
- 预计工时：1-2 天
- 输出人：技术架构师
- 更新时间：2026-04-12 10:05 CST
- 项目根目录：`/Users/hh/Desktop/领意服装管理系统/`
- 当前状态：待工程师整改

## 一、任务目标

为 BOM 读接口和展开接口补后端鉴权，确保 BOM 用料、工价、展开结果等敏感经营数据不能被未授权用户直接读取。

## 二、整改范围

必须整改接口：

| 接口 | 权限动作 | 说明 |
| --- | --- | --- |
| `GET /api/bom/` | `bom:read` | BOM 列表 |
| `GET /api/bom/{bom_id}` | `bom:read` | BOM 详情、物料和工序 |
| `POST /api/bom/{bom_id}/explode` | `bom:read` | BOM 展开结果、用量和工序成本 |

不在本任务范围：

1. 不改 BOM 表结构。
2. 不改 BOM 展开公式。
3. 不改外发、生产、工票、利润模块。
4. 不修改 `/02_源码/lingyi_apparel/` 历史 app。

## 三、涉及文件

修改后端：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_permission_adapter.py`

修改前端：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/bom.ts`

## 四、后端整改要求

1. 在 `permissions.py` 中新增或确认 `BOM_READ = "bom:read"`。
2. 将 `bom:read` 加入 `ALL_BOM_ACTIONS`。
3. 有 BOM 管理权限的角色默认包含 `bom:read`。
4. `GET /api/bom/` 增加 `current_user = Depends(get_current_user)`。
5. `GET /api/bom/` 调用 `ensure_permission(current_user, "bom:read")`。
6. `GET /api/bom/{bom_id}` 增加 `current_user = Depends(get_current_user)`。
7. `GET /api/bom/{bom_id}` 必须校验资源级权限：用户对该 BOM 的 `item_code` 有读取权限。
8. `POST /api/bom/{bom_id}/explode` 增加 `current_user = Depends(get_current_user)`。
9. `POST /api/bom/{bom_id}/explode` 必须校验资源级权限：用户对该 BOM 的 `item_code` 有读取权限。
10. 无登录态返回 401，错误码 `AUTH_UNAUTHORIZED`。
11. 无读取权限返回 403，错误码 `AUTH_FORBIDDEN`。

## 五、资源级权限要求

资源级校验规则：

1. 列表接口只能返回当前用户有权读取的 `item_code` 对应 BOM。
2. 详情接口必须先根据 `bom_id` 找到 BOM，再校验用户是否能读该 BOM 的 `item_code`。
3. 展开接口必须和详情接口使用同一套资源级读权限。
4. 如果 ERPNext `User Permission` 限制了 `Item` 或 `Company`，BOM 读权限必须受同样限制。
5. 如果当前 Sprint 仍使用 static 权限源，必须至少限制为拥有 `bom:read` 的用户才能读取。

## 六、前端整改要求

1. BOM 列表页加载前必须调用 `/api/auth/actions?module=bom`。
2. 无 `bom:read` 时不请求 `/api/bom/`，显示“无权查看 BOM”。
3. BOM 详情页加载前必须确认用户有 `bom:read`。
4. 展开按钮必须由 `bom:read` 控制。
5. 前端 `canRead` 只能控制显示，不能作为唯一权限边界。
6. 401 统一提示登录失效。
7. 403 统一提示无权访问。

## 七、验收标准

必须全部满足：

□ 未登录调用 `GET /api/bom/` 返回 401，错误码 `AUTH_UNAUTHORIZED`。

□ 无 `bom:read` 用户调用 `GET /api/bom/` 返回 403，错误码 `AUTH_FORBIDDEN`。

□ 无 `bom:read` 用户调用 `GET /api/bom/{bom_id}` 返回 403。

□ 无 `bom:read` 用户调用 `POST /api/bom/{bom_id}/explode` 返回 403。

□ 有 `bom:read` 但无目标 `item_code` 权限的用户，不能读取该 BOM 详情。

□ BOM 列表只返回当前用户有权读取的 BOM。

□ 前端无 `bom:read` 时不展示 BOM 数据和展开结果。

□ 后端 `GET /api/bom/`、`GET /api/bom/{bom_id}`、`POST /api/bom/{bom_id}/explode` 均有 `Depends(get_current_user)`。

□ `rg 'bom:read' /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app` 能看到权限动作、router 校验、权限聚合。

## 八、工程师回报格式

```text
TASK-001C BOM 读接口资源级鉴权完成

后端文件：
- ...

前端文件：
- ...

自测结果：
- 未登录 GET /api/bom/ 返回 401：通过 / 失败
- 无 bom:read GET /api/bom/ 返回 403：通过 / 失败
- 无 bom:read GET /api/bom/{bom_id} 返回 403：通过 / 失败
- 无 bom:read POST /api/bom/{bom_id}/explode 返回 403：通过 / 失败
- 有 bom:read 但无 item_code 权限读取详情失败：通过 / 失败
- 前端无 bom:read 不展示 BOM 数据：通过 / 失败

遗留问题：
- 无 / ...
```
