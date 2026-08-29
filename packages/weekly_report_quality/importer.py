"""Import legacy weekly-report markdown cases into the versioned contract.

The importer preserves the source location and only fills fields that are
actually present in the markdown; it never invents route, FAQ, Skill, or
MCP expectations (spec: Import historical markdown cases).
"""

from __future__ import annotations

import re
from pathlib import Path

from weekly_report_quality.contracts import CASE_CONTRACT

CASE_HEADING_RE = re.compile(r"^(#{2,6})\s+(?P<title>.*?\bTC\\?-?\d+.*)$", re.IGNORECASE)
SECTION_LABEL_RE = re.compile(r"^\s*\*\*(?P<label>[^*]+)\*\*\s*$")
FENCE_RE = re.compile(r"^\s*```")

PREVIOUS_LABELS = {
    "上一期", "上期", "上周期", "上一周期", "上个周期",
    "previous", "previous_cycle", "previous cycle",
}
CURRENT_LABELS = {
    "当前期", "本期", "本周期", "当前周期", "下一期", "下期", "下周期", "下个周期",
    "current", "current_cycle", "current cycle", "next", "next_cycle", "next cycle",
}
EMPTY_MARKERS = {"", "无", "（无）", "(无)", "none", "null", "n/a", "na"}


def _normalize_escapes(value: str) -> str:
    return re.sub(r"\\([\\`*_{}\[\]()#+\-.!|>])", r"\1", value).strip()


def _normalize_label(value: str) -> str:
    return _normalize_escapes(value).strip().lower().replace(" ", "_")


def _normalize_report(value: str) -> str:
    stripped = _normalize_escapes(value)
    compact = re.sub(r"\s+", "", stripped).lower()
    if compact in EMPTY_MARKERS:
        return ""
    return stripped


def _case_id_from_title(title: str, fallback_index: int) -> str:
    match = re.search(r"TC\\?-?(\d+)", title, re.IGNORECASE)
    if match:
        return f"TC{int(match.group(1)):02d}"
    return f"CASE{fallback_index:02d}"


def import_markdown(path: Path) -> list[dict]:
    """Parse a markdown case file into a list of versioned case dicts."""
    lines = path.read_text(encoding="utf-8").splitlines()
    boundaries: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        match = CASE_HEADING_RE.match(line)
        if match:
            boundaries.append((idx, _normalize_escapes(match.group("title"))))
    cases: list[dict] = []
    for order, (start, title) in enumerate(boundaries, start=1):
        end = boundaries[order][0] if order < len(boundaries) else len(lines)
        sections = _parse_sections(lines[start + 1 : end])
        previous = _normalize_report(sections.get("previous", ""))
        current = _normalize_report(sections.get("current", ""))
        notes = sections.get("notes", [])
        case_id = _case_id_from_title(title, order)
        cases.append(
            {
                "contract": CASE_CONTRACT,
                "id": case_id,
                "version": 1,
                "tags": ["imported", "markdown"],
                "input": {
                    "material": {
                        "current": current,
                        "previous": previous or None,
                    },
                },
                "expect": {},
                "oracle": {
                    "source": "markdown_import",
                    "evidence": title,
                    "notes": notes,
                },
                "scoring": {},
                "source": {
                    "file": str(path),
                    "title": title,
                    "start_line": start + 1,
                    "end_line": end,
                },
            }
        )
    return cases


def _parse_sections(lines: list[str]) -> dict:
    sections: dict = {"notes": []}
    label: str | None = None
    in_fence = False
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer, label
        if label and buffer:
            sections[label] = "\n".join(buffer).strip()
        buffer = []

    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            match = SECTION_LABEL_RE.match(line)
            if match:
                flush()
                normalized = _normalize_label(match.group("label"))
                if normalized in PREVIOUS_LABELS:
                    label = "previous"
                elif normalized in CURRENT_LABELS:
                    label = "current"
                else:
                    label = None
                    sections["notes"].append(_normalize_escapes(match.group("label")))
                continue
        if label:
            buffer.append(line)
        elif line.strip() and not in_fence:
            sections["notes"].append(line.strip())
    flush()
    return sections
