# TASK-004C5 前端 CI 平台 Required Check 闭环工程任务单

- 任务编号：TASK-004C5
- 模块：生产计划集成 / 前端工程基建 / GitHub 平台门禁
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 20:51 CST
- 作者：技术架构师
- 审计来源：审计意见书第 70 份，TASK-004C4 通过；最优先风险为 GitHub 平台侧 required check 尚未闭环
- 前置依赖：TASK-004C4 已通过
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.9；`ADR-067`
- 任务边界：只做 GitHub hosted runner 实跑证据、required check 配置证据和证据文档；不新增业务功能，不修改前后端业务逻辑，不进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C5
模块：前端 CI 平台 Required Check 闭环
优先级：P0（平台级合并门禁固化）
════════════════════════════════════════════════════════════════════════════

【任务目标】
由仓库管理员完成 GitHub 平台侧闭环：实跑 `Frontend Verify Hard Gate / lingyi-pc-verify`，确认 hosted runner 通过，并将该 check 配置为主干 required check。

【模块概述】
TASK-004C4 已在仓库内补齐前端 verify workflow、Node/npm 版本锁定和本地验证。但 workflow 文件存在并不等于平台合并门禁已经生效。第 70 份审计指出，还需要管理员在 GitHub 平台完成 hosted runner 实跑、artifact/日志核验和 branch protection required check 配置，才能把本地门禁真正升级为团队合并硬约束。

【涉及文件】

允许新建：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C5_前端CI平台闭环证据.md

允许修改：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md（仅允许记录 TASK-004C5 状态）
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md（仅允许追加会话记录）

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/.github/workflows/frontend-verify.yml（除非审计官明确指出 workflow 文件本身有问题）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/**
- 任意 TASK-005/TASK-006 文件

【管理员必须完成】

1. 在 GitHub 平台手动触发或通过 PR 触发 workflow：`Frontend Verify Hard Gate`。
2. 确认 job `lingyi-pc-verify` 在 hosted runner 上执行成功。
3. 核验日志中存在以下关键步骤且均成功：
   - `Setup Node`
   - `Assert Node and npm versions`
   - `Install dependencies`
   - `Run frontend verify`
   - `Audit high vulnerabilities`
4. 核验日志中 `node -v` 为 `v22.22.1`。
5. 核验日志中 `npm -v` 为 `10.9.4`。
6. 核验日志中 `npm ci` 成功。
7. 核验日志中 `npm run verify` 成功。
8. 核验日志中 `npm audit --audit-level=high` 成功。
9. 在 GitHub branch protection 或 ruleset 中，将 required check 配置为：`Frontend Verify Hard Gate / lingyi-pc-verify`。
10. 确认 main 分支合并策略要求该 required check 通过。

【证据文档要求】

必须创建：
`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C5_前端CI平台闭环证据.md`

文档必须包含：

```markdown
# TASK-004C5 前端 CI 平台闭环证据

- 任务编号：TASK-004C5
- 更新时间：YYYY-MM-DD HH:MM CST
- 执行人：
- GitHub 仓库：
- Workflow 名称：Frontend Verify Hard Gate
- Job 名称：lingyi-pc-verify
- 运行方式：workflow_dispatch / pull_request / push main
- Run URL：
- Commit SHA：
- Branch：

## Hosted Runner 结果

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| Setup Node 成功 | 通过/不通过 | 日志行或截图说明 |
| node -v = v22.22.1 | 通过/不通过 | 日志行 |
| npm -v = 10.9.4 | 通过/不通过 | 日志行 |
| npm ci 成功 | 通过/不通过 | 日志行 |
| npm run verify 成功 | 通过/不通过 | 日志行 |
| npm audit --audit-level=high 成功 | 通过/不通过 | 日志行 |

## Required Check 配置

- Branch protection / Ruleset 名称：
- 受保护分支：main
- Required check 名称：Frontend Verify Hard Gate / lingyi-pc-verify
- 配置结果：通过/不通过
- 证据：截图说明或平台页面记录

## 敏感信息检查

- Run URL 中无 token：通过/不通过
- 日志摘录无 password/token/secret/cookie 明文：通过/不通过
- 截图或文档无 GitHub token、npm token、cookie、私钥：通过/不通过

## 结论

- 结论：通过/不通过
- 备注：
```

【验收标准】

□ GitHub hosted runner 已实跑 `Frontend Verify Hard Gate`。  
□ job `lingyi-pc-verify` 通过。  
□ 证据文档记录 Run URL。  
□ 证据文档记录 Commit SHA。  
□ 证据文档记录 Branch。  
□ 证据文档确认 Node 为 `v22.22.1`。  
□ 证据文档确认 npm 为 `10.9.4`。  
□ 证据文档确认 `npm ci` 成功。  
□ 证据文档确认 `npm run verify` 成功。  
□ 证据文档确认 `npm audit --audit-level=high` 成功。  
□ GitHub branch protection/ruleset 已将 `Frontend Verify Hard Gate / lingyi-pc-verify` 配置为 main 分支 required check。  
□ 证据文档无 token、password、secret、cookie、私钥等敏感信息。  
□ 未修改前端业务代码。  
□ 未修改后端业务代码。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止把本地 `npm run verify` 当成 hosted runner 实跑证据。
- 禁止只创建 workflow 但不配置 required check。
- 禁止使用截图或日志时暴露 token、cookie、password、secret、私钥。
- 禁止修改前端 production 业务代码。
- 禁止修改后端业务代码。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

管理员/工程师完成后按以下格式回复：

```text
TASK-004C5 已完成。

平台闭环结果：
1. Frontend Verify Hard Gate hosted runner：通过 / 不通过
2. Run URL：...
3. Commit SHA：...
4. Branch：...
5. Required check：Frontend Verify Hard Gate / lingyi-pc-verify 已配置 / 未配置

证据文件：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C5_前端CI平台闭环证据.md

敏感信息检查：
- 无 token/password/secret/cookie/私钥泄露：是 / 否

未进入范围：
- 未修改前端业务代码
- 未修改后端业务代码
- 未进入 TASK-005/TASK-006
```
