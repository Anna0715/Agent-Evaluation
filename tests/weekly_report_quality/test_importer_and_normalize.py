import tempfile
import unittest
from pathlib import Path

import helpers

from weekly_report_quality.importer import import_markdown
from weekly_report_quality.normalize import build_evidence, from_business_agent_trace, redact

MARKDOWN = """\
## TC-1 正常双周期
**上一期**
```
上周完成压测
```
**当前期**
```
本周完成灰度发布
```

## TC-2 无上期
**上一期**
```
无
```
**当前期**
```
本周完成看板 MVP
```
"""


class ImporterTests(unittest.TestCase):
    def test_import_preserves_source_and_invents_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.md"
            path.write_text(MARKDOWN, encoding="utf-8")
            cases = import_markdown(path)
        self.assertEqual([c["id"] for c in cases], ["TC01", "TC02"])
        first = cases[0]
        self.assertEqual(first["input"]["material"]["current"], "本周完成灰度发布")
        self.assertEqual(first["input"]["material"]["previous"], "上周完成压测")
        self.assertEqual(first["expect"], {})
        self.assertEqual(first["source"]["start_line"], 1)
        self.assertEqual(first["oracle"]["source"], "markdown_import")
        second = cases[1]
        self.assertIsNone(second["input"]["material"]["previous"])


class NormalizeTests(unittest.TestCase):
    def test_redacts_sensitive_keys_and_values(self):
        data = {
            "jwt_token": "abc",
            "nested": {"internal_key": "xyz", "ok": "value"},
            "text": "header eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIx.sig-part-okhere trailing",
        }
        redacted = redact(data)
        self.assertEqual(redacted["jwt_token"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["internal_key"], "[REDACTED]")
        self.assertNotIn("eyJ", redacted["text"])

    def test_build_evidence_conforms_to_contract(self):
        evidence = build_evidence("C1", "output text")
        self.assertEqual(evidence["contract"], "weekly_report_quality.evidence.v1")
        self.assertEqual(evidence["case_id"], "C1")
        self.assertIsNone(evidence["route"])

    def test_trace_mapping_leaves_missing_sections_none(self):
        trace = {
            "workflow": {"key": "weekly_report.recipient_summary", "confidence": 0.9},
            "tool_calls": [{"name": "reader", "arguments": {"id": "r1"}}],
        }
        evidence = from_business_agent_trace("C1", "text", trace)
        self.assertEqual(evidence["route"]["name"], "weekly_report.recipient_summary")
        self.assertEqual(evidence["mcp_calls"][0]["tool"], "reader")
        self.assertIsNone(evidence["faq_candidates"])
        self.assertIsNone(evidence["memory_events"])


if __name__ == "__main__":
    unittest.main()
