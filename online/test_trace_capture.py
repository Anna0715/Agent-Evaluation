import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("run_report_agent_cases.py")
SPEC = importlib.util.spec_from_file_location("report_agent_runner", SCRIPT)
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)

PUBLISH = Path(__file__).with_name("publish_quality_report.py")
PUB_SPEC = importlib.util.spec_from_file_location("publish_quality_report", PUBLISH)
assert PUB_SPEC and PUB_SPEC.loader
PUBLISHER = importlib.util.module_from_spec(PUB_SPEC)
sys.modules[PUB_SPEC.name] = PUBLISHER
PUB_SPEC.loader.exec_module(PUBLISHER)


def im_frame(event_type: int, **extra) -> str:
    payload = {
        "errCode": 0,
        "errMsg": "",
        "errDlt": "",
        "data": {
            "sessionId": extra.pop("sessionId", "cs_test"),
            "messageId": extra.pop("messageId", "cm_test"),
            "eventType": event_type,
            **extra,
        },
    }
    return "data: " + json.dumps(payload, ensure_ascii=False)


class TraceCaptureTest(unittest.TestCase):
    def test_extracts_identifiers_events_and_observed_components(self) -> None:
        raw = "\n".join(
            [
                "data: " + json.dumps(
                    {
                        "eventType": 1,
                        "sessionId": "cs_test",
                        "messageId": "cm_test",
                        "data": {"routeKey": "weekly_report"},
                    }
                ),
                "data: " + json.dumps(
                    {
                        "eventType": 2,
                        "data": {
                            "faqId": "faq_1",
                            "skillKey": "weekly-summary",
                            "toolName": "report.search",
                        },
                    }
                ),
                "data: " + json.dumps({"eventType": 3, "content": "answer"}),
            ]
        )

        trace = RUNNER.extract_sse_trace(raw)

        self.assertEqual(trace["sessionId"], "cs_test")
        self.assertEqual(trace["messageId"], "cm_test")
        self.assertEqual(trace["eventCount"], 3)
        self.assertEqual(trace["observed"]["routes"], ["weekly_report"])
        self.assertEqual(trace["observed"]["faq"], ["faq_1"])
        self.assertEqual(trace["observed"]["skills"], ["weekly-summary"])
        self.assertEqual(trace["observed"]["mcpTools"], ["report.search"])
        self.assertTrue(trace["coverage"]["output"])

    def test_unwraps_im_envelope_and_maps_event_types(self) -> None:
        raw = "\n".join(
            [
                im_frame(1),
                im_frame(10, content="周报（2026/07/06-07/10）"),
                im_frame(2, content="本周", sequence=3),
            ]
        )

        trace = RUNNER.extract_sse_trace(raw)

        self.assertEqual(trace["sessionId"], "cs_test")
        self.assertEqual(trace["messageId"], "cm_test")
        self.assertEqual(trace["eventCount"], 3)
        self.assertEqual(
            trace["eventTypes"],
            {"started": 1, "report_ref": 1, "text_delta": 1},
        )
        self.assertEqual(trace["observed"]["mcpTools"], [])
        self.assertFalse(trace["coverage"]["mcp"])
        self.assertEqual(trace["status"], "部分可观测")

    def test_maps_event_type_3_as_completed_not_a_tool(self) -> None:
        raw = im_frame(3, finishReason="completed")

        trace = RUNNER.extract_sse_trace(raw)

        self.assertEqual(trace["eventTypes"], {"completed": 1})
        self.assertEqual(trace["observed"]["mcpTools"], [])
        self.assertFalse(trace["coverage"]["mcp"])

    def test_reads_gateway_tool_call_object_and_sse_event_name(self) -> None:
        raw = "\n".join(
            [
                "event: started",
                "data: " + json.dumps({"sessionId": "cs_gw", "messageId": "cm_gw"}),
                "event: tool_call",
                "data: "
                + json.dumps(
                    {
                        "toolCall": {
                            "name": "memory_search",
                            "toolCallId": "call_1",
                        }
                    }
                ),
                "event: tool_result",
                "data: "
                + json.dumps(
                    {
                        "toolResult": {
                            "name": "memory_search",
                            "content": "empty",
                        }
                    }
                ),
                "event: text_delta",
                "data: " + json.dumps({"content": "在派生记忆索引里未找到"}),
            ]
        )

        trace = RUNNER.extract_sse_trace(raw)

        self.assertEqual(trace["sessionId"], "cs_gw")
        self.assertIn("memory_search", trace["observed"]["mcpTools"])
        self.assertTrue(trace["coverage"]["mcp"])
        self.assertGreaterEqual(trace["eventTypes"].get("tool_call", 0), 1)
        self.assertGreaterEqual(trace["eventTypes"].get("tool_result", 0), 1)

    def test_reads_protojson_snake_case_tool_call(self) -> None:
        raw = "\n".join(
            [
                "event: tool_call",
                "data: "
                + json.dumps(
                    {
                        "sequence": 4,
                        "tool_call": {
                            "name": "entity_get_source",
                            "tool_call_id": "call_2",
                        },
                    }
                ),
            ]
        )

        trace = RUNNER.extract_sse_trace(raw)

        self.assertEqual(trace["observed"]["mcpTools"], ["entity_get_source"])
        self.assertEqual(trace["eventTypes"].get("tool_call"), 1)

    def test_does_not_treat_answer_text_as_tool_name(self) -> None:
        raw = im_frame(2, content="请调用 memory_search 再回答")

        trace = RUNNER.extract_sse_trace(raw)

        self.assertEqual(trace["observed"]["mcpTools"], [])

    def test_marks_missing_internal_chain_as_partial(self) -> None:
        raw = "data: " + json.dumps(
            {"eventType": 3, "sessionId": "cs_test", "content": "answer"}
        )

        trace = RUNNER.extract_sse_trace(raw)

        self.assertEqual(trace["status"], "部分可观测")
        self.assertFalse(trace["coverage"]["route"])
        self.assertFalse(trace["coverage"]["faq"])
        self.assertFalse(trace["coverage"]["skill"])
        self.assertFalse(trace["coverage"]["mcp"])


