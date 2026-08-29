import unittest

import helpers
from helpers import make_case, make_evidence

from weekly_report_quality.checks import (
    baseline_check,
    confidence_from_signals,
    judge_recheck,
    replay_check,
)
from weekly_report_quality.contracts import CheckResult
from weekly_report_quality.evaluators import run_deterministic
from weekly_report_quality.metamorphic import compare_metamorphic, derive_case


def _verdict(passed=True, score=0.9):
    return {"pass": passed, "score": score, "reasons": [], "model": "stub", "prompt_digest": "d"}


class ReplayCheckTests(unittest.TestCase):
    def test_reproducible_results_corroborate(self):
        case = make_case(expect={"route": {"allowed": ["wf"]}})
        evidence = make_evidence(route={"name": "wf", "confidence": 0.9})
        original = run_deterministic(case, evidence)
        signal = replay_check(case, evidence, original)
        self.assertEqual(signal["outcome"], "corroborate")

    def test_tampered_results_contradict(self):
        case = make_case(expect={"route": {"allowed": ["wf"]}})
        evidence = make_evidence(route={"name": "wf", "confidence": 0.9})
        tampered = [CheckResult("route", "route", "fail", score=0.0)]
        signal = replay_check(case, evidence, tampered)
        self.assertEqual(signal["outcome"], "contradict")


class JudgeRecheckTests(unittest.TestCase):
    def _case(self):
        return make_case(expect={"grounding": {"required": True}})

    def test_no_semantic_dimensions_unavailable(self):
        signal = judge_recheck(make_case(), make_evidence(), [])
        self.assertEqual(signal["outcome"], "unavailable")

    def test_stable_second_verdict_corroborates(self):
        evidence = make_evidence(
            judge_responses={"grounding": _verdict(), "grounding_second": _verdict(score=0.85)}
        )
        original = [CheckResult("grounding", "grounding", "pass", score=0.9)]
        signal = judge_recheck(self._case(), evidence, original)
        self.assertEqual(signal["outcome"], "corroborate")

    def test_verdict_flip_contradicts(self):
        evidence = make_evidence(
            judge_responses={"grounding": _verdict(), "grounding_second": _verdict(passed=False, score=0.2)}
        )
        original = [CheckResult("grounding", "grounding", "pass", score=0.9)]
        signal = judge_recheck(self._case(), evidence, original)
        self.assertEqual(signal["outcome"], "contradict")

    def test_missing_second_verdict_unavailable(self):
        evidence = make_evidence(judge_responses={"grounding": _verdict()})
        original = [CheckResult("grounding", "grounding", "pass", score=0.9)]
        signal = judge_recheck(self._case(), evidence, original)
        self.assertEqual(signal["outcome"], "unavailable")


class BaselineCheckTests(unittest.TestCase):
    def test_missing_baseline_unavailable(self):
        result = {"case_id": "A", "case_digest": "d", "status": "pass", "critical_failures": []}
        self.assertEqual(baseline_check(result, None)["outcome"], "unavailable")

    def test_status_flip_contradicts(self):
        result = {"case_id": "A", "case_digest": "d", "status": "fail", "critical_failures": []}
        base = [{"case_id": "A", "case_digest": "d", "status": "pass", "critical_failures": []}]
        self.assertEqual(baseline_check(result, base)["outcome"], "contradict")

    def test_version_change_unavailable(self):
        result = {"case_id": "A", "case_digest": "new", "status": "pass", "critical_failures": []}
        base = [{"case_id": "A", "case_digest": "old", "status": "pass", "critical_failures": []}]
        self.assertEqual(baseline_check(result, base)["outcome"], "unavailable")


class ConfidenceTests(unittest.TestCase):
    def test_all_corroborate_high(self):
        signals = [{"check": c, "outcome": "corroborate", "detail": ""} for c in "abc"]
        self.assertEqual(confidence_from_signals(signals), ("high", False))

    def test_any_contradict_low_with_adjudication(self):
        signals = [
            {"check": "a", "outcome": "corroborate", "detail": ""},
            {"check": "b", "outcome": "contradict", "detail": ""},
        ]
        self.assertEqual(confidence_from_signals(signals), ("low", True))

    def test_unavailable_without_contradiction_medium(self):
        signals = [
            {"check": "a", "outcome": "corroborate", "detail": ""},
            {"check": "b", "outcome": "unavailable", "detail": ""},
        ]
        self.assertEqual(confidence_from_signals(signals), ("medium", False))


class MetamorphicTests(unittest.TestCase):
    def test_drop_previous_derivation(self):
        case = make_case(expect={"output": {"must_contain": ["A"]}})
        derived, contract = derive_case(case, "drop_previous")
        self.assertIsNone(derived.input["material"]["previous"])
        self.assertIn("cross_period", contract["may_change"])
        self.assertIn("route", contract["must_not_change"])
        self.assertIn("相比上周", derived.expect["output"]["must_not_contain"])

    def test_compare_flags_disallowed_changes(self):
        contract = {"mutation": "drop_previous", "must_not_change": ["route"], "may_change": ["cross_period"]}
        base = [
            CheckResult("route", "route", "pass", score=1.0),
            CheckResult("cross_period", "cross_period", "pass", score=1.0),
        ]
        derived = [
            CheckResult("route", "route", "fail", score=0.0),
            CheckResult("cross_period", "cross_period", "fail", score=0.0),
        ]
        violations = compare_metamorphic(base, derived, contract)
        self.assertEqual(len(violations), 1)
        self.assertIn("route", violations[0])

    def test_paraphrase_preserves_grounded_dimensions_contract(self):
        case = make_case()
        derived, contract = derive_case(case, "paraphrase_current")
        self.assertNotEqual(
            derived.input["material"]["current"], case.input["material"]["current"]
        )
        self.assertIn("grounding", contract["must_not_change"])
        self.assertIn("style_semantics", contract["may_change"])

    def test_swap_segments_allows_no_changes(self):
        case = make_case(
            input={
                "material": {"current": "段落一\n段落二", "previous": None},
                "context": {"tenant_id": "tenant-a", "user_id": "user-1"},
            }
        )
        derived, contract = derive_case(case, "swap_unrelated_segments")
        self.assertEqual(derived.input["material"]["current"], "段落二\n段落一")
        self.assertEqual(contract["may_change"], [])

    def test_unknown_mutation_rejected(self):
        with self.assertRaises(ValueError):
            derive_case(make_case(), "unknown")


if __name__ == "__main__":
    unittest.main()
