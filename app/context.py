"""O1/O2/O3/O5：渠道对照、条款级覆盖、证据缺口、决策后果与时效状态。

设计约束（为「同一基准集复跑不回退」服务）：
- 全部是**附加区块**，只在显式触发词下追加到答案末尾；
- 不改变主答案、引用编号与 conflicts 结构；
- 只使用 `data/channels.json` / `data/coverage.json` 里已核实的一手原文措辞，
  不推断、不编造群内内容、不虚构联系人、不写未核实的金额或时间。
"""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEADLINE = datetime(2026, 11, 18, 15, 0)  # 官方通知 + 提交表单双重确认


def _load(rel):
    path = ROOT / rel
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


CHANNELS = _load("data/channels.json")
COVERAGE = _load("data/coverage.json")

COVERAGE_TRIGGERS = ("补充通知", "调整通知", "以本", "以哪", "以哪个为准",
                     "条款", "沿用", "哪些变了", "还有效吗", "覆盖")
CHANNEL_TRIGGERS = ("渠道", "信哪", "以哪个为准", "以哪份为准", "不一致",
                    "哪个为准", "官方通知和", "入口在哪", "链接用哪个")
RISK_TRIGGERS = ("后果", "风险", "错过", "逾期", "来不及", "还来得及", "会怎样")

GAP_HINTS = {
    "检索片段与断言资产均未覆盖问题的核心对象": (
        "公开网页未收录该事项；多份高校通知明示「后续通知将在群内发布」，"
        "请核对本校报名群 / 教务处 / 牵头部门联系人，不要以非官方转述为准。"
    ),
    "资料只提到缴费要求，未给出金额": (
        "赛事官方语料只写「需完成缴费」，未公开金额；请登录赛事个人中心或咨询组委会核对，"
        "不要采用二手整理稿中的价格。"
    ),
}


def channel_of(doc_id):
    return CHANNELS.get("docs", {}).get(doc_id, {})


def _level_label(key):
    for level in CHANNELS.get("levels", []):
        if level["key"] == key:
            return level["label"]
    return key


def channel_table(question):
    """O2：同一事项在各渠道的写法与效力层级（仅触发词命中时输出）。"""
    if not any(w in question for w in CHANNEL_TRIGGERS):
        return ""
    cases = [
        c for c in CHANNELS.get("cross_channel_cases", [])
        if any(word in question for word in c["topic"].split()) or "不一致" in question or "哪个为准" in question
    ]
    if not cases:
        return ""
    lines = ["【渠道对照】同一事项在不同官方渠道的写法（按效力层级，不擅自合并）："]
    for case in cases[:3]:
        lines.append(f"- 事项：{case['topic']}（行动影响：{case['action_impact']}）")
        for item in case["values"]:
            label = _level_label(item["channel"])
            lines.append(f"  · [{label}] {item['value']}（{item['doc_id']}）")
        lines.append(f"  裁决说明：{case['verdict']}")
    return "\n".join(lines)


def coverage_note(question):
    """O1：条款级覆盖，只采用通知原文里显式写出的效力措辞。"""
    if not any(w in question for w in COVERAGE_TRIGGERS):
        return ""
    cases = COVERAGE.get("cases", [])
    if not cases:
        return ""
    lines = ["【条款级覆盖】补充/调整通知只覆盖部分条款，其余明确沿用原通知（原文措辞，不推断）："]
    for case in cases[:3]:
        lines.append(f"- {case['id']} {case['title']}（{case['date']}）")
        lines.append(f"  被覆盖：{'、'.join(case['supersedes_scope'])}")
        lines.append(f"  明确沿用：{'、'.join(case['retains'])}")
        lines.append(f"  原文依据：{case['url']}")
    lines.append("依据：宁波大学「申报方式和时间安排以本补充通知为准」、温州大学「不作调整，按照原通知执行」、云南大学「报名截止时间仍按原通知执行」。")
    return "\n".join(lines)


def time_status(now=None):
    now = now or datetime.now()
    delta = DEADLINE - now
    if delta.total_seconds() <= 0:
        return "已过官方截止时间（2026-11-18 15:00），本结论仅作历史核查"
    return f"距省赛提交截止还有 {delta.days} 天 {delta.seconds // 3600} 小时（截止 2026-11-18 15:00）"


def risk_note(question):
    """O5：错判后果 + 时效状态。只在问题显式问后果/风险时输出。

    刻意不写具体被排除口径的数值，避免把「错误日期」带进答案造成二次误导。
    """
    if not any(w in question for w in RISK_TRIGGERS):
        return ""
    return (
        "【决策后果】官方通知原文（official-03）写明「逾期未提交将错失省赛参赛机会」；"
        "若采信被排除的口径或沿用已失效节点，可能导致提交失败。\n"
        f"【时效状态】{time_status()}。\n"
        "【可推翻条件】若组委会发布新的补充通知，以其显式效力措辞为准；本系统不自动改写已归档原文。"
    )


def gap_note(reason):
    """O3：拒答时说明缺口类型与下一步核对路径，不把缺失包装成结论。"""
    hint = GAP_HINTS.get(reason)
    if not hint:
        return ""
    return f"【证据缺口】{hint}"


def enrich_answer(question, reason=None):
    """返回要追加到答案末尾的附加区块（可能为空串）。"""
    if reason is not None:
        return gap_note(reason)
    parts = [channel_table(question), coverage_note(question), risk_note(question)]
    return "\n\n".join(p for p in parts if p)
