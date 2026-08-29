import unittest

import helpers
from helpers import make_case, make_evidence

from weekly_report_quality.evaluators import (
    evaluate_faq,
    evaluate_mcp,
    evaluate_output_contract,
    evaluate_route,
    evaluate_skill,
)


def _by_dim(results):
    return {r.dimension: r for r in results}


class RouteTests(unittest.TestCase):
    def test_missing_evidence_skips(self):
        case = make_case(expect={"route": {"allowed": ["wf"]}})
        result = evaluate_route(case, make_evidence())[0]
        self.assertEqual(result.status, "skip")
        self.assertEqual(result.reason, "missing_evidence")

    def test_forbidden_route_is_critical_fail(self):
        case = make_case(expect={"route": {"allowed": ["wf"], "forbidden": ["chat"]}})
        evidence = make_evidence(route={"name": "chat", "confidence": 0.9})
        result = evaluate_route(case, evidence)[0]
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.severity, "critical")

    def test_low_confidence_fails(self):
        case = make_case(expect={"route": {"allowed": ["wf"], "min_confidence": 0.8}})
        evidence = make_evidence(route={"name": "wf", "confidence": 0.5})
        self.assertEqual(evaluate_route(case, evidence)[0].status, "fail")


class FaqTests(unittest.TestCase):
    def _case(self, **faq):
        base = {"top_k": 3, "must_hit": ["d1"], "must_not_hit": ["d9"]}
        base.update(faq)
        return make_case(expect={"faq": base})

    def _evidence(self, ids, tenant="tenant-a"):
        return make_evidence(
            faq_candidates=[
                {"doc_id": i, "score": 1.0 - n * 0.1, "tenant_id": tenant, "visible": True}
                for n, i in enumerate(ids)
            ]
        )

    def test_metrics_pass(self):
        result = _by_dim(evaluate_faq(self._case(min_recall_at_k=1.0, min_mrr=1.0), self._evidence(["d1", "d2"])))
        self.assertEqual(result["faq_retrieval"].status, "pass")

    def test_low_recall_fails(self):
        result = _by_dim(evaluate_faq(self._case(min_recall_at_k=1.0), self._evidence(["d2", "d3", "d4"])))
        self.assertEqual(result["faq_retrieval"].status, "fail")

    def test_must_not_hit_fails(self):
        result = _by_dim(evaluate_faq(self._case(), self._evidence(["d1", "d9"])))
        self.assertEqual(result["faq_retrieval"].status, "fail")

    def test_cross_tenant_candidate_fails_permission_filter(self):
        evidence = make_evidence(
            faq_candidates=[
                {"doc_id": "d1", "score": 0.9, "tenant_id": "tenant-b", "visible": True}
            ]
        )
        result = _by_dim(evaluate_faq(self._case(), evidence))
        filter_check = result["faq_retrieval.permission_filter"]
        self.assertEqual(filter_check.status, "fail")
        self.assertEqual(filter_check.severity, "critical")


class SkillTests(unittest.TestCase):
    def test_missing_required_tool_fails(self):
        case = make_case(expect={"skill": {"key": "s", "required_tools": ["t1", "t2"]}})
        evidence = make_evidence(skill={"key": "s", "tools": ["t1"]})
        result = evaluate_skill(case, evidence)[0]
        self.assertEqual(result.status, "fail")
        self.assertIn("t2", result.reason)

    def test_version_drift_fails(self):
        case = make_case(expect={"skill": {"key": "s", "version": "1.0"}})
        evidence = make_evidence(skill={"key": "s", "version": "2.0"})
        self.assertEqual(evaluate_skill(case, evidence)[0].status, "fail")


class McpTests(unittest.TestCase):
    def test_forbidden_tool_is_critical(self):
        case = make_case(expect={"mcp": {"forbidden_tools": ["contact_lookup"]}})
        evidence = make_evidence(
            mcp_calls=[{"tool": "contact_lookup", "args": {}, "status": "ok", "seq": 1}]
        )
        result = evaluate_mcp(case, evidence)[0]
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.severity, "critical")

    def test_args_subset_and_counts(self):
        case = make_case(
            expect={
                "mcp": {
                    "required_calls": [
                        {"tool": "reader", "args_subset": {"id": "r1"}, "min_count": 1, "max_count": 1}
                    ]
                }
            }
        )
        good = make_evidence(
            mcp_calls=[{"tool": "reader", "args": {"id": "r1", "extra": 1}, "status": "ok", "seq": 1}]
        )
        self.assertEqual(evaluate_mcp(case, good)[0].status, "pass")
        wrong_args = make_evidence(
            mcp_calls=[{"tool": "reader", "args": {"id": "r2"}, "status": "ok", "seq": 1}]
        )
        self.assertEqual(evaluate_mcp(case, wrong_args)[0].status, "fail")

    def test_order_subsequence(self):
        case = make_case(expect={"mcp": {"order": ["a", "b"]}})
        ok = make_evidence(
            mcp_calls=[
                {"tool": "a", "args": {}, "status": "ok", "seq": 1},
                {"tool": "x", "args": {}, "status": "ok", "seq": 2},
                {"tool": "b", "args": {}, "status": "ok", "seq": 3},
            ]
        )
        self.assertEqual(evaluate_mcp(case, ok)[0].status, "pass")
        bad = make_evidence(
            mcp_calls=[
                {"tool": "b", "args": {}, "status": "ok", "seq": 1},
                {"tool": "a", "args": {}, "status": "ok", "seq": 2},
            ]
        )
        self.assertEqual(evaluate_mcp(case, bad)[0].status, "fail")


class OutputContractTests(unittest.TestCase):
    def test_unparseable_json_is_critical(self):
        case = make_case(expect={"output": {"schema": {"required": ["summary"]}}})
        evidence = make_evidence(output={"text": "not json", "json": None})
        result = evaluate_output_contract(case, evidence)[0]
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.severity, "critical")

    def test_must_contain_and_enum(self):
        case = make_case(
            expect={
                "output": {
                    "schema": {"required": ["level"], "enums": {"level": ["low", "high"]}},
                    "must_contain": ["风险"],
                }
            }
        )
        evidence = make_evidence(
            output={"text": "本周风险可控", "json": {"level": "mid"}}
        )
        result = evaluate_output_contract(case, evidence)[0]
        self.assertEqual(result.status, "fail")
        self.assertIn("enum", result.reason)


if __name__ == "__main__":
    unittest.main()
