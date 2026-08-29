# online — 在线评测 (Online E2E)

test/pre 环境端到端链路：**执行 → 打分 → 发布 → 同步 → 定时**。

| 脚本 | 职责 |
|------|------|
| `env_config.py` / `login.py` | 环境与登录 |
| `run_report_agent_cases.py` | 跑用例 |
| `eval_engine.py` | 在线打分 |
| `publish_quality_report.py` | 发布报告 |
| `serve_quality_report.py` | 本地复核 |
| `quality_sync*.py` | 同步发布 |
| `schedule/` | 定时任务 |