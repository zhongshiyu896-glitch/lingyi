# TASK-S-002 Acceptance Smoke Report

- Report Generated At (UTC): 2026-04-15T01:13:37+00:00
- Task ID: TASK-S-002
- Module: bom
- Base URL: http://127.0.0.1:18081
- Execution Command: `python tools/acceptance_smoke/run_smoke.py --module bom --base-url http://127.0.0.1:18081 --token <redacted> --report-dir ../../03_需求与设计/06_交付与验收/TASK-S-002/failure_sample`
- Total Cases: 3
- Passed: 0
- Failed: 2
- Skipped: 1
- Exit Suggestion: 1

## Module Pass Rate

| Module | Total | Passed | Failed | Skipped | Pass Rate |
| --- | --- | --- | --- | --- | --- |
| bom | 3 | 0 | 2 | 1 | 0.0% |

## Case Matrix

| # | Module | Case ID | Method | Endpoint | Expected Status | Actual Status | Expected Code | Actual Code | Result | Elapsed(ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | bom | bom-create-001 | POST | /api/bom/ | 200 | None | 0 | None | FAIL | 13.879 |
| 2 | bom | bom-list-001 | GET | /api/bom/ | 200 | None | 0 | None | FAIL | 0.261 |
| 3 | bom | bom-detail-001 | GET | /api/bom/{{bom_id}} | 200 | None | 0 | None | SKIP | 0.001 |

## Duration Stats

- Total Elapsed: 14.644 ms
- Avg Per Case: 4.881 ms
- Max Case Elapsed: 13.879 ms

## Failure Details

- `bom/bom-create-001` error: transport_error=[Errno 61] Connection refused; status_mismatch(expected=200,actual=None); code_mismatch(expected=0,actual=None); extract_failed:response_not_json_object
- `bom/bom-list-001` error: transport_error=[Errno 61] Connection refused; status_mismatch(expected=200,actual=None); code_mismatch(expected=0,actual=None); extract_failed:response_not_json_object

## Skip Reasons

- `bom/bom-detail-001` reason: dependency_not_passed:bom-list-001
