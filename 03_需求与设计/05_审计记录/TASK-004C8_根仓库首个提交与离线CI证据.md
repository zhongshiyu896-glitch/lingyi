# TASK-004C8 根仓库首个提交与离线 CI 证据

- 任务编号：TASK-004C8
- 更新时间：2026-04-13 21:33 CST
- 执行人：Codex 自动化代理（线程 B）
- 结论：通过（首个提交清单满足要求，离线 CI 模拟通过）

## 一、当前阻断修复结果

已按任务单将首个提交扩展到 workflow、前端构建与契约脚本、后端应用与测试与迁移目录，且保持禁止路径未入 index。

## 二、.gitignore 核验

### 1) 生成物命中 ignore（通过）

- `06_前端/lingyi-pc/node_modules`
- `06_前端/lingyi-pc/dist`
- `07_后端/lingyi_service/.venv`
- `07_后端/lingyi_service/lingyi_service.db`
- `07_后端/lingyi_service/.pytest-postgresql.xml`

### 2) 关键源码与 workflow 未被 ignore（通过）

- `.github/workflows/frontend-verify.yml`
- `.github/workflows/backend-postgresql.yml`
- `06_前端/lingyi-pc/package-lock.json`
- `06_前端/lingyi-pc/scripts/check-production-contracts.mjs`
- `06_前端/lingyi-pc/src/api/production.ts`
- `07_后端/lingyi_service/app/main.py`
- `07_后端/lingyi_service/tests/test_production_plan.py`

## 三、首个提交清单核验

### 1) 禁止路径未进入 index（通过）

- 未发现 `node_modules/dist/.vite/.venv/__pycache__/.pytest_cache/*.pyc/*.log/.env`
- 未发现 `07_后端/lingyi_service/lingyi_service.db`
- 未发现 `07_后端/lingyi_service/.pytest-postgresql.xml`
- 未发现 `02_源码/**`
- 未发现 `04_测试与验收/测试证据/**`

### 2) 必需文件已进入 index（通过）

- `.github/workflows/frontend-verify.yml`
- `.github/workflows/backend-postgresql.yml`
- `06_前端/lingyi-pc/package-lock.json`
- `06_前端/lingyi-pc/scripts/check-production-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-production-contracts.mjs`
- `06_前端/lingyi-pc/tsconfig.json`
- `06_前端/lingyi-pc/vite.config.ts`
- `06_前端/lingyi-pc/src/api/production.ts`
- `06_前端/lingyi-pc/src/views/production/**`
- `07_后端/lingyi_service/requirements-dev.txt`
- `07_后端/lingyi_service/pytest.ini`
- `07_后端/lingyi_service/app/main.py`
- `07_后端/lingyi_service/app/routers/production.py`
- `07_后端/lingyi_service/tests/test_production_plan.py`
- `07_后端/lingyi_service/tests/test_production_work_order_outbox.py`
- `07_后端/lingyi_service/tests/test_production_job_card_sync.py`

## 四、离线 CI Snapshot 生成

- Snapshot 路径：`/tmp/lingyi-root-ci-snapshot`
- 生成方式：`git ls-files -z | rsync -a --files-from=- --from0 ./ /tmp/lingyi-root-ci-snapshot/`
- 生成后检查：`find . -maxdepth 3 -type d (node_modules|dist|.venv|__pycache__)` 无输出（通过）

## 五、Snapshot 内前端 CI 等价验证

目录：`/tmp/lingyi-root-ci-snapshot/06_前端/lingyi-pc`

- `node -v`：`v22.22.1`
- `npm -v`：`10.9.4`
- `npm ci`：通过
- `npm run verify`：通过
  - `check:production-contracts`：通过
  - `test:production-contracts`：通过，`scenarios=12`
  - `typecheck`：通过
  - `build`：通过
- `npm audit --audit-level=high`：`found 0 vulnerabilities`

## 六、Snapshot 内后端回归验证

目录：`/tmp/lingyi-root-ci-snapshot/07_后端/lingyi_service`

- `python3 -m venv .venv`：通过
- `pip install -r requirements.txt -r requirements-dev.txt`：通过
- 定向 pytest：`31 passed`
- 全量 pytest：`460 passed, 5 skipped`
- `unittest discover`：`Ran 449 tests ... OK`
- `py_compile`：通过

## 七、执行命令摘要

```bash
cd /Users/hh/Desktop/领意服装管理系统
# ignore 与 index 核验
# staged forbidden/required 检查
# snapshot 生成
rm -rf /tmp/lingyi-root-ci-snapshot
mkdir -p /tmp/lingyi-root-ci-snapshot
git ls-files -z | rsync -a --files-from=- --from0 ./ /tmp/lingyi-root-ci-snapshot/

# snapshot frontend
cd /tmp/lingyi-root-ci-snapshot/06_前端/lingyi-pc
npm ci
npm run verify
npm audit --audit-level=high

# snapshot backend
cd /tmp/lingyi-root-ci-snapshot/07_后端/lingyi_service
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest -q tests/test_production_plan.py tests/test_production_work_order_outbox.py tests/test_production_job_card_sync.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests scripts -name '*.py' -print)
```

## 八、范围声明

- 未修改前端业务逻辑（仅执行清单纳入与离线验证）
- 未修改后端业务逻辑（仅执行清单纳入与离线验证）
- 未进入 TASK-005/TASK-006

