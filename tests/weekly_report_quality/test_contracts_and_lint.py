import unittest

import helpers
from helpers import make_case

from weekly_report_quality.contracts import (
    CASE_CONTRACT,
    CheckResult,
    ContractError,
    parse_case,
    parse_evidence,
)
from weekly_report_quality.lint import lint_case, lint_cases


class ContractTests(unittest.TestCase):
    def test_case_requires_contract_and_material(self):
        with self.assertRaises(ContractError):
            parse_case({"id": "x"}, "t")
        with self.assertRaises(ContractError):
            parse_case(
                {"contract": CASE_CONTRACT, "id": "x", "version": 1, "input": {}}, "t"
            )

    def test_case_digest_is_stable(self):
        a, b = make_case("C1"), make_case("C1")
        self.assertEqual(a.digest(), b.digest())
        c = make_case("C1", version=2)
        self.assertNotEqual(a.digest(), c.digest())

    def test_evidence_requires_output_text(self):
        with self.assertRaises(ContractError):
            parse_evidence(
                {"contract": "weekly_report_quality.evidence.v1", "case_id": "x", "output": {}},
                "t",
            )

    def test_check_result_rejects_bad_status(self):
        with self.assertRaises(ContractError):
            CheckResult(evaluator="x", dimension="x", status="maybe")


class LintTests(unittest.TestCase):
    def test_conflicting_faq_expectations_rejected(self):
        case = make_case(
            expect={"faq": {"top_k": 3, "must_hit": ["d1"], "must_not_hit": ["d1"]}}
        )
        issues = lint_case(case)
        self.assertTrue(any("must_hit and must_not_hit" in i.message for i in issues))

    def test_required_and_forbidden_mcp_tool_rejected(self):
        case = make_case(
            expect={
                "mcp": {
                    "required_calls": [{"tool": "t1"}],
                    "forbidden_tools": ["t1"],
                }
            }
        )
        issues = lint_case(case)
        self.assertTrue(any("required and forbidden" in i.message for i in issues))

    def test_expect_refusal_requires_markers(self):
        case = make_case(expect={"permission": {"expect_refusal": True}})
        issues = lint_case(case)
        self.assertTrue(any("refusal_markers" in i.message for i in issues))

    def test_strong_assertions_require_oracle(self):
        case = make_case(
            expect={"output": {"must_contain": ["x"]}}, oracle={}
        )
        issues = lint_case(case)
        self.assertTrue(any("oracle.source" in i.message for i in issues))

    def test_duplicate_ids_detected(self):
        issues = lint_cases([make_case("DUP"), make_case("DUP")])
        self.assertTrue(any("duplicate case id" in i.message for i in issues))

    def test_clean_case_passes(self):
        self.assertEqual(lint_case(make_case()), [])


if __name__ == "__main__":
    unittest.main()
