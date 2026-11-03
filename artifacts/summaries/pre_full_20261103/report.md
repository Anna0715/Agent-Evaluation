# pre 用例全量范围与执行报告

生成时间（UTC）：2026-11-03T09:30:41+00:00
范围：401 条，环境：pre。工作簿 SHA-256：`b929eac441c3de2fb67b8d8f63e3335560eb76e05f17f5b0eca213938d46756a`。

## 执行与裁判

- 已取得认证 Trace：248；有运行结果但无 Trace：13；启动未完成：0；未执行：140。
- 业务裁判：通过 73、失败 67、证据不足 108、尚未裁判 153。
- 任务成功率：52.1%（73/140）
- 裁判覆盖：248/248 条有 Trace 用例。普通问答经过真实 pre 业务接口；裁判使用 `gpt-6.1-sol` 流式接口。
- 助手模型（执行回执）：`openai/gpt-6.1-terra` 248 条。
- 自动状态与业务判定分列；自动跳过或请求成功都不直接等于业务失败或通过。

## 未执行原因

| 代码 | 说明 | 数量 |
| --- | --- | ---: |
| `actor_login_failed` | 测试账号登录或验证码不可用 | 1 |
| `authorization_hold` | 此前明确保留的持久提醒或群监控用例 | 4 |
| `controlled_setup_required` | 需要逐例受控环境、故障或权限条件 | 91 |
| `dedicated_automation_driver` | 需要专用自动化调度与运行证据 | 22 |
| `fixture_provision_required` | 业务夹具尚未准备完成 | 7 |
| `gold_missing` | 参考真值不完整 | 1 |
| `independent_source_missing` | 缺少可独立核验的正向来源 | 12 |
| `source_read_failed` | 独立业务源回读失败 | 2 |

## 业务失败分类

| 分类 | 数量 |
| --- | ---: |
| 信息缺失 | 64 |
| 指令未遵循 | 4 |
| 时序错误 | 3 |
| 范围错误 | 13 |
| 证据不足 | 1 |
| 评论解析错误 | 1 |

## 认证 Trace 缺口

- `AA-ATT-IMG-004`
- `AA-ATT-PDF-014`
- `AA-ATT-XLS-004`
- `AA-ATT-DOC-003`
- `AA-ATT-DOC-007`
- `AA-ATT-DOC-014`
- `AA-ATT-CTX-003`
- `AA-ATT-SEC-002`
- `AA-ATT-QAL-007`
- `AA-SMEM-PRE-012`
- `AA-SMEM-PRE-013`
- `AA-SMEM-PRE-015`
- `AA-SMEM-PRE-016`

## 逐案台账

