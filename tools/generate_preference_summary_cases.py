#!/usr/bin/env python3
"""偏好场景配套单篇总结 + 单篇汇报偏好追问用例。

对应 Agent 用例 WA-031/032/034/035：
  WS-022 按项目分类
  WS-023 详细版
  WS-024 按风险
  WS-025 删除偏好后默认结构
再加：
  WA-115 偏好仅针对某篇汇报有效
  WS-026 其他汇报仍保持历史最后一次全局偏好（按风险），不受单篇偏好影响

本脚本只写 CSV / Excel / catalog。执行时 runner 会在对应 Agent 用例之后立刻跑这些单篇总结：
只发报并轮询 /reports/detail，用 format_ai_summary 评接收人摘要，不走追问 Agent。
"""

from __future__ import annotations

from _paths import CATALOG_PATH
import csv
import json
from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from eval_engine import (
    PREF_DEFAULT_MARKER,
    PREF_DETAIL_MARKER,
    PREF_RISK_MARKER,
    PREF_STRUCT_MARKER,
    SCOPED_PREF_SCENE,
)

CSV_PATH = report_data_csv()
from env_config import test_case_xlsx_path

XLSX_PATH = test_case_xlsx_path()

FIELDNAMES = ["日期", "发送人", "接收人", "周报类型", "周报内容", "AI总结内容", "reportId"]
CASE_HEADER_ROW = 2
RECORD_HEADER_ROW = 2
SENDER = "智本_Anna5"
RECEIVER = "智本_anrou"
SUMMARY_MODULE = "单篇总结"


def weekly_struct() -> dict[str, str]:
    body = (
        "本周工作：\n"
        f"本周并行推进两个项目，评测标记 {PREF_STRUCT_MARKER}。\n"
        "【项目】澜石网关（对外代号 LANSHI-GW-2208）：周一把超时切片从 180ms 收到 120ms，"
        "周三压测 20 分钟 P95 落到 92ms。灰度 12%，未全量。接口负责人柳衡。\n"
        "【项目】青渚对账（对外代号 QINGZHU-RECON-7712）：周二核出 3 笔错账，金额分别是 "
        "860、1240、390 元，周四只关了 860 那笔，另外两笔未关。对账窗口仍是 41 分钟。\n"
        "风险：澜石网关 92ms 是压测峰值不是日常均值；青渚对账两笔错账未关闭，不能写成已轧平。\n"
        "下周工作：\n"
        "澜石网关灰度提到 20%；青渚对账关掉剩余 2 笔错账。\n"
        "需要协调和帮助：\n"
        "无"
    )
    return {
        "日期": "2026/03/09-03/13",
        "发送人": SENDER,
        "接收人": RECEIVER,
        "周报类型": "周报",
        "周报内容": body,
        "AI总结内容": "",
        "reportId": "",
    }


def weekly_detail() -> dict[str, str]:
    body = (
        "本周工作：\n"
        f"梧北配置专项，评测标记 {PREF_DETAIL_MARKER}。项目代号 WUBEI-CFG-3301。\n"
        "周一梳理配置项 126 条，其中 18 条仍是手工开关。预算口径 318420 元，未追加。\n"
        "周二压测网关 P95 从 110ms 降到 64ms，错误率 0.52%，灰度 18%，未全量。\n"
        "周三回滚窗口定为 45 分钟，演练只跑了一次，没有第二次。\n"
        "周四柳衡核对 126 条清单，确认 18 条手工开关本周不改成自动。\n"
        "周五把压测报告归档，P95 保持 64ms，不宣称已经低于 40ms。\n"
        "风险：18% 灰度未扩大；45 分钟回滚窗口只演练一次；318420 预算里的专线扩容单未批。\n"
        "下周工作：\n"
        "继续梧北配置第二阶段，灰度提到 30%，并把剩余 18 条手工开关排期。\n"
        "需要协调和帮助：\n"
        "无"
    )
    return {
        "日期": "2026/03/16-03/20",
        "发送人": SENDER,
        "接收人": RECEIVER,
        "周报类型": "周报",
        "周报内容": body,
        "AI总结内容": "",
        "reportId": "",
    }


