# Change: 新增周报 Agent 模块化质检框架

## Why
现有批量摘要脚本（如 backend 仓库的 `weekly_report_batch_eval.py`）能批量生成周报摘要并交给单个 LLM 裁判，但评测主要依赖最终输出和单一主观判断，无法验证 Agent 是否选择了正确路由、命中了合适的 FAQ、加载了目标 Skill、正确调用 MCP 工具，也无法区分“答案碰巧正确”和“执行链路正确”。单一裁判还存在自洽偏差，人工预期本身也可能不合理。

需要建立一个证据驱动、可拆分单测、支持多向验证的质检框架：同一用例既有人工预期，也由确定性规则、执行 Trace、检索指标、语义裁判和变形测试交叉验证，并输出可追溯的分项结论。

## What Changes
- 定义版本化的周报 Agent 质检用例契约，覆盖输入上下文、期望路由、FAQ 检索、目标 Skill、MCP 调用、输出话术、禁止行为和评分权重。
- 增加测试集加载与校验能力，兼容导入现有周报 Markdown 用例，并提供可独立维护的 JSON/YAML 用例格式。
- 建立统一的运行证据模型，将最终输出、路由决策、FAQ 候选及分数、Skill 快照、MCP 调用与结果、模型用量和错误归一化为可评测 Trace。
- 将质检拆分为路由、FAQ 召回、Skill、MCP、输出契约、事实一致性、跨周期信息、话术语义等独立评测器；每个评测器可单独运行和单元测试。
- 增加多向验证：确定性断言、LLM-as-judge、双裁判/仲裁、预期合理性审查、变形测试和跨接收人一致性检查，避免单一人工预期或单一模型裁判成为唯一真值。
- 扩展批量评测 CLI，支持选择评测器、离线重放已有 Trace、阈值门禁、断点续跑，以及 JSON/Markdown 汇总报告。
- 新增独立的多维度权限校验评测器（`permission_boundary`）：覆盖租户数据隔离、跨租户选择/分析拒绝、周报可见范围（ACL 与分享关系）、通讯录人员可见性、Prompt 注入越权诱导、用户习惯记忆按 `租户ID+userID` 隔离；任何权限越界一律记为 `critical` 硬失败。
- 提供可复现的种子测试集，覆盖无上期、延期/冲突、风险遗漏、FAQ 歧义、错误路由、Skill 缺失、MCP 参数/权限/失败回退、话术编造和接收人差异等场景；并从《周报 AI 支持总结多人、追问和记住用户习惯》PRD 的场景测试集导入权限/安全用例（跨租户拒绝、Prompt 注入、不可见人员、无权限数据拒绝等）。
- 增加定时批量执行：用例集每天定时执行两次，记录运行标识、用例集版本和执行证据，运行失败或未完成时显式告警而非静默跳过。
- 增加评测结果三轮 check，目的是提升结果置信度而非强制三轮一致：每次运行结束后依次执行确定性重放校验、语义 Judge 复评、与基线/上一次运行的回归比对；三轮产出的佐证/矛盾信号汇总为逐用例置信等级（high/medium/low），低置信结果进入仲裁并在报告单列，最后输出带置信标注的当日 JSON/Markdown 报告。
- 首期只提供离线 CLI 与可复用评测包，不新增在线 API、数据库表或自动阻断生产流量；定时执行以 cron/Jenkins 调度现有 CLI 实现。

## Impact
- Affected specs: `weekly-report-agent-quality`
- Affected code:
  - `packages/weekly_report_quality/*`
  - `tests/weekly_report_quality/*`
  - `testdata/weekly_report_quality/*`
  - `docs/weekly-report-agent-quality.md`
  - `live/`（在线 E2E 评测，可选对接外部批量摘要脚本）
  - 每日两次定时调度配置（cron/Jenkins）
- Read-only integration points:
  - `business-agent` 周报摘要输出与 Trace
  - `agent-engine` Skill 快照和 MCP 调用事件
  - FAQ/向量检索候选及相关性分数

