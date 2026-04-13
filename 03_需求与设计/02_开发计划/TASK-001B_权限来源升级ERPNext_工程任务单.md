# TASK-001B 权限来源升级为 ERPNext 权威权限任务单

- 任务编号：TASK-001B
- 关联任务：TASK-001A BOM 鉴权权限审计整改
- 优先级：P1（生产前必须完成）
- 预计工时：2-4 天
- 输出人：技术架构师
- 更新时间：2026-04-12 09:49 CST
- 项目根目录：`/Users/hh/Desktop/领意服装管理系统/`
- 当前状态：待工程师开发

## 一、任务目标

将 BOM 权限动作来源从 FastAPI 静态角色映射升级为 ERPNext `Role / User Permission` 权威来源，并新增 FastAPI 权限聚合接口供前端按钮权限使用。

当前 `app/core/permissions.py` 中的静态角色映射只允许作为 Sprint 1 临时方案，不允许作为生产权限来源。

## 二、开发边界

必须遵守：

1. ERPNext 是权限权威来源。
2. FastAPI 只做权限聚合和动作映射，不自行成为最终权限事实源。
3. 前端按钮权限从 FastAPI `/api/auth/actions` 读取。
4. 后端写接口继续强制校验权限动作，不能只依赖前端按钮隐藏。
5. 不修改 `/02_源码/lingyi_apparel/` 历史 app。

禁止：

1. 禁止生产环境继续依赖 `LINGYI_ROLE_ACTIONS_JSON` 作为唯一权限来源。
2. 禁止在前端硬编码角色与按钮。
3. 禁止前端直接调用 ERPNext 权限 API。

## 三、涉及文件

新建后端文件：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/auth.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_permission_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/auth.py`

修改后端文件：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/auth.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py`

新建前端文件：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/auth.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts`

修改前端文件：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`

## 四、权限来源策略

### Sprint 1 临时方案

允许保留：

- `permissions.py` 内置角色映射
- `LINGYI_ROLE_ACTIONS_JSON`
- `X-LY-Dev-User`

限制：

1. 只允许开发和 Sprint 1 验收临时使用。
2. 必须受环境变量控制。
3. 生产环境默认禁用。
4. 代码注释必须标明“临时方案，生产前替换”。

### 生产前正式方案

权限来源顺序：

1. ERPNext `Role`
2. ERPNext `User Permission`
3. ERPNext `Workflow` 当前状态可执行动作
4. FastAPI 动作映射表

FastAPI 负责把 ERPNext 权限聚合为前端和后端可识别的动作码：

- `bom:create`
- `bom:update`
- `bom:publish`
- `bom:deactivate`
- `bom:set_default`
- `bom:read`

## 五、接口清单

统一前缀：`/api/auth/`

### 1. 当前用户信息

GET `/api/auth/me`

入参：

- 无

出参：

- username
- roles
- is_service_account
- source

### 2. 当前用户动作权限

GET `/api/auth/actions`

入参：

- module，可选，例如 `bom`
- resource_type，可选，例如 `bom`
- resource_id，可选，例如 `123`

出参：

- username
- module
- actions
- button_permissions

示例返回：

```json
{
  "code": "0",
  "message": "success",
  "data": {
    "username": "zhangsan",
    "module": "bom",
    "actions": [
      "bom:read",
      "bom:create",
      "bom:update"
    ],
    "button_permissions": {
      "create": true,
      "update": true,
      "publish": false,
      "deactivate": false,
      "set_default": false
    }
  }
}
```

### 3. BOM 资源动作权限

GET `/api/auth/actions/bom/{bom_id}`

入参：

- bom_id

出参：

- bom_id
- status
- actions
- button_permissions

用途：

1. 前端详情页按 BOM 当前状态显示按钮。
2. 后端可复用同一权限聚合逻辑。

## 六、ERPNext 集成要求

新增 `/app/services/erpnext_permission_adapter.py`。

必须封装：

1. 获取当前用户角色。
2. 获取当前用户 User Permission。
3. 判断用户是否可读 ERPNext `Item`。
4. 判断用户是否可对 BOM 关联的 `item_code` 执行业务动作。
5. 获取 Workflow 当前状态可执行动作，若该动作已接入 Workflow。

调用方式建议：

| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| User | REST API 或 method API | 获取当前用户 |
| Role | REST API 或 method API | 获取用户角色 |
| User Permission | REST API 或 method API | 获取数据权限 |
| Workflow | REST API 或 method API | 获取状态动作 |

## 七、动作映射规则

FastAPI 将 ERPNext 角色/权限映射为业务动作。

最低要求：

| ERPNext 权限/角色 | FastAPI 动作 |
| --- | --- |
| System Manager | 全部 BOM 动作 |
| BOM Manager | 全部 BOM 动作 |
| BOM Editor | `bom:read`, `bom:create`, `bom:update` |
| BOM Publisher | `bom:read`, `bom:publish`, `bom:set_default`, `bom:deactivate` |
| 仅可读用户 | `bom:read` |

数据权限要求：

1. 如果 ERPNext User Permission 限制了 `Item` 或 `Company`，BOM 动作必须受同样限制。
2. 用户没有目标 `item_code` 权限时，不能更新、发布、停用或设默认。
3. 权限校验失败返回 `AUTH_FORBIDDEN`。

## 八、前端按钮权限要求

前端必须从 `/api/auth/actions` 或 `/api/auth/actions/bom/{bom_id}` 读取按钮权限。

BOM 页面按钮映射：

| 页面按钮 | 权限动作 |
| --- | --- |
| 新建 BOM | `bom:create` |
| 保存草稿 | `bom:update` |
| 发布 BOM | `bom:publish` |
| 停用 BOM | `bom:deactivate` |
| 设置默认 | `bom:set_default` |
| 查看 | `bom:read` |

要求：

1. 无权限按钮不显示或置灰。
2. 按钮隐藏不能替代后端强校验。
3. 401 时提示登录失效。
4. 403 时提示无权执行该操作。

## 九、配置要求

新增环境变量：

- `LINGYI_PERMISSION_SOURCE`

可选值：

- `static`
- `erpnext`

规则：

1. 开发环境允许 `static`。
2. Sprint 1 可临时使用 `static`。
3. 生产环境必须使用 `erpnext`。
4. 当 `APP_ENV=production` 且 `LINGYI_PERMISSION_SOURCE!=erpnext` 时，应用启动必须报错。

## 十、验收标准

必须全部满足：

□ `GET /api/auth/me` 能返回当前用户 username 和 roles。

□ `GET /api/auth/actions?module=bom` 能返回 BOM 动作列表。

□ `GET /api/auth/actions/bom/{bom_id}` 能按 BOM 状态返回按钮权限。

□ 前端 BOM 新建按钮由 `bom:create` 控制。

□ 前端 BOM 发布按钮由 `bom:publish` 控制。

□ 前端 BOM 停用按钮由 `bom:deactivate` 控制。

□ 前端 BOM 设置默认按钮由 `bom:set_default` 控制。

□ 后端 BOM 写接口继续强制执行权限校验。

□ 无权限用户即使绕过前端直接调接口，也返回 403。

□ `LINGYI_PERMISSION_SOURCE=static` 时日志必须提示“临时权限来源，不可用于生产”。

□ `APP_ENV=production` 且 `LINGYI_PERMISSION_SOURCE=static` 时，应用启动失败。

□ 权限聚合逻辑至少有单元测试覆盖 System Manager、BOM Editor、BOM Publisher、无权限用户。

## 十一、自测命令建议

```bash
rg 'LINGYI_PERMISSION_SOURCE|/api/auth/actions|bom:create|bom:publish|bom:set_default' /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app
```

预期：

- 能看到权限来源配置、auth 路由、权限聚合和 BOM 动作码。

```bash
rg 'button_permissions|bom:create|bom:publish|bom:set_default' /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

预期：

- BOM 页面按钮从权限接口读取。

## 十二、工程师完成后回报格式

```text
TASK-001B 权限来源升级 ERPNext 开发完成

后端文件：
- ...

前端文件：
- ...

自测结果：
- GET /api/auth/me：通过 / 失败
- GET /api/auth/actions?module=bom：通过 / 失败
- GET /api/auth/actions/bom/{bom_id}：通过 / 失败
- 无权限用户直接调用 POST /api/bom/ 返回 403：通过 / 失败
- 前端 BOM 按钮按权限显示：通过 / 失败
- 生产环境 static 权限源启动失败：通过 / 失败

遗留问题：
- 无 / ...
```
