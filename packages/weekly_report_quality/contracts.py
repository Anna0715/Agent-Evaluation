"""Versioned data contracts: CaseSpec, RunEvidence, CheckResult.

Contract versions are embedded in every artifact so offline replay can
detect incompatible inputs instead of silently mis-evaluating them.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CASE_CONTRACT = "weekly_report_quality.case.v1"
EVIDENCE_CONTRACT = "weekly_report_quality.evidence.v1"
RESULT_CONTRACT = "weekly_report_quality.result.v1"

PASS = "pass"
FAIL = "fail"
SKIP = "skip"
ERROR = "error"
STATUSES = (PASS, FAIL, SKIP, ERROR)

SEVERITY_INFO = "info"
SEVERITY_MAJOR = "major"
SEVERITY_CRITICAL = "critical"

MISSING_EVIDENCE = "missing_evidence"


class ContractError(ValueError):
    """Raised when an artifact violates its declared contract."""

    def __init__(self, path: str, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message


def json_dumps(value: Any, *, indent: int | None = 2) -> str:
    return json.dumps(value, ensure_ascii=False, indent=indent, sort_keys=False)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_dumps(value) + "\n", encoding="utf-8")


def canonical_digest(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _require(obj: dict, key: str, kind: type | tuple, where: str) -> Any:
    if key not in obj:
        raise ContractError(where, f"missing required field '{key}'")
    value = obj[key]
    if not isinstance(value, kind):
        raise ContractError(where, f"field '{key}' must be {kind}, got {type(value).__name__}")
    return value


def _optional(obj: dict, key: str, kind: type | tuple, where: str, default: Any = None) -> Any:
    if key not in obj or obj[key] is None:
        return default
    value = obj[key]
    if not isinstance(value, kind):
        raise ContractError(where, f"field '{key}' must be {kind}, got {type(value).__name__}")
    return value


@dataclass
class CheckResult:
    evaluator: str
    dimension: str
    status: str
    score: float | None = None
    severity: str = SEVERITY_MAJOR
    reason: str = ""
    evidence: list[str] = field(default_factory=list)
    suggestion: str = ""

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ContractError(self.dimension, f"invalid status '{self.status}'")

    def to_dict(self) -> dict:
        return {
            "evaluator": self.evaluator,
            "dimension": self.dimension,
            "status": self.status,
            "score": self.score,
            "severity": self.severity,
            "reason": self.reason,
            "evidence": list(self.evidence),
            "suggestion": self.suggestion,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CheckResult":
        return cls(
            evaluator=data["evaluator"],
            dimension=data["dimension"],
            status=data["status"],
            score=data.get("score"),
            severity=data.get("severity", SEVERITY_MAJOR),
            reason=data.get("reason", ""),
            evidence=list(data.get("evidence", [])),
            suggestion=data.get("suggestion", ""),
        )


@dataclass
class CaseSpec:
    id: str
    version: int
    tags: list[str]
    input: dict
    expect: dict
    oracle: dict
    scoring: dict
    source: dict
    raw: dict

    @property
    def tenant_id(self) -> str:
        return str(self.input.get("context", {}).get("tenant_id", ""))

    @property
    def user_id(self) -> str:
        return str(self.input.get("context", {}).get("user_id", ""))

    def digest(self) -> str:
        return canonical_digest(self.raw)


def parse_case(data: dict, where: str) -> CaseSpec:
    contract = _require(data, "contract", str, where)
    if contract != CASE_CONTRACT:
        raise ContractError(where, f"unsupported case contract '{contract}'")
    case_id = _require(data, "id", str, where)
    version = _require(data, "version", int, where)
    tags = _optional(data, "tags", list, where, default=[])
    input_ = _require(data, "input", dict, where)
    material = _require(input_, "material", dict, f"{where}.input")
    _require(material, "current", str, f"{where}.input.material")
    expect = _optional(data, "expect", dict, where, default={})
    oracle = _optional(data, "oracle", dict, where, default={})
    scoring = _optional(data, "scoring", dict, where, default={})
    source = _optional(data, "source", dict, where, default={})
    return CaseSpec(
        id=case_id,
        version=version,
        tags=[str(t) for t in tags],
        input=input_,
        expect=expect,
        oracle=oracle,
        scoring=scoring,
        source=source,
        raw=data,
    )


def load_case(path: Path) -> CaseSpec:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(str(path), f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError(str(path), "case file must contain a JSON object")
    return parse_case(data, str(path))


def load_cases(directory: Path) -> list[CaseSpec]:
    cases = [load_case(p) for p in sorted(directory.glob("*.json"))]
    if not cases:
        raise ContractError(str(directory), "no case files (*.json) found")
    return cases


@dataclass
class RunEvidence:
    case_id: str
    generated_at: str
    output: dict
    route: dict | None
    faq_candidates: list[dict] | None
    skill: dict | None
    mcp_calls: list[dict] | None
    memory_events: list[dict] | None
    model: dict
    judge_responses: dict
    errors: list[dict]
    raw: dict

    @property
    def output_text(self) -> str:
        return str(self.output.get("text", ""))

    def digest(self) -> str:
        return canonical_digest(self.raw)


def parse_evidence(data: dict, where: str) -> RunEvidence:
    contract = _require(data, "contract", str, where)
    if contract != EVIDENCE_CONTRACT:
        raise ContractError(where, f"unsupported evidence contract '{contract}'")
    case_id = _require(data, "case_id", str, where)
    output = _require(data, "output", dict, where)
    _require(output, "text", str, f"{where}.output")
    return RunEvidence(
        case_id=case_id,
        generated_at=_optional(data, "generated_at", str, where, default=""),
        output=output,
        route=_optional(data, "route", dict, where),
        faq_candidates=_optional(data, "faq_candidates", list, where),
        skill=_optional(data, "skill", dict, where),
        mcp_calls=_optional(data, "mcp_calls", list, where),
        memory_events=_optional(data, "memory_events", list, where),
        model=_optional(data, "model", dict, where, default={}),
        judge_responses=_optional(data, "judge_responses", dict, where, default={}),
        errors=_optional(data, "errors", list, where, default=[]),
        raw=data,
    )


def load_evidence(path: Path) -> RunEvidence:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(str(path), f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError(str(path), "evidence file must contain a JSON object")
    return parse_evidence(data, str(path))


def load_evidence_for_case(directory: Path, case_id: str) -> RunEvidence | None:
    path = directory / f"{case_id}.json"
    if not path.exists():
        return None
    return load_evidence(path)
