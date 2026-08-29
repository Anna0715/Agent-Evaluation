"""Metamorphic testing: derive cases that alter one controlled input
dimension and assert which dimensions may (and must not) change.
"""

from __future__ import annotations

import copy

from weekly_report_quality.contracts import CaseSpec, CheckResult, parse_case

ALL_DIMENSIONS = (
    "route",
    "faq_retrieval",
    "skill",
    "mcp",
    "output_contract",
    "grounding",
    "cross_period",
    "style_semantics",
    "cross_recipient_consistency",
)


def _derive(case: CaseSpec, suffix: str, may_change: list[str]) -> tuple[dict, dict]:
    raw = copy.deepcopy(case.raw)
    raw["id"] = f"{case.id}-{suffix}"
    tags = set(raw.get("tags", []))
    tags.add("metamorphic")
    raw["tags"] = sorted(tags)
    contract = {
        "base_case_id": case.id,
        "mutation": suffix,
        "may_change": may_change,
        "must_not_change": [d for d in ALL_DIMENSIONS if d not in may_change],
    }
    return raw, contract


def drop_previous(case: CaseSpec) -> tuple[dict, dict]:
    """Remove previous-period content; only cross-period conclusions may change."""
    raw, contract = _derive(case, "drop-previous", ["cross_period", "grounding"])
    raw["input"]["material"]["previous"] = None
    output = raw.setdefault("expect", {}).setdefault("output", {})
    must_not = set(output.get("must_not_contain", []))
    must_not.update({"相比上周", "较上期", "上期对比"})
    output["must_not_contain"] = sorted(must_not)
    return raw, contract


def inject_irrelevant_faq(case: CaseSpec, doc_id: str = "faq-irrelevant-noise") -> tuple[dict, dict]:
    """Add an irrelevant FAQ candidate; recall and grounded answer must hold."""
    raw, contract = _derive(case, "inject-faq", [])
    faq = raw.setdefault("expect", {}).setdefault("faq", {})
    must_not = set(faq.get("must_not_hit", []))
    must_not.add(doc_id)
    faq["must_not_hit"] = sorted(must_not)
    faq.setdefault("top_k", 5)
    return raw, contract


def change_recipient_role(case: CaseSpec, role: str = "cross_team_lead") -> tuple[dict, dict]:
    """Change recipient role; only style/recipient dimensions may change."""
    raw, contract = _derive(
        case, "recipient-role", ["style_semantics", "cross_recipient_consistency"]
    )
    raw["input"].setdefault("recipient", {})["role"] = role
    return raw, contract


_PARAPHRASE_RULES = (
    ("本周", "这一周"),
    ("上周", "上一周"),
    ("完成", "已完成"),
    ("风险：", "存在风险："),
    ("；", "。"),
)


def paraphrase_current(case: CaseSpec) -> tuple[dict, dict]:
    """Meaning-preserving rewrite of current material; no grounded conclusion
    may change (style wording may)."""
    raw, contract = _derive(case, "paraphrase", ["style_semantics"])
    current = raw["input"]["material"]["current"]
    for old, new in _PARAPHRASE_RULES:
        current = current.replace(old, new)
    raw["input"]["material"]["current"] = current
    return raw, contract


def swap_unrelated_segments(case: CaseSpec) -> tuple[dict, dict]:
    """Reverse paragraph order of current material; nothing may change."""
    raw, contract = _derive(case, "swap-segments", [])
    current = raw["input"]["material"]["current"]
    paragraphs = [p for p in current.split("\n") if p.strip()]
    raw["input"]["material"]["current"] = "\n".join(reversed(paragraphs))
    return raw, contract


MUTATIONS = {
    "drop_previous": drop_previous,
    "inject_irrelevant_faq": inject_irrelevant_faq,
    "change_recipient_role": change_recipient_role,
    "paraphrase_current": paraphrase_current,
    "swap_unrelated_segments": swap_unrelated_segments,
}


def derive_case(case: CaseSpec, mutation: str) -> tuple[CaseSpec, dict]:
    if mutation not in MUTATIONS:
        raise ValueError(f"unknown mutation '{mutation}', supported: {sorted(MUTATIONS)}")
    raw, contract = MUTATIONS[mutation](case)
    return parse_case(raw, f"derived:{raw['id']}"), contract


def compare_metamorphic(
    base_checks: list[CheckResult],
    derived_checks: list[CheckResult],
    contract: dict,
) -> list[str]:
    """Return violations: dimensions that changed status but were not allowed to."""
    must_not_change = set(contract.get("must_not_change", []))
    base_map = {c.dimension: c.status for c in base_checks}
    derived_map = {c.dimension: c.status for c in derived_checks}
    violations = []
    for dimension in sorted(set(base_map) & set(derived_map)):
        root = dimension.split(".", 1)[0]
        if root not in must_not_change:
            continue
        if base_map[dimension] != derived_map[dimension]:
            violations.append(
                f"{dimension}: {base_map[dimension]} -> {derived_map[dimension]} "
                f"(mutation '{contract.get('mutation')}' must not affect it)"
            )
    return violations
