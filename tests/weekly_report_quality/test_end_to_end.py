"""End-to-end: seed cases + evidence fixtures -> run -> checks -> reports."""

import tempfile
import unittest
from pathlib import Path

import helpers
from helpers import TESTDATA

from weekly_report_quality.report import daily_report, write_run_outputs
from weekly_report_quality.runner import RunConfig, execute_run

CASES = TESTDATA / "cases"
EVIDENCE = TESTDATA / "evidence"


class EndToEndTests(unittest.TestCase):
    def _run(self, out_dir: Path, baseline: Path | None = None, run_id: str = "") -> dict:
        config = RunConfig(
            cases_dir=CASES,
            evidence_dir=EVIDENCE,
            out_dir=out_dir,
            baseline_file=baseline,
            run_id=run_id,
            trigger="test",
        )
        return execute_run(config)

    def test_seed_suite_statuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self._run(Path(tmp))
        by_id = {r["case_id"]: r for r in run["case_results"]}
        self.assertEqual(by_id["TC01"]["status"], "pass")
        self.assertEqual(by_id["TC02"]["status"], "pass")
        self.assertEqual(by_id["PERM01"]["status"], "pass")
        self.assertEqual(by_id["PERM03"]["status"], "pass")
        self.assertEqual(by_id["PERM04"]["status"], "pass")
        self.assertEqual(by_id["PERM05"]["status"], "pass")
        leak = by_id["PERM02"]
        self.assertEqual(leak["status"], "fail")
        self.assertTrue(
            any("contact_visibility" in d for d in leak["critical_failures"]),
            leak["critical_failures"],
        )

    def test_confidence_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            first = self._run(out, run_id="scheduled-20260820T0900")
            paths = write_run_outputs(first, out)
            second = self._run(
                out,
                baseline=Path(paths["run_json"]),
                run_id="scheduled-20260820T2100",
            )
            write_run_outputs(second, out)

            # First run: baseline unavailable -> at most medium confidence.
            for result in first["case_results"]:
                self.assertIn(result["confidence"], ("medium", "low"))
            # Second run: TC01 has semantic second verdict + baseline -> high.
            by_id = {r["case_id"]: r for r in second["case_results"]}
            self.assertEqual(by_id["TC01"]["confidence"], "high")
            # Permission-only cases lack semantic dimensions -> medium, not low.
            self.assertEqual(by_id["PERM01"]["confidence"], "medium")

            report = daily_report(out, "20260820")
            self.assertIn("scheduled-20260820T0900", report)
            self.assertIn("scheduled-20260820T2100", report)
            self.assertIn("两次运行对比", report)

            run_dir = out / first["run_id"]
            self.assertTrue((run_dir / "run.json").exists())
            self.assertTrue((run_dir / "junit.xml").exists())
            self.assertTrue((run_dir / "report.md").exists())
            self.assertTrue((run_dir / "cases" / "TC01.json").exists())

    def test_missing_evidence_case_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty_evidence = Path(tmp) / "evidence"
            empty_evidence.mkdir()
            config = RunConfig(
                cases_dir=CASES,
                evidence_dir=empty_evidence,
                out_dir=Path(tmp) / "out",
                trigger="test",
            )
            run = execute_run(config)
        self.assertEqual(run["summary"]["skip"], run["summary"]["total_cases"])
        self.assertEqual(
            len(run["summary"]["missing_evidence_cases"]), run["summary"]["total_cases"]
        )
        for result in run["case_results"]:
            self.assertTrue(result["adjudication_required"])


if __name__ == "__main__":
    unittest.main()
