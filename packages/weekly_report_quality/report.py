"""Report emitters: per-case JSON, aggregate JSON, JUnit XML, Markdown,
and the daily comparison view across the two scheduled runs.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from weekly_report_quality.contracts import json_dumps, write_json


def write_run_outputs(run: dict, out_dir: Path) -> dict:
    """Persist all artifacts for one run; returns emitted paths."""
    run_dir = out_dir / run["run_id"]
    per_case_dir = run_dir / "cases"
    for result in run["case_results"]:
        write_json(per_case_dir / f"{result['case_id']}.json", result)
    write_json(run_dir / "run.json", run)
    junit_path = run_dir / "junit.xml"
    junit_path.write_text(to_junit_xml(run), encoding="utf-8")
    md_path = run_dir / "report.md"
    md_path.write_text(to_markdown(run), encoding="utf-8")
    return {
        "run_dir": str(run_dir),
        "run_json": str(run_dir / "run.json"),
        "junit": str(junit_path),
        "markdown": str(md_path),
    }


def to_junit_xml(run: dict) -> str:
    summary = run["summary"]
    suite = ET.Element(
        "testsuite",
        name=f"weekly-report-quality:{run['run_id']}",
        tests=str(summary["total_cases"]),
        failures=str(summary["fail"]),
        errors=str(summary["error"]),
        skipped=str(summary["skip"]),
    )
    for result in run["case_results"]:
        case = ET.SubElement(
            suite,
            "testcase",
            classname="weekly_report_quality",
            name=result["case_id"],
        )
        message = result.get("gating_reason", "")
        if result["status"] == "fail":
            ET.SubElement(case, "failure", message=message).text = json_dumps(
                result["critical_failures"], indent=None
            )
        elif result["status"] == "error":
            ET.SubElement(case, "error", message=message)
        elif result["status"] == "skip":
            ET.SubElement(case, "skipped", message=message)
        props = ET.SubElement(case, "properties")
        ET.SubElement(
            props, "property", name="confidence", value=str(result.get("confidence", ""))
        )
    return ET.tostring(suite, encoding="unicode", xml_declaration=True)


def _fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def to_markdown(run: dict) -> str:
    summary = run["summary"]
    lines = [
        f"# 周报 Agent 质检报告 — {run['run_id']}",
        "",
        f"- 触发方式: {run['trigger']}",
        f"- 开始/结束: {run['started_at']} → {run['finished_at']}",
        f"- 用例数: {summary['total_cases']}  通过: {summary['pass']}  失败: {summary['fail']}  "
        f"跳过: {summary['skip']}  错误: {summary['error']}",
        f"- 通过率: {_fmt(summary['pass_rate'])}  平均加权分: {_fmt(summary['avg_weighted_score'])}",
        f"- critical 失败用例: {summary['critical_failure_cases'] or '无'}",
        "",
        "## 置信度分布（三轮 check）",
        "",
        "| 置信等级 | 用例数 |",
        "| --- | --- |",
    ]
    for level in ("high", "medium", "low"):
        lines.append(f"| {level} | {summary['confidence_distribution'][level]} |")
    adjudication = summary.get("adjudication_required_cases", [])
    lines += [
        "",
        f"需要仲裁（低置信）: {adjudication or '无'}",
        "",
        "## 权限校验覆盖",
        "",
        "| 子维度 | pass | fail | skip |",
        "| --- | --- | --- | --- |",
    ]
    for dim, stats in summary["permission_coverage"].items():
        lines.append(f"| {dim} | {stats['pass']} | {stats['fail']} | {stats['skip']} |")
    lines += [
        "",
        "## 逐用例结果",
        "",
        "| 用例 | 状态 | 加权分 | 置信度 | 关键失败/原因 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in run["case_results"]:
        reason = result.get("gating_reason") or ""
        lines.append(
            f"| {result['case_id']} | {result['status']} | {_fmt(result['weighted_score'])} "
            f"| {result.get('confidence', '-')} | {reason} |"
        )
    diff = run.get("baseline_diff")
    if diff:
        lines += [
            "",
            "## 相对基线",
            "",
            f"- 回归用例: {diff['regressed'] or '无'}",
            f"- 修复用例: {diff['improved'] or '无'}",
            f"- 新增 critical: {diff['new_critical'] or '无'}",
            f"- 版本不兼容告警: {diff['incompatible_version'] or '无'}",
        ]
    lines += [
        "",
        "## 三轮 check 明细（低/中置信用例）",
        "",
    ]
    flagged = [
        r for r in run["case_results"] if r.get("confidence") in ("low", "medium")
    ]
    if not flagged:
        lines.append("全部用例三轮 check 佐证，置信度 high。")
    for result in flagged:
        lines.append(f"### {result['case_id']} — confidence {result['confidence']}")
        for signal in result.get("confidence_signals", []):
            lines.append(f"- `{signal['check']}` → {signal['outcome']}: {signal['detail']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def list_runs(runs_dir: Path) -> list[dict]:
    runs = []
    for run_json in sorted(runs_dir.glob("*/run.json")):
        runs.append(json.loads(run_json.read_text(encoding="utf-8")))
    return runs


def daily_report(runs_dir: Path, date: str) -> str:
    """Comparison view across the (up to two) scheduled runs of one day.

    date format: YYYYMMDD (matched against run started_at).
    """
    runs = [r for r in list_runs(runs_dir) if r["started_at"].replace("-", "").startswith(date)]
    if not runs:
        return f"# 每日质检报告 {date}\n\n当日无运行记录。\n"
    runs.sort(key=lambda r: r["started_at"])
    lines = [f"# 每日质检报告 {date}", "", f"当日运行次数: {len(runs)}", ""]
    lines += [
        "| 运行 | 开始时间 | 通过/失败/跳过 | 通过率 | critical | 低置信 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for run in runs:
        s = run["summary"]
        lines.append(
            f"| {run['run_id']} | {run['started_at']} | {s['pass']}/{s['fail']}/{s['skip']} "
            f"| {_fmt(s['pass_rate'])} | {len(s['critical_failure_cases'])} "
            f"| {s['confidence_distribution']['low']} |"
        )
    if len(runs) >= 2:
        first, second = runs[-2], runs[-1]
        first_by_id = {r["case_id"]: r for r in first["case_results"]}
        flips, new_critical = [], []
        for result in second["case_results"]:
            prev = first_by_id.get(result["case_id"])
            if prev is None:
                continue
            if prev["status"] != result["status"]:
                flips.append(f"{result['case_id']}: {prev['status']} → {result['status']}")
            fresh = set(result["critical_failures"]) - set(prev["critical_failures"])
            if fresh:
                new_critical.append(f"{result['case_id']}: {sorted(fresh)}")
        lines += [
            "",
            f"## 两次运行对比（{first['run_id']} → {second['run_id']}）",
            "",
            f"- 状态翻转: {flips or '无'}",
            f"- 第二次运行新增 critical: {new_critical or '无'}",
        ]
    return "\n".join(lines) + "\n"