def weekly_risk() -> dict[str, str]:
    body = (
        "本周工作：\n"
        f"本周两个项目都有进展，但风险优先，评测标记 {PREF_RISK_MARKER}。\n"
        "【赤岸发布】版本包已打出，灰度名单写了 10%，发布窗口定在周五夜。灰度回滚方案还没批准，"
        "不能写成已上线。\n"
        "【墨桐监控】新增 4 个告警面板，覆盖超时和错误率。日志缺口仍未补：callerDept 字段缺失，"
        "周五对账时有 11 条调用无法归因。\n"
        "风险：赤岸发布灰度回滚未批；墨桐监控日志缺口未补；不要把未上线写成已上线。\n"
        "下周工作：\n"
        "先把灰度回滚批下来，再补日志缺口。\n"
        "需要协调和帮助：\n"
        "需要审批灰度回滚。"
    )
    return {
        "日期": "2026/03/23-03/27",
        "发送人": SENDER,
        "接收人": RECEIVER,
        "周报类型": "周报",
        "周报内容": body,
        "AI总结内容": "",
        "reportId": "",
    }


def weekly_default() -> dict[str, str]:
    body = (
        "本周工作：\n"
        f"岑南值班周报，评测标记 {PREF_DEFAULT_MARKER}。\n"
        "周一到周五完成机房巡检 17 项，其中备用电源测试未做完，剩 2 项放到下周。\n"
        "告警演练跑了 1 次，没有升级到全员。\n"
        "风险：备用电源测试未完成，不能写成 17 项全部通过。\n"
        "下周工作：\n"
        "补完剩余 2 项备用电源测试。\n"
        "需要协调和帮助：\n"
        "无"
    )
    return {
        "日期": "2026/03/30-04/03",
        "发送人": SENDER,
        "接收人": RECEIVER,
        "周报类型": "周报",
        "周报内容": body,
        "AI总结内容": "",
        "reportId": "",
    }


WEEKLY_ROWS = (weekly_struct, weekly_detail, weekly_risk, weekly_default)


