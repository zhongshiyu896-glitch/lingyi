# TASK-Z029B-22-PREP CAND003 只读验证边界报告

## Gate Checks

- current HEAD: 63dee234e6f462f229b1e550ee1da50e4e3774b7
- cached: empty
- `git diff --check`: PASS
- B21 selected candidate: Z029-CAND-003
- B21 next task: TASK-Z029B-22-PREP

## Frozen Boundary

- candidate_id: Z029-CAND-003
- module: subcontract_stock_worker
- risk: LOW
- frozen workdir: /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
- frozen command: `.venv/bin/python -m pytest tests/test_subcontract_stock_worker.py -q`
- target test: 07_后端/lingyi_service/tests/test_subcontract_stock_worker.py
- target test exists: true
- target test dirty diff: false
- readonly single-file pytest: true

## Source Evidence

- 07_后端/lingyi_service/tests/test_subcontract_stock_worker.py
- 07_后端/lingyi_service/app/services/subcontract_stock_worker_service.py
- 07_后端/lingyi_service/app/services/subcontract_stock_outbox_service.py
- 07_后端/lingyi_service/app/services/erpnext_stock_entry_service.py
- 07_后端/lingyi_service/app/routers/subcontract.py
- 07_后端/lingyi_service/app/models/subcontract.py
- source_evidence_missing: []

## Next

- next task: TASK-Z029B-23-IMPL
- run_this_task: false

## Lifecycle

- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback_ready: false
- go_live_ready: false
- project_completion_claimed: false