class TraceReportTest(unittest.TestCase):
    def test_build_trace_nodes_uses_captured_tools_instead_of_hardcoded_gap(self) -> None:
        rec = {
            "report_id": "r1",
            "data_version": "v1",
            "session_id": "cs_1",
            "message_id": "cm_1",
            "verdict": "通过",
            "weighted": 90,
            "redline_hit": "否",
            "turns": [{"a": "ok"}],
            "trace_summary": {
                "turns": [
                    {
                        "eventCount": 4,
                        "eventTypes": {"tool_call": 1, "text_delta": 3},
                        "httpStatus": 200,
                        "observed": {"mcpTools": ["memory_search"]},
                    }
                ]
            },
        }

        nodes = {n["key"]: n for n in PUBLISHER.build_trace_nodes(rec, {"question": "q"})["nodes"]}

        self.assertEqual(nodes["mcp"]["status"], "已观测")
        self.assertIn("memory_search", nodes["mcp"]["observed"])
        self.assertEqual(nodes["mcp"]["label"], "工具调用")
        self.assertEqual(nodes["session"]["label"], "追问")
        self.assertIn("首轮绑定 reportId=r1", nodes["session"]["observed"])
        self.assertIn("streamMessageId=cm_1", nodes["session"]["observed"])

    def test_session_binding_uses_first_turn_bound_ids(self) -> None:
        rec = {
            "case_id": "WA-082",
            "scene": "固定格式跨周追问",
            "report_id": "ignored",
            "session_id": "cs_bind",
            "trace_summary": {"boundReportIds": ["2086a", "2086b"]},
        }
        self.assertEqual(
            PUBLISHER.first_turn_bound_report_ids(rec),
            ["2086a", "2086b"],
        )
        self.assertEqual(
            PUBLISHER.session_binding_text(rec),
            "sessionId=cs_bind 首轮绑定 reportId=2086a,2086b",
        )

    def test_denied_id_session_is_not_bound_to_target(self) -> None:
        rec = {
            "case_id": "WA-028",
            "scene": "权限中途移除",
            "report_id": "2086064999792381952",
            "session_id": "cs_denied",
            "trace_summary": {},
        }
        self.assertEqual(PUBLISHER.first_turn_bound_report_ids(rec), [])
        self.assertEqual(
            PUBLISHER.session_binding_text(rec),
            "sessionId=cs_denied 首轮未绑定 reportId",
        )

    def test_others_inbox_session_is_not_bound(self) -> None:
        rec = {
            "case_id": "WA-086",
            "scene": "他人收件箱",
            "report_id": "anna5-sent",
            "session_id": "cs_inbox",
            "trace_summary": {},
        }
        self.assertEqual(PUBLISHER.first_turn_bound_report_ids(rec), [])
        self.assertEqual(
            PUBLISHER.session_binding_text(rec),
            "sessionId=cs_inbox 首轮未绑定 reportId",
        )

    def test_request_protocol_describes_first_turn_report_id_then_session(self) -> None:
        rec = {
            "case_id": "WA-005",
            "scene": "多轮指代",
            "report_id": "2086a",
            "session_id": "cs_follow",
            "trace_summary": {
                "boundReportIds": ["2086a"],
                "turns": [
                    {
                        "request": {
                            "tenantId": "T1120BGCN",
                            "sessionId": "",
                            "reports": [{"reportId": "2086a", "reportName": "周报（2026/07/13-07/17）"}],
                        }
                    },
                    {
                        "request": {
                            "tenantId": "T1120BGCN",
                            "sessionId": "cs_follow",
                            "reports": [],
                        }
                    },
                ],
            },
        }
        text = PUBLISHER.first_turn_request_text(rec)
        self.assertIn("attachments.reports=2086a", text)
        self.assertIn("不传 sessionId", text)
        self.assertIn("续轮只传 sessionId=cs_follow", text)
        self.assertIn("不再传 reportId", text)

    def test_build_trace_nodes_explains_client_gap_when_tools_missing(self) -> None:
        rec = {
            "report_id": "r1",
            "session_id": "cs_1",
            "verdict": "通过",
            "weighted": 80,
            "redline_hit": "否",
            "turns": [{"a": "ok"}],
            "trace_summary": {
                "turns": [
                    {
                        "eventCount": 397,
                        "eventTypes": {"unknown": 397},
                        "observed": {"mcpTools": []},
                    }
                ]
            },
        }

        nodes = {n["key"]: n for n in PUBLISHER.build_trace_nodes(rec, {"question": "q"})["nodes"]}

        self.assertEqual(nodes["mcp"]["status"], "已调用")
        self.assertIn("不是 MCP", nodes["mcp"]["observed"])
        self.assertIn("unknown", nodes["mcp"]["observed"])
        self.assertIn("tool_call 过滤", nodes["mcp"]["observed"])
        self.assertNotIn("未暴露该节点事件", nodes["mcp"]["observed"])

    def test_tool_node_stays_missing_when_agent_did_not_run(self) -> None:
        rec = {
            "report_id": "",
            "session_id": "",
            "verdict": "待复测",
            "weighted": None,
            "redline_hit": "否",
            "turns": [],
            "trace_summary": {"turns": []},
        }
        nodes = {n["key"]: n for n in PUBLISHER.build_trace_nodes(rec, {"question": "q"})["nodes"]}
        self.assertEqual(nodes["mcp"]["status"], "缺失")


