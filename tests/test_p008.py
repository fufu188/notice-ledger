"""P-008 regression tests: the three real defects found by benchmark v1.

These lock in behaviour that used to be broken, so a future refactor cannot
silently reintroduce it. No LLM, no network: everything runs on committed data.
"""
import unittest

from app.answer import compose
from app.claims import load_claim_index
from app.cli import build


class P008Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs, cls.retriever = build()

    def ask(self, question, **kwargs):
        hits = self.retriever.search(question, top_k=5)
        return compose(question, hits, min_score=0.35, **kwargs)

    # ---- D1: semantic abstention -------------------------------------------------
    def test_d1_abstain_when_topic_absent(self):
        """Q19 曾把「报名截止」片段当成答辩安排直接作答。"""
        result = self.ask("省赛答辩安排在哪一天？")
        self.assertTrue(result.refused)
        self.assertIn("没有可靠依据", result.text)
        self.assertEqual(result.citations, [])

    def test_d1_abstain_when_amount_absent(self):
        """资料只写「需完成缴费」，不得编造金额。"""
        result = self.ask("省赛报名费是多少钱？")
        self.assertTrue(result.refused)
        self.assertNotIn("198", result.text)
        self.assertNotIn("128", result.text)

    def test_d1_can_be_disabled_for_ablation(self):
        result = self.ask("省赛答辩安排在哪一天？", semantic_abstain=False)
        self.assertFalse(result.refused)

    def test_d1_must_not_reject_covered_topic(self):
        """回归：组别规则只在 demo 文档、断言索引未收录，曾被 D1 误拒。"""
        result = self.ask("选错组别会怎样")
        self.assertFalse(result.refused)
        self.assertIn("组别", result.text)
        self.assertTrue(result.citations)

    # ---- D2: structured claim recall --------------------------------------------
    def test_d2_ratio_facts_recovered(self):
        """Q13 曾只召回通用条款，漏掉 20%/25%。"""
        result = self.ask("国赛二等奖的获奖比例是多少？")
        self.assertFalse(result.refused)
        self.assertIn("20%", result.text)
        self.assertIn("25%", result.text)

    def test_d2_can_be_disabled_for_ablation(self):
        result = self.ask("国赛二等奖的获奖比例是多少？",
                          use_claims=False, semantic_abstain=False)
        self.assertFalse(result.refused)
        self.assertNotIn("[补充", result.text)

    def test_claim_index_uses_verified_spans_only(self):
        index = load_claim_index(self.docs)
        self.assertIsNotNone(index)
        self.assertGreater(len(index.claims), 100)
        self.assertTrue(all(c["text"] for c in index.claims))

    # ---- D3: verdict + honest citation numbering ---------------------------------
    def test_d3_verdict_sentence_present(self):
        result = self.ask("省赛作品提交截止是哪一天？")
        self.assertIn("排序最高的来源记载为", result.text)
        self.assertIn("15:00", result.text)

    def test_d3_supplement_does_not_steal_citation_numbers(self):
        """补充片段必须用 [补充N]，否则正文 [2][3] 与 citation 列表错配 = 伪造溯源。"""
        result = self.ask("国赛二等奖的获奖比例是多少？")
        numbered = sum(1 for line in result.citations if line.startswith("["))
        self.assertIn("[补充1]", result.text)
        self.assertLessEqual(numbered, 3)
        # 正文里不得出现 citation 不存在的编号
        for i in range(numbered + 1, 4):
            self.assertNotIn(f"[{i}] ", result.text)

    def test_d3_can_be_disabled_for_ablation(self):
        result = self.ask("省赛作品提交截止是哪一天？", verdict=False)
        self.assertNotIn("排序最高的来源记载为", result.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
