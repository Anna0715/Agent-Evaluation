"""Normalize agent outputs and traces into RunEvidence with redaction.

Sensitive values (JWT, internal keys, bearer tokens) are redacted by
default so evidence artifacts can be committed as offline fixtures.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

from weekly_report_quality.contracts import EVIDENCE_CONTRACT

REDACTED = "[REDACTED]"
_SENSITIVE_KEY_RE = re.compile(
    r"(jwt|token|secret|password|internal[-_]?key|api[-_]?key|authorization)", re.IGNORECASE
)
_SENSITIVE_VALUE_RES = (
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\b"),  # JWT
    re.compile(r"\b(?:sk|rk|ak)-[A-Za-z0-9]{16,}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{8,}\b"),
)


def redact(value: Any) -> Any:
    """Recursively redact sensitive keys and value patterns."""
    if isinstance(value, dict):
        return {
            k: REDACTED if _SENSITIVE_KEY_RE.search(str(k)) else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        result = value
        for pattern in _SENSITIVE_VALUE_RES:
            result = pattern.sub(REDACTED, result)
        return result
    return value


def build_evidence(
    case_id: str,
    output_text: str,
    *,
    output_json: dict | None = None,
    route: dict | None = None,
    faq_candidates: list[dict] | None = None,
    skill: dict | None = None,
    mcp_calls: list[dict] | None = None,
    memory_events: list[dict] | None = None,
    model: dict | None = None,
    judge_responses: dict | None = None,
    errors: list[dict] | None = None,
    generated_at: str | None = None,
) -> dict:
    """Assemble a redacted evidence dict conforming to the evidence contract."""
    evidence = {
        "contract": EVIDENCE_CONTRACT,
        "case_id": case_id,
        "generated_at": generated_at
        or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "output": {"text": output_text, "json": output_json},
        "route": route,
        "faq_candidates": faq_candidates,
        "skill": skill,
        "mcp_calls": mcp_calls,
        "memory_events": memory_events,
        "model": model or {},
        "judge_responses": judge_responses or {},
        "errors": errors or [],
    }
    return redact(evidence)


def from_business_agent_trace(case_id: str, output_text: str, trace: dict) -> dict:
    """Best-effort mapping from a business-agent trace export to evidence.

    Missing sections stay None so evaluators report skip(missing_evidence)
    instead of guessing behavior.
    """
    route = None
    workflow = trace.get("workflow") or trace.get("route")
    if isinstance(workflow, dict):
        route = {
            "name": workflow.get("key") or workflow.get("name"),
            "confidence": workflow.get("confidence"),
        }

    faq_candidates = None
    retrieval = trace.get("faq_candidates") or trace.get("retrieval")
    if isinstance(retrieval, list):
        faq_candidates = [
            {
                "doc_id": item.get("doc_id") or item.get("id"),
                "score": item.get("score"),
                "tenant_id": item.get("tenant_id"),
                "visible": item.get("visible", True),
            }
            for item in retrieval
            if isinstance(item, dict)
        ]

    skill = None
    snapshot = trace.get("skill") or trace.get("skill_snapshot")
    if isinstance(snapshot, dict):
        skill = {
            "key": snapshot.get("key"),
            "version": snapshot.get("version"),
            "channel": snapshot.get("channel"),
            "digest": snapshot.get("digest"),
            "tools": snapshot.get("tools") or snapshot.get("required_tools"),
        }

    mcp_calls = None
    calls = trace.get("mcp_calls") or trace.get("tool_calls")
    if isinstance(calls, list):
        mcp_calls = [
            {
                "tool": call.get("tool") or call.get("name"),
                "args": call.get("args") or call.get("arguments") or {},
                "status": call.get("status", "ok"),
                "seq": call.get("seq", idx + 1),
            }
            for idx, call in enumerate(calls)
            if isinstance(call, dict)
        ]

    memory_events = None
    events = trace.get("memory_events")
    if isinstance(events, list):
        memory_events = [
            {
                "op": event.get("op"),
                "tenant_id": event.get("tenant_id"),
                "user_id": event.get("user_id"),
            }
            for event in events
            if isinstance(event, dict)
        ]

    return build_evidence(
        case_id,
        output_text,
        route=route,
        faq_candidates=faq_candidates,
        skill=skill,
        mcp_calls=mcp_calls,
        memory_events=memory_events,
        model=trace.get("model") if isinstance(trace.get("model"), dict) else None,
        errors=trace.get("errors") if isinstance(trace.get("errors"), list) else None,
    )