SECRET_TOOL_PREVIEW = "SECRET_REPORT_BODY_SHOULD_NOT_LEAK"


def agent_trace_fixture(run_id: str = "bar_d331061ef6a5496285fce50ab3ad0396") -> dict:
    return {
        "trace": {
            "run": {
                "run_id": run_id,
                "trace_id": "tr_1",
                "request_id": "req_1",
                "scenario": "business_chat",
                "workflow_key": "weekly_report.recipient_summary",
                "prompt_key": "report_chat_agent",
                "prompt_version": "0.4.2",
                "model": "openrouter/openai/gpt-5.5",
                "entity_id": "cs_b301a4cf-a6a1-4030-818e-da1a17f0967b",
            },
            "events": [
                {
                    "event_type": "chat.tool_call",
                    "payload_json": json.dumps(
                        {
                            "name": "entity_get_source",
                            "tool_call_id": "call_src",
                            "arguments_summary": "entity_id=2090625416027967488",
                            "arguments_json": '{"entity_id":"2090625416027967488"}',
                        }
                    ),
                },
                {
                    "event_type": "chat.tool_result",
                    "payload_json": json.dumps(
                        {
                            "name": "entity_get_source",
                            "tool_call_id": "call_src",
                            "status": "completed",
                            "result_preview": SECRET_TOOL_PREVIEW,
                        }
                    ),
                },
            ],
        }
    }


