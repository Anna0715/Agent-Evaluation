"""Shared fixture paths for scenario generator scripts."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "fixtures" / "online"
SCENARIOS_DIR = REPO_ROOT / "scenarios"
ONLINE_DIR = REPO_ROOT / "online"

XLSX_PATH = FIXTURES_DIR / "周报追问Agent全面评测用例.xlsx"
CATALOG_PATH = FIXTURES_DIR / "dataset_catalog.json"
ROLE_PERIOD_PEOPLE_PATH = FIXTURES_DIR / "role_period_people.json"

for _entry in (SCENARIOS_DIR, ONLINE_DIR):
    _s = str(_entry)
    if _s not in sys.path:
        sys.path.insert(0, _s)
