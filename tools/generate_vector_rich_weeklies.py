#!/usr/bin/env python3
"""生成两篇 ≥10000 汉字、带检索探针的周报，追加到 report_data.csv。"""

from __future__ import annotations

import csv
from pathlib import Path

from _paths import FIXTURES_DIR, ROLE_PERIOD_PEOPLE_PATH  # noqa: E402
from env_config import report_data_csv  # noqa: E402

CSV_PATH = report_data_csv()
FROST_CANARY = "VEC-CANARY-FROST-20260824-M9K4"
TIDE_CANARY = "VEC-CANARY-TIDE-20260824-P2N8"
MIN_CJK = 10000


def cjk_count(text: str) -> int:
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def _expand(paragraphs: list[str], min_chars: int, filler_factory) -> str:
    body = "\n".join(paragraphs)
    idx = 0
    while cjk_count(body) < min_chars:
        body += "\n" + filler_factory(idx)
        idx += 1
        if idx > 400:
            break
    return body


def frost_weekly() -> str:
    facts = [
        "本周工作：",
        f"【数据集标记】{VEC_RICH_MARKER}。本篇只服务向量匹配 / 关键词检索评测，正文含可检索探针。",
        "【项目】霜灯索引（对外代号 FROST-LANTERN-IDX）在青岚实验舱完成第一阶段召回改造。",
        f"【探针】{FROST_CANARY}。负责人岑栖梧。本周专项预算 4182650 元，不得与潮汐对账项目串写。",
        "【关键指标】召回@10 从 0.781 提到 0.917；在线检索 QPS 从 312 提到 1480；P99 从 410ms 降到 163ms。",
        "【组件】青霜分词器已切到词典 1.8；夜莺召回闸负责超时熔断；琥珀重排器 AmberRerank v3.2 负责二段排序。",
        "周一：青岚实验舱把倒排拉链从 48 路扩到 96 路。原先单切片高峰只能撑 310 QPS，扩路后压测 20 分钟稳定在 1480 QPS。分词侧发现「索引」和「检索」会被切成单字，青霜分词器补了 126 条领域词，回归集 400 条查询无新增切碎。",
        "周二：对照金标 2000 条查询重跑。旧链路召回@10=0.781，新链路 0.917。失败样本 166 条里，有 41 条是同名项目跨空间误召，已在过滤里加 projectId。其余 125 条先记入夜莺召回闸观察，不宣称已修好。",
        "周三：夜莺召回闸熔断阈值改成了 86ms。原阈值 140ms 时，慢查询会把整批 32 路召回拖到 400ms 以上。改到 86ms 后，超时切片改走缓存兜底，P99 从 410ms 落到 163ms。缓存命中率 61%，还不能当主召回。",
        "周四：琥珀重排器 AmberRerank v3.2 上线。特征从 18 维扩到 41 维，增加「是否同一汇报人」「是否同一周期」两项。离线 NDCG@5 从 0.62 到 0.71。线上只灰度 8% 流量，未全量。",
        "周五：把 FROST-LANTERN-IDX 的审计日志接到青岚实验舱。每条检索写 queryHash、召回集合大小、熔断次数。本周熔断 327 次，主要来自超长查询。岑栖梧要求下周把超长查询截断规则写进文档，本周未完成。",
        "风险：召回@10=0.917 只在 2000 条金标上成立，生产长尾查询还没复测；1480 QPS 是压测峰值不是日常均值；AmberRerank v3.2 仍在 8% 灰度；夜莺召回闸 86ms 可能导致个别相关切片被丢。",
        "未完成：多语言查询、跨租户过滤回归、全量重排、以及把 4182650 预算里的 GPU 扩容单走完。",
    ]
    themes = [
        "青霜分词器对复合专名的切分",
        "夜莺召回闸在突发流量下的排队",
        "琥珀重排器特征缺失时的兜底",
        "青岚实验舱磁盘抖动对倒排加载的影响",
        "FROST-LANTERN-IDX 灰度开关的回滚路径",
        "召回集合去重与同名任务误合并",
        "queryHash 冲突和审计补齐",
        "缓存兜底与主召回结果混排",
        "P99 毛刺和 GC 停顿",
        "领域词典与用户自定义别名",
    ]
    details = [
        "当天把相关日志按小时切片核对，确认没有把潮汐对账或银杏轧差的数据写进霜灯索引索引库。",
        "评测同学用 50 条手工查询复查，命中的都是向量检索主题，没有串到对账数字。",
        "和前端约定检索框占位符改成「搜周报关键词」，避免用户以为这是生成周报入口。",
        "对超时切片只返回缓存标题，不返回未完成重排的摘要，以免看起来像已完成。",
        "文档里写明 0.917 是金标召回@10，不是生产保证值。",
        "QPS 1480 标注为压测峰值，监控看板单独列日常均值。",
        "86ms 熔断只作用于夜莺召回闸，不影响琥珀重排器自己的 120ms 超时。",
        "岑栖梧在评审里强调：没看原文不要回答数字。",
        "本篇正文后半是为长文检索准备的，探针仍是霜灯索引与 FROST-LANTERN-IDX。",
        "若检索只扫标题，应仍能看到霜灯索引；若能扫正文，应能看到夜莺召回闸 86ms。",
    ]

    def filler(i: int) -> str:
        theme = themes[i % len(themes)]
        detail = details[i % len(details)]
        day = ["周一", "周二", "周三", "周四", "周五"][i % 5]
        return (
            f"{day}补充记录 {i + 1:03d}：围绕{theme}继续联调。"
            f"{detail}当前霜灯索引仍在青岚实验舱小流量验证，"
            f"召回@10 金标值保持 0.917，压测峰值 QPS 仍记 1480。"
            f"AmberRerank v3.2 灰度 8% 未扩大。预算口径 4182650 元不变。"
            f"标记 {FROST_CANARY}。不要把本篇写成潮汐对账或银杏轧差。"
        )

    body = _expand(facts, MIN_CJK - 80, filler)
    tail = (
        "下周工作：\n"
        "继续霜灯索引第二阶段：长尾查询复测、多语言分词对照、夜莺召回闸 86ms 是否误杀相关切片、"
        "AmberRerank v3.2 灰度从 8% 提到 20%。预算仍按 4182650 元，负责人仍是岑栖梧。\n"
        "需要协调和帮助：\n"
        "需要检索评测同学用「霜灯索引」「FROST-LANTERN-IDX」「青岚实验舱」「夜莺召回闸」做关键词检索，"
        f"确认能命中本篇而不是对账周报。探针 {FROST_CANARY}。"
    )
    return body.rstrip() + "\n" + tail


