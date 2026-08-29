"""Deterministic evaluators: route, faq_retrieval, skill, mcp, output_contract.

Every evaluator takes (CaseSpec, RunEvidence) and returns CheckResults.
Missing expectations mean the dimension does not apply (no result);
missing evidence yields skip(missing_evidence), never an inferred verdict.
"""

from __future__ import annotations

import json
import math

from weekly_report_quality.contracts import (
    ERROR,
    FAIL,
    MISSING_EVIDENCE,
    PASS,
    SEVERITY_CRITICAL,
    SEVERITY_MAJOR,
    SKIP,
    CaseSpec,
    CheckResult,
    RunEvidence,
)


def _skip(evaluator: str, dimension: str, detail: str = "") -> CheckResult:
    return CheckResult(
        evaluator=evaluator,
        dimension=dimension,
        status=SKIP,
        reason=MISSING_EVIDENCE,
        evidence=[detail] if detail else [],
    )


def evaluate_route(case: CaseSpec, evidence: RunEvidence) -> list[CheckResult]:
    exp = case.expect.get("route")
    if not exp:
        return []
    if evidence.route is None:
        return [_skip("route", "route", "evidence.route absent")]
    name = str(evidence.route.get("name", ""))
    confidence = evidence.route.get("confidence")
    failures: list[str] = []
    allowed = [str(r) for r in exp.get("allowed", [])]
    if allowed and name not in allowed:
        failures.append(f"route '{name}' not in allowed {allowed}")
    forbidden = [str(r) for r in exp.get("forbidden", [])]
    if name in forbidden:
        failures.append(f"route '{name}' is forbidden")
    min_confidence = exp.get("min_confidence")
    if min_confidence is not None:
        if confidence is None:
            failures.append("route confidence missing while min_confidence is set")
        elif float(confidence) < float(min_confidence):
            failures.append(f"confidence {confidence} < min {min_confidence}")
    status = FAIL if failures else PASS
    return [
        CheckResult(
            evaluator="route",
            dimension="route",
            status=status,
            score=0.0 if failures else 1.0,
            severity=SEVERITY_CRITICAL if name in forbidden else SEVERITY_MAJOR,
            reason="; ".join(failures),
            evidence=[f"observed route={name!r} confidence={confidence!r}"],
        )
    ]


def _ranking_metrics(ranked_ids: list[str], must_hit: list[str], top_k: int) -> dict:
    top = ranked_ids[:top_k]
    hits = [doc for doc in must_hit if doc in top]
    recall = len(hits) / len(must_hit) if must_hit else None
    mrr = 0.0
    for doc in must_hit:
        if doc in top:
            mrr = max(mrr, 1.0 / (top.index(doc) + 1))
    dcg = sum(1.0 / math.log2(idx + 2) for idx, doc in enumerate(top) if doc in must_hit)
    ideal = sum(1.0 / math.log2(idx + 2) for idx in range(min(len(must_hit), top_k)))
    ndcg = (dcg / ideal) if ideal else None
    return {"recall_at_k": recall, "mrr": mrr if must_hit else None, "ndcg": ndcg}


