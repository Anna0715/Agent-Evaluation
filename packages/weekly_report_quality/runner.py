"""Run orchestration: lint cases, load evidence, evaluate, aggregate,
verify with the three confidence checks, and persist the run artifacts.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from weekly_report_quality import __version__
from weekly_report_quality.aggregate import (
    DEFAULT_PASS_THRESHOLD,
    aggregate_case,
    baseline_diff,
    summarize_run,
)
from weekly_report_quality.checks import verify_case
from weekly_report_quality.contracts import (
    RESULT_CONTRACT,
    CaseSpec,
    CheckResult,
    ContractError,
    load_cases,
    load_evidence_for_case,
)
from weekly_report_quality.evaluators import run_deterministic
from weekly_report_quality.lint import lint_cases
from weekly_report_quality.permission import evaluate_permission
from weekly_report_quality.semantic import evaluate_semantic


@dataclass
class RunConfig:
    cases_dir: Path
    evidence_dir: Path
    out_dir: Path
    baseline_file: Path | None = None
    run_id: str = ""
    trigger: str = "manual"
    selected_evaluators: list[str] | None = None
    selected_tags: list[str] | None = None
    selected_cases: list[str] | None = None
    pass_threshold: float = DEFAULT_PASS_THRESHOLD
    resume: bool = False


def _select(cases: list[CaseSpec], config: RunConfig) -> list[CaseSpec]:
    selected = cases
    if config.selected_cases:
        wanted = set(config.selected_cases)
        selected = [c for c in selected if c.id in wanted]
    if config.selected_tags:
        wanted = set(config.selected_tags)
        selected = [c for c in selected if wanted & set(c.tags)]
    return selected


def load_baseline(path: Path | None) -> list[dict] | None:
    if path is None or not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "case_results" in data:
        return data["case_results"]
    if isinstance(data, list):
        return data
    raise ContractError(str(path), "baseline must be a run file or list of case results")


def evaluate_one(
    case: CaseSpec, evidence, selected: list[str] | None = None
) -> list[CheckResult]:
    checks = run_deterministic(case, evidence, selected)
    if selected is None or "permission_boundary" in selected:
        checks += evaluate_permission(case, evidence)
    semantic_selected = selected is None or any(
        s in selected
        for s in ("grounding", "cross_period", "style_semantics", "cross_recipient_consistency")
    )
    if semantic_selected:
        checks += evaluate_semantic(case, evidence)
    return checks


def execute_run(config: RunConfig) -> dict:
    run_id = config.run_id or f"run-{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"
    started_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    cases = load_cases(config.cases_dir)
    issues = lint_cases(cases)
    if issues:
        details = "; ".join(f"{i.case_id}.{i.field}: {i.message}" for i in issues)
        raise ContractError(str(config.cases_dir), f"case lint failed: {details}")
    cases = _select(cases, config)
    if not cases:
        raise ContractError(str(config.cases_dir), "no cases selected after filters")

    baseline = load_baseline(config.baseline_file)
    case_results: list[dict] = []
    missing_evidence_cases: list[str] = []

    for case in cases:
        if config.resume and run_id:
            done = config.out_dir / run_id / "cases" / f"{case.id}.json"
            if done.exists():
                previous_result = json.loads(done.read_text(encoding="utf-8"))
                if previous_result.get("case_digest") == case.digest():
                    case_results.append(previous_result)
                    continue
        evidence = load_evidence_for_case(config.evidence_dir, case.id)
        if evidence is None:
            missing_evidence_cases.append(case.id)
            case_results.append(
                {
                    "case_id": case.id,
                    "case_version": case.version,
                    "case_digest": case.digest(),
                    "tags": case.tags,
                    "status": "skip",
                    "gating_reason": "missing_evidence: no evidence file for case",
                    "weighted_score": None,
                    "pass_threshold": config.pass_threshold,
                    "critical_failures": [],
                    "skipped_dimensions": [],
                    "errored_dimensions": [],
                    "disagreements": [],
                    "checks": [],
                    "confidence": "low",
                    "confidence_signals": [
                        {
                            "check": "replay_check",
                            "outcome": "unavailable",
                            "detail": "no evidence artifact",
                        }
                    ],
                    "adjudication_required": True,
                }
            )
            continue
        checks = evaluate_one(case, evidence, config.selected_evaluators)
        result = aggregate_case(case, checks, config.pass_threshold)
        result["evidence_digest"] = evidence.digest()
        result = verify_case(case, evidence, checks, result, baseline)
        case_results.append(result)

    summary = summarize_run(case_results)
    summary["missing_evidence_cases"] = missing_evidence_cases
    summary["confidence_distribution"] = {
        level: sum(1 for r in case_results if r.get("confidence") == level)
        for level in ("high", "medium", "low")
    }
    summary["adjudication_required_cases"] = [
        r["case_id"] for r in case_results if r.get("adjudication_required")
    ]

    run = {
        "contract": RESULT_CONTRACT,
        "framework_version": __version__,
        "run_id": run_id,
        "trigger": config.trigger,
        "started_at": started_at,
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "cases_dir": str(config.cases_dir),
        "evidence_dir": str(config.evidence_dir),
        "case_count": len(cases),
        "summary": summary,
        "baseline_diff": baseline_diff(case_results, baseline) if baseline else None,
        "case_results": case_results,
    }
    return run
