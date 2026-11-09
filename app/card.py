"""O4：通知五要素卡片 + 本地 .ics 日历导出（零第三方依赖）。

字段原型来自中国大学生在线《读懂学校通知是大学生的必修课》：
「圈出关键信息，时间、地点、对象、要求、截止时间」。
抽不到的字段一律写「原文未明确」，不猜测、不补全。

ICS 采用 RFC 5545 的 VEVENT / DTSTART / DTEND / SUMMARY / DESCRIPTION / VALARM
基本结构（本地生成，不联网、不需要账号），可用标准日历程序导入验证。
"""
import re
from datetime import datetime, timedelta
from pathlib import Path

FIELDS = ("时间", "地点", "对象", "要求", "截止时间")
UNKNOWN = "原文未明确"

DATE_PATTERNS = (
    r"(20\d{2}年\d{1,2}月\d{1,2}日(?:\d{1,2}:\d{2}(?::\d{2})?)?)",
    r"(20\d{2}-\d{1,2}-\d{1,2}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?)",
)


def _first(pattern, text, limit=60):
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group(1) if match.lastindex else match.group(0)
    return value.strip()[:limit]


def build_card(question, hits, claim_texts=None):
    """从命中片段与补充断言里抽取五要素；只做规则抽取，不做语义改写。"""
    texts = [h.chunk.text for h in hits]
    texts += list(claim_texts or [])
    joined = "\n".join(texts)

    deadline = _first(r"(?:提交|作品提交|报名)?截止时间[：:]\s*([^\n。；]{4,40})", joined)
    if not deadline:
        deadline = _first(r"请于([^\n。；]{2,30}?)前", joined)
    when = _first(r"(?:报名时间|省赛时间|国赛时间|时间安排)[：:]\s*([^\n。；]{4,50})", joined)
    where = _first(r"(?:地点|地址)[：:]\s*([^\n。；]{2,40})", joined)
    who = _first(r"(?:参赛对象|参赛选手|各位)[：:]?\s*([^\n。；]{2,40})", joined)
    requirement = _first(r"(?:请|须|应|要求)[：:]?\s*([^\n。；]{4,60})", joined)

    values = {
        "时间": when or UNKNOWN,
        "地点": where or UNKNOWN,
        "对象": who or UNKNOWN,
        "要求": requirement or UNKNOWN,
        "截止时间": deadline or UNKNOWN,
    }
    known = sum(1 for v in values.values() if v != UNKNOWN)
    return {
        "question": question,
        "fields": values,
        "coverage": f"{known}/{len(FIELDS)}",
        "attachments": "原文提及附件/链接，本知识库未收录其内容，需自行核对" if re.search(r"附件|链接|http", joined) else "原文未提及附件或链接",
        "source": "规则抽取自命中的官方原文片段，未做语义补全",
    }


def parse_deadline(value):
    """把中文/ISO 写法解析成 datetime；解析不了返回 None（不编造）。"""
    if not value or value == UNKNOWN:
        return None
    patterns = (
        (r"(20\d{2})年(\d{1,2})月(\d{1,2})日(\d{1,2}):(\d{2})", "%Y-%m-%d %H:%M"),
        (r"(20\d{2})年(\d{1,2})月(\d{1,2})日", "%Y-%m-%d"),
        (r"(20\d{2})-(\d{1,2})-(\d{1,2})[ T](\d{1,2}):(\d{2})", "%Y-%m-%d %H:%M"),
        (r"(20\d{2})-(\d{1,2})-(\d{1,2})", "%Y-%m-%d"),
    )
    for pattern, _ in patterns:
        match = re.search(pattern, value)
        if not match:
            continue
        groups = [int(g) for g in match.groups()]
        try:
            if len(groups) == 5:
                return datetime(*groups)
            if len(groups) == 3:
                return datetime(groups[0], groups[1], groups[2], 23, 59)
        except ValueError:
            return None
    return None


def ics_text(card, reminder_days=2):
    """按 RFC 5545 生成单事件 .ics 文本；无有效截止则返回 None。"""
    due = parse_deadline(card["fields"]["截止时间"])
    if due is None:
        return None
    start = due - timedelta(hours=1)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    fmt = lambda d: d.strftime("%Y%m%dT%H%M%S")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//notice-ledger//Campus Notice Card//ZH",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:notice-ledger-{stamp}@local",
        f"DTSTAMP:{stamp}",
        f"DTSTART:{fmt(start)}", f"DTEND:{fmt(due)}",
        "SUMMARY:省赛作品提交截止（请核对官方原文）",
        "DESCRIPTION:" + card["question"].replace("\n", " ") + "；依据见项目裁决书",
        "BEGIN:VALARM", "ACTION:DISPLAY",
        f"TRIGGER:-P{reminder_days}D",
        "DESCRIPTION:距提交截止前的提醒，请核对最新补充通知",
        "END:VALARM",
        "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"


def to_ics(card, out_path, reminder_days=2):
    """落盘一份 .ics 供 README/演示使用；无有效截止则返回 None。"""
    text = ics_text(card, reminder_days=reminder_days)
    if text is None:
        return None
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # 用二进制写，避免 Windows 文本模式把 RFC 5545 要求的 CRLF 二次转换成 CRCRLF
    path.write_bytes(text.encode("utf-8"))
    return str(path)