def case_specs() -> list[dict[str, str]]:
    return [
        {
            "用例ID": "WS-022",
            "一级模块": SUMMARY_MODULE,
            "场景": "偏好-按项目分类",
            "优先级": "P1",
            "优先级说明": "对应 WA-031。设置「以后按项目分类」后，接收人单篇总结应分项目成段",
            "测试输入/用户话术": "总结这篇周报",
            "前置条件": (
                f"对应 WA-031。先由 {RECEIVER} 记住以后按项目分类，再发本周报并评接收人 AI 总结。"
                f"marker={PREF_STRUCT_MARKER}。{SENDER} 2026/03/09-03/13 → {RECEIVER}。"
            ),
            "执行步骤": (
                "1. 先执行 WA-031，由追问 Agent 记住按项目分类；\n"
                "2. 本用例不走追问，提交澜石网关/青渚对账周报；\n"
                "3. 接收人轮询 /reports/detail，用 format_ai_summary 评是否按项目分段。"
            ),
            "必须满足": "澜石网关；青渚对账",
            "禁止出现": "霜灯索引；潮汐对账；999万",
            "预期结果": "单篇总结按项目分类覆盖澜石网关和青渚对账，与已设置的结构偏好一致。",
            "评测维度": "指令理解|忠实度|完整度",
            "Gold Case": "是",
            "红线用例": "否",
            "建议方式": "自动+人工",
            "需求来源": "单篇总结/偏好-WA-031",
            "expect_tools": "",
        },
        {
            "用例ID": "WS-023",
            "一级模块": SUMMARY_MODULE,
            "场景": "偏好-详细版",
            "优先级": "P1",
            "优先级说明": "对应 WA-032。设置详细版后，单篇总结应展开关键数字，不能只写两三句",
            "测试输入/用户话术": "总结这篇周报",
            "前置条件": (
                f"对应 WA-032。先由 {RECEIVER} 记住默认详细版，再发本周报并评接收人 AI 总结。"
                f"marker={PREF_DETAIL_MARKER}。{SENDER} 2026/03/16-03/20 → {RECEIVER}。"
            ),
            "执行步骤": (
                "1. 先执行 WA-032，由追问 Agent 记住详细版；\n"
                "2. 本用例不走追问，提交梧北配置周报；\n"
                "3. 接收人轮询 /reports/detail，用 format_ai_summary 评是否展开 318420、64ms、126 条。"
            ),
            "必须满足": "318420；64ms；126 条",
            "禁止出现": "霜灯索引；潮汐对账；已经低于 40ms",
            "预期结果": "单篇总结按详细版展开梧北配置事实，不把 P95 写成已低于 40ms。",
            "评测维度": "指令理解|完整度|忠实度",
            "Gold Case": "是",
            "红线用例": "否",
            "建议方式": "自动+人工",
            "需求来源": "单篇总结/偏好-WA-032",
            "expect_tools": "",
        },
        {
            "用例ID": "WS-024",
            "一级模块": SUMMARY_MODULE,
            "场景": "偏好-按风险",
            "优先级": "P1",
            "优先级说明": "对应 WA-034。把结构偏好改为按风险后，单篇总结应风险优先",
            "测试输入/用户话术": "总结这篇周报",
            "前置条件": (
                f"对应 WA-034。先由 {RECEIVER} 把偏好改为按风险，再发本周报并评接收人 AI 总结。"
                f"marker={PREF_RISK_MARKER}。{SENDER} 2026/03/23-03/27 → {RECEIVER}。"
                "本篇也是 WS-026 的「历史最后一次全局偏好」对照周报。"
            ),
            "执行步骤": (
                "1. 先执行 WA-034，由追问 Agent 把偏好改为按风险；\n"
                "2. 本用例不走追问，提交赤岸发布/墨桐监控周报；\n"
                "3. 接收人轮询 /reports/detail，用 format_ai_summary 评灰度回滚未批和日志缺口。"
            ),
            "必须满足": "灰度回滚；日志缺口",
            "禁止出现": "澜石网关；青渚对账；已经上线",
            "预期结果": "单篇总结按风险组织，写出灰度回滚未批和日志缺口，不能写成已上线。",
            "评测维度": "指令理解|风险趋势|忠实度",
            "Gold Case": "是",
            "红线用例": "否",
            "建议方式": "自动+人工",
            "需求来源": "单篇总结/偏好-WA-034",
            "expect_tools": "",
        },
        {
            "用例ID": "WS-025",
            "一级模块": SUMMARY_MODULE,
            "场景": "偏好-删除后默认",
            "优先级": "P1",
            "优先级说明": "对应 WA-035。忘记全部周报偏好后，单篇总结应回到默认结构",
            "测试输入/用户话术": "总结这篇周报",
            "前置条件": (
                f"对应 WA-035。先由 {RECEIVER} 忘记所有周报偏好，再发本周报并评接收人 AI 总结。"
                f"marker={PREF_DEFAULT_MARKER}。{SENDER} 2026/03/30-04/03 → {RECEIVER}。"
            ),
            "执行步骤": (
                "1. 先执行 WA-035，由追问 Agent 忘记所有周报偏好；\n"
                "2. 本用例不走追问，提交岑南值班周报；\n"
                "3. 接收人轮询 /reports/detail，用 format_ai_summary 评是否回到默认结构。"
            ),
            "必须满足": "岑南值班；17 项",
            "禁止出现": "澜石网关；青渚对账；999万",
            "预期结果": "删除偏好后单篇总结回到默认结构，保留巡检 17 项和备用电源未完成。",
            "评测维度": "指令理解|忠实度|完整度",
            "Gold Case": "是",
            "红线用例": "否",
            "建议方式": "自动+人工",
            "需求来源": "单篇总结/偏好-WA-035",
            "expect_tools": "",
        },
        {
            "用例ID": "WA-115",
            "一级模块": "用户习惯记忆",
            "场景": SCOPED_PREF_SCENE,
            "优先级": "P1",
            "优先级说明": "偏好只对指定周报有效；不要改其他周报的全局偏好",
            "测试输入/用户话术": (
                "请记住：只对当前附带的这篇周报按项目分类整理"
                "（澜石网关 / 青渚对账）；不要改其他周报的全局偏好。"
            ),
            "前置条件": (
                f"追问账号={RECEIVER}。先完成 WS-024 的全局「按风险」偏好。"
                f"本用例只绑定澜石/青渚周报。marker={PREF_STRUCT_MARKER}。"
                "新会话追问「请总结这篇周报」，不得改口总结日历本周。"
            ),
            "执行步骤": (
                "1. 附带澜石/青渚周报，记住仅本篇按项目分类；\n"
                "2. 新会话仍附带该周报，问「请总结这篇周报，不要总结日历上的本周」；\n"
                "3. 输出应按项目分段，且不得把偏好应用到其他周报。"
            ),
            "必须满足": "澜石网关；青渚对账",
            "禁止出现": "赤岸发布；墨桐监控；霜灯索引",
            "预期结果": "仅对附带的澜石/青渚周报按项目分类总结，不引用其他汇报，也不改全局偏好。",
            "评测维度": "记忆准确|指令遵循|忠实度",
            "Gold Case": "是",
            "红线用例": "否",
            "建议方式": "自动+人工",
            "需求来源": "追问/单篇汇报偏好",
            "expect_tools": '{"required":["memory_settle"],"allow_settle":true}',
        },
        {
            "用例ID": "WS-026",
            "一级模块": SUMMARY_MODULE,
            "场景": "偏好-他篇保持全局",
            "优先级": "P1",
            "优先级说明": "WA-115 单篇偏好之后，赤岸/墨桐周报仍应保持 WS-024 最后一次全局「按风险」",
            "测试输入/用户话术": "总结这篇周报",
            "前置条件": (
                "评接收人 AI 总结，对象是 WS-024 那篇赤岸/墨桐周报，不重新设置偏好、不重发。"
                f"marker={PREF_RISK_MARKER}。应保持历史最后一次全局偏好（按风险），"
                "不受 WA-115 单篇按项目分类影响。"
            ),
            "执行步骤": (
                "1. 确认 WA-115 已对澜石/青渚周报设置单篇偏好；\n"
                "2. 本用例不走追问、不重发，只轮询赤岸/墨桐周报；\n"
                "3. 用 format_ai_summary 评仍按风险组织，且不得出现澜石网关/青渚对账。"
            ),
            "必须满足": "灰度回滚；日志缺口",
            "禁止出现": "澜石网关；青渚对账；LANSHI-GW-2208",
            "预期结果": "其他汇报的单篇总结保持历史最后一次全局按风险偏好，不受单篇偏好设置影响。",
            "评测维度": "指令理解|风险趋势|忠实度",
            "Gold Case": "是",
            "红线用例": "否",
            "建议方式": "自动+人工",
            "需求来源": "单篇总结/偏好隔离",
            "expect_tools": "",
        },
        {
            "用例ID": "WS-027",
            "一级模块": SUMMARY_MODULE,
            "场景": "偏好一致性对照",
            "优先级": "P0",
            "优先级说明": "单篇总结评测：先追问「我现在的总结偏好是什么」，再对照 format_ai_summary 是否一致",
            "测试输入/用户话术": "总结这篇周报",
            "前置条件": (
                f"对应 WA-031 / WS-022。追问账号={RECEIVER}。"
                f"先对附带周报追问「我现在的总结偏好是什么」，再评接收人 format_ai_summary。"
                f"marker={PREF_STRUCT_MARKER}。{SENDER} 2026/03/09-03/13 → {RECEIVER}。"
                "实际总结结构必须与用户自述偏好一致（如按项目分类）。"
            ),
            "执行步骤": (
                "1. 确认 WA-031 已写入按项目分类偏好，并完成 WS-022 发报；\n"
                "2. 附带澜石/青渚周报，追问「我现在的总结偏好是什么」；\n"
                "3. 轮询 /reports/detail，用 format_ai_summary 取实际总结；\n"
                "4. 对照首轮偏好陈述与总结结构是否一致。"
            ),
            "必须满足": "澜石网关；青渚对账；总结偏好",
            "禁止出现": "赤岸发布；墨桐监控；已经上线",
            "预期结果": (
                "首轮能说出当前总结偏好；"
                "format_ai_summary 结果与该偏好一致（例如自述按项目，则摘要按项目分段覆盖澜石网关与青渚对账）。"
            ),
            "评测维度": "指令理解|忠实度|完整度",
            "Gold Case": "是",
            "红线用例": "否",
            "建议方式": "自动+人工",
            "需求来源": "单篇总结/偏好一致性对照",
            "expect_tools": "",
        },
    ]


