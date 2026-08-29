# Agent-Evaluation

评测核心在 `packages/weekly_report_quality`（纯 Python 标准库），种子用例与证据 fixture 在 `testdata/weekly_report_quality`，单元测试在 `tests/weekly_report_quality`。

## 快速开始

```bash
# 用例 lint
PYTHONPATH=packages python3 -m weekly_report_quality lint \
  --cases testdata/weekly_report_quality/cases

# 离线评测一次（从证据 artifact 重放）
PYTHONPATH=packages python3 -m weekly_report_quality run \
  --cases testdata/weekly_report_quality/cases \
  --evidence testdata/weekly_report_quality/evidence \
  --out testdata/weekly_report_quality/runs

# 定时入口（每天两次调度用，自动以上一次运行为基线）
PYTHONPATH=packages python3 -m weekly_report_quality daily \
  --cases ... --evidence ... --out ...

# 当日两次运行的对比报告
PYTHONPATH=packages python3 -m weekly_report_quality report \
  --runs-dir testdata/weekly_report_quality/runs --date 20260820

# 单元测试
python3 -m unittest discover -s tests/weekly_report_quality
```

常用参数：`--evaluators route,mcp`（按评测器选择）、`--tags permission`、`--case TC01`、`--resume`（断点续跑）、`--gate`（fail/error 时退出非零，供 CI 门禁）、`--baseline <run.json>`。

## 定时执行（每天两次）

`packages/weekly_report_quality/schedule/run_twice_daily.sh` 是调度入口，crontab 示例：

```
0 9,21 * * * /path/to/Agent-Evaluation/packages/weekly_report_quality/schedule/run_twice_daily.sh
```

同一命令也可以配置成 Jenkins cron job。运行失败/超时会输出 `ALERT:` 行并以非零退出，不会静默跳过；目录可用 `WRQ_CASES_DIR`、`WRQ_EVIDENCE_DIR`、`WRQ_RUNS_DIR` 覆盖。每次运行归档在 `<runs>/<run_id>/`，并自动刷新 `daily-<date>.md` 对比视图。

## 数据契约

三层分离（`contracts.py`）：

- `CaseSpec`（`weekly_report_quality.case.v1`）：`input`（material/recipient/context 含租户、用户、可见范围）、`expect`（route/faq/skill/mcp/output/permission/语义维度）、`oracle`（预期来源与置信度）、`scoring`（权重与阈值）。
- `RunEvidence`（`weekly_report_quality.evidence.v1`）：输出、路由、FAQ 候选、Skill 快照、MCP 调用、记忆读写事件、Judge 结构化响应；缺失的部分保持 `null`，评测器返回 `skip: missing_evidence` 而不是猜测。
- `CheckResult`：`status(pass/fail/skip/error)` + `score` + `severity` + 证据。

在线执行链路（可选）：外部批量摘要脚本或 `live/run_report_agent_cases.py` 产出 Trace 后，通过 `normalize.build_evidence` / `normalize.from_business_agent_trace` 归一化为 Evidence（默认脱敏 JWT/密钥/Bearer token），之后全部离线评测、可重放。

## 评测维度

确定性评测器（`evaluators.py`）：`route`、`faq_retrieval`（Recall@K/MRR/NDCG/must-not-hit/权限过滤）、`skill`、`mcp`（工具、参数子集、顺序、次数、失败回退、禁止调用）、`output_contract`。

权限评测器（`permission.py`，全部 critical 硬门禁，不参与加权分）：

| 子维度 | 断言 |
| --- | --- |
| tenant_isolation | 跨租户请求必须拒绝；输出与检索候选不得含其他租户数据 |
| report_acl | 检索候选必须落在可见/被分享周报范围内（即使输出未引用） |
| contact_visibility | 不可见人员不得出现在输出，也不得通过 MCP 拉取 |
| prompt_injection | 注入用例不得泄漏越权数据，抵抗率单独统计 |
| memory_isolation | 习惯记忆读写限定在 租户ID+userID |

语义评测器（`semantic.py`，Judge 结构化裁决）：`grounding`、`cross_period`、`style_semantics`、`cross_recipient_consistency`。同时运行 expectation critic：预期本身推不出来时标记 `expectation_disagreement` 交人工复核，不惩罚候选输出。

变形测试（`metamorphic.py`）：`drop_previous`、`inject_irrelevant_faq`、`change_recipient_role`、`paraphrase_current`、`swap_unrelated_segments`，每个变形声明允许/禁止变化的维度，用 `compare_metamorphic` 检出违例。

## 聚合与硬门禁

- 加权总分按维度权重聚合（默认见 `aggregate.DEFAULT_WEIGHTS`，用例可用 `scoring.weights` 覆盖）。
- 任何 critical 失败（权限越界、禁用 MCP、输出不可解析、禁止路由等）直接判 fail，加权分不能补偿。
- `skip` 不算通过也不算失败，报告单列，防止缺失 Trace 被掩盖。

## 三轮 check 与置信度

三轮 check 的目的是提升评测结果置信度，不要求三轮结论强制一致：

1. `replay_check`：用落盘证据重放全部确定性评测器，验证可复现。
2. `judge_recheck`：语义维度用独立第二 Judge 复评，衡量稳定性。
3. `baseline_check`：与基线/上一次定时运行比对回归。

每轮产出 `corroborate/contradict/unavailable` 信号，聚合为置信等级：全佐证 = `high`；有 unavailable 无矛盾 = `medium`（注明缺失原因）；任一矛盾 = `low` 并进入 `adjudication_required`，报告中单列，不平均、不选边。所有结果都会带置信标注进入报告。

## 报告产物

每次运行输出到 `<runs>/<run_id>/`：

- `run.json`：完整机器可读结果（含 summary、baseline diff、逐用例三轮 check 信号）。
- `cases/<id>.json`：逐用例结果。
- `junit.xml`：CI 兼容。
- `report.md`：人类可读，含通过率、置信度分布、权限覆盖、逐用例结论、基线对比。
- `daily-<date>.md`：当日两次运行的对比（状态翻转、新增 critical）。

## 用例编写指南

1. 复制 `testdata/weekly_report_quality/cases/TC01.json` 起步；`id` 唯一、`version` 递增。
2. 只声明可观察的预期；强 must 断言必须填 `oracle.source` 与证据。
3. 权限用例写 `expect.permission`；`expect_refusal: true` 必须给 `refusal_markers`。
4. 语义维度需要在证据里录制 Judge 结构化响应（`judge_responses.<dim>` / `<dim>_second` / `critic`）。
5. 提交前跑 `lint` 与单测。

## 故障排查

- `contract error: ... case lint failed`：按提示修用例字段冲突。
- 用例全部 `skip`：证据目录里缺 `<case_id>.json`，检查 `--evidence` 路径。
- `medium` 置信偏多：通常是无语义维度（judge_recheck 不可用）或首个运行无基线，属预期行为。
- Judge verdict 报 error：`judge_responses` 里的结构不满足 `{pass: bool, score: 0..1, reasons: []}`。

## 灰度计划（运营侧）

- 先以非阻断模式运行每日两次调度，观察 Trace 完整率与权限证据覆盖率。
- 人工盲审抽样语义结论，记录 Judge 与人工一致率；达标前语义分不作为硬门禁。
- 达标后按模块逐步在 CI 中启用 `--gate`。
