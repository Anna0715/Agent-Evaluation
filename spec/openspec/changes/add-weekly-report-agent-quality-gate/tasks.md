## 1. 契约与测试资产
- [x] 1.1 定义并文档化版本化 CaseSpec、RunEvidence、CheckResult 和聚合报告契约。
- [x] 1.2 实现用例 lint，覆盖冲突预期、不可观察断言、缺失证据来源和 Skill/MCP 约束不一致。
- [x] 1.3 实现现有周报 Markdown 测试集导入器，并提供脱敏种子用例与 fixture。
- [x] 1.4 从《周报 AI 支持总结多人、追问和记住用户习惯》PRD 场景测试集脱敏导入权限/安全种子用例（跨租户拒绝、Prompt 注入、不可见人员、无权限数据拒绝）。

## 2. 证据采集与重放
- [x] 2.1 将摘要输出、模型信息和现有 Business-Agent Trace 归一化为 RunEvidence。
- [x] 2.2 接入可获得的路由、FAQ 候选、Skill 快照和 MCP 调用证据；敏感正文、密钥和工具结果默认脱敏。
- [x] 2.3 实现 Evidence 落盘、离线重放、版本/digest 校验和缺失证据显式 skip。

## 3. 模块化评测器
- [x] 3.1 实现路由评测器。
- [x] 3.2 实现 FAQ 召回评测器，包括 Recall@K、MRR、NDCG、must-not-hit 和权限过滤断言。
- [x] 3.3 实现 Skill key/version/channel/digest 与 required MCP tools 评测器。
- [x] 3.4 实现 MCP 工具选择、参数、顺序/次数、失败回退和禁止调用评测器。
- [x] 3.5 实现输出契约、事实一致性、跨周期信息、话术语义和跨接收人一致性评测器。
- [x] 3.6 实现 permission_boundary 评测器：租户隔离、周报可见范围（ACL/分享）、通讯录人员可见性、Prompt 注入抵抗、记忆按租户+用户隔离；全部子维度为 critical 硬门禁并支持 missing_evidence skip。

## 4. 多向验证与聚合
- [x] 4.1 将语义 Judge 输出改为稳定结构化契约，记录模型、prompt digest、原始结果和解析错误。
- [x] 4.2 实现 expectation critic、可选第二 Judge、分歧检测和仲裁状态。
- [x] 4.3 实现无上期、同义改写、无关内容、接收人角色和无关 FAQ 注入的变形测试。
- [x] 4.4 实现权重聚合、critical 硬门禁、baseline 差异和 skip/error 单列统计。

## 5. 定时执行与结果复核
- [x] 5.1 增加每天两次的定时调度入口（cron/Jenkins），分配 run_id 并记录触发时间、用例集版本和证据 digest；失败/超时显式告警。
- [x] 5.2 实现三轮结果 check 流水线：确定性重放校验、独立 Judge 复评、baseline 与上次运行回归比对；将 corroborate/contradict/unavailable 信号聚合为逐用例置信等级，低置信进入 adjudication_required。
- [x] 5.3 实现运行归档与两次每日运行的对比视图。

## 6. CLI 与报告
- [x] 6.1 扩展批量评测 CLI，支持按评测器/标签/用例选择、在线执行、离线重放、断点续跑和阈值门禁。
- [x] 6.2 输出逐用例 JSON、汇总 JSON、JUnit 兼容结果和 Markdown 质检报告，报告含权限覆盖率、三轮 check 结论和当日两次运行对比。
- [x] 6.3 补充运行指南、用例编写指南、指标解释和故障排查文档。

## 7. 验证与灰度
- [x] 7.1 为所有契约和评测器增加表驱动单元测试，真实模型调用使用 stub。
- [x] 7.2 增加从 CaseSpec、Evidence 到聚合报告的脱敏端到端测试，覆盖权限用例和三轮 check 不一致路径。
- [ ] 7.3 使用历史周报测试集建立首个 baseline，人工盲审抽样并记录 Judge 一致率。（种子集 baseline 已归档于 testdata/weekly_report_quality/runs；历史全量集导入与人工盲审为运营侧待办）
- [ ] 7.4 以非阻断模式启动每日两次定时运行；Trace 完整率、Judge 一致率和权限证据覆盖率达标后再启用选定硬门禁。（调度脚本与 --gate 开关已就绪，需在目标机器安装 crontab/Jenkins job）