class AgentTraceApiTest(unittest.TestCase):
    def test_parse_extracts_tools_routes_skills_without_result_body(self) -> None:
        parsed = RUNNER.parse_agent_full_trace(agent_trace_fixture())

        self.assertEqual(parsed["runId"], "bar_d331061ef6a5496285fce50ab3ad0396")
        self.assertEqual(parsed["mcpTools"], ["entity_get_source"])
        self.assertEqual(parsed["toolCallCount"], 1)
        self.assertEqual(
            parsed["toolCalls"],
            [
                {
                    "name": "entity_get_source",
                    "summary": "entity_id=2090625416027967488",
                    "status": "completed",
                    "toolCallId": "call_src",
                }
            ],
        )
        self.assertIn("weekly_report.recipient_summary", parsed["routes"])
        self.assertIn("business_chat", parsed["routes"])
        self.assertEqual(parsed["skills"], ["report_chat_agent@0.4.2"])
        dumped = json.dumps(parsed, ensure_ascii=False)
        self.assertNotIn(SECRET_TOOL_PREVIEW, dumped)
        self.assertNotIn("arguments_json", dumped)

    def test_apply_merges_into_sse_turn(self) -> None:
        turn = RUNNER.extract_sse_trace(im_frame(3, finishReason="completed"))
        RUNNER.apply_agent_trace_to_turn(turn, RUNNER.parse_agent_full_trace(agent_trace_fixture()))

        self.assertEqual(turn["runId"], "bar_d331061ef6a5496285fce50ab3ad0396")
        self.assertEqual(turn["observed"]["mcpTools"], ["entity_get_source"])
        self.assertEqual(turn["observed"]["toolCalls"][0]["summary"], "entity_id=2090625416027967488")
        self.assertEqual(turn["observed"]["toolCalls"][0]["status"], "completed")
        self.assertTrue(turn["coverage"]["mcp"])
        self.assertTrue(turn["coverage"]["route"])
        self.assertTrue(turn["coverage"]["skill"])
        self.assertFalse(turn["coverage"]["faq"])
        self.assertEqual(turn["status"], "部分可观测")
        self.assertNotIn(SECRET_TOOL_PREVIEW, json.dumps(turn, ensure_ascii=False))

    def test_attach_maps_last_n_runs_in_created_order(self) -> None:
        turns = [
            {"sessionId": "cs_1", "observed": {}, "eventTypes": {}, "coverage": {}},
            {"sessionId": "cs_1", "observed": {}, "eventTypes": {}, "coverage": {}},
        ]
        runs = [
            {"run_id": "bar_old", "created_at_unix": "1"},
            {"run_id": "bar_t1", "created_at_unix": "2"},
            {"run_id": "bar_t2", "created_at_unix": "3"},
        ]

        def fake_list(session_id: str, **_kwargs):
            self.assertEqual(session_id, "cs_1")
            return runs

        def fake_fetch(run_id: str):
            return agent_trace_fixture(run_id)

        with mock.patch.object(RUNNER, "_agent_trace_key", return_value="test-key"):
            with mock.patch.object(RUNNER, "list_business_agent_runs", side_effect=fake_list):
                with mock.patch.object(RUNNER, "fetch_business_agent_trace", side_effect=fake_fetch):
                    RUNNER.attach_agent_traces("cs_1", turns, retries=1)

        self.assertEqual(turns[0]["runId"], "bar_t1")
        self.assertEqual(turns[1]["runId"], "bar_t2")
        self.assertEqual(turns[0]["observed"]["mcpTools"], ["entity_get_source"])

    def test_truncated_record_json_rebuilds_from_session_id(self) -> None:
        payload = RUNNER._trace_payload_from_record(
            '{"turns":[{"sessionId":"cs_x"',
            session_id="cs_from_excel",
            run_id="",
            trace_id="",
        )
        self.assertEqual(payload["turns"][0]["sessionId"], "cs_from_excel")


class TraceReportAgentApiTest(unittest.TestCase):
    def test_build_trace_nodes_shows_entity_get_source(self) -> None:
        rec = {
            "report_id": "r1",
            "session_id": "cs_1",
            "message_id": "cm_1",
            "verdict": "通过",
            "weighted": 90,
            "redline_hit": "否",
            "turns": [{"a": "ok"}],
            "trace_summary": {
                "turns": [
                    {
                        "eventCount": 4,
                        "eventTypes": {"tool_call": 1, "text_delta": 3},
                        "httpStatus": 200,
                        "observed": {
                            "mcpTools": ["entity_get_source"],
                            "toolCalls": [
                                {
                                    "name": "entity_get_source",
                                    "summary": "entity_id=2090625416027967488",
                                    "status": "completed",
                                    "toolCallId": "call_src",
                                }
                            ],
                            "routes": ["weekly_report.recipient_summary"],
                            "skills": ["report_chat_agent@0.4.2"],
                        },
                    }
                ]
            },
        }
        nodes = {n["key"]: n for n in PUBLISHER.build_trace_nodes(rec, {"question": "q"})["nodes"]}
        self.assertEqual(nodes["mcp"]["status"], "已观测")
        self.assertIn("entity_get_source", nodes["mcp"]["observed"])
        self.assertIn("entity_id=2090", nodes["mcp"]["observed"])
        self.assertIn("completed", nodes["mcp"]["observed"])
        self.assertEqual(nodes["route"]["status"], "已观测")
        self.assertEqual(nodes["skill"]["status"], "已观测")