def evaluate_faq(case: CaseSpec, evidence: RunEvidence) -> list[CheckResult]:
    exp = case.expect.get("faq")
    if not exp:
        return []
    if evidence.faq_candidates is None:
        return [_skip("faq_retrieval", "faq_retrieval", "evidence.faq_candidates absent")]
    candidates = evidence.faq_candidates
    ranked_ids = [str(c.get("doc_id")) for c in candidates]
    top_k = int(exp.get("top_k", len(ranked_ids) or 1))
    must_hit = [str(d) for d in exp.get("must_hit", [])]
    must_not = [str(d) for d in exp.get("must_not_hit", [])]
    metrics = _ranking_metrics(ranked_ids, must_hit, top_k)

    failures: list[str] = []
    for name, minimum in (
        ("recall_at_k", exp.get("min_recall_at_k")),
        ("mrr", exp.get("min_mrr")),
        ("ndcg", exp.get("min_ndcg")),
    ):
        if minimum is not None and metrics[name] is not None and metrics[name] < float(minimum):
            failures.append(f"{name}={metrics[name]:.3f} < min {minimum}")
    banned_hits = [doc for doc in must_not if doc in ranked_ids[:top_k]]
    if banned_hits:
        failures.append(f"must_not_hit docs retrieved: {banned_hits}")

    results = [
        CheckResult(
            evaluator="faq_retrieval",
            dimension="faq_retrieval",
            status=FAIL if failures else PASS,
            score=0.0 if failures else (metrics["recall_at_k"] if metrics["recall_at_k"] is not None else 1.0),
            reason="; ".join(failures),
            evidence=[f"metrics={metrics}", f"top_{top_k}={ranked_ids[:top_k]}"],
        )
    ]

    tenant = case.tenant_id
    visible_ids = case.input.get("context", {}).get("visible_report_ids")
    acl_violations = []
    for cand in candidates:
        if cand.get("visible") is False:
            acl_violations.append(f"invisible candidate {cand.get('doc_id')}")
        if tenant and cand.get("tenant_id") and str(cand["tenant_id"]) != tenant:
            acl_violations.append(f"cross-tenant candidate {cand.get('doc_id')}")
        if visible_ids is not None and str(cand.get("doc_id")) not in [str(v) for v in visible_ids]:
            acl_violations.append(f"candidate {cand.get('doc_id')} outside visible_report_ids")
    results.append(
        CheckResult(
            evaluator="faq_retrieval",
            dimension="faq_retrieval.permission_filter",
            status=FAIL if acl_violations else PASS,
            score=None,
            severity=SEVERITY_CRITICAL,
            reason="; ".join(sorted(set(acl_violations))),
        )
    )
    return results


def evaluate_skill(case: CaseSpec, evidence: RunEvidence) -> list[CheckResult]:
    exp = case.expect.get("skill")
    if not exp:
        return []
    if evidence.skill is None:
        return [_skip("skill", "skill", "evidence.skill absent")]
    skill = evidence.skill
    failures: list[str] = []
    for field in ("key", "version", "channel", "digest"):
        expected = exp.get(field)
        if expected is not None and str(skill.get(field)) != str(expected):
            failures.append(f"skill.{field}={skill.get(field)!r} expected {expected!r}")
    required_tools = [str(t) for t in exp.get("required_tools", [])]
    available = [str(t) for t in (skill.get("tools") or [])]
    missing = [t for t in required_tools if t not in available]
    if missing:
        failures.append(f"required tools missing from skill snapshot: {missing}")
    return [
        CheckResult(
            evaluator="skill",
            dimension="skill",
            status=FAIL if failures else PASS,
            score=0.0 if failures else 1.0,
            reason="; ".join(failures),
            evidence=[f"observed skill={ {k: skill.get(k) for k in ('key', 'version', 'channel')} }"],
        )
    ]


def _args_subset(expected: dict, actual: dict) -> bool:
    for key, value in expected.items():
        if key not in actual:
            return False
        if isinstance(value, dict) and isinstance(actual[key], dict):
            if not _args_subset(value, actual[key]):
                return False
        elif actual[key] != value:
            return False
    return True