def tide_weekly() -> str:
    facts = [
        "本周工作：",
        f"【数据集标记】{VEC_RICH_MARKER}。本篇只服务向量匹配 / 关键词检索评测，主题是资金对账，不是向量检索。",
        "【项目】潮汐对账（对外代号 TIDE-LEDGER-CLR）。核心模块叫银杏轧差，日终管道叫子午清分。",
        f"【探针】{TIDE_CANARY}。负责人裴疏影。本周专项预算 2654190 元，不得与霜灯索引项目串写。",
        "【关键指标】错账率从 1.82% 降到 0.37%；单批对账窗口从 91 分钟降到 47 分钟；未达账悬挂从 126 笔降到 18 笔。",
        "【组件】银杏轧差负责多边净额；子午清分负责 23:30 日终切批；梧桐轧账闸负责通道超时。",
        "周一：把三家渠道的流水对齐到银杏轧差。原先按商户号汇总，同名商户会轧到一起。改成商户号+渠道号后，错账样本从 44 笔降到 9 笔。裴疏影要求保留冲突双方，不要单边判已平账。",
        "周二：子午清分把切批从 00:10 提前到 23:30，避开渠道对账高峰。窗口从 91 分钟降到 47 分钟。有 3 笔跨日退款被切到次日，已标记待确认，不写成本周完成。",
        "周三：梧桐轧账闸的静默超时改成了 19 秒。原先 45 秒，通道卡住时整批对账跟着停。改到 19 秒后，超时单据进悬挂队列，错账率当天降到 0.37%。悬挂队列还要人工抽检，不能当自动平账。",
        "周四：对 18 笔未达账做了原因分类：7 笔渠道延迟、6 笔币种精度、5 笔退款时序。精度问题准备改成分单位存储，本周只出方案未上线。",
        "周五：TIDE-LEDGER-CLR 审计字段补了 batchId、nettingKey、timeoutCount。本周超时 86 次，全部来自同一家渠道。裴疏影让渠道侧下周给说明，本周没有结论。",
        "风险：0.37% 是本周工作日均值，不含周末补跑；47 分钟窗口依赖 23:30 切批，假期会漂移；19 秒超时可能把慢但正确的单据打进悬挂；2654190 预算里的对账专线还没采购。",
        "未完成：币种分单位改造、周末补跑、渠道说明、以及和霜灯索引完全无关的任何检索指标。",
    ]
    themes = [
        "银杏轧差的多边净额计算",
        "子午清分假期切批漂移",
        "梧桐轧账闸超时单据悬挂",
        "渠道延迟和退款时序",
        "币种精度与分单位存储",
        "batchId 冲突",
        "未达账人工抽检",
        "对账窗口监控口径",
        "同名商户误轧",
        "TIDE-LEDGER-CLR 灰度回滚",
    ]
    details = [
        "当天核对流水时明确排除霜灯索引、青岚实验舱、夜莺召回闸这些检索项目字段。",
        "评测同学若搜「银杏轧差」应落到本篇，而不是召回@10 或 QPS。",
        "错账率 0.37% 不要改写成已经清零。",
        "47 分钟是工作日窗口，不是承诺 SLA。",
        "19 秒只作用于梧桐轧账闸，不影响子午清分自己的 8 分钟批次超时。",
        "裴疏影强调：没看对账原单不要回答笔数。",
        "本篇后半是为长文检索准备的，探针仍是潮汐对账与银杏轧差。",
        "如果检索把 AmberRerank 或 0.917 写进本篇摘要，视为串库。",
        "预算 2654190 元与霜灯索引的 4182650 元不得相加后对外口径。",
        "TIDE-LEDGER-CLR 不提供向量检索能力，只提供对账结果。",
    ]

    def filler(i: int) -> str:
        theme = themes[i % len(themes)]
        detail = details[i % len(details)]
        day = ["周一", "周二", "周三", "周四", "周五"][i % 5]
        return (
            f"{day}补充记录 {i + 1:03d}：围绕{theme}继续对账。"
            f"{detail}当前潮汐对账仍由银杏轧差与子午清分支撑，"
            f"错账率维持 0.37%，对账窗口维持 47 分钟。"
            f"梧桐轧账闸静默超时 19 秒未再改。预算口径 2654190 元不变。"
            f"标记 {TIDE_CANARY}。不要把本篇写成霜灯索引或青岚实验舱。"
        )

    body = _expand(facts, MIN_CJK - 80, filler)
    tail = (
        "下周工作：\n"
        "继续潮汐对账第二阶段：周末补跑、币种分单位、渠道延迟说明、梧桐轧账闸 19 秒是否误杀慢单。"
        "预算仍按 2654190 元，负责人仍是裴疏影。\n"
        "需要协调和帮助：\n"
        "需要检索评测同学用「潮汐对账」「银杏轧差」「子午清分」「梧桐轧账闸」做关键词检索，"
        f"确认能命中本篇而不是霜灯索引。探针 {TIDE_CANARY}。"
    )
    return body.rstrip() + "\n" + tail


