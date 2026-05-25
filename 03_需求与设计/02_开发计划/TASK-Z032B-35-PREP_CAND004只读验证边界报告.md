# TASK-Z032B-35-PREP CAND004 只读验证边界报告

## 基本信息

- task_id: TASK-Z032B-35-PREP
- role: B Engineer
- source_task: TASK-Z032B-34-PREP
- candidate_id: Z032-CAND-004
- current_head: aedc2d39cca4d065a028ce42e325de17490d95b6

## Git 状态核对

- cached_empty: true
- git_diff_check: PASS
- historical_dirty_forbidden_staged: []

## B34 refresh 核对

- selected_candidate: Z032-CAND-004
- next_task: TASK-Z032B-35-PREP
- remaining_candidates:
  - Z032-CAND-004
  - Z032-CAND-005
- reuse_scan.reused_target_tests: []

## 冻结执行边界

- frozen_workdir: `07_后端/lingyi_service`
- frozen_command: `.venv/bin/python -m pytest tests/test_workshop_job_card_sync.py -q`
- target_test: `07_后端/lingyi_service/tests/test_workshop_job_card_sync.py`
- target_test_exists: true
- target_test_dirty_diff: false
- source_evidence_missing: []
- reuse_check.reused_from_Z015_Z031: false

## Source Evidence

- `07_后端/lingyi_service/tests/test_workshop_job_card_sync.py`
- `07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py`
- `07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py`
- `07_后端/lingyi_service/app/models/workshop.py`
- `07_后端/lingyi_service/app/routers/workshop.py`

## 下一步

- next_task: TASK-Z032B-36-IMPL
- run_this_task: false

## 生命周期门禁

- stage: false
- commit: false
- push: false
- tag: false
- pr: false
- release: false
- remote_lifecycle_parked: true
- production_readback: false
- go_live: false
- project_completion: false

## 本轮产物状态

- B35 report/json/tsv 未暂存
- 未运行 pytest/npm/browser/build/typecheck/verify
- 未生成 B36 result/stdout
- 未 stage/commit/push/tag/PR/release