def evaluate_mcp(case: CaseSpec, evidence: RunEvidence) -> list[CheckResult]:
    exp = case.expect.get("mcp")
    if not exp:
        return []
    if evidence.mcp_calls is None:
        return [_skip("mcp", "mcp", "evidence.mcp_calls absent")]
    calls = evidence.mcp_calls
    call_tools = [str(c.get("tool")) for c in calls]
    failures: list[str] = []
    critical = False

    forbidden = [str(t) for t in exp.get("forbidden_tools", [])]
    forbidden_used = [t for t in call_tools if t in forbidden]
    if forbidden_used:
        failures.append(f"forbidden MCP tools invoked: {sorted(set(forbidden_used))}")
        critical = True

    for spec in exp.get("required_calls", []):
        tool = str(spec.get("tool"))
        matching = [
            c for c in calls
            if str(c.get("tool")) == tool and _args_subset(spec.get("args_subset", {}), c.get("args", {}))
        ]
        count = len(matching)
        min_count = int(spec.get("min_count", 1))
        max_count = spec.get("max_count")
        if count < min_count:
            failures.append(f"tool {tool!r} matched {count} calls, expected >= {min_count}")
        if max_count is not None and count > int(max_count):
            failures.append(f"tool {tool!r} matched {count} calls, expected <= {max_count}")
        if spec.get("expect_fallback_on_error"):
            errored = [c for c in matching if c.get("status") == "error"]
            if errored and count == len(errored):
                failures.append(f"tool {tool!r} failed with no successful fallback call")

    order = [str(t) for t in exp.get("order", [])]
    if order:
        positions = []
        cursor = 0
        for tool in order:
            found = next((i for i in range(cursor, len(call_tools)) if call_tools[i] == tool), None)
            if found is None:
                failures.append(f"expected call order {order} not satisfied (missing {tool!r})")
                break
            positions.append(found)
            cursor = found + 1

    return [
        CheckResult(
            evaluator="mcp",
            dimension="mcp",
            status=FAIL if failures else PASS,
            score=0.0 if failures else 1.0,
            severity=SEVERITY_CRITICAL if critical else SEVERITY_MAJOR,
            reason="; ".join(failures),
            evidence=[f"observed calls={call_tools}"],
        )
    ]


def evaluate_output_contract(case: CaseSpec, evidence: RunEvidence) -> list[CheckResult]:
    exp = case.expect.get("output")
    if not exp:
        return []
    text = evidence.output_text
    failures: list[str] = []
    critical = False

    schema = exp.get("schema")
    if schema:
        payload = evidence.output.get("json")
        if payload is None:
            try:
                payload = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                payload = None
        if not isinstance(payload, dict):
            failures.append("output is not parseable as the expected JSON object")
            critical = True
        else:
            for field in schema.get("required", []):
                if field not in payload:
                    failures.append(f"required field '{field}' missing from output JSON")
            for field, values in (schema.get("enums") or {}).items():
                if field in payload and payload[field] not in values:
                    failures.append(f"field '{field}'={payload[field]!r} not in enum {values}")

    for term in exp.get("must_contain", []):
        if str(term) not in text:
            failures.append(f"output missing required text {term!r}")
    for term in exp.get("must_not_contain", []):
        if str(term) in text:
            failures.append(f"output contains prohibited text {term!r}")
    max_length = exp.get("max_length")
    if max_length is not None and len(text) > int(max_length):
        failures.append(f"output length {len(text)} > max {max_length}")

    return [
        CheckResult(
            evaluator="output_contract",
            dimension="output_contract",
            status=FAIL if failures else PASS,
            score=0.0 if failures else 1.0,
            severity=SEVERITY_CRITICAL if critical else SEVERITY_MAJOR,
            reason="; ".join(failures),
        )
    ]


DETERMINISTIC_EVALUATORS = {
    "route": evaluate_route,
    "faq_retrieval": evaluate_faq,
    "skill": evaluate_skill,
    "mcp": evaluate_mcp,
    "output_contract": evaluate_output_contract,
}


def run_deterministic(
    case: CaseSpec, evidence: RunEvidence, selected: list[str] | None = None
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for name, evaluator in DETERMINISTIC_EVALUATORS.items():
        if selected is not None and name not in selected:
            continue
        try:
            results.extend(evaluator(case, evidence))
        except Exception as exc:  # noqa: BLE001 - evaluator bugs must not kill the run
            results.append(
                CheckResult(
                    evaluator=name,
                    dimension=name,
                    status=ERROR,
                    reason=f"evaluator raised {type(exc).__name__}: {exc}",
                )
            )
    return results
