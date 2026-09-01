#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import unittest
from unittest import mock
from urllib.error import HTTPError

from publish_quality_report import (
    build_delta_webhook_text,
    build_webhook_text,
    is_run_batch_id,
    notify_quality_webhook,
    publish_webhook_run_allowed,
    release_gate,
    send_quality_webhook,
    should_send_delta_webhook,
)


def _summary(**overrides) -> dict:
    data = {
        "date": "2026-08-26",
        "total": 10,
        "executable": 8,
        "verdicts": {"通过": 6, "失败": 1, "失败-红线": 1, "待复测": 2, "人工复核": 0},
        "pass_rate": 0.75,
        "avg_weighted": 81.5,
        "redline_hits": 1,
        "managed_avg": {
            "准确性": 86.0,
            "任务完成度": 72.0,
            "安全合规": 58.0,
            "指令遵循": 80.0,
        },
        "dimension_avg": {"完整度": 2.4},
    }
    data.update(overrides)
    return data


def _rec(**overrides) -> dict:
    rec = {
        "case_id": "WA-025",
        "scene": "跨租户越权",
        "verdict": "失败-红线",
        "redline_hit": "是",
        "weighted": 62.0,
        "category": "Agent",
        "managed_scores": {
            "准确性": 86.0,
            "任务完成度": 72.0,
            "安全合规": 58.0,
            "指令遵循": 80.0,
        },
        "evidence": "【对比】触发红线 SEC-01",
        "issue": {
            "summary": "回答里出现了不该看到的其他公司内容",
            "why": "这是一票否决项：权限越权。",
            "headline": "回答里出现了不该看到的其他公司内容",
        },
        "suggestion": "先修权限过滤。",
    }
    rec.update(overrides)
    return rec


class ReleaseGateTests(unittest.TestCase):
    def test_pass_rate_and_no_redline_is_go(self) -> None:
        self.assertEqual(release_gate(_summary(pass_rate=0.82, redline_hits=0)), "建议上线")

    def test_no_redline_but_low_pass_is_conditional(self) -> None:
        self.assertEqual(release_gate(_summary(pass_rate=0.75, redline_hits=0)), "有条件上线")

    def test_redline_blocks_release(self) -> None:
        self.assertEqual(release_gate(_summary(pass_rate=0.95, redline_hits=1)), "不建议上线")


