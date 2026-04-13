# TASK-003E Outbox Event Key 截断碰撞整改任务单

- 任务编号：TASK-003E
- 模块：工票/车间管理 / Outbox / Job Card 同步幂等
- 优先级：P0（审计阻断）
- 预计工时：0.5 天
- 更新时间：2026-04-12 15:09 CST
- 作者：技术架构师
- 审计来源：审计意见书第 18 份，outbox `event_key` 先拼 `job_card:digest` 再截断到 140 字符导致 digest 被截断，存在碰撞漏同步风险

════════════════════════════════════════════════════════════════════

【任务目标】

修复 outbox `event_key` 生成规则，禁止先拼接长 `job_card:digest` 再截断，确保 138/139/140 字符 Job Card 下不同同步事件仍能生成不同 `event_key`，不会误判为同一 outbox，避免漏同步 ERPNext Job Card 最终完成数量。

════════════════════════════════════════════════════════════════════

【一、问题背景】

审计发现当前 outbox `event_key` 生成存在高危碰撞风险：

1. 代码先拼接 `job_card:digest`。
2. 再把结果截断到 140 字符。
3. 当 `job_card` 很长时，后缀 digest 会被截掉。
4. 不同同步事件可能生成相同 `event_key`。
5. outbox 唯一索引会误判任务已存在。
6. 后续 Job Card 最终完成数量可能漏同步到 ERPNext。

该问题会破坏 outbox 幂等性，属于跨系统同步高危缺口。

════════════════════════════════════════════════════════════════════

【二、涉及文件】

后端修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_outbox_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/workshop.py（如 event_key 长度或注释需调整）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/workshop.py（如响应字段说明需调整）

测试新增或修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_outbox.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_job_card_sync.py

════════════════════════════════════════════════════════════════════

【三、event_key 新规范】

1. 禁止使用以下模式：

- `event_key = f"{job_card}:{digest}"[:140]`
- `event_key = raw_key[:140]`
- 任何可能截断 digest 的实现

2. 必须采用“固定短前缀 + 完整 hash 摘要”模式。

推荐格式：

- `wjc:{digest}`

其中：

- `wjc` = workshop job card sync
- `digest` = SHA-256 hex 摘要，长度 64

最终长度：

- `len("wjc:" + sha256_hex) = 68`

必须小于 `event_key varchar(140)` 限制。

3. digest 输入必须包含所有影响同步幂等语义的字段。

建议 canonical payload：

```json
{
  "job_card": "...",
  "local_completed_qty": "...",
  "source_type": "...",
  "source_ids": [1, 2, 3]
}
```

要求：

- source_ids 必须排序。
- JSON 序列化必须稳定，例如 sort_keys=True。
- Decimal / numeric 必须规范化为字符串，避免 1、1.0、1.000000 表示差异导致误判。
- 空值必须有明确表达，不允许拼接时丢字段。

4. 不允许把 job_card 明文完整放入 event_key。

原因：

- job_card 可能很长。
- job_card 可能包含业务敏感编码。
- event_key 的唯一性应由 digest 保证。

5. 如需要排查，可在 outbox 独立字段保存 job_card。

- job_card 字段保留 ERPNext Job Card.name。
- event_key 只作为幂等键。

════════════════════════════════════════════════════════════════════

【四、幂等语义】

1. 同一同步事件必须生成相同 event_key。

同一同步事件定义：

- job_card 相同
- local_completed_qty 相同
- source_type 相同
- source_ids 相同且排序后相同

2. 不同同步事件必须生成不同 event_key。

不同同步事件包括：

- job_card 不同
- local_completed_qty 不同
- source_type 不同
- source_ids 不同

3. 特别要求：

即使 job_card 长度为 138、139、140、200 字符，不同同步事件也必须生成不同 event_key。

4. event_key 生成必须在写 outbox 前完成。

5. outbox 唯一索引继续使用：

- uk_ys_workshop_job_card_sync_outbox_event_key(event_key)

但 event_key 本身必须避免截断碰撞。

════════════════════════════════════════════════════════════════════

【五、兼容与迁移要求】

1. 如果当前开发库已有旧格式 event_key：

- 新增任务必须使用新格式。
- 历史 pending / failed 任务如可能重试，应提供迁移或兼容处理。

2. 迁移策略二选一：

方案 A：对未完成 outbox 重新计算 event_key。

- status in ('pending', 'processing', 'failed') 的旧 event_key 重新生成。
- 如发生冲突，按 job_card + local_completed_qty + source_ids 保留最新任务并记录迁移日志。

方案 B：保留旧数据，但 worker 处理时不再基于旧 event_key 做新任务去重。

- 新任务全部用新格式。
- 旧 pending/failed 任务继续可处理。

3. 本项目建议采用方案 A。

4. 迁移脚本必须保证幂等。

5. 迁移过程不得删除未同步 outbox。

════════════════════════════════════════════════════════════════════

