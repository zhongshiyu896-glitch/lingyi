# TASK-014B3 管理员平台证据缺失升级处置单

- 任务编号：TASK-014B3
- 任务名称：管理员平台证据缺失升级处置单
- 角色：架构师
- 优先级：P0
- 前置依赖：TASK-014B2 执行完成且四个 gate 仍为 missing
- 任务类型：阻塞升级与管理员回传清单冻结
- 当前结论：REL 平台阻塞未解除

## 一、升级目标

将 TASK-014B / TASK-014B1 / TASK-014B2 连续无法取得真实 Hosted Runner 平台证据的状态，正式升级为“管理员外部阻塞”；冻结后续唯一可接受的最小平台证据包，避免继续重复执行无效回填任务。

## 二、当前事实（冻结）

1. `TASK-014B`：未提供 Run URL / artifact / PostgreSQL JUnit。
2. `TASK-014B1`：已补齐失败/阻塞说明。
3. `TASK-014B2`：四个 gate 仍为 `missing`。
4. Hosted Runner 未闭环。
5. Branch Protection required checks 未闭环。
6. 不允许进入 `TASK-014C`。
7. 不允许生产发布。

## 三、管理员最小回传清单（一次性）

管理员必须一次性回传以下材料；任一缺失即视为平台证据包不完整：

1. GitHub 仓库 URL。
2. 当前分支名。
3. 当前 commit SHA。
4. 四个 workflow run URL：
   - `Frontend Verify Hard Gate / lingyi-pc-verify`
   - `Backend Test Hard Gate / lingyi-service-test`
   - `Backend PostgreSQL Hard Gate / postgresql-non-skip-gate`
   - `Docs Boundary Gate / docs-boundary-check`
5. 四个 gate 的 conclusion。
6. 四个 gate 的 artifact 链接或下载归档路径。
7. PostgreSQL JUnit 指标：
   - `tests`
   - `skipped`
   - `failures`
   - `errors`
8. CI metadata artifact。
9. workflow log / artifact / JUnit / evidence 的敏感信息扫描结论。
10. Branch Protection required checks 配置截图或 API 响应。

## 四、阻塞升级结论（冻结口径）

在管理员未提供最小平台证据包之前：
- 不再重复执行 TASK-014B / TASK-014B2。
- 不进入 TASK-014C。
- 不声明 required checks 闭环。
- 不生产发布。
- 允许继续进行不依赖平台闭环的文档规划任务，但不得绕过该阻塞进入发布链路。

## 五、执行边界与禁止事项

- 禁止伪造 Run URL。
- 禁止用本地测试结果替代平台结果。
- 禁止写业务代码。
- 禁止修改前端、后端、`.github`、`02_源码`。
- 禁止 push。
- 禁止配置 remote。
- 禁止创建 PR。
- 禁止声明平台 required checks 已闭环。
- 禁止生产发布。

## 六、恢复条件

仅当管理员提交完整且可核验的最小平台证据包后，才允许重新执行 `TASK-014B` 进行真实平台证据回填复核。

## 七、状态声明

- 本处置单不代表平台闭环完成。
- 本处置单不代表 Hosted Runner 通过。
- 本处置单仅用于将 REL 平台阻塞升级为管理员外部阻塞并冻结后续证据输入要求。
