"""Case lint: reject internally inconsistent or unobservable expectations
before any Agent execution or evaluation happens.
"""

from __future__ import annotations

from dataclasses import dataclass

from weekly_report_quality.contracts import CaseSpec


@dataclass
class LintIssue:
    case_id: str
    field: str
    message: str

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "field": self.field, "message": self.message}


def _overlap(a: list, b: list) -> list:
    return sorted(set(map(str, a)) & set(map(str, b)))


def lint_case(case: CaseSpec) -> list[LintIssue]:
    issues: list[LintIssue] = []

    def add(field: str, message: str) -> None:
        issues.append(LintIssue(case.id, field, message))

    expect = case.expect

    route = expect.get("route") or {}
    conflict = _overlap(route.get("allowed", []), route.get("forbidden", []))
    if conflict:
        add("expect.route", f"routes both allowed and forbidden: {conflict}")

    faq = expect.get("faq") or {}
    conflict = _overlap(faq.get("must_hit", []), faq.get("must_not_hit", []))
    if conflict:
        add("expect.faq", f"FAQ docs both must_hit and must_not_hit: {conflict}")
    top_k = faq.get("top_k")
    if faq and not isinstance(top_k, int):
        add("expect.faq", "faq expectation requires integer top_k")

    mcp = expect.get("mcp") or {}
    required_tools = [c.get("tool") for c in mcp.get("required_calls", [])]
    conflict = _overlap(required_tools, mcp.get("forbidden_tools", []))
    if conflict:
        add("expect.mcp", f"MCP tools both required and forbidden: {conflict}")

    skill = expect.get("skill") or {}
    skill_tools = skill.get("required_tools", [])
    conflict = _overlap(skill_tools, mcp.get("forbidden_tools", []))
    if conflict:
        add("expect.skill", f"skill required_tools forbidden by expect.mcp: {conflict}")

    output = expect.get("output") or {}
    conflict = _overlap(output.get("must_contain", []), output.get("must_not_contain", []))
    if conflict:
        add("expect.output", f"terms both must_contain and must_not_contain: {conflict}")

    permission = expect.get("permission") or {}
    if permission.get("expect_refusal") and not permission.get("refusal_markers"):
        add("expect.permission", "expect_refusal requires non-empty refusal_markers")

    context = case.input.get("context") or {}
    if permission and not context.get("tenant_id"):
        add("input.context", "permission expectations require input.context.tenant_id")

    strong_assertions = bool(
        output.get("must_contain") or faq.get("must_hit") or mcp.get("required_calls")
    )
    oracle = case.oracle or {}
    if strong_assertions and not oracle.get("source"):
        add("oracle", "strong must-assertions require oracle.source evidence")
    confidence = oracle.get("confidence")
    if confidence is not None and not (0.0 <= float(confidence) <= 1.0):
        add("oracle.confidence", "must be within [0, 1]")

    return issues


def lint_cases(cases: list[CaseSpec]) -> list[LintIssue]:
    issues: list[LintIssue] = []
    seen: dict[str, int] = {}
    for case in cases:
        seen[case.id] = seen.get(case.id, 0) + 1
        issues.extend(lint_case(case))
    for case_id, count in seen.items():
        if count > 1:
            issues.append(LintIssue(case_id, "id", f"duplicate case id ({count} occurrences)"))
    return issues
