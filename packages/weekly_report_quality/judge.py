"""Semantic Judge contract and clients.

Verdicts are a stable structured contract: {pass, score, reasons, model,
prompt_digest}. The first-phase offline framework ships a StubJudge that
reads recorded verdicts from evidence fixtures; a live judge can implement
the same interface later without touching evaluators.
"""

from __future__ import annotations

from typing import Protocol

from weekly_report_quality.contracts import ContractError, RunEvidence


class JudgeVerdict(dict):
    """Validated judge verdict; behaves as a plain dict for serialization."""


def parse_verdict(raw: object, where: str) -> JudgeVerdict:
    if not isinstance(raw, dict):
        raise ContractError(where, "judge verdict must be a JSON object")
    if not isinstance(raw.get("pass"), bool):
        raise ContractError(where, "judge verdict requires boolean 'pass'")
    score = raw.get("score")
    if not isinstance(score, (int, float)) or not (0.0 <= float(score) <= 1.0):
        raise ContractError(where, "judge verdict requires numeric 'score' in [0,1]")
    reasons = raw.get("reasons", [])
    if not isinstance(reasons, list):
        raise ContractError(where, "'reasons' must be a list")
    verdict = JudgeVerdict(raw)
    verdict["reasons"] = [str(r) for r in reasons]
    verdict.setdefault("model", "unknown")
    verdict.setdefault("prompt_digest", "")
    return verdict


class Judge(Protocol):
    def verdict(self, dimension: str, role: str = "primary") -> JudgeVerdict | None:
        """Return a verdict for a dimension, or None when unavailable.

        role: "primary" | "second" | "critic"
        """


class StubJudge:
    """Reads recorded verdicts from evidence.judge_responses.

    Key layout inside judge_responses:
      "<dimension>"          primary verdict
      "<dimension>_second"   independent second verdict (recheck)
      "critic"               expectation critic: {"supported": bool, "reasons": [...]}
    """

    def __init__(self, evidence: RunEvidence) -> None:
        self._responses = evidence.judge_responses or {}
        self._case_id = evidence.case_id

    def verdict(self, dimension: str, role: str = "primary") -> JudgeVerdict | None:
        key = dimension if role == "primary" else f"{dimension}_second"
        raw = self._responses.get(key)
        if raw is None:
            return None
        return parse_verdict(raw, f"{self._case_id}.judge_responses.{key}")

    def critic(self) -> dict | None:
        raw = self._responses.get("critic")
        if raw is None:
            return None
        if not isinstance(raw, dict) or not isinstance(raw.get("supported"), bool):
            raise ContractError(
                f"{self._case_id}.judge_responses.critic",
                "critic requires boolean 'supported'",
            )
        return raw
