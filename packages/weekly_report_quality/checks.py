"""Three result checks that raise confidence in evaluation results.

The goal is confidence, not forced agreement: every check emits a
corroborate / contradict / unavailable signal per case, aggregated into a
high / medium / low confidence level. Low-confidence results still appear
in the report but enter adjudication_required instead of being averaged
or silently resolved.
"""

from __future__ import annotations

from weekly_report_quality.contracts import (
    CaseSpec,
    CheckResult,
    ContractError,
    RunEvidence,
)
from weekly_report_quality.evaluators import run_deterministic
from weekly_report_quality.judge import StubJudge
from weekly_report_quality.permission import evaluate_permission
from weekly_report_quality.semantic import semantic_dimensions_for

CORROBORATE = "corroborate"
CONTRADICT = "contradict"
UNAVAILABLE = "unavailable"

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

DEFAULT_SCORE_DIFF_THRESHOLD = 0.2


def _signal(check: str, outcome: str, detail: str = "") -> dict:
    return {"check": check, "outcome": outcome, "detail": detail}


def replay_check(case: CaseSpec, evidence: RunEvidence, original: list[CheckResult]) -> dict:
    """Re-run all deterministic evaluators from persisted evidence and
    verify the conclusions reproduce."""
    replayed = run_deterministic(case, evidence) + evaluate_permission(case, evidence)
    original_map = {
        c.dimension: c for c in original if c.evaluator not in _SEMANTIC_EVALUATORS
    }
    replay_map = {c.dimension: c for c in replayed}
    if not original_map:
        return _signal("replay_check", UNAVAILABLE, "no deterministic dimensions in this case")
    mismatches = []
    for dimension, first in original_map.items():
        second = replay_map.get(dimension)
        if second is None:
            mismatches.append(f"{dimension}: missing on replay")
        elif (first.status, first.score) != (second.status, second.score):
            mismatches.append(
                f"{dimension}: {first.status}/{first.score} -> {second.status}/{second.score}"
            )
    if mismatches:
        return _signal("replay_check", CONTRADICT, "; ".join(mismatches))
    return _signal("replay_check", CORROBORATE, f"{len(original_map)} dimensions reproduced")


_SEMANTIC_EVALUATORS = (
    "grounding",
    "cross_period",
    "style_semantics",
    "cross_recipient_consistency",
    "expectation_critic",
)


def judge_recheck(
    case: CaseSpec,
    evidence: RunEvidence,
    original: list[CheckResult],
    score_diff_threshold: float = DEFAULT_SCORE_DIFF_THRESHOLD,
) -> dict:
    """Re-judge semantic dimensions with an independent second verdict and
    measure the stability of the semantic conclusions."""
    dims = semantic_dimensions_for(case)
    if not dims:
        return _signal("judge_recheck", UNAVAILABLE, "case has no semantic dimensions")
    judge = StubJudge(evidence)
    original_map = {c.dimension: c for c in original if c.dimension in dims}
    contradictions, compared = [], 0
    for dim in dims:
        first = original_map.get(dim)
        if first is None or first.status not in ("pass", "fail") or first.score is None:
            continue
        try:
            second = judge.verdict(dim, role="second")
        except ContractError as exc:
            contradictions.append(f"{dim}: second verdict invalid ({exc.message})")
            continue
        if second is None:
            continue
        compared += 1
        first_pass = first.status == "pass"
        if bool(second["pass"]) != first_pass:
            contradictions.append(
                f"{dim}: primary={'pass' if first_pass else 'fail'} second={'pass' if second['pass'] else 'fail'}"
            )
        elif abs(float(second["score"]) - float(first.score)) > score_diff_threshold:
            contradictions.append(
                f"{dim}: score diff {abs(float(second['score']) - float(first.score)):.3f} "
                f"> {score_diff_threshold}"
            )
    if contradictions:
        return _signal("judge_recheck", CONTRADICT, "; ".join(contradictions))
    if compared == 0:
        return _signal("judge_recheck", UNAVAILABLE, "no second judge verdicts recorded")
    return _signal("judge_recheck", CORROBORATE, f"{compared} semantic dimensions stable")


def baseline_check(case_result: dict, baseline_results: list[dict] | None) -> dict:
    """Compare a case result with the same case in the baseline/previous run."""
    if not baseline_results:
        return _signal("baseline_check", UNAVAILABLE, "no compatible baseline run")
    base = next(
        (r for r in baseline_results if r["case_id"] == case_result["case_id"]), None
    )
    if base is None:
        return _signal("baseline_check", UNAVAILABLE, "case not present in baseline")
    if base.get("case_digest") != case_result.get("case_digest"):
        return _signal("baseline_check", UNAVAILABLE, "case version changed since baseline")
    details = []
    if base["status"] != case_result["status"]:
        details.append(f"status {base['status']} -> {case_result['status']}")
    new_critical = set(case_result["critical_failures"]) - set(base.get("critical_failures", []))
    if new_critical:
        details.append(f"new critical failures: {sorted(new_critical)}")
    if details:
        return _signal("baseline_check", CONTRADICT, "; ".join(details))
    return _signal("baseline_check", CORROBORATE, "consistent with baseline")


def confidence_from_signals(signals: list[dict]) -> tuple[str, bool]:
    """Aggregate check signals into (confidence_level, adjudication_required).

    All corroborate -> high; any contradict -> low + adjudication;
    otherwise (some unavailable, none contradict) -> medium.
    """
    outcomes = {s["outcome"] for s in signals}
    if CONTRADICT in outcomes:
        return CONFIDENCE_LOW, True
    if outcomes == {CORROBORATE}:
        return CONFIDENCE_HIGH, False
    return CONFIDENCE_MEDIUM, False


def verify_case(
    case: CaseSpec,
    evidence: RunEvidence,
    checks: list[CheckResult],
    case_result: dict,
    baseline_results: list[dict] | None,
) -> dict:
    """Run the three checks and attach confidence to the case result."""
    signals = [
        replay_check(case, evidence, checks),
        judge_recheck(case, evidence, checks),
        baseline_check(case_result, baseline_results),
    ]
    level, adjudication = confidence_from_signals(signals)
    case_result["confidence"] = level
    case_result["confidence_signals"] = signals
    case_result["adjudication_required"] = adjudication
    return case_result
