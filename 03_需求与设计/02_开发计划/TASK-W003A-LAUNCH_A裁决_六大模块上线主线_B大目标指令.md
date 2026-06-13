# A 裁决:上线主线 W003A-LAUNCH(六大模块上线 · B 大目标指令)

- 裁决人:用户(经总架构顾问评估)
- 生效:即刻
- 优先序:晚于本文件的用户裁决 > 本文件 > RUN-S > RUN-A > 旧 W001A 文件
- 主线切换:W001A 候选队列(CAND-01..05/收口)**收编**进本主线对应模块目标,编号作废;原定 W002A 生产化批次**不再单独立项**,其范围(登录认证/PostgreSQL/剥离测试桩/ERPNext flag 化/部署基线)拆分吸收进 M1-M6;已冻结的 W002A 自创批次维持冻结,W002A 标签作废不复用。
- RUN-A/RUN-S 继续生效,自治队列对象由旧候选替换为 M1→M6;S 的 D4 顺序裁决基准随之更新。
- **前置 gate 0(不变)**:FIX-W001A-VERIFY-01 绿 + 干净 HEAD `npm run verify` PASS,之后 M1 自动启动。

## 一、模块口径(以 HomePage.vue 模块分组为准)

基础资料(/sales-inventory/references)| 物料开发(/bom/list,含生产计划)| 大货管理(/sales-inventory/sales-orders,含工票/质检/工资)| 物料采购(/subcontract/list,含加工厂对账)| 物料进销存(/sales-inventory/stock-ledger + /warehouse)| 首页工作台(/home + /dashboard/overview,全局收口)。
style_profit / reports / system 治理面板归 M6 附属验收面:上线标准为"可达 + 只读正确",不扩写闭环。

## 二、每模块通用完成标准(DoD,六个目标共用)

1. 页面入口可达,UI 贴近衣算云既有对齐基准。
2. 该模块核心单据真实后端写闭环:创建 → 编辑 → 状态流转(提交/确认/撤销)→ 回读,走生产 API 路径,不依赖 local-dev 桩。
3. 权限 fail-closed(403/503 优先于 422 的全模块契约,对齐 FIX-BOM-01 先例);写操作审计落库。
4. 测试:模块 pytest + 契约测试绿;封板基线(107+)与既有 verify 套件不回退;新写闭环必须带新测试。
5. 浏览器端到端闭环证据(创建→流转→回读截图/readback 入 04_测试与验收)。
6. C 审计通过 + DAILY_STATUS 重锚 + commit/push(沿用长期授权)。

## 三、六个大目标(严格串行,完成一个进下一个)

### M1 基础资料 + 登录认证(P0,全线地基)
- 业务:客户/供应商/款号维护写闭环(吸收原 CAND-05,后端最小写端点由 B 评估、C 审计把关)。
- 上线化增量:**真实登录认证替换 dev-auth**(登录页、会话、登出;`LINGYI_ALLOW_DEV_AUTH` 生产默认关);全后端路由鉴权扫描,无鉴权端点清零。
- 验收追加:未登录访问任意业务路由 → 拦截;dev-auth 关闭下全测试绿。

### M2 物料开发:BOM + 生产计划 + PostgreSQL(P0,数据地基)
- 业务:BOM 编辑/版本/默认版本/展开与生产计划联动收口(BOM 写闭环已封板,此处补前端可用面与计划联动)。
- 上线化增量:**PostgreSQL 双轨切换**(`LINGYI_DB_URL` flag;迁移脚本;sqlite 仅保留本地开发);全部基线测试在 PG 上跑绿一次并归档证据。此后 M3-M6 回归默认跑 PG。
- 验收追加:同一套测试 sqlite/PG 双绿;数据迁移脚本可重复执行。

### M3 大货管理:订单 → 工票 → 质检 → 工资(P0,业务主干)
- 业务:大货订单写闭环;工票登记/撤销/批量浏览器验收(吸收原 CAND-04);**质检检验写闭环**(吸收原 CAND-01:POST inspections / PATCH / confirm / cancel / defects);工资工价页面可用面。
- 验收追加:订单→工票→质检→工资一条链浏览器走通,金标准参照 GC-ORDER-02/03 行为(仅参照交互结构,不连衣算云)。