| 用例 | 模块 | 数据状态 | 执行器 | 执行 | 自动状态 | Trace | 业务裁判 | 原因代码 |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| AA-QAP-004 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-QAP-005 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-QAP-006 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-QAP-007 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-QAP-008 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-QAP-009 | 跨源事实与风险 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-QAP-010 | 跨源事实与风险 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-QAP-011 | 跨源事实与风险 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-QAP-012 | 跨源事实与风险 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-QAP-013 | 跨源事实与风险 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-QAP-014 | 跨源事实与风险 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-QAP-015 | 跨源事实与风险 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-QAP-016 | 跨源事实与风险 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 2 | skip | judged |
| AA-QAP-017 | 跨源事实与风险 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-QAP-019 | 跨源事实与风险 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-QAP-020 | 跨源事实与风险 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-QAP-021 | 跨源事实与风险 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-QAP-025 | 时效与安全 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-QAP-026 | 时效与安全 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-018 | 任务事实 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-FU-020 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-FU-021 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-FU-022 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-FU-023 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-FU-024 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-FU-025 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-FU-026 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-FU-027 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-FU-028 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-FU-029 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-FU-031 | 跨源分析与风险 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-FU-032 | 跨源分析与风险 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-FU-033 | 跨源分析与风险 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-FU-035 | 跨源分析与风险 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-FU-036 | 跨源分析与风险 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-FU-038 | 跨源分析与风险 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-FU-052 | 冲突澄清与安全 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-053 | 冲突澄清与安全 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-FU-054 | 冲突澄清与安全 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-FU-055 | 冲突澄清与安全 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-FU-059 | 冲突澄清与安全 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-062 | 自动化追问 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | authorization_hold |
| AA-FU-064 | 自动化追问 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | authorization_hold |
| AA-FU-065 | 自动化追问 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-FU-066 | 自动化追问 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | authorization_hold |
| AA-FU-068 | 自动化追问 | SPEC_PENDING | chat_api | not_executed | not_run | 0 | not_judged | authorization_hold |
| AA-SMEM-001 | 短期记忆与多轮 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 2 | skip | judged |
| AA-SMEM-010 | 短期记忆与多轮 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 2 | skip | judged |
| AA-LMEM-001 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-002 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-003 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-004 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-005 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-006 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-007 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-008 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-009 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-010 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-011 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-012 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-013 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-014 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-015 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-016 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-017 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-018 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-PRE-MSG-001 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-PRE-MSG-002 | 冲突澄清与安全 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-PRE-MSG-003 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-PRE-MSG-004 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-PRE-MSG-005 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-PRE-MSG-006 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-PRE-MSG-007 | 冲突澄清与安全 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PRE-MSG-008 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-PRE-MSG-009 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-PRE-MSG-010 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PRE-MSG-011 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PRE-MSG-012 | 冲突澄清与安全 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-PRE-MSG-013 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-PRE-MSG-014 | 时效与安全 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | independent_source_missing |
| AA-PRE-MSG-015 | 时效与安全 | NEED_PROVISION | chat_api | not_executed | not_run | 0 | not_judged | fixture_provision_required |
| AA-PRE-MSG-016 | 权限与隔离 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | independent_source_missing |
| AA-AGENT-EVAL-001 | 任务成功率 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-AGENT-EVAL-002 | 任务成功率 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-AGENT-EVAL-003 | 任务成功率 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | independent_source_missing |
| AA-AGENT-EVAL-004 | 工具调用正确率 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-AGENT-EVAL-005 | 工具调用正确率 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-AGENT-EVAL-007 | 工具调用正确率 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-AGENT-EVAL-008 | 计划质量 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-AGENT-EVAL-009 | 计划质量 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-AGENT-EVAL-010 | 计划质量 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-AGENT-EVAL-015 | 资源效率 | LIVE_VERIFIED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-PRE-MSG-017 | 群聊事实 | NEED_PROVISION | chat_api | not_executed | not_run | 0 | not_judged | fixture_provision_required |
| AA-REC-001-dab82f62c7a3 | AI助手 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-REC-002-e232da726b70 | AI助手 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-REC-003-d40fd5977ace | AI助手 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-PRE-SEC-043 | 权限、隔离与注入防护 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | source_read_failed |
| AA-PRE-SEC-044 | 权限、隔离与注入防护 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | actor_login_failed |
| AA-PRE-SEC-045 | 权限、隔离与注入防护 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-PRE-SEC-046 | 权限、隔离与注入防护 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PRE-SEC-047 | 权限、隔离与注入防护 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-PRE-SEC-048 | 权限、隔离与注入防护 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | source_read_failed |
| AA-PRE-SEC-049 | 权限、隔离与注入防护 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-PRE-SEC-050 | 权限、隔离与注入防护 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-PRE-OPLOG-001 | 项目与任务事实 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PRE-OPLOG-002 | 项目与任务事实 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | independent_source_missing |
| AA-PRE-REAL-001 | 空间项目任务追问 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-PRE-REAL-002 | 消息业务追问 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | independent_source_missing |
| AA-PRE-REAL-003 | 消息业务追问 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | independent_source_missing |
| AA-PRE-REAL-004 | 消息业务追问 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | independent_source_missing |
| AA-PRE-REAL-005 | 消息业务追问 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | independent_source_missing |
| AA-PRE-REAL-006 | 消息业务追问 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | independent_source_missing |
| AA-PRE-REAL-007 | 空间项目任务追问 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-PRE-REAL-008 | 空间项目任务追问 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-PRE-REAL-009 | 空间项目任务追问 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 4 | pass | judged |
| AA-PRE-REAL-010 | 空间项目任务追问 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 3 | fail | judged |
| AA-PRE-REAL-011 | 空间项目任务追问 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 3 | pass | judged |
| AA-PRE-REAL-012 | 空间项目任务追问 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AUTO-001 | 自动化任务/空间 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-002 | 自动化任务/空间 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-003 | 自动化任务/空间 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-004 | 自动化任务/空间 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-005 | 自动化任务/项目 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-006 | 自动化任务/项目 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-007 | 自动化任务/项目 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-008 | 自动化任务/项目 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-009 | 自动化任务/项目 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-010 | 自动化任务/任务 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-011 | 自动化任务/任务 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-012 | 自动化任务/任务 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-013 | 自动化任务/任务 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-014 | 自动化任务/消息 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-015 | 自动化任务/消息 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-016 | 自动化任务/消息 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-017 | 自动化任务/消息 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-018 | 自动化任务/消息 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-019 | 自动化任务/跨域 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-020 | 自动化任务/跨域 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-021 | 自动化任务/消息 | LIVE_VERIFIED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-AUTO-022 | 自动化任务/消息 | PRECHECK_REQUIRED | assistant-automation-monitor-v1 | not_executed | not_run | 0 | not_judged | dedicated_automation_driver |
| AA-ATT-UPL-001 | 附件分析/上传与交互 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-UPL-002 | 附件分析/上传与交互 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-UPL-003 | 附件分析/上传与交互 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-UPL-004 | 附件分析/上传与交互 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-UPL-005 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-006 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-007 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-008 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-009 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-010 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-011 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-012 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-013 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-014 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-015 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-016 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-017 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-018 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-019 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-020 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-021 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-022 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-023 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-024 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-025 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-UPL-026 | 附件分析/上传与交互 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-IMG-001 | 附件分析/图片 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-IMG-002 | 附件分析/图片 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-IMG-003 | 附件分析/图片 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-IMG-004 | 附件分析/图片 | PRECHECK_REQUIRED | chat_api | live_without_trace | skip | 0 | not_judged | trace_missing |
| AA-ATT-IMG-005 | 附件分析/图片 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-IMG-006 | 附件分析/图片 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-IMG-007 | 附件分析/图片 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-IMG-008 | 附件分析/图片 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-IMG-009 | 附件分析/图片 | NEED_PROVISION | chat_api | not_executed | not_run | 0 | not_judged | fixture_provision_required |
| AA-ATT-IMG-010 | 附件分析/图片 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-IMG-011 | 附件分析/图片 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-IMG-012 | 附件分析/图片 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-PDF-001 | 附件分析/PDF | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-PDF-002 | 附件分析/PDF | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-PDF-003 | 附件分析/PDF | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-PDF-004 | 附件分析/PDF | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-PDF-005 | 附件分析/PDF | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-PDF-006 | 附件分析/PDF | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-PDF-007 | 附件分析/PDF | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-PDF-008 | 附件分析/PDF | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-PDF-009 | 附件分析/PDF | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-PDF-010 | 附件分析/PDF | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-PDF-011 | 附件分析/PDF | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-ATT-PDF-012 | 附件分析/PDF | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-ATT-PDF-013 | 附件分析/PDF | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-PDF-014 | 附件分析/PDF | PRECHECK_REQUIRED | chat_api | live_without_trace | skip | 0 | not_judged | trace_missing |
| AA-ATT-XLS-001 | 附件分析/Excel | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-XLS-002 | 附件分析/Excel | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-XLS-003 | 附件分析/Excel | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-XLS-004 | 附件分析/Excel | PRECHECK_REQUIRED | chat_api | live_without_trace | skip | 0 | not_judged | trace_missing |
| AA-ATT-XLS-005 | 附件分析/Excel | NEED_PROVISION | chat_api | not_executed | not_run | 0 | not_judged | fixture_provision_required |
| AA-ATT-XLS-006 | 附件分析/Excel | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-XLS-007 | 附件分析/Excel | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-XLS-008 | 附件分析/Excel | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-XLS-009 | 附件分析/Excel | NEED_PROVISION | chat_api | not_executed | not_run | 0 | not_judged | fixture_provision_required |
| AA-ATT-XLS-010 | 附件分析/Excel | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-XLS-011 | 附件分析/Excel | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-XLS-012 | 附件分析/Excel | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-XLS-013 | 附件分析/Excel | NEED_PROVISION | chat_api | not_executed | not_run | 0 | not_judged | fixture_provision_required |
| AA-ATT-XLS-014 | 附件分析/Excel | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-XLS-015 | 附件分析/Excel | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-XLS-016 | 附件分析/Excel | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-XLS-017 | 附件分析/Excel | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-XLS-018 | 附件分析/Excel | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-DOC-001 | 附件分析/Word | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-DOC-002 | 附件分析/Word | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-DOC-003 | 附件分析/Word | PRECHECK_REQUIRED | chat_api | live_without_trace | skip | 0 | not_judged | trace_missing |
| AA-ATT-DOC-004 | 附件分析/Word | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-DOC-005 | 附件分析/Word | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-DOC-006 | 附件分析/Word | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-DOC-007 | 附件分析/Word | PRECHECK_REQUIRED | chat_api | live_without_trace | skip | 0 | not_judged | trace_missing |
| AA-ATT-DOC-008 | 附件分析/Word | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-DOC-009 | 附件分析/Word | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-DOC-010 | 附件分析/Word | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-DOC-011 | 附件分析/Word | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-DOC-012 | 附件分析/Word | NEED_PROVISION | chat_api | not_executed | not_run | 0 | not_judged | fixture_provision_required |
| AA-ATT-DOC-013 | 附件分析/Word | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-DOC-014 | 附件分析/Word | PRECHECK_REQUIRED | chat_api | live_without_trace | skip | 0 | not_judged | trace_missing |
| AA-ATT-CTX-001 | 附件分析/多文件与上下文 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-CTX-002 | 附件分析/多文件与上下文 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | skip | judged |
| AA-ATT-CTX-003 | 附件分析/多文件与上下文 | PRECHECK_REQUIRED | chat_api | live_without_trace | skip | 0 | not_judged | trace_missing |
| AA-ATT-CTX-004 | 附件分析/多文件与上下文 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 3 | skip | judged |
| AA-ATT-CTX-005 | 附件分析/多文件与上下文 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-CTX-006 | 附件分析/多文件与上下文 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 3 | fail | judged |
| AA-ATT-CTX-007 | 附件分析/多文件与上下文 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | skip | judged |
| AA-ATT-CTX-008 | 附件分析/多文件与上下文 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-QAL-001 | 附件分析/分析质量 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | skip | judged |
| AA-ATT-QAL-002 | 附件分析/分析质量 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-QAL-003 | 附件分析/分析质量 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-QAL-004 | 附件分析/分析质量 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-QAL-005 | 附件分析/分析质量 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | skip | judged |
| AA-ATT-QAL-006 | 附件分析/分析质量 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | skip | judged |
| AA-ATT-SEC-001 | 附件分析/权限与安全 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-ATT-SEC-002 | 附件分析/权限与安全 | PRECHECK_REQUIRED | chat_api | live_without_trace | skip | 0 | not_judged | trace_missing |
| AA-ATT-SEC-003 | 附件分析/权限与安全 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-SEC-004 | 附件分析/权限与安全 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-SEC-005 | 附件分析/权限与安全 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | skip | judged |
| AA-ATT-SEC-006 | 附件分析/权限与安全 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-SEC-007 | 附件分析/权限与安全 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-SEC-008 | 附件分析/权限与安全 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-SEC-009 | 附件分析/权限与安全 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-PER-001 | 附件分析/性能与稳定性 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-PER-002 | 附件分析/性能与稳定性 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-PER-003 | 附件分析/性能与稳定性 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-PER-004 | 附件分析/性能与稳定性 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-PER-005 | 附件分析/性能与稳定性 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-PER-006 | 附件分析/性能与稳定性 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-PER-007 | 附件分析/性能与稳定性 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-PER-008 | 附件分析/性能与稳定性 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-XLS-019 | 附件分析/Excel | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-DOC-015 | 附件分析/Word | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-XLS-020 | 附件分析/Excel | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-PER-009 | 附件分析/性能与稳定性 | CONTROLLED_SETUP | attachment_controlled | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-ATT-QAL-007 | 附件分析/分析质量 | PRECHECK_REQUIRED | chat_api | live_without_trace | skip | 0 | not_judged | trace_missing |
| AA-LMEM-019 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-020 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-021 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-022 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-023 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-024 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-025 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-026 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-LMEM-027 | 长期记忆与历史召回 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-SMEM-PRE-017 | 短期记忆与多轮 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-SMEM-PRE-018 | 短期记忆与多轮 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-SMEM-PRE-019 | 短期记忆与多轮 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-SMEM-PRE-020 | 短期记忆与多轮 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-SMEM-PRE-021 | 短期记忆与多轮 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-SMEM-PRE-022 | 短期记忆与多轮 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-SMEM-PRE-023 | 短期记忆与多轮 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-PRE-MSG-018 | 群聊事实 | LIVE_VERIFIED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-AGG-PRE-001 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AGG-PRE-002 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-AGG-PRE-003 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-AGG-PRE-004 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AGG-PRE-005 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AGG-PRE-006 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AGG-PRE-007 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AGG-PRE-008 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-AGG-PRE-009 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AGG-PRE-010 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AGG-PRE-011 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-AGG-PRE-012 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-AGG-PRE-013 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AGG-PRE-014 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AGG-PRE-015 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AGG-PRE-016 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-AGG-PRE-017 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-AGG-PRE-018 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AGG-PRE-019 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 2 | fail | judged |
| AA-AGG-PRE-020 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 3 | pass | judged |
| AA-AGG-PRE-021 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-AGG-PRE-022 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AGG-PRE-023 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-AGG-PRE-024 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-MULTI-PRE-001 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-MULTI-PRE-002 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | fail | judged |
| AA-MULTI-PRE-003 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-MULTI-PRE-004 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-MULTI-PRE-005 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 3 | pass | judged |
| AA-MULTI-PRE-006 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-MULTI-PRE-007 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | pass | judged |
| AA-MULTI-PRE-008 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-MULTI-PRE-009 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-MULTI-PRE-010 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-MULTI-PRE-011 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-MULTI-PRE-012 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-REAL-PRE-001 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-REAL-PRE-002 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | fail | judged |
| AA-REAL-PRE-003 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | pass | judged |
| AA-REAL-PRE-004 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-REAL-PRE-005 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | pass | judged |
| AA-REAL-PRE-006 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-REAL-PRE-007 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-REAL-PRE-008 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | fail | judged |
| AA-REAL-PRE-009 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-REAL-PRE-010 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-REAL-PRE-011 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-REAL-PRE-012 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-REAL-PRE-013 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | fail | judged |
| AA-REAL-PRE-014 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 2 | pass | judged |
| AA-REAL-PRE-015 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 2 | fail | judged |
| AA-REAL-PRE-016 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | pass | judged |
| AA-REAL-PRE-017 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | fail | judged |
| AA-REAL-PRE-018 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 3 | fail | judged |
| AA-REAL-PRE-019 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | pass | judged |
| AA-REAL-PRE-020 | 空间任务真实场景问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-RPT-PRE-001 | 汇报聚合问答 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | gold_missing |
| AA-QAP-PRE-018 | 跨源事实与风险 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-QAP-PRE-027 | 项目语义检索 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-001 | 项目语义检索 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-002 | 项目语义检索 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-004 | 项目语义检索 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-FU-PRE-005 | 项目语义检索 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-FU-PRE-006 | 项目语义检索 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-FU-PRE-007 | 项目语义检索 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-008 | 项目语义检索 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | skip | judged |
| AA-FU-PRE-009 | 项目语义检索 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-011 | 任务事实 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-012 | 任务事实 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-013 | 任务事实 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-014 | 任务事实 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-015 | 任务事实 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-FU-PRE-016 | 任务事实 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-017 | 任务事实 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-FU-PRE-019 | 任务事实 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-030 | 跨源分析与风险 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-FU-PRE-034 | 跨源分析与风险 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-FU-PRE-037 | 跨源分析与风险 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-FU-PRE-039 | 跨源分析与风险 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-040 | 跨源分析与风险 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-FU-PRE-041 | 权限与隔离 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |
| AA-FU-PRE-042 | 权限与隔离 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-FU-PRE-043 | 权限与隔离 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-FU-PRE-044 | 权限与隔离 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-FU-PRE-045 | 权限与隔离 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-FU-PRE-046 | 权限与隔离 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-FU-PRE-047 | 权限与隔离 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-050 | 权限与隔离 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-FU-PRE-051 | 权限与隔离 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-FU-PRE-056 | 冲突澄清与安全 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | independent_source_missing |
| AA-FU-PRE-057 | 冲突澄清与安全 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | independent_source_missing |
| AA-FU-PRE-058 | 冲突澄清与安全 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-FU-PRE-060 | 冲突澄清与安全 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-FU-PRE-061 | 冲突澄清与安全 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-SMEM-PRE-002 | 短期记忆与多轮 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | skip | judged |
| AA-SMEM-PRE-003 | 短期记忆与多轮 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 2 | pass | judged |
| AA-SMEM-PRE-004 | 短期记忆与多轮 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 2 | pass | judged |
| AA-SMEM-PRE-005 | 短期记忆与多轮 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 2 | skip | judged |
| AA-SMEM-PRE-006 | 短期记忆与多轮 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 3 | fail | judged |
| AA-SMEM-PRE-007 | 短期记忆与多轮 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 3 | fail | judged |
| AA-SMEM-PRE-008 | 短期记忆与多轮 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 2 | pass | judged |
| AA-SMEM-PRE-009 | 短期记忆与多轮 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 3 | fail | judged |
| AA-SMEM-PRE-011 | 短期记忆与多轮 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 3 | fail | judged |
| AA-SMEM-PRE-012 | 短期记忆与多轮 | PRECHECK_REQUIRED | chat_api | live_without_trace | skip | 0 | not_judged | trace_missing |
| AA-SMEM-PRE-013 | 短期记忆与多轮 | PRECHECK_REQUIRED | chat_api | live_without_trace | skip | 0 | not_judged | trace_missing |
| AA-SMEM-PRE-014 | 短期记忆与多轮 | CONTROLLED_SETUP | chat_api | not_executed | not_run | 0 | not_judged | controlled_setup_required |
| AA-SMEM-PRE-015 | 短期记忆与多轮 | PRECHECK_REQUIRED | chat_api | live_without_trace | skip | 0 | not_judged | trace_missing |
| AA-SMEM-PRE-016 | 短期记忆与多轮 | PRECHECK_REQUIRED | chat_api | live_without_trace | fail | 0 | not_judged | trace_missing |
| AA-AGENT-EVAL-PRE-011 | 计划质量 | PRECHECK_REQUIRED | chat_api | not_executed | not_run | 0 | not_judged | independent_source_missing |
| AA-AGENT-EVAL-PRE-013 | 执行稳定性 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 10 | fail | judged |
| AA-PROG-PRE-001 | 项目/任务进度 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PROG-PRE-002 | 项目/任务进度 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PROG-PRE-003 | 项目/任务进度 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PROG-PRE-004 | 项目/任务进度 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | fail | judged |
| AA-PROG-PRE-005 | 项目/任务进度 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PROG-PRE-006 | 项目/任务进度 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PROG-PRE-007 | 项目/任务进度 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PROG-PRE-008 | 项目/任务进度 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | skip | judged |
| AA-PROG-PRE-009 | 项目/任务进度 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PROG-PRE-010 | 项目/任务进度 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PROG-PRE-011 | 项目/任务进度 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 1 | pass | judged |
| AA-PROG-PRE-012 | 项目/任务进度 | PRECHECK_REQUIRED | chat_api | live_with_trace | fail | 2 | fail | judged |
| AA-FU-PRE-069 | 项目与任务事实 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | pass | judged |
| AA-MULTI-PRE-013 | 空间任务聚合问答 | PRECHECK_REQUIRED | chat_api | live_with_trace | skip | 1 | fail | judged |

## 口径

`live_with_trace` 仅表示获得认证内部 Trace；业务结果以逐轮裁判为准。`not_judged` 不进入任务成功率分母。未执行原因记录前置条件或授权状态，不当作产品质量失败。原始回答、认证日志、请求体和凭据保存在本机运行目录，未纳入 Git 报告。