def _sheet_headers(ws: Worksheet, header_row: int) -> list[str]:
    return [str(c.value or "").strip() for c in next(ws.iter_rows(min_row=header_row, max_row=header_row))]


def _copy_row_style(ws: Worksheet, src_row: int, dst_row: int, max_col: int) -> None:
    for col in range(1, max_col + 1):
        src = ws.cell(src_row, col)
        dst = ws.cell(dst_row, col)
        if src.has_style:
            dst.font = copy(src.font)
            dst.border = copy(src.border)
            dst.fill = copy(src.fill)
            dst.number_format = src.number_format
            dst.protection = copy(src.protection)
            dst.alignment = copy(src.alignment)


def append_csv(path: Path = CSV_PATH) -> int:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    added = 0
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="ignore")
        for factory in WEEKLY_ROWS:
            row = factory()
            marker = next(
                token
                for token in (
                    PREF_STRUCT_MARKER,
                    PREF_DETAIL_MARKER,
                    PREF_RISK_MARKER,
                    PREF_DEFAULT_MARKER,
                )
                if token in row["周报内容"]
            )
            if marker in existing:
                print(f"[SKIP] report_data.csv 已含 {marker}")
                continue
            writer.writerow(row)
            existing += row["周报内容"]
            added += 1
            print(f"[CSV] {row['日期']} {marker}")
    print(f"[WRITE] appended {added} row(s) -> {path}")
    return added


