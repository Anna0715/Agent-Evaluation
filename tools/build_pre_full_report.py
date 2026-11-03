#!/usr/bin/env python3
"""Summarize a pre run without publishing raw answers or authentication data."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CaseInfo:
    id: str
    module: str
    priority: str
    data_state: str
    executor: str


REASON_LABELS = {
    "authorization_hold": "此前明确保留的持久提醒或群监控用例",
    "controlled_setup_required": "需要逐例受控环境、故障或权限条件",
    "dedicated_automation_driver": "需要专用自动化调度与运行证据",
    "fixture_provision_required": "业务夹具尚未准备完成",
    "acceptance_spec_pending": "验收口径尚未定稿",
    "actor_login_failed": "测试账号登录或验证码不可用",
    "source_read_failed": "独立业务源回读失败",
    "independent_source_missing": "缺少可独立核验的正向来源",
    "gold_missing": "参考真值不完整",
    "ready_not_executed": "已准备但本轮尚未执行",
    "not_prechecked": "未完成前置核验",
    "precheck_not_ready": "前置核验未通过",
}


def read_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_scope_cases(workbook: Path, scope_ids: list[str]) -> list[CaseInfo]:
    book = load_workbook(workbook, read_only=True, data_only=True)
    try:
        sheet = book["用例库"]
        headers = [cell.value for cell in sheet[2]]
        selected: dict[str, CaseInfo] = {}
        wanted = set(scope_ids)
        for values in sheet.iter_rows(min_row=3, values_only=True):
            row = dict(zip(headers, values))
            case_id = str(row.get("用例ID") or "").strip()
            if case_id not in wanted:
                continue
            if case_id in selected:
                raise ValueError(f"duplicate workbook case: {case_id}")
            selected[case_id] = CaseInfo(
                id=case_id,
                module=str(row.get("一级模块") or ""),
                priority=str(row.get("优先级") or ""),
                data_state=str(row.get("数据状态") or ""),
                executor=str(row.get("执行器") or ""),
            )
        if set(selected) != wanted:
            raise ValueError(f"workbook/scope mismatch: {len(wanted - set(selected))} missing")
        return [selected[case_id] for case_id in scope_ids]
    finally:
        book.close()


def precheck_code(case: Any, readiness: dict[str, Any], held: set[str]) -> str:
    if case.id in held:
        return "authorization_hold"
    if case.executor == "assistant-automation-monitor-v1":
        return "dedicated_automation_driver"
    if case.data_state == "CONTROLLED_SETUP":
        return "controlled_setup_required"
    if case.data_state == "NEED_PROVISION":
        return "fixture_provision_required"
    if case.data_state == "SPEC_PENDING":
        return "acceptance_spec_pending"
    item = readiness.get(case.id) or {}
    if item.get("ready") is True:
        return "ready_not_executed"
    reason = str(item.get("reason") or "")
    if "login failed" in reason or "验证码" in reason or "OTP_AUTH" in reason:
        return "actor_login_failed"
    if "必要业务对象回读未通过" in reason:
        return "source_read_failed"
    if "无可独立核验" in reason:
        return "independent_source_missing"
    if "Gold" in reason:
        return "gold_missing"
    return "precheck_not_ready" if item else "not_prechecked"


def collect(run_dir: Path) -> dict[str, Any]:
    workbook = run_dir / "private/workbook.xlsx"
    scope = read_json(run_dir / "historical_scope.json", {})
    scope_ids = scope.get("case_ids") or []
    assert len(scope_ids) == len(set(scope_ids)) == 401
    cases = load_scope_cases(workbook, scope_ids)
    held = set(scope.get("authorization_denied") or [])

    direct = run_dir / "direct"
    ready = run_dir / "ready-live/cases"
    direct_results = read_json(direct / "case_results.json", {})
    direct_records = read_json(direct / "live_evidence.json", {}).get("records") or {}
    readiness = read_json(direct / "readiness.json", {}).get("cases") or {}
    judgments = {
        path.stem: read_json(path, {})
        for path in (direct / "judgments").glob("*.json")
    }
    for case_id, verdict in judgments.items():
        meta = verdict.get("judge_meta") or {}
        if (meta.get("model"), meta.get("endpoint"), meta.get("transport")) != (
            "gpt-6.1-sol", "https://test-ai.oa-test.org/sub2api/v1/chat/completions", "sse"
        ):
            raise ValueError(f"unverified judge provenance: {case_id}")
    results = dict(direct_results)
    records = dict(direct_records)
    started = set()
    for directory in ready.iterdir() if ready.is_dir() else []:
        if not directory.is_dir():
            continue
        if (directory / "started.json").is_file():
            started.add(directory.name)
        run = read_json(directory / "run.json", {})
        evidence = read_json(directory / "live_evidence.json", {})
        for result in run.get("case_results") or []:
            case_id = result["case_id"]
            if case_id in results:
                raise ValueError(f"duplicate live result: {case_id}")
            results[case_id] = result
        for case_id, record in (evidence.get("records") or {}).items():
            if case_id in records:
                raise ValueError(f"duplicate live evidence: {case_id}")
            records[case_id] = record
    for path in (direct / "trace-backfill").glob("*.json"):
        if path.stem in records:
            records[path.stem] = read_json(path, {})

    unknown = (set(results) | set(records) | set(judgments) | started) - set(scope_ids)
    if unknown:
        raise ValueError(f"out-of-scope evidence: {sorted(unknown)}")
    rows = []
    for case in cases:
        result = results.get(case.id) or {}
        record = records.get(case.id) or {}
        verdict = judgments.get(case.id) or {}
        trace_runs = len((record.get("metadata") or {}).get("trace_runs") or [])
        if verdict and not trace_runs:
            raise ValueError(f"judgment without authenticated Trace: {case.id}")
        if trace_runs:
            execution = "live_with_trace"
        elif record or result:
            execution = "live_without_trace"
        elif case.id in started:
            execution = "started_incomplete"
        else:
            execution = "not_executed"
        business = verdict.get("business_status") or "not_judged"
        if business not in {"pass", "fail", "skip", "not_judged"}:
            raise ValueError(f"invalid business verdict: {case.id}")
        if verdict:
            reason_code = "judged"
        elif trace_runs:
            reason_code = "judge_pending"
        elif record or result:
            reason_code = "trace_missing"
        elif case.id in started:
            reason_code = "interrupted"
        else:
            reason_code = precheck_code(case, readiness, held)
        rows.append({
            "case_id": case.id,
            "module": case.module,
            "priority": case.priority,
            "data_state": case.data_state,
            "executor": case.executor,
            "execution": execution,
            "automatic_status": result.get("status") or "not_run",
            "trace_runs": trace_runs,
            "business_status": business,
            "reason_code": reason_code,
            "failure_categories": [str(value)[:80] for value in verdict.get("failure_categories") or []] if business == "fail" else [],
            "agent_model": (result.get("versions") or {}).get("model") or "",
            "agent_prompt": (result.get("versions") or {}).get("prompt") or "",
        })

    execution_counts = Counter(row["execution"] for row in rows)
    business_counts = Counter(row["business_status"] for row in rows)
    automatic_counts = Counter(row["automatic_status"] for row in rows)
    reason_counts = Counter(row["reason_code"] for row in rows if row["execution"] == "not_executed")
    category_counts = Counter(category for row in rows for category in row["failure_categories"])
    assessed = business_counts["pass"] + business_counts["fail"]
    trace_total = execution_counts["live_with_trace"]
    judged = assessed + business_counts["skip"]
    summary = {
        "scope_total": 401,
        "execution": dict(sorted(execution_counts.items())),
        "automatic": dict(sorted(automatic_counts.items())),
        "business": dict(sorted(business_counts.items())),
        "not_executed_reasons": dict(sorted(reason_counts.items())),
        "business_failure_categories": dict(sorted(category_counts.items())),
        "authenticated_trace_cases": trace_total,
        "judged_cases": judged,
        "unjudged_trace_cases": trace_total - judged,
        "business_success_denominator": assessed,
        "business_success_rate": business_counts["pass"] / assessed if assessed else None,
        "agent_models": dict(sorted(Counter(row["agent_model"] for row in rows if row["agent_model"]).items())),
        "agent_prompts": dict(sorted(Counter(row["agent_prompt"] for row in rows if row["agent_prompt"]).items())),
        "started_incomplete": execution_counts["started_incomplete"],
        "all_ready_cases_settled": not any(row["reason_code"] == "ready_not_executed" for row in rows),
        "judge_complete_for_trace": judged == trace_total,
    }
    assert sum(execution_counts.values()) == sum(business_counts.values()) == 401
    assert judged <= trace_total
    return {
        "contract": "ai_assistant.pre_full_execution_report.v1",
        "environment": "pre",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workbook_sha256": hashlib.sha256(workbook.read_bytes()).hexdigest(),
        "source_run_dir": str(run_dir.relative_to(ROOT)),
        "judge": {
            "endpoint": "https://test-ai.oa-test.org/sub2api/v1/chat/completions",
            "model": "gpt-6.1-sol",
            "stream": True,
            "purpose": "business verdicts only",
        },
        "summary": summary,
        "cases": rows,
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    execution = summary["execution"]
    business = summary["business"]
    rate = summary["business_success_rate"]
    lines = [
        "# pre 用例全量范围与执行报告",
        "",
        f"生成时间（UTC）：{report['generated_at']}",
        f"范围：{summary['scope_total']} 条，环境：pre。工作簿 SHA-256：`{report['workbook_sha256']}`。",
        "",
        "## 执行与裁判",
        "",
        f"- 已取得认证 Trace：{summary['authenticated_trace_cases']}；有运行结果但无 Trace：{execution.get('live_without_trace', 0)}；启动未完成：{execution.get('started_incomplete', 0)}；未执行：{execution.get('not_executed', 0)}。",
        f"- 业务裁判：通过 {business.get('pass', 0)}、失败 {business.get('fail', 0)}、证据不足 {business.get('skip', 0)}、尚未裁判 {business.get('not_judged', 0)}。",
        f"- 任务成功率：{rate:.1%}（{business.get('pass', 0)}/{summary['business_success_denominator']}）" if rate is not None else "- 任务成功率：未形成可判定分母。",
        f"- 裁判覆盖：{summary['judged_cases']}/{summary['authenticated_trace_cases']} 条有 Trace 用例。普通问答经过真实 pre 业务接口；裁判使用 `gpt-6.1-sol` 流式接口。",
        "- 助手模型（执行回执）：" + ("、".join(f"`{name}` {count} 条" for name, count in summary["agent_models"].items()) or "未采集") + "。",
        "- 自动状态与业务判定分列；自动跳过或请求成功都不直接等于业务失败或通过。",
        "",
        "## 未执行原因",
        "",
        "| 代码 | 说明 | 数量 |",
        "| --- | --- | ---: |",
    ]
    lines.extend(f"| `{code}` | {REASON_LABELS.get(code, '待复核')} | {count} |" for code, count in summary["not_executed_reasons"].items())
    if summary["business_failure_categories"]:
        lines.extend(["", "## 业务失败分类", "", "| 分类 | 数量 |", "| --- | ---: |"])
        lines.extend(f"| {category.replace('|', '\\|')} | {count} |" for category, count in summary["business_failure_categories"].items())
    missing_trace = [row["case_id"] for row in report["cases"] if row["execution"] == "live_without_trace"]
    if missing_trace:
        lines.extend(["", "## 认证 Trace 缺口", ""])
        lines.extend(f"- `{case_id}`" for case_id in missing_trace)
    lines.extend([
        "",
        "## 逐案台账",
        "",
        "| 用例 | 模块 | 数据状态 | 执行器 | 执行 | 自动状态 | Trace | 业务裁判 | 原因代码 |",
        "| --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
    ])
    for row in report["cases"]:
        cells = [row[key] for key in ("case_id", "module", "data_state", "executor", "execution", "automatic_status")]
        cells += [str(row["trace_runs"]), row["business_status"], row["reason_code"]]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in cells) + " |")
    lines.extend([
        "",
        "## 口径",
        "",
        "`live_with_trace` 仅表示获得认证内部 Trace；业务结果以逐轮裁判为准。`not_judged` 不进入任务成功率分母。未执行原因记录前置条件或授权状态，不当作产品质量失败。原始回答、认证日志、请求体和凭据保存在本机运行目录，未纳入 Git 报告。",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = collect(args.run_dir.resolve())
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "report.json", report)
    (args.out / "report.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
