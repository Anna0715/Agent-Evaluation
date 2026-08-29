"""Aggregation: weighted scores, critical hard gates, run summary,
baseline diff. Critical failures always fail the case regardless of the
weighted score; skips are reported separately and never counted as passes.
"""

from __future__ import annotations

from weekly_report_quality.contracts import (
    ERROR,
    FAIL,
    PASS,
    SEVERITY_CRITICAL,
    SKIP,
    CaseSpec,
    CheckResult,
)
from weekly_report_quality.permission import permission_coverage

DEFAULT_WEIGHTS = {
    "route": 1.0,
    "faq_retrieval": 1.0,
    "skill": 1.0,
    "mcp": 1.0,
    "output_contract": 1.0,
    "grounding": 2.0,
    "cross_period": 1.0,
    "style_semantics": 1.0,
    "cross_recipient_consistency": 1.0,
}
DEFAULT_PASS_THRESHOLD = 0.7


def _weight_for(dimension: str, weights: dict) -> float:
    root = dimension.split(".", 1)[0]
    return float(weights.get(dimension, weights.get(root, 0.0)))


def aggregate_case(
    case: CaseSpec,
    checks: list[CheckResult],
    pass_threshold: float = DEFAULT_PASS_THRESHOLD,
) -> dict:
    weights = {**DEFAULT_WEIGHTS, **(case.scoring.get("weights") or {})}
    threshold = float(case.scoring.get("pass_threshold", pass_threshold))

    critical_failures = [
        c.dimension for c in checks if c.status == FAIL and c.severity == SEVERITY_CRITICAL
    ]
    errors = [c.dimension for c in checks if c.status == ERROR]
    skips = [c.dimension for c in checks if c.status == SKIP]

    weighted_sum = 0.0
    weight_total = 0.0
    for check in checks:
        if check.status not in (PASS, FAIL) or check.score is None:
            continue
        weight = _weight_for(check.dimension, weights)
        if weight <= 0:
            continue
        weighted_sum += weight * float(check.score)
        weight_total += weight
    weighted_score = (weighted_sum / weight_total) if weight_total else None

    disagreements = []
    semantic_pass = any(
        c.status == PASS and c.evaluator in ("grounding", "style_semantics") for c in checks
    )
    if semantic_pass and critical_failures:
        disagreements.append(
            {
                "kind": "oracle_conflict",
                "detail": (
                    "semantic judge passed while deterministic critical assertions failed; "
                    f"deterministic gate prevails: {critical_failures}"
                ),
            }
        )
    disagreements.extend(
        {"kind": "expectation_disagreement", "detail": c.dimension}
        for c in checks
        if c.reason == "expectation_disagreement" and c.evaluator != "expectation_critic"
    )

    has_verdicts = any(c.status in (PASS, FAIL) for c in checks)
    if critical_failures:
        status = FAIL
        gating_reason = f"critical failure: {critical_failures[0]}"
    elif any(c.status == FAIL for c in checks):
        status = FAIL
        gating_reason = "non-critical dimension failed"
    elif errors and not has_verdicts:
        status = ERROR
        gating_reason = f"all evaluators errored: {errors}"
    elif not has_verdicts:
        status = SKIP
        gating_reason = "no evaluable dimensions (all skipped)"
    elif weighted_score is not None and weighted_score < threshold:
        status = FAIL
        gating_reason = f"weighted score {weighted_score:.3f} < threshold {threshold}"
    else:
        status = PASS
        gating_reason = ""

    return {
        "case_id": case.id,
        "case_version": case.version,
        "case_digest": case.digest(),
        "tags": case.tags,
        "status": status,
        "gating_reason": gating_reason,
        "weighted_score": weighted_score,
        "pass_threshold": threshold,
        "critical_failures": critical_failures,
        "skipped_dimensions": skips,
        "errored_dimensions": errors,
        "disagreements": disagreements,
        "checks": [c.to_dict() for c in checks],
    }


def summarize_run(case_results: list[dict]) -> dict:
    statuses = [r["status"] for r in case_results]
    all_checks = [
        CheckResult.from_dict(c) for r in case_results for c in r["checks"]
    ]
    dimension_stats: dict[str, dict] = {}
    for check in all_checks:
        stats = dimension_stats.setdefault(
            check.dimension, {"pass": 0, "fail": 0, "skip": 0, "error": 0}
        )
        stats[check.status] += 1
    scored = [r["weighted_score"] for r in case_results if r["weighted_score"] is not None]
    finished = statuses.count(PASS) + statuses.count(FAIL)
    return {
        "total_cases": len(case_results),
        "pass": statuses.count(PASS),
        "fail": statuses.count(FAIL),
        "skip": statuses.count(SKIP),
        "error": statuses.count(ERROR),
        "pass_rate": (statuses.count(PASS) / finished) if finished else None,
        "avg_weighted_score": (sum(scored) / len(scored)) if scored else None,
        "critical_failure_cases": [r["case_id"] for r in case_results if r["critical_failures"]],
        "expectation_disagreements": [
            r["case_id"] for r in case_results
            if any(d["kind"] == "expectation_disagreement" for d in r["disagreements"])
        ],
        "dimension_stats": dimension_stats,
        "permission_coverage": permission_coverage(all_checks),
    }


def baseline_diff(current: list[dict], baseline: list[dict]) -> dict:
    """Per-case regression comparison against a baseline run."""
    base_by_id = {r["case_id"]: r for r in baseline}
    regressed, improved, new_critical, incompatible = [], [], [], []
    for result in current:
        base = base_by_id.get(result["case_id"])
        if base is None:
            continue
        if base.get("case_digest") != result.get("case_digest"):
            incompatible.append(result["case_id"])
            continue
        if base["status"] == PASS and result["status"] == FAIL:
            regressed.append(result["case_id"])
        if base["status"] == FAIL and result["status"] == PASS:
            improved.append(result["case_id"])
        new_crit = set(result["critical_failures"]) - set(base.get("critical_failures", []))
        if new_crit:
            new_critical.append({"case_id": result["case_id"], "dimensions": sorted(new_crit)})
    return {
        "baseline_cases": len(baseline),
        "compared_cases": len([r for r in current if r["case_id"] in base_by_id]),
        "regressed": regressed,
        "improved": improved,
        "new_critical": new_critical,
        "incompatible_version": incompatible,
    }