def write_xlsx(path: Path = XLSX_PATH) -> None:
    specs = case_specs()
    wb = load_workbook(path)
    case_ws = wb["用例库"]
    record_ws = wb["执行记录"]
    case_headers = _sheet_headers(case_ws, CASE_HEADER_ROW)
    record_headers = _sheet_headers(record_ws, RECORD_HEADER_ROW)
    case_idx = {name: i + 1 for i, name in enumerate(case_headers) if name}
    case_rows: dict[str, int] = {}
    last_case_row = CASE_HEADER_ROW
    for row in range(CASE_HEADER_ROW + 1, case_ws.max_row + 1):
        cid = str(case_ws.cell(row, case_idx["用例ID"]).value or "").strip()
        if cid:
            case_rows[cid] = row
            last_case_row = row
    added = 0
    updated = 0
    for spec in specs:
        cid = spec["用例ID"]
        if cid in case_rows:
            target = case_rows[cid]
            updated += 1
            print(f"[UPDATE] {cid} {spec['场景']}")
        else:
            last_case_row += 1
            _copy_row_style(case_ws, last_case_row - 1, last_case_row, len(case_headers))
            target = last_case_row
            case_rows[cid] = target
            added += 1
            print(f"[CASE] {cid} {spec['场景']}")
        for key, value in spec.items():
            if key in case_idx:
                case_ws.cell(target, case_idx[key], value=value)
    if "用例ID" in record_headers:
        rec_case_col = record_headers.index("用例ID") + 1
        rec_ids = {
            str(record_ws.cell(row, rec_case_col).value or "").strip()
            for row in range(RECORD_HEADER_ROW + 1, record_ws.max_row + 1)
        }
        last_rec = RECORD_HEADER_ROW
        for row in range(RECORD_HEADER_ROW + 1, record_ws.max_row + 1):
            if str(record_ws.cell(row, rec_case_col).value or "").strip():
                last_rec = row
        for spec in specs:
            cid = spec["用例ID"]
            if cid in rec_ids:
                continue
            last_rec += 1
            _copy_row_style(record_ws, last_rec - 1, last_rec, len(record_headers))
            record_ws.cell(last_rec, rec_case_col, value=cid)
    wb.save(path)
    print(f"[XLSX] added {added} updated {updated} -> {path.name}")


def write_catalog(path: Path = CATALOG_PATH) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    unlocks = data.setdefault("unlocks", {})
    for spec in case_specs():
        unlocks[spec["用例ID"]] = spec["前置条件"]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[CATALOG] wrote {len(case_specs())} unlocks")


def main() -> int:
    append_csv()
    write_xlsx()
    write_catalog()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
