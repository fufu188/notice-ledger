"""Regression tests for the O1–O5 optimizations (2026-11-09).

All tests run on committed data only: no LLM, no network.
"""
import json
import unittest
from pathlib import Path

from app.answer import compose
from app.card import UNKNOWN, build_card, ics_text, parse_deadline
from app.cli import ROOT, build
from app.context import channel_of, coverage_note, gap_note, risk_note, time_status


class OptimizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs, cls.retriever = build()

    def ask(self, question, **kwargs):
        hits = self.retriever.search(question, top_k=5)
        return compose(question, hits, min_score=0.35, **kwargs)

    # ---- O2 渠道对照 ------------------------------------------------------------
    def test_channel_registry_covers_all_docs(self):
        data = json.loads((ROOT / "data" / "channels.json").read_text(encoding="utf-8"))
        ids = {d.doc_id for d in self.docs}
        self.assertEqual(ids, set(data["docs"].keys()))
        self.assertEqual(channel_of("official-04")["channel"], "official_form")

    def test_channel_table_triggered_by_authority_question(self):
        result = self.ask("官方通知和交接整理稿的说法不一致时，应该以哪个为准？")
        self.assertIn("【渠道对照】", result.text)
        self.assertFalse(result.refused)

    # ---- O1 条款级覆盖 ----------------------------------------------------------
    def test_coverage_data_has_explicit_scopes_and_sources(self):
        data = json.loads((ROOT / "data" / "coverage.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["cases"]), 4)
        for case in data["cases"]:
            self.assertTrue(case["supersedes_scope"])
            self.assertTrue(case["retains"])
            self.assertTrue(case["quote"])
            self.assertTrue(case["url"].startswith("http"))

    def test_coverage_note_lists_both_changed_and_retained(self):
        note = coverage_note("申报方式和时间安排以哪个为准，哪些条款沿用原通知？")
        self.assertIn("被覆盖", note)
        self.assertIn("明确沿用", note)
        self.assertIn("以本补充通知为准", note)

    # ---- O3 证据缺口 ------------------------------------------------------------
    def test_gap_note_has_actionable_hint_without_inventing_contact(self):
        note = gap_note("检索片段与断言资产均未覆盖问题的核心对象")
        self.assertIn("【证据缺口】", note)
        self.assertIn("教务处", note)
        self.assertNotIn("198", note)
        self.assertNotIn("128", note)

    def test_abstain_still_refuses_and_explains(self):
        result = self.ask("省赛答辩安排在哪一天？")
        self.assertTrue(result.refused)
        self.assertIn("【证据缺口】", result.text)
        self.assertNotIn("2026-11-18", result.text)

    def test_enrich_can_be_disabled_for_ablation(self):
        result = self.ask("省赛答辩安排在哪一天？", enrich=False, semantic_abstain=True)
        self.assertTrue(result.refused)
        self.assertNotIn("【证据缺口】", result.text)

    # ---- O5 决策后果与时效 ------------------------------------------------------
    def test_risk_question_is_not_wrongly_refused(self):
        result = self.ask("如果错过提交会有什么后果？")
        self.assertFalse(result.refused)
        self.assertIn("逾期未提交将错失省赛参赛机会", result.text)
        self.assertIn("【时效状态】", result.text)

    def test_risk_note_has_no_fabricated_deadline_value(self):
        note = risk_note("如果错过提交会有什么后果？")
        self.assertIn("可推翻条件", note)
        self.assertNotIn("24:00", note)

    def test_time_status_mentions_official_deadline(self):
        self.assertIn("2026-11-18 15:00", time_status())

    # ---- O4 五要素卡片与 ICS ---------------------------------------------------
    def test_card_fields_are_honest_about_missing_values(self):
        result = self.ask("省赛作品提交截止是哪一天？")
        self.assertIsNotNone(result.card)
        self.assertEqual(len(result.card["fields"]), 5)
        for key in ("时间", "地点", "对象", "要求", "截止时间"):
            self.assertIn(key, result.card["fields"])
        self.assertIn("截止时间", result.card["fields"])

    def test_card_missing_fields_marked_as_unknown(self):
        card = build_card("一个知识库里没有的问题", [], [])
        self.assertEqual(card["coverage"], "0/5")
        self.assertTrue(all(v == UNKNOWN for v in card["fields"].values()))

    def test_ics_is_rfc5545_shaped_and_has_reminder(self):
        result = self.ask("省赛作品提交截止是哪一天？")
        text = ics_text(result.card)
        self.assertIsNotNone(text)
        for marker in ("BEGIN:VCALENDAR", "BEGIN:VEVENT", "DTSTART:", "DTEND:",
                       "BEGIN:VALARM", "TRIGGER:-P2D", "END:VCALENDAR"):
            self.assertIn(marker, text)

    def test_parse_deadline_handles_chinese_and_iso(self):
        self.assertEqual(parse_deadline("2026年11月18日15:00").hour, 15)
        self.assertEqual(parse_deadline("2026-11-18 15:00:00").hour, 15)
        self.assertIsNone(parse_deadline(UNKNOWN))


if __name__ == "__main__":
    unittest.main(verbosity=2)