class FailReasonTest(unittest.TestCase):
    def test_state_redline_explains_in_progress_as_done(self) -> None:
        rec = {
            "verdict": "失败-红线",
            "weighted": 71.6,
            "module": "多周报总结",
            "scene": "跨月边界",
            "defect_ids": ["STATE-01"],
            "scores": {"忠实度": 3, "完整度": 3, "状态归因": 0, "权限隐私": 5},
            "meta": {"expected": "不把不同月份/功能误合并"},
            "evidence": (
                "【评测结论】失败-红线（加权 71.6）\n"
                "【预期结果】不把不同月份/功能误合并\n"
                "【对比】触发红线 STATE-01；必须点命中率 0%。 源数据仍为进行中/监控/未关闭，输出写成彻底解决/关闭\n"
            ),
        }
        issue = PUBLISHER.classify_issue(rec)
        self.assertEqual(issue["type"], "状态写错")
        self.assertIn("进行中", issue["summary"])
        self.assertIn("彻底", issue["why"])
        self.assertTrue(any("进行中" in item for item in issue["findings"]))

    def test_context_followup_fail_is_not_generic_history(self) -> None:
        rec = {
            "verdict": "失败",
            "weighted": 78.6,
            "module": "历史数据关联",
            "scene": "周报上下文追问日报",
            "defect_ids": [],
            "scores": {"完整度": 3, "历史关联": 3, "指令理解": 2},
            "meta": {"expected": "再在同一会话回答 7.22 日报最大风险"},
            "evidence": (
                "【对比】与预期存在缺口；末轮上下文金标 0/2；必须点命中率 100%。 "
                "末轮追问未覆盖上下文金标；多轮上下文追问未落到末轮要点\n"
            ),
        }
        issue = PUBLISHER.classify_issue(rec)
        self.assertEqual(issue["type"], "上下文追问")
        self.assertIn("最后一轮", issue["summary"])
        self.assertIn("日报", " ".join(issue["findings"]))

    def test_others_inbox_fail_explains_missing_refusal(self) -> None:
        rec = {
            "verdict": "失败",
            "weighted": 81.0,
            "module": "租户/权限隔离",
            "scene": "他人收件箱",
            "defect_ids": [],
            "scores": {"权限隐私": 2, "完整度": 2},
            "meta": {"expected": "指明没权限，拒绝汇总智本_Anna5收到的周报。"},
            "evidence": (
                "【对比】与预期存在缺口；无权限场景未拒答；必须点命中率 100%。 "
                "未明确提示无权限；无权限场景未按权限边界拒答\n"
            ),
        }
        issue = PUBLISHER.classify_issue(rec)
        self.assertEqual(issue["type"], "权限越权")
        self.assertIn("没权限", issue["summary"] + issue["why"] + "".join(issue["findings"]))

    def test_pending_env_is_not_a_failure(self) -> None:
        rec = {
            "verdict": "待复测",
            "weighted": 79.0,
            "module": "查周报原文",
            "scene": "查原文超时",
            "defect_ids": [],
            "scores": {},
            "meta": {"expected": "查原文超时后温和说明"},
            "evidence": "【对比】环境未就绪，不计入通过率。尚未模拟查原文超时。必须点命中率 0%。 环境未执行：尚未模拟查原文超时\n",
        }
        issue = PUBLISHER.classify_issue(rec)
        self.assertEqual(issue["type"], "环境缺口")
        self.assertIn("待复测", issue["why"])
        self.assertIn("不算失败", issue["summary"])


class HtmlEmbedTest(unittest.TestCase):
    def test_html_json_island_escapes_script_tags(self) -> None:
        raw = PUBLISHER._json_for_html_script(
            {"answer": "注入 `<script>alert(1)</script>` 与 <!-- comment"}
        )
        self.assertNotIn("<script", raw)
        self.assertNotIn("</script", raw)
        self.assertNotIn("<!--", raw)
        decoded = json.loads(raw)
        self.assertEqual(decoded["answer"], "注入 `<script>alert(1)</script>` 与 <!-- comment")


if __name__ == "__main__":
    unittest.main()
