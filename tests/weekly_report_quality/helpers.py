"""Shared test helpers: path shim and contract factories."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGES_DIR = REPO_ROOT / "packages"
if str(PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGES_DIR))

FIXTURES_OFFLINE_CASES = REPO_ROOT / "fixtures" / "offline" / "cases"
FIXTURES_OFFLINE_EVIDENCE = REPO_ROOT / "fixtures" / "offline" / "evidence"
ARTIFACTS_OFFLINE_RUNS = REPO_ROOT / "artifacts" / "offline-runs"

TESTDATA = REPO_ROOT / "fixtures" / "offline"
CASES = FIXTURES_OFFLINE_CASES
EVIDENCE = FIXTURES_OFFLINE_EVIDENCE

from weekly_report_quality.contracts import (  # noqa: E402
    CASE_CONTRACT,
    EVIDENCE_CONTRACT,
    parse_case,
    parse_evidence,
)


def make_case(case_id: str = "T1", **overrides):
    data = {
        "contract": CASE_CONTRACT,
        "id": case_id,
        "version": 1,
        "tags": ["test"],
        "input": {
            "material": {"current": "本周完成 A", "previous": "上周计划 A"},
            "context": {"tenant_id": "tenant-a", "user_id": "user-1"},
        },
        "expect": {},
        "oracle": {"source": "human"},
        "scoring": {},
    }
    data.update(overrides)
    return parse_case(data, f"test:{case_id}")


def make_evidence(case_id: str = "T1", **overrides):
    data = {
        "contract": EVIDENCE_CONTRACT,
        "case_id": case_id,
        "generated_at": "2026-08-20T00:00:00+00:00",
        "output": {"text": "本周完成 A", "json": None},
        "route": None,
        "faq_candidates": None,
        "skill": None,
        "mcp_calls": None,
        "memory_events": None,
        "model": {},
        "judge_responses": {},
        "errors": [],
    }
    data.update(overrides)
    return parse_evidence(data, f"test:{case_id}")