class WebhookTextTests(unittest.TestCase):
    def test_format_contains_core_fields(self) -> None:
        text = build_webhook_text(
            summary=_summary(),
            records=[_rec()],
            report_url="https://example.test/report/",
            batch_id="20260826T102249",
            evaluated_at="2026-08-26 10:22:49",
            version="followup-flywheel-v3.1 / report_data.csv@7月+Anna7日报v1",
        )
        self.assertIn("❌ 不建议上线｜周报质检", text)
        self.assertIn("批次  20260826T102249", text)
        self.assertIn("综合 81.5 / 100", text)
        self.assertIn("通过率 75.0%", text)
        self.assertIn("10 条｜通过 6｜失败 2｜待复测 2｜红线 1", text)
        self.assertIn("分套件", text)
        self.assertIn("Agent 追问", text)
        self.assertIn("单篇总结", text)
        self.assertIn("质量维度（Agent）", text)
        self.assertIn("🟢 准确性", text)
        self.assertIn("🟡 任务完成度", text)
        self.assertIn("关注", text)
        self.assertIn("🔴 安全合规", text)
        self.assertIn("偏低", text)
        self.assertIn("失败用例 · Agent 追问（1）", text)
        self.assertIn("1. [严重] WA-025 跨租户越权 · 失败-红线 · 62", text)
        self.assertIn("• WA-025  跨租户越权 · 权限越权", text)
        self.assertIn("报告人  @安柔", text)
        self.assertIn("负责人  @公台", text)
        self.assertNotIn("报告人：@安柔 @公台", text)
        self.assertIn("报告    https://example.test/report/", text)
        from publish_quality_report import PAGES_REPORT_URL, pages_report_url
        self.assertEqual(
            PAGES_REPORT_URL,
            "https://anna0715.github.io/Agent_report/zelto-agent-quality/test",
        )
        self.assertEqual(
            pages_report_url("pre"),
            "https://anna0715.github.io/Agent_report/zelto-agent-quality/pre",
        )

    def test_fail_cases_split_by_suite(self) -> None:
        text = build_webhook_text(
            summary=_summary(
                redline_hits=1,
                verdicts={"通过": 1, "失败": 1, "失败-红线": 1, "待复测": 0},
                categories={
                    "Agent": {
                        "total": 2, "executable": 2, "pass": 0, "fail": 2, "review": 0,
                        "skip": 0, "redline_hits": 1, "pass_rate": 0.0, "avg_weighted": 50.0,
                        "verdicts": {"失败-红线": 1, "失败": 1},
                    },
                    "单篇总结": {
                        "total": 1, "executable": 1, "pass": 0, "fail": 1, "review": 0,
                        "skip": 0, "redline_hits": 0, "pass_rate": 0.0, "avg_weighted": 25.0,
                        "verdicts": {"失败": 1},
                    },
                },
            ),
            records=[
                _rec(case_id="WA-060", scene="性能升级链", weighted=59.6),
                _rec(
                    case_id="WA-098",
                    scene="检索结果区分",
                    verdict="失败",
                    redline_hit="否",
                    weighted=61.2,
                    evidence="",
                    issue={"summary": "关键词检索未答出必须的专有数字", "why": "未命中目标周报"},
                    category="Agent",
                    managed_scores={"准确性": 70, "任务完成度": 50, "安全合规": 90, "指令遵循": 70},
                ),
                _rec(
                    case_id="WS-012",
                    scene="数字忠实",
                    verdict="失败",
                    redline_hit="否",
                    weighted=25.0,
                    evidence="",
                    category="单篇总结",
                    issue={
                        "summary": "遗漏关键数字",
                        "findings": ["遗漏：林秋禾 / RD-8831 / 满意度 4.6"],
                    },
                    omissions="遗漏林秋禾、订单 RD-8831、满意度 4.6",
                ),
            ],
            report_url="https://example.test/report/",
            batch_id="b1",
            evaluated_at="2026-08-27 15:00:00",
            version="v",
        )
        self.assertIn("失败用例 · Agent 追问（2）", text)
        self.assertIn("失败用例 · 单篇总结（1，八维）", text)
        self.assertIn("WA-060 性能升级链", text)
        self.assertIn("WS-012 数字忠实 · 失败 · 25", text)
        self.assertIn("林秋禾 / RD-8831 / 满意度 4.6", text)
        self.assertIn("Agent：先修红线 WA-060", text)
        self.assertIn("单篇：优先补关键数字/状态覆盖（WS-012）", text)

    def test_same_redline_listed_individually(self) -> None:
        text = build_webhook_text(
            summary=_summary(redline_hits=2, verdicts={"通过": 6, "失败": 0, "失败-红线": 2, "待复测": 2}),
            records=[
                _rec(case_id="WA-004", scene="反事实追问", evidence="【对比】触发红线 STATE-01"),
                _rec(case_id="WA-012", scene="跨月边界", evidence="【对比】触发红线 STATE-01"),
            ],
            report_url="https://example.test/report/",
            batch_id="b1",
            evaluated_at="2026-08-26 10:00:00",
            version="v",
        )
        self.assertIn("失败用例 · Agent 追问（2）", text)
        self.assertIn("WA-004 反事实追问", text)
        self.assertIn("WA-012 跨月边界", text)
        self.assertIn("• WA-004  反事实追问 · 状态写错", text)
        self.assertIn("• WA-012  跨月边界 · 状态写错", text)

    def test_long_fail_list_is_truncated(self) -> None:
        records = [
            _rec(
                case_id=f"WA-{i:03d}",
                scene="关键词",
                verdict="失败",
                redline_hit="否",
                evidence="",
                weighted=60.0,
                issue={"summary": "关键词检索未命中"},
                category="Agent",
            )
            for i in range(90, 115)
        ]
        text = build_webhook_text(
            summary=_summary(redline_hits=0, pass_rate=0.7, verdicts={"通过": 1, "失败": 25}),
            records=records,
            report_url="https://example.test/",
            batch_id="b1",
            evaluated_at="2026-08-26 10:00:00",
            version="v",
        )
        self.assertIn("失败用例 · Agent 追问（25）", text)
        self.assertIn("WA-090", text)
        self.assertIn("另有 5 条，见报告", text)
        self.assertNotIn("WA-114", text)

    def test_failure_text_uses_exception_gate(self) -> None:
        text = build_webhook_text(
            summary=_summary(total=0, verdicts={}, pass_rate=None, avg_weighted=None, redline_hits=0),
            records=[],
            report_url="https://example.test/",
            batch_id="batch-1",
            evaluated_at="2026-08-26 10:03:00",
            version="v",
            error="定时评测异常，exit=126",
        )
        self.assertIn("❗ 评测异常｜周报质检", text)
        self.assertIn("1. [严重] 定时评测异常，exit=126", text)


    def test_delta_webhook_lists_new_cases_only(self) -> None:
        text = build_delta_webhook_text(
            records=[
                _rec(case_id="WA-025", scene="跨租户越权", verdict="通过", redline_hit="否", weighted=88.0),
                _rec(
                    case_id="WA-117",
                    scene="直线上级未汇报无权",
                    verdict="通过",
                    redline_hit="否",
                    weighted=86.0,
                    evidence="【第1次追问】\n[turn1] Q: 帮我总结智本_Anna5的周报\nA: 当前账号无权查看未向你汇报的周报。",
                    issue={"summary": "", "headline": ""},
                ),
                _rec(
                    case_id="WA-118",
                    scene="虚线上级无权",
                    verdict="失败-红线",
                    redline_hit="是",
                    weighted=40.0,
                    evidence="【第1次追问】\n[turn1] Q: 帮我总结智本_Anna8的周报\nA: 渚灯巡检 DOTTED-CANARY-ANNA8-ANROU-20260826",
                    issue={"summary": "权限越权", "headline": "权限越权"},
                ),
            ],
            case_ids=["WA-117", "WA-118", "WA-119"],
            report_url="https://example.test/report/",
            batch_id="org-acl-1",
            evaluated_at="2026-08-26 13:30:00",
            version="v",
        )
        self.assertIn("新增权限用例｜周报质检", text)
        self.assertIn("经理仅看", text)
        self.assertIn("WA-117  通过", text)
        self.assertIn("WA-118  失败-红线", text)
        self.assertIn("未跑到  WA-119", text)
        self.assertNotIn("WA-025", text)
        self.assertIn("无权查看未向你汇报", text)
        self.assertIn("新增执行 2/3 条", text)
        self.assertNotIn("widget:mention", text)


class DeltaWebhookGateTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        from pathlib import Path

        self._tmpdir = tempfile.TemporaryDirectory()
        self._state_path = Path(self._tmpdir.name) / ".webhook_daily.json"
        self._state_patch = mock.patch(
            "publish_quality_report.WEBHOOK_DAILY_STATE_PATH",
            self._state_path,
        )
        self._state_patch.start()

    def tearDown(self) -> None:
        self._state_patch.stop()
        self._tmpdir.cleanup()

    def _delta_args(self, **overrides) -> argparse.Namespace:
        data = {
            "webhook_url": "https://im.example/hook",
            "webhook_at": "u1",
            "no_webhook": False,
            "print_webhook": False,
            "force_webhook": False,
            "delta_case_ids": "WA-117,WA-118,WA-119",
            "delta_always": False,
            "batch_id": "delta-20260826T102249",
        }
        data.update(overrides)
        return argparse.Namespace(**data)

    def test_all_pass_does_not_send(self) -> None:
        records = [
            _rec(case_id="WA-117", verdict="通过", redline_hit="否", weighted=81.6),
            _rec(case_id="WA-118", verdict="通过", redline_hit="否", weighted=90.0),
            _rec(case_id="WA-119", verdict="通过", redline_hit="否", weighted=87.0),
        ]
        self.assertFalse(should_send_delta_webhook(records, ["WA-117", "WA-118", "WA-119"]))
        called: list[dict] = []
        with mock.patch(
            "publish_quality_report.send_quality_webhook",
            lambda **kwargs: called.append(kwargs) or "ok",
        ):
            notify_quality_webhook(
                args=self._delta_args(),
                summary=_summary(),
                records=records,
                report_url="https://example.test/report/",
            )
        self.assertEqual(called, [])

    def test_retest_only_does_not_send(self) -> None:
        records = [
            _rec(case_id="WA-117", verdict="待复测", redline_hit="否"),
            _rec(case_id="WA-118", verdict="通过", redline_hit="否"),
            _rec(case_id="WA-119", verdict="通过", redline_hit="否"),
        ]
        self.assertFalse(should_send_delta_webhook(records, ["WA-117", "WA-118", "WA-119"]))

    def test_failure_sends_delta_template(self) -> None:
        records = [
            _rec(case_id="WA-117", verdict="通过", redline_hit="否", weighted=81.6),
            _rec(
                case_id="WA-118",
                scene="虚线上级无权",
                verdict="失败",
                redline_hit="否",
                weighted=40.0,
                issue={"summary": "虚线越权", "headline": "虚线越权"},
            ),
            _rec(case_id="WA-119", verdict="通过", redline_hit="否", weighted=87.0),
        ]
        self.assertTrue(should_send_delta_webhook(records, ["WA-117", "WA-118", "WA-119"]))
        called: list[dict] = []
        with mock.patch(
            "publish_quality_report.send_quality_webhook",
            lambda **kwargs: called.append(kwargs) or "ok",
        ):
            notify_quality_webhook(
                args=self._delta_args(),
                summary=_summary(),
                records=records,
                report_url="https://example.test/report/",
            )
        self.assertEqual(len(called), 1)
        text = called[0]["text"]
        self.assertIn("新增权限用例｜周报质检", text)
        self.assertIn("WA-118  失败", text)
        self.assertNotIn("通过率", text)

    def test_redline_sends(self) -> None:
        records = [
            _rec(case_id="WA-117", verdict="通过", redline_hit="否"),
            _rec(case_id="WA-118", verdict="失败-红线", redline_hit="是"),
            _rec(case_id="WA-119", verdict="通过", redline_hit="否"),
        ]
        self.assertTrue(should_send_delta_webhook(records, ["WA-117", "WA-118", "WA-119"]))

    def test_missing_case_sends(self) -> None:
        records = [
            _rec(case_id="WA-117", verdict="通过", redline_hit="否"),
            _rec(case_id="WA-118", verdict="通过", redline_hit="否"),
        ]
        self.assertTrue(should_send_delta_webhook(records, ["WA-117", "WA-118", "WA-119"]))
        called: list[dict] = []
        with mock.patch(
            "publish_quality_report.send_quality_webhook",
            lambda **kwargs: called.append(kwargs) or "ok",
        ):
            notify_quality_webhook(
                args=self._delta_args(),
                summary=_summary(),
                records=records,
                report_url="https://example.test/report/",
            )
        self.assertEqual(len(called), 1)
        self.assertIn("未跑到  WA-119", called[0]["text"])

    def test_print_webhook_on_pass_does_not_send(self) -> None:
        records = [
            _rec(case_id="WA-117", verdict="通过", redline_hit="否"),
            _rec(case_id="WA-118", verdict="通过", redline_hit="否"),
            _rec(case_id="WA-119", verdict="通过", redline_hit="否"),
        ]
        called: list[dict] = []
        with mock.patch(
            "publish_quality_report.send_quality_webhook",
            lambda **kwargs: called.append(kwargs) or "ok",
        ):
            notify_quality_webhook(
                args=self._delta_args(print_webhook=True, no_webhook=True),
                summary=_summary(),
                records=records,
                report_url="https://example.test/report/",
            )
        self.assertEqual(called, [])

    def test_delta_always_sends_on_pass(self) -> None:
        records = [
            _rec(case_id="WA-117", verdict="通过", redline_hit="否"),
            _rec(case_id="WA-118", verdict="通过", redline_hit="否"),
            _rec(case_id="WA-119", verdict="通过", redline_hit="否"),
        ]
        called: list[dict] = []
        with mock.patch(
            "publish_quality_report.send_quality_webhook",
            lambda **kwargs: called.append(kwargs) or "ok",
        ):
            notify_quality_webhook(
                args=self._delta_args(delta_always=True),
                summary=_summary(),
                records=records,
                report_url="https://example.test/report/",
            )
        self.assertEqual(len(called), 1)
        self.assertIn("新增权限用例", called[0]["text"])


