import unittest

import helpers
from helpers import make_case, make_evidence

from weekly_report_quality.aggregate import aggregate_case, baseline_diff, summarize_run
from weekly_report_quality.contracts import CheckResult
from weekly_report_quality.semantic import evaluate_semantic


def _verdict(passed=True, score=0.9, reasons=None):
    return {
        "pass": passed,
        "score": score,
        "reasons": reasons or [],
        "model": "stub",
        "prompt_digest": "d",
    }


class SemanticTests(unittest.TestCase):
    def test_missing_verdict_skips(self):
        case = make_case(expect={"grounding": {"required": True}})
        results = evaluate_semantic(case, make_evidence())
        grounding = next(r for r in results if r.dimension == "grounding")
        self.assertEqual(grounding.status, "skip")
        self.assertEqual(grounding.reason, "missing_evidence")

    def test_pass_and_fail_verdicts(self):
        case = make_case(expect={"grounding": {"required": True}})
        passing = make_evidence(
            judge_responses={"grounding": _verdict(True, 0.9), "critic": {"supported": True}}
        )
        result = next(r for r in evaluate_semantic(case, passing) if r.dimension == "grounding")
        self.assertEqual(result.status, "pass")
        failing = make_evidence(
            judge_responses={
                "grounding": _verdict(False, 0.3, ["fabricated numbers"]),
                "critic": {"supported": True},
            }
        )
        result = next(r for r in evaluate_semantic(case, failing) if r.dimension == "grounding")
        self.assertEqual(result.status, "fail")
        self.assertIn("fabricated", result.reason)

    def test_unsupported_expectation_flags_disagreement_not_failure(self):
        case = make_case(expect={"grounding": {"required": True}})
        evidence = make_evidence(
            judge_responses={
                "grounding": _verdict(False, 0.2),
                "critic": {"supported": False, "reasons": ["expectation not derivable from input"]},
            }
        )
        results = evaluate_semantic(case, evidence)
        critic = next(r for r in results if r.evaluator == "expectation_critic")
        self.assertEqual(critic.reason, "expectation_disagreement")
        grounding = next(r for r in results if r.dimension == "grounding")
        self.assertEqual(grounding.status, "skip")

    def test_invalid_verdict_contract_is_error(self):
        case = make_case(expect={"grounding": {"required": True}})
        evidence = make_evidence(judge_responses={"grounding": {"pass": "yes"}})
        grounding = next(r for r in evaluate_semantic(case, evidence) if r.dimension == "grounding")
        self.assertEqual(grounding.status, "error")


class AggregateTests(unittest.TestCase):
    def test_critical_failure_overrides_high_score(self):
        case = make_case()
        checks = [
            CheckResult("grounding", "grounding", "pass", score=1.0),
            CheckResult(
                "permission_boundary",
                "permission_boundary.tenant_isolation",
                "fail",
                severity="critical",
                reason="leak",
            ),
        ]
        result = aggregate_case(case, checks)
        self.assertEqual(result["status"], "fail")
        self.assertIn("critical", result["gating_reason"])
        self.assertTrue(result["disagreements"])

    def test_permission_only_pass_is_pass(self):
        case = make_case()
        checks = [
            CheckResult("permission_boundary", "permission_boundary.tenant_isolation", "pass",
                        severity="critical"),
            CheckResult("permission_boundary", "permission_boundary.prompt_injection", "skip",
                        severity="critical", reason="missing_evidence"),
        ]
        result = aggregate_case(case, checks)
        self.assertEqual(result["status"], "pass")

    def test_all_skips_stay_skip(self):
        case = make_case()
        checks = [CheckResult("route", "route", "skip", reason="missing_evidence")]
        result = aggregate_case(case, checks)
        self.assertEqual(result["status"], "skip")

    def test_low_weighted_score_fails(self):
        case = make_case()
        checks = [
            CheckResult("grounding", "grounding", "pass", score=0.5),
        ]
        result = aggregate_case(case, checks)
        self.assertEqual(result["status"], "fail")
        self.assertIn("threshold", result["gating_reason"])

    def test_summary_separates_skips(self):
        case = make_case()
        results = [
            aggregate_case(case, [CheckResult("route", "route", "skip", reason="missing_evidence")]),
            aggregate_case(case, [CheckResult("route", "route", "pass", score=1.0)]),
        ]
        summary = summarize_run(results)
        self.assertEqual(summary["skip"], 1)
        self.assertEqual(summary["pass"], 1)
        self.assertEqual(summary["pass_rate"], 1.0)

    def test_baseline_diff_detects_regression_and_version_change(self):
        current = [
            {"case_id": "A", "case_digest": "d1", "status": "fail", "critical_failures": ["mcp"]},
            {"case_id": "B", "case_digest": "d2-new", "status": "pass", "critical_failures": []},
        ]
        baseline = [
            {"case_id": "A", "case_digest": "d1", "status": "pass", "critical_failures": []},
            {"case_id": "B", "case_digest": "d2-old", "status": "pass", "critical_failures": []},
        ]
        diff = baseline_diff(current, baseline)
        self.assertEqual(diff["regressed"], ["A"])
        self.assertEqual(diff["new_critical"][0]["case_id"], "A")
        self.assertEqual(diff["incompatible_version"], ["B"])


if __name__ == "__main__":
    unittest.main()
