"""Standard-library unit tests for the zero-dependency core."""
import unittest

from app.answer import compose, detect_conflicts
from app.chunker import chunk_docs
from app.models import Doc
from app.retriever import Retriever, tokenize

TODAY = "2026-11-09"


def make_doc(doc_id, title, body, authority=2):
    return Doc(
        doc_id=doc_id,
        title=title,
        source="单元测试语料",
        source_url="",
        published_at=TODAY,
        authority=authority,
        body=body,
    )


DOCS = [
    make_doc("t-01", "省赛报名截止", "省赛报名截止日期为 2026-11-18，逾期不再受理。"),
    make_doc("t-02", "作品提交截止", "作品提交截止与作品指导提交截止同为 2026-11-18，三种口径并存。"),
    make_doc("t-03", "国赛作品提交", "国赛报名为 2026-12-10 至 2026-12-21，国赛作品提交截止 2026-12-27；省赛专家评审意见预计 2027年1月底发布。"),
    make_doc("t-04", "组别规则", "组别分研究生组、A 组、B 组、C 组，选错无条件取消其参赛资格及所有成绩。"),
]


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.retriever = Retriever(chunk_docs(DOCS))

    def test_tokenize_chinese_bigram(self):
        tokens = tokenize("省赛报名截止 2026-11-18")
        self.assertIn("省赛", tokens)
        self.assertIn("2026", tokens)

    def test_retrieval_finds_expected_doc(self):
        hits = self.retriever.search("选错组别会怎样", top_k=5)
        self.assertTrue(hits)
        self.assertIn("t-04", [h.chunk.doc.doc_id for h in hits[:3]])

    def test_conflict_lists_multiple_dates(self):
        hits = self.retriever.search("作品提交截止和国赛评审时间", top_k=5)
        conflicts = detect_conflicts(hits)
        self.assertTrue(any("2026-11-18" in line for line in conflicts) or
                        any("2026-12-27" in line for line in conflicts))
        self.assertGreaterEqual(len({line.split("｜")[0] for line in conflicts}), 1)

    def test_conflict_ignores_enrollment_window_and_dedupes(self):
        """P-002 regression: a date range in a non-deadline clause must not be
        reported as a 口径差异, and one document must not appear twice."""
        hits = self.retriever.search("作品提交截止和国赛评审时间", top_k=5)
        conflicts = detect_conflicts(hits)
        joined = "\n".join(conflicts)
        self.assertNotIn("2026-12-10", joined)
        self.assertNotIn("2026-12-21", joined)
        self.assertIn("2026-12-27", joined)
        self.assertEqual(len(conflicts), len(set(conflicts)))

    def test_answer_does_not_repeat_same_source(self):
        hits = self.retriever.search("作品提交截止是哪一天", top_k=5)
        result = compose("作品提交截止是哪一天", hits, min_score=0.0)
        doc_ids = [h.chunk.doc.doc_id for h in result.hits]
        self.assertEqual(len(doc_ids), len(set(doc_ids)))

    def test_abstain_on_unrelated_question(self):
        hits = self.retriever.search("今天天气适合放风筝吗", top_k=5)
        result = compose("今天天气适合放风筝吗", hits, min_score=0.35)
        self.assertTrue(result.refused)
        self.assertIn("没有可靠依据", result.text)

    def test_answer_has_citations(self):
        hits = self.retriever.search("省赛报名什么时候截止", top_k=5)
        result = compose("省赛报名什么时候截止", hits, min_score=0.0)
        self.assertFalse(result.refused)
        self.assertTrue(result.citations)
        self.assertTrue(all(line.startswith("[") for line in result.citations))

    # —— 以下两个测试锁死 P-005 修掉的两类真实缺陷，防止回归 ——

    def test_heading_is_merged_into_body(self):
        """小节标题不得单独成块（真实语料里它会把含答案的段落挤出 top-K）。"""
        doc = make_doc(
            "t-05",
            "提交通道",
            "二、作品提交方式\n\n登录官网，进入个人中心，点击参赛流程完成提交。",
        )
        chunks = [c for c in chunk_docs([doc])]
        self.assertEqual(len(chunks), 1)
        self.assertIn("作品提交方式", chunks[0].text)
        self.assertIn("个人中心", chunks[0].text)

    def test_heading_alone_does_not_become_dead_chunk(self):
        """整篇只有标题时也不能产出空壳块。"""
        doc = make_doc("t-06", "只有一个标题", "三、特别提醒")
        chunks = chunk_docs([doc])
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, "三、特别提醒")

    def test_synonym_expansion_bridges_entry_vs_link(self):
        """用户问「入口」、原文写「提交链接」时，不能因为词表不重合而漏召。"""
        docs = [
            make_doc("t-07", "提交通道", "省赛最终作品提交链接：https://example.invalid/form 。"),
            make_doc("t-08", "无关通知", "本次比赛的颁奖典礼另行通知。"),
        ]
        retriever = Retriever(chunk_docs(docs))
        hits = retriever.search("入口在哪", top_k=2)
        self.assertTrue(hits)
        self.assertEqual(hits[0].chunk.doc.doc_id, "t-07")

    def test_expansion_can_be_disabled(self):
        """扩展必须是可关闭的，否则消融实验做不了。"""
        docs = [make_doc("t-09", "提交通道", "省赛最终作品提交链接：https://example.invalid/form 。")]
        retriever = Retriever(chunk_docs(docs))
        self.assertEqual(retriever.search("入口在哪", top_k=1, expand=False), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