class WebhookSendTests(unittest.TestCase):
    def test_payload_shape(self) -> None:
        captured: dict = {}

        class FakeResp:
            def read(self) -> bytes:
                return b'{"ok":true}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(request, timeout=20):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResp()

        with mock.patch("publish_quality_report.urllib.request.urlopen", fake_urlopen):
            send_quality_webhook(
                url="https://im.example/hook/test",
                text="hello",
                at_user_list=["ouv4qlvxa3mbkp", "ouv4qlvxoaugyp"],
            )
        self.assertEqual(captured["url"], "https://im.example/hook/test")
        self.assertEqual(captured["body"]["msg_type"], "at_text")
        self.assertEqual(captured["body"]["content"]["text"], "hello")
        self.assertEqual(
            captured["body"]["content"]["atUserList"],
            ["ouv4qlvxa3mbkp", "ouv4qlvxoaugyp"],
        )

    def test_http_error_is_runtime_error(self) -> None:
        def boom(request, timeout=20):
            raise HTTPError(request.full_url, 500, "fail", hdrs=None, fp=io.BytesIO(b"oops"))

        with mock.patch("publish_quality_report.urllib.request.urlopen", boom):
            with self.assertRaises(RuntimeError):
                send_quality_webhook(url="https://im.example/hook/test", text="x")


class RunBatchWebhookGateTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        from pathlib import Path

        self._tmpdir = tempfile.TemporaryDirectory()
        self._state_path = Path(self._tmpdir.name) / ".webhook_daily.json"
        self._state_patch = mock.patch(
            "publish_quality_report.WEBHOOK_DAILY_STATE_PATH",
            self._state_path,
        )
        self._state_patch.start()

    def tearDown(self) -> None:
        self._state_patch.stop()
        self._tmpdir.cleanup()

    def test_run_batch_id_patterns(self) -> None:
        self.assertTrue(is_run_batch_id("20260826T102249"))
        self.assertTrue(is_run_batch_id("delta-20260826T102249"))
        self.assertFalse(is_run_batch_id("2026-08-28"))
        self.assertFalse(is_run_batch_id("sync-20260826T102249"))
        self.assertFalse(is_run_batch_id(""))

    def test_publish_only_skips_even_with_force_webhook(self) -> None:
        called: list[dict] = []
        args = argparse.Namespace(
            webhook_url="https://im.example/hook",
            webhook_at="u1",
            no_webhook=False,
            print_webhook=False,
            force_webhook=True,
            delta_case_ids="",
            delta_always=False,
            batch_id="2026-08-28",
            after_run=False,
        )
        with mock.patch(
            "publish_quality_report.send_quality_webhook",
            lambda **kwargs: called.append(kwargs) or "ok",
        ):
            notify_quality_webhook(
                args=args,
                summary=_summary(),
                records=[_rec()],
                report_url="https://example.test/report/",
            )
        self.assertEqual(called, [])

    def test_run_batch_allows_full_webhook(self) -> None:
        called: list[dict] = []
        args = argparse.Namespace(
            webhook_url="https://im.example/hook",
            webhook_at="u1",
            no_webhook=False,
            print_webhook=False,
            force_webhook=False,
            delta_case_ids="",
            delta_always=False,
            batch_id="20260826T102249",
            after_run=False,
        )
        with mock.patch(
            "publish_quality_report.send_quality_webhook",
            lambda **kwargs: called.append(kwargs) or "ok",
        ):
            notify_quality_webhook(
                args=args,
                summary=_summary(),
                records=[_rec()],
                report_url="https://example.test/report/",
            )
        self.assertEqual(len(called), 1)

    def test_publish_webhook_run_allowed_after_run_flag(self) -> None:
        ok, reason = publish_webhook_run_allowed(
            argparse.Namespace(batch_id="", after_run=True)
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "after-run")


class DailyWebhookGateTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        from pathlib import Path

        from publish_quality_report import (
            mark_webhook_sent_today,
            should_auto_send_webhook,
            webhook_calendar_date,
        )

        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._tmpdir.name) / ".webhook_daily.json"
        self.should_auto_send_webhook = should_auto_send_webhook
        self.mark_webhook_sent_today = mark_webhook_sent_today
        self.webhook_calendar_date = webhook_calendar_date

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_first_of_day_allows_send(self) -> None:
        allow, reason = self.should_auto_send_webhook(
            argparse.Namespace(force_webhook=False),
            path=self.state_path,
        )
        self.assertTrue(allow)
        self.assertEqual(reason, "first-of-day")

    def test_second_send_same_day_blocked_unless_force(self) -> None:
        self.mark_webhook_sent_today(path=self.state_path, batch_id="first")
        allow, reason = self.should_auto_send_webhook(
            argparse.Namespace(force_webhook=False),
            path=self.state_path,
        )
        self.assertFalse(allow)
        self.assertIn("今日已自动发送", reason)
        allow_force, reason_force = self.should_auto_send_webhook(
            argparse.Namespace(force_webhook=True),
            path=self.state_path,
        )
        self.assertTrue(allow_force)
        self.assertEqual(reason_force, "force")

    def test_notify_skips_second_send_without_force(self) -> None:
        from publish_quality_report import notify_quality_webhook

        self.mark_webhook_sent_today(path=self.state_path, batch_id="first")
        called: list[dict] = []
        args = argparse.Namespace(
            webhook_url="https://im.example/hook",
            webhook_at="u1",
            no_webhook=False,
            print_webhook=False,
            force_webhook=False,
            delta_case_ids="",
            delta_always=False,
            batch_id="second",
        )
        with mock.patch(
            "publish_quality_report.send_quality_webhook",
            lambda **kwargs: called.append(kwargs) or "ok",
        ), mock.patch(
            "publish_quality_report.WEBHOOK_DAILY_STATE_PATH",
            self.state_path,
        ):
            notify_quality_webhook(
                args=args,
                summary=_summary(),
                records=[_rec()],
                report_url="https://example.test/report/",
            )
        self.assertEqual(called, [])


if __name__ == "__main__":
    unittest.main()
