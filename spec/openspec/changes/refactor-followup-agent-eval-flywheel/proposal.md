# Change: 按七层飞轮重构周报追问 Agent 评测

## Why
当前线上 76 条追问评测通过率约 2.6%、完整度均分 0.8/5，大量「失败」来自评测系统本身：成功标准套用了「生成周报」而不是「追问已有周报」；必须点用关键词硬匹配；图片/点赞/记忆等未真正造环境的用例仍被判失败；源周报里出现「越权」会被当成 Agent 越权。评测结果无法指导优化，也不能作为门禁。

## What Changes
- 按任务定义 → 成功标准 → 分层数据集 → 环境与执行器 → 评测器 → 报告与门禁 → 反馈闭环 重建追问 Agent 评测飞轮。
- **BREAKING**：自动判定改为 `通过 / 人工复核 / 失败 / 失败-红线 / 待复测`；质量分与合同/红线分离，关键词完整度不再单独决定失败。
- 用例按黄金/边界/对抗/权限/需环境 分层；环境未就绪时必须 `待复测`，不得记失败。
- 规则优先打分：仅对真实泄漏、注入成功、把进行中写成彻底完成等行为记红线；讨论历史越权或算术题不算越权红线。
- 提供离线重打分：用已有执行记录重判，不必重跑 Agent。
- 失败与人工改判回写用例集版本，形成数据集迭代闭环。

## Impact
- Affected specs: `weekly-report-agent-quality`
- Affected code:
  - `live/eval_engine.py`
  - `live/run_report_agent_cases.py`
  - `live/publish_quality_report.py`
  - `live/scoring_rubric.md`
  - `packages/weekly_report_quality/*`（契约对齐，不替换离线种子门禁）
