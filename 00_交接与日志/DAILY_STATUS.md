# DAILY_STATUS
updated_at: 2026-06-14 10:42 CST+8
## W003A
- state: `MAINLINE_ACTIVE`
- task: `TASK-W003A-LAUNCH`
- branch: `codex/sprint4-seal`
- base_head_before_m1_commit: `bbc1cd494393e873f30a6d86b3489f1a76af8a96`
- origin_delta: `0/0`
- staged_area: `empty`
- queue: `M1 -> M2 -> M3 -> M4 -> M5 -> M6`
## W001A
- status: `ABSORBED_BY_W003A`
- CAND-01 quality write closure: `PASS / committed / pushed`
- CAND-02 subcontract write closure: `PASS / committed / pushed`
- CAND-03 warehouse stock-entry-draft: `merged into W003A M5, no standalone advance`
## M1
- current_target: `ERPNext 代理登录入口`
- S1_S4: `LOCAL_SELF_TEST_PASS / S3 backend session cache补做已通过`
- evidence: `04_测试与验收/TASK-W003A-M1_登录认证验收报告.md`
- next_gate: `DEFERRED_USER_GATE / 用户后续启动本地 ERPNext(16.12.0) 后补做真实账号登录与按钮权限抽验；不阻塞 M2`
- ui_rule: `登录页无衣算云对应业务页，不追 1:1；仅保持衣算云业务页基线风格`
- backend_cache: `LINGYI_AUTH_CACHE_TTL_SECONDS 默认45s、上限60s；key=ERPNext sid 或本地会话 token；logout 清对应缓存`
## M2
- current_target: `BOM 写闭环 + 衣算云物料开发 UI 1:1`
- status: `LOCAL_SELF_TEST_PASS / READY_FOR_CONSULTANT_REVIEW`
- ui_dod: `按 35_UI1对1像素级复刻规范、37_UI1对1验收清单、40_UI1对1开发团队执行包、41_本地UI自动对照覆盖缺口清单执行`
- pixel_baseline: `01_需求与资料/衣算云文档/证据数据/yisuan_ui_1to1_shots_20260405/04_物料开发_面料.png`
- state_baselines: `01_需求与资料/衣算云文档/证据数据/*ui_state*/screenshots_*/04_物料开发_面料_{loading,error,disabled,empty,no_permission}.png`
- write_endpoints: `createBom(POST /api/bom/), updateBomDraft(PUT /api/bom/{id}); lifecycle buttons use real BOM endpoints only`
- forbidden_ui: `no /api/local-dev/bom, no scenario_tag/回滚/回读本地沙箱面板, no non-1:1 temporary BOM UI`
- closeout_gate: `PASS: npm run verify + BOM M2 contract + Playwright e2e; grep /api/local-dev/bom src/views 为空`
- evidence: `04_测试与验收/TASK-W003A-M2_BOM衣算云1对1验收报告.md`
- screenshots: `04_测试与验收/测试证据/W003A_M2_bom_yisuan_1to1/`
## Frozen
- W002A: `FROZEN_NOT_STARTED`
- excluded_dirty: `none for BOM after M2; warehouse carryover remains separate`
- carryover_not_to_stage: `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- parked_blockers: `not released`
- forbidden: no M3 before consultant review, no PR/merge/tag/release, no ERPNext production write
