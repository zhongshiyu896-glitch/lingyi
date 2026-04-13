# TASK-004C7 项目根仓库根策略落地证据

- 任务编号：TASK-004C7
- 更新时间：2026-04-13 21:20 CST
- 执行人：Codex 自动化代理（线程 B）
- 结论：部分通过（本地仓库根整改完成；GitHub 平台项待管理员执行）

## 架构决策

- 采用方案：项目根作为唯一 GitHub 仓库根
- 仓库根：`/Users/hh/Desktop/领意服装管理系统`
- 不采用方案：把 `.github`、`06_前端`、`07_后端` 迁入 `/02_源码`

## 嵌套 git 备份

- 原嵌套 git 路径：`/Users/hh/Desktop/领意服装管理系统/02_源码/.git`
- 备份文件：`/Users/hh/Desktop/领意服装管理系统_git_backups/02_源码_git_20260413_211316.tar.gz`
- SHA256：`699553d94ff9f730b8ed7c505a306008acd1dced7d333c6d26a1146f36564daf`
- 迁出目录：`/Users/hh/Desktop/领意服装管理系统_git_backups/02_源码.git.backup_20260413_211323`
- 是否已移出项目目录：是

## Git 根确认

- `git rev-parse --show-toplevel`：`/Users/hh/Desktop/领意服装管理系统`
- `git remote -v`：空（未配置 remote）
- 当前分支：`main`
- Commit SHA：无（当前仓库尚未产生首个 commit）

## 关键文件跟踪确认

| 文件 | git ls-files 可见 | git check-ignore 命中 | 结论 |
| --- | --- | --- | --- |
| `.github/workflows/frontend-verify.yml` | 是 | 否 | 通过 |
| `.github/workflows/backend-postgresql.yml` | 是 | 否 | 通过 |
| `06_前端/lingyi-pc/package.json` | 是 | 否 | 通过 |
| `07_后端/lingyi_service/requirements.txt` | 是 | 否 | 通过 |
| `03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` | 是 | 否 | 通过 |

## GitHub 平台确认

- GitHub 仓库 URL：未配置（阻塞）
- `Frontend Verify Hard Gate` 是否可见：待管理员配置 remote 后验证
- `Backend PostgreSQL Hard Gate` 是否可见：待管理员配置 remote 后验证
- Frontend Hosted Runner Run URL：无（阻塞）
- `Frontend Verify Hard Gate / lingyi-pc-verify`：未执行（阻塞）
- main required check 是否已配置：否（阻塞）

## 已完成命令证据

```bash
cd /Users/hh/Desktop/领意服装管理系统
git init -b main
git rev-parse --show-toplevel
# /Users/hh/Desktop/领意服装管理系统

git symbolic-ref --short HEAD
# main

git ls-files .github/workflows/frontend-verify.yml .github/workflows/backend-postgresql.yml \
  "06_前端/lingyi-pc/package.json" "07_后端/lingyi_service/requirements.txt" \
  "03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md"
# 均可见

git check-ignore -v .github/workflows/frontend-verify.yml .github/workflows/backend-postgresql.yml \
  "06_前端/lingyi-pc/package.json" "07_后端/lingyi_service/requirements.txt" \
  "03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md"
# 无输出（未被忽略）
```

## 平台侧待办（管理员）

1. 在项目根仓库配置 `origin` remote 并推送 `main`。
2. 在 GitHub Actions 实跑 `Frontend Verify Hard Gate / lingyi-pc-verify`。
3. 在主干分支配置 required check：`Frontend Verify Hard Gate / lingyi-pc-verify`。
4. 回填 run URL、required check 配置截图/记录后提交审计复核。

## 敏感信息检查

- `git remote -v` 输出无 token：通过（当前为空）
- 当前证据无 password/token/secret/cookie/私钥：通过

