# TASK-S-002 Acceptance Smoke Report

- Report Generated At (UTC): 2026-04-14T13:06:30+00:00
- Task ID: TASK-S-002
- Module: all
- Base URL: http://127.0.0.1:18080
- Execution Command: `python tools/acceptance_smoke/run_smoke.py --config tools/acceptance_smoke/config.example.json`
- Total Cases: 13
- Passed: 13
- Failed: 0
- Skipped: 0
- Exit Suggestion: 0

## Module Pass Rate

| Module | Total | Passed | Failed | Skipped | Pass Rate |
| --- | --- | --- | --- | --- | --- |
| bom | 3 | 3 | 0 | 0 | 100.0% |
| workshop | 4 | 4 | 0 | 0 | 100.0% |
| production | 3 | 3 | 0 | 0 | 100.0% |
| subcontract | 3 | 3 | 0 | 0 | 100.0% |

## Case Matrix

| # | Module | Case ID | Method | Endpoint | Expected Status | Actual Status | Expected Code | Actual Code | Result | Elapsed(ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | bom | bom-create-001 | POST | /api/bom/ | 200 | 200 | 0 | 0 | PASS | 14.531 |
| 2 | bom | bom-list-001 | GET | /api/bom/ | 200 | 200 | 0 | 0 | PASS | 0.492 |
| 3 | bom | bom-detail-001 | GET | /api/bom/101 | 200 | 200 | 0 | 0 | PASS | 0.44 |
| 4 | workshop | workshop-register-001 | POST | /api/workshop/tickets/register | 200 | 200 | 0 | 0 | PASS | 0.313 |
| 5 | workshop | workshop-reversal-001 | POST | /api/workshop/tickets/reversal | 200 | 200 | 0 | 0 | PASS | 0.306 |
| 6 | workshop | workshop-ticket-list-001 | GET | /api/workshop/tickets | 200 | 200 | 0 | 0 | PASS | 0.393 |
| 7 | workshop | workshop-daily-wage-001 | GET | /api/workshop/daily-wages | 200 | 200 | 0 | 0 | PASS | 0.337 |
| 8 | production | production-plan-create-001 | POST | /api/production/plans | 200 | 200 | 0 | 0 | PASS | 0.294 |
| 9 | production | production-plan-list-001 | GET | /api/production/plans | 200 | 200 | 0 | 0 | PASS | 0.276 |
| 10 | production | production-material-check-001 | POST | /api/production/plans/301/material-check | 200 | 200 | 0 | 0 | PASS | 0.375 |
| 11 | subcontract | subcontract-create-001 | POST | /api/subcontract/ | 200 | 200 | 0 | 0 | PASS | 0.266 |
| 12 | subcontract | subcontract-list-001 | GET | /api/subcontract/ | 200 | 200 | 0 | 0 | PASS | 0.311 |
| 13 | subcontract | subcontract-issue-material-001 | POST | /api/subcontract/401/issue-material | 200 | 200 | 0 | 0 | PASS | 0.392 |

## Duration Stats

- Total Elapsed: 19.438 ms
- Avg Per Case: 1.495 ms
- Max Case Elapsed: 14.531 ms

## Failure Details

- None

## Skip Reasons

- None
