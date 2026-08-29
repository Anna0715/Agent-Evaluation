"""Repository root and canonical path constants."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

SPEC_DIR = REPO_ROOT / "spec"
CRITERIA_DIR = REPO_ROOT / "criteria"
FIXTURES_DIR = REPO_ROOT / "fixtures"
SCENARIOS_DIR = REPO_ROOT / "scenarios"
ONLINE_DIR = REPO_ROOT / "online"
PACKAGES_DIR = REPO_ROOT / "packages"
ARTIFACTS_DIR = REPO_ROOT / "artifacts"

FIXTURES_OFFLINE_CASES = FIXTURES_DIR / "offline" / "cases"
FIXTURES_OFFLINE_EVIDENCE = FIXTURES_DIR / "offline" / "evidence"
FIXTURES_ONLINE_DIR = FIXTURES_DIR / "online"

ARTIFACTS_OFFLINE_RUNS = ARTIFACTS_DIR / "offline-runs"
ARTIFACTS_REVIEWS = ARTIFACTS_DIR / "reviews"
ARTIFACTS_SUMMARIES = ARTIFACTS_DIR / "summaries"

ONLINE_SCHEDULE_DIR = ONLINE_DIR / "schedule"
ONLINE_REPORT_LIVE_DIR = ONLINE_DIR / "report_live"