### M4 物料采购:外发 + 对账(P0,碰钱碰库存,边界最严)
- 业务:外发订单前端写闭环(吸收原 CAND-02:create/issue-material/receive/inspect/settlement-preview);加工厂对账单可用面(已封板后端的前端收口)。
- 上线化增量:**ERPNext flag 化**:所有 ERPNext bridge 置 `LINGYI_ERPNEXT_ENABLED` 默认关,关闭态零外呼;生产配置模板不含 ERPNext 凭据。
- 验收追加:ERPNext/worker/internal 写计数 = 0;flag 关闭下全链可用。

### M5 物料进销存:台账 + 仓库 + 剥离测试桩(P0)
- 业务:仓库出入库草稿真实入口(吸收原 CAND-03,stock-entry-draft create/cancel/outbox-status);盘点闭环前端收口;库存台账查询/回读完整。
- 上线化增量:**剥离 local-dev 测试桩**:local_dev.py 全域置 `APP_ENV=development` 硬门禁(生产构建/生产 env 下 404),前端无任何 local-dev 调用残留;本目标解除"不改 local_dev.py"旧隔离令(仅限此目标内,改动仅许收紧不许放宽)。
- 验收追加:生产模式启动下扫描 local-dev 端点全 404;前端构建产物 grep 无 local-dev 路径。

### M6 首页工作台 + 部署基线 + 全链路试运行(收口)
- 业务:首页/总览六模块状态面板接真实闭环状态(吸收原收口任务,禁装饰性扩面)。
- 上线化增量:**部署基线**:一键部署/回滚脚本(前端构建+后端服务+PG+反向代理)、数据备份与恢复脚本、健康检查端点、生产 env 模板、上线 checklist 文档(05_运维 或 04_测试与验收 落档)。
- 终验:六模块端到端试运行走单(基础资料建档→BOM→订单→工票/质检→外发→入出库→对账→首页状态正确),全程生产模式(无 dev-auth、无 local-dev、PG、ERPNext 关);C 出具 RELEASE_READY 审计报告 → 主线宣告 `W003A RELEASE_READY`,进入 PARKED 等用户执行上线。

## 四、流程规则(对 B 的授权放大)

1. 每个 M 目标内,**B 自治拆解子任务**,不再逐候选请示;单子任务回交心跳与 4h 死亡判定沿用 RUN-A。
2. FIX 循环规则沿用(≤2 轮,S 可按 D3 加授 1 轮);单模块卡死 → 该模块内卡点挂 PARKED,**不许跳模块**(串行主线,与旧"切下一候选"不同;跳模块需 S 按 D4 出文或用户裁决)。
3. 冻结 untracked 转正通道:目标内确需复用某冻结件(如 quality 三目录组件),B 列清单 → C 审计来源与质量 → 逐文件白名单转正并记入该目标验收报告;未转正的继续禁 add。
4. 测试为契约:封板测试与各模块既有契约测试禁改(迁就实现);确属测试自身缺陷 → 回 A/S 裁决。
5. 每目标收口物:模块验收报告(04_测试与验收)+ DAILY_STATUS 重锚 + push。

## 五、红线(沿用 + 上线特有)

1. 沿用全部既有 HUMAN_ONLY:PR/merge/tag/release、衣算云与 ERPNext 生产写、生产账号、force-push、删 untracked。
2. 上线特有 HUMAN_ONLY:**真实生产部署执行、真实用户账号开放、ERPNext 生产凭据配置、域名/服务器/远端基础设施变更**——M6 交付 RELEASE_READY + 一键脚本 + checklist,最后一步由用户执行或陪同执行。
3. 禁止为赶进度削弱安全语义:fail-closed、审计、鉴权覆盖只许加强。
4. 影子采集线规则不变(独立、预授权制)。
