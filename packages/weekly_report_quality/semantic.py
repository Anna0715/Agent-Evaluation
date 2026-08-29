"""Judge-backed semantic evaluators: grounding, cross_period,
style_semantics, cross_recipient_consistency.

Also runs the expectation critic: when the critic says a strong expectation
cannot be derived from the inputs, the case is flagged as an expectation
disagreement for human review instead of penalizing the candidate.
"""

from __future__ import annotations

from weekly_report_quality.contracts import (
    ERROR,
    FAIL,
    MISSING_EVIDENCE,
    PASS,
    SEVERITY_MAJOR,
    SKIP,
    CaseSpec,
    CheckResult,
    ContractError,
    RunEvidence,
)
from weekly_report_quality.judge import StubJudge

SEMANTIC_DIMENSIONS = (
    "grounding",
    "cross_period",
    "style_semantics",
    "cross_recipient_consistency",
)

EXPECTATION_DISAGREEMENT = "expectation_disagreement"


def semantic_dimensions_for(case: CaseSpec) -> list[str]:
    return [dim for dim in SEMANTIC_DIMENSIONS if case.expect.get(dim)]


def evaluate_semantic(
    case: CaseSpec, evidence: RunEvidence, min_pass_score: float = 0.6
) -> list[CheckResult]:
    dims = semantic_dimensions_for(case)
    if not dims:
        return []
    judge = StubJudge(evidence)
    results: list[CheckResult] = []

    critic_flags: list[str] = []
    try:
        critic = judge.critic()
    except ContractError as exc:
        critic = None
        results.append(
            CheckResult(
                evaluator="expectation_critic",
                dimension="expectation_critic",
                status=ERROR,
                reason=str(exc),
            )
        )
    if critic is not None and not critic.get("supported", True):
        critic_flags = [str(r) for r in critic.get("reasons", [])]
        results.append(
            CheckResult(
                evaluator="expectation_critic",
                dimension="expectation_critic",
                status=SKIP,
                reason=EXPECTATION_DISAGREEMENT,
                evidence=critic_flags,
                suggestion="human review required: expectation may not be derivable from inputs",
            )
        )

    for dim in dims:
        try:
            verdict = judge.verdict(dim)
        except ContractError as exc:
            results.append(
                CheckResult(evaluator=dim, dimension=dim, status=ERROR, reason=str(exc))
            )
            continue
        if verdict is None:
            results.append(
                CheckResult(
                    evaluator=dim,
                    dimension=dim,
                    status=SKIP,
                    reason=MISSING_EVIDENCE,
                    evidence=[f"no judge verdict recorded for '{dim}'"],
                )
            )
            continue
        if critic_flags:
            # Expectation itself is disputed: report, do not penalize.
            results.append(
                CheckResult(
                    evaluator=dim,
                    dimension=dim,
                    status=SKIP,
                    reason=EXPECTATION_DISAGREEMENT,
                    score=float(verdict["score"]),
                    evidence=[f"judge verdict withheld pending expectation review: {critic_flags}"],
                )
            )
            continue
        passed = bool(verdict["pass"]) and float(verdict["score"]) >= min_pass_score
        results.append(
            CheckResult(
                evaluator=dim,
                dimension=dim,
                status=PASS if passed else FAIL,
                score=float(verdict["score"]),
                severity=SEVERITY_MAJOR,
                reason="" if passed else "; ".join(verdict["reasons"]) or "judge verdict failed",
                evidence=[
                    f"judge model={verdict.get('model')}",
                    f"prompt_digest={verdict.get('prompt_digest')}",
                ],
            )
        )
    return results