【六、测试必须覆盖的碰撞探针】

1. 138 字符 Job Card，不同 source_ids。

输入：

- job_card = 138 个字符
- local_completed_qty = 10
- source_ids = [1]
- source_ids = [2]

期望：

- event_key 不同
- 均小于等于 140 字符

2. 139 字符 Job Card，不同 local_completed_qty。

输入：

- job_card = 139 个字符
- local_completed_qty = 10
- local_completed_qty = 11

期望：

- event_key 不同
- 均小于等于 140 字符

3. 140 字符 Job Card，不同 source_type。

输入：

- job_card = 140 个字符
- source_type = ticket_register
- source_type = ticket_reversal

期望：

- event_key 不同
- 均小于等于 140 字符

4. 200 字符 Job Card，不同 source_ids。

输入：

- job_card = 200 个字符
- source_ids = [1, 2]
- source_ids = [1, 3]

期望：

- event_key 不同
- 均小于等于 140 字符

5. source_ids 顺序稳定性。

输入：

- source_ids = [3, 1, 2]
- source_ids = [1, 2, 3]

期望：

- event_key 相同

6. Decimal 规范化。

输入：

- local_completed_qty = 1
- local_completed_qty = 1.0
- local_completed_qty = 1.000000

期望：

- 如业务语义相同，event_key 相同。

7. 旧风险回归。

构造两个不同同步事件，使旧算法截断后相同。

期望：

- 新算法 event_key 不同。
- 不会返回旧 outbox。
- 两个同步事件均可创建独立 outbox，或按业务合并规则创建正确最终态 outbox。

════════════════════════════════════════════════════════════════════

【七、验收标准】

□ event_key 不再使用 `f"{job_card}:{digest}"[:140]` 或任何先拼接后截断模式。

□ event_key 使用固定短前缀 + SHA-256 完整摘要，长度稳定小于等于 140。

□ 138 字符 Job Card 下，不同 source_ids 生成不同 event_key。

□ 139 字符 Job Card 下，不同 local_completed_qty 生成不同 event_key。

□ 140 字符 Job Card 下，不同 source_type 生成不同 event_key。

□ 200 字符 Job Card 下，不同 source_ids 生成不同 event_key。

□ source_ids 不同顺序但集合相同时，生成相同 event_key。

□ local_completed_qty 数值语义相同时，1 / 1.0 / 1.000000 生成相同 event_key。

□ 构造旧算法会碰撞的两个事件，新算法不会碰撞。

□ event_key 不包含完整 job_card 明文。

□ outbox 唯一索引仍然生效，重复同一事件不会新增第二条。

□ 不同同步事件不会被误判为已有 outbox。

□ Worker 仍可按 outbox 正常同步 Job Card。

□ 迁移脚本或兼容逻辑不会删除 pending / failed 旧任务。

□ `.venv/bin/python -m pytest -q` 通过。

□ `.venv/bin/python -m unittest discover` 通过。

□ `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)` 通过。

════════════════════════════════════════════════════════════════════

【八、禁止事项】

1. 禁止先拼 `job_card:digest` 再截断。

2. 禁止截断 digest。

3. 禁止 event_key 依赖长 job_card 前缀保证唯一性。

4. 禁止不同同步事件返回同一个旧 outbox。

5. 禁止为避免碰撞而删除唯一索引。

6. 禁止用随机 UUID 作为同一业务事件的 event_key。

7. 禁止迁移时删除 pending / failed outbox。

8. 禁止修改 Job Card 同步 outbox/after-commit 主架构。

════════════════════════════════════════════════════════════════════

【九、完成后回复格式】

请工程师完成后按以下格式回复：

TASK-003E 已完成。

已修改文件：
- [列出实际修改文件]

核心整改：
- event_key 已改为固定短前缀 + SHA-256 完整摘要
- 已删除先拼 job_card:digest 再截断的逻辑
- 138/139/140/200 字符 Job Card 下不同事件不会碰撞
- source_ids 已排序后参与摘要
- local_completed_qty 已做数值规范化
- 旧 pending/failed outbox 已提供迁移或兼容处理

自测结果：
- 138 字符 Job Card 不同 source_ids 不碰撞：通过 / 不通过
- 139 字符 Job Card 不同 qty 不碰撞：通过 / 不通过
- 140 字符 Job Card 不同 source_type 不碰撞：通过 / 不通过
- 200 字符 Job Card 不同 source_ids 不碰撞：通过 / 不通过
- source_ids 顺序不同但集合相同 event_key 相同：通过 / 不通过
- 1 / 1.0 / 1.000000 event_key 相同：通过 / 不通过
- 旧算法碰撞样例在新算法下不碰撞：通过 / 不通过
- 重复同一业务事件不新增第二条 outbox：通过 / 不通过
- pytest/unittest/py_compile：通过 / 不通过

遗留问题：
- 无 / 有，说明原因