def reports() -> list[dict[str, str]]:
    frost = frost_weekly()
    tide = tide_weekly()
    return [
        {
            "日期": "2026/08/10-08/14",
            "发送人": "智本_Anna5",
            "接收人": "智本_anrou",
            "周报类型": "周报",
            "周报内容": frost,
            "AI总结内容": "",
            "reportId": "",
        },
        {
            "日期": "2026/08/17-08/21",
            "发送人": "智本_Anna7",
            "接收人": "智本_anrou",
            "周报类型": "周报",
            "周报内容": tide,
            "AI总结内容": "",
            "reportId": "",
        },
    ]


def append_csv(path: Path = CSV_PATH) -> list[dict[str, str]]:
    fieldnames = ["日期", "发送人", "接收人", "周报类型", "周报内容", "AI总结内容", "reportId"]
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if FROST_CANARY in existing and TIDE_CANARY in existing:
        print("[SKIP] report_data.csv 已含霜灯/潮汐长周报")
        return []
    rows = reports()
    for row in rows:
        n = cjk_count(row["周报内容"])
        if n < MIN_CJK:
            raise RuntimeError(f"{row['日期']} 汉字数 {n} < {MIN_CJK}")
        print(f"[OK] {row['发送人']} {row['日期']} cjk={n}")
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        for row in rows:
            writer.writerow(row)
    print(f"[WRITE] appended {len(rows)} rows -> {path}")
    return rows


if __name__ == "__main__":
    append_csv()
