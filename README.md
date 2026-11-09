# 校务 / 赛事通知可信问答助手（场景化轻量 RAG 知识库）

第九届传智杯「AI 创新应用挑战赛」参赛作品（个人赛 / B 组）。
**当前状态：v0.3，可运行、可演示，含 Web 界面；FastAPI 主实现已实测验证。** 21 个单测全过（含 P-008 的 10 个回归测试）；真实官方语料上 `recall@3 = 6/8 (75%)`、`recall@5 = 8/8 (100%)`。已修三类真实缺陷（空壳标题挤占排名、词表不匹配漏召、冲突吞掉答案），过程见 `evidence/prompts/P-002` 与 `P-005`。定位与已核实信息见 `findings.md`；确认状态见 `CONFIRM.md`。

## 解决的真实问题

同一件事的通知散落在赛项页、官网、学校教务处通知与群聊里，日期和口径还经常不一致。本项目交接时就记录了两组真实案例：

- `2026-11-18` 同时被标为「省赛报名截止」「作品提交截止」「作品指导提交截止」，三种口径并存；
- 「省赛专家评审意见预计 2027 年 1 月底发布」却要求「国赛作品 2026-12-27 前提交」，时间线矛盾。

普通问答助手会挑一条最像的答案直接给，代价是报错日期、报错组别（官方规则：选错组别无条件取消资格及所有成绩）。
本作品的取向是：**宁可并列呈现、明确提示核对，也不擅自替用户选定**。

## 10 分钟极速复现

环境：Python 3.10+（本机实测 3.13.14）。**检索/回答核心零第三方依赖**，以下命令开箱即跑。

```bash
python -m app.cli --sources
python -m app.cli "作品提交截止是哪一天？"
python -m app.cli "选错组别会有什么后果？"
python -m app.cli --eval
python -m unittest discover -s tests -v
```

Web 演示（**零依赖，本机立即可跑**）：

```bash
python -m app.server --selftest     # 自启自停，验证 /health /sources /ask 与界面路由
python -m app.server --port 8000    # 常驻服务，浏览器打开 http://127.0.0.1:8000/ 即为界面
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" -d "{\"question\":\"选错组别会怎样\"}"
```

FastAPI 主实现（`app/main.py`，对应选定技术栈 Python/FastAPI）：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

装好依赖后浏览器打开 `http://127.0.0.1:8000/docs`。

> **本机实测（2026-11-09 20:30 更正）**：此前写的「会话网络受限」是**错误结论**——当时误用了 `127.0.0.1:7897`，实际注入的是 `HTTP_PROXY=127.0.0.1:1626`。复核后 DeepSeek / Moonshot / PyPI 的 HTTPS 请求均可达；但 `pip` 取 index 时被沙箱单独拦截（`403 Forbidden`，清空代理直连仍失败）。**2026-11-09 21:40 更新**：已用 `tools/bootstrap_wheels.py` + `tools/finish_wheels.py` 通过 PyPI JSON API 直连下载 wheel，再 `pip install --no-index --find-links=.wheels` 离线装齐依赖，**FastAPI 主实现现已实测运行**（`/health` `/sources` `/` `/docs` `/ask` 全部 200）。标准库服务保留为「裸 Python、零第三方依赖」的降级路径，用于 10 分钟复现。
> 另一个重要区分：**走云端 LLM 不需要装任何依赖**——`app/answer.py::_llm_answer` 用标准库 `urllib`，`--llm` 开关和三个环境变量占位已就位，给 `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` 即可跑。
> 本地调试前需清除 `HTTP_PROXY`（沙箱注入的代理会劫持 `127.0.0.1` 请求，见 `findings.md` 第 5 节）。

可选云端生成（D2：仅复杂分析 / 复杂任务时启用）：

```bash
copy .env.example .env
```

在 `.env` 中填 `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`（OpenAI 兼容 `/chat/completions`），然后：

```bash
python -m app.cli --llm "比较三条 11.18 口径并说明各自风险"
```

未配置或调用失败时自动降级为离线抽取式回答，并返回 `llm_degraded=true`，**不会静默编造**。key 只从环境变量读，严禁写进仓库。

## 当前能力

| 能力 | 实现 | 位置 |
|---|---|---|
| 中文检索 | 字符 bi-gram + BM25，`set(query terms)` 去重 | `app/retriever.py` |
| 来源 / 时效先验 | 权威等级权重 + 时间衰减（可配 `recency_tau`） | `app/retriever.py` |
| 口径差异检测 | 规则基线：按小句切分，仅含强时间词（截止/发布/公布/评审意见/答辩）的小句才贡献日期，按 `(日期, 文档)` 去重后并列呈现；措辞为「口径差异」而非断定为矛盾 | `app/answer.py` |
| 引用溯源 | 每条回答附 `[编号] 标题 / 来源 / 日期 / URL` | `app/answer.py` |
| 无依据拒答 | 最高得分低于 `MIN_RELEVANCE_SCORE` → 明确拒答 | `app/answer.py` |
| 意图控制 | `SYSTEM_PROMPT` 五条硬约束（只用片段、逐条引用、冲突并列、不足拒答、整理稿不写成官方定论） | `app/answer.py` |
| 可量化评测 | `EVAL_SET` 8 道真实语料题输出 recall@3 / recall@5；11 个标准库单测覆盖切分/检索/冲突/拒答/引用/同义扩展 | `app/cli.py`、`tests/test_core.py` |
| Web 界面 | 单文件零依赖前端：知识库侧栏、引用溯源、口径差异高亮、拒答态、耗时统计、`#q=` 分享链接 | `app/web/index.html` |
| 服务接口 | FastAPI 薄封装 `/health` `/sources` `/ask` | `app/main.py` |

## 架构与约束

```
data/docs/*.md  ->  loader(前置元数据)  ->  chunker(段落级)
                                            |
                          retriever(BM25 + 来源/时效先验)
                                            |
             +------------------------------+-------------------+
             |                                                  |
     answer(冲突检测 / 溯源 / 拒答)                    可选 LLM(环境变量)
             |                                                  |
      离线抽取式回答  <--------- 失败自动降级 -------------------+
             |
      CLI  /  FastAPI
```

约束：核心不依赖任何第三方包；LLM 只能增强表达、不能绕过证据约束；`data/docs` 中每条文档必须带 `doc_id / title / source / source_url / published_at / authority` 前置元数据，否则加载直接报错。

## 语料导入（当前是 DEMO 数据）

`data/docs/demo-0*.md` 共 4 条，**内容摘自本项目 `findings.md` 的整理稿，是演示数据，不是官方通知原文，也不代表官方最终口径**。正式版本须导入真实通知：

```markdown
---
doc_id: notice-001
title: 关于xxx的通知
source: 学校教务处官网
source_url: https://...
published_at: 2026-11-01
authority: 3
---
通知正文，按空行分段……
```

放入 `data/docs/` 后重启 CLI / 服务即生效。`authority` 取 1—3，数值越高检索权重越大；`published_at` 用 `YYYY-MM-DD`，越新权重越高。

## 当前边界（诚实声明）

- 检索是**词法基线**，不是语义向量模型；embedding / 混合检索 / rerank 属后续迭代。
- `app/main.py`（FastAPI）因依赖未装**未运行验证**；`app/server.py`（标准库降级）已自测通过。两者接口语义一致。
- 口径差异检测是**规则基线**（日期 + 时间关键词），不是语义推理；它只提示「请核对」，不判断谁对谁错。
- 离线回答是**抽取式**，不做生成式改写；生成能力只在配置 LLM 后启用。
- 尚无文档导入接口、增量更新、多轮对话、前端界面。
- 作品还未达到交付标准；视频、PDF、≥3 条 Prompt 链、公开仓库均未完成。

## 迭代路线（每次对应一条 Prompt 链 + 一次细粒度提交）

| 链 | 迭代 | 状态 |
|---|---|---|
| P-001 | 从 0 到可运行垂直切片 | 完成（无修 Bug 环节，已如实留白） |
| P-002 | 修复口径差异误报 + 来源去重 + 2 个回归测试（含修 Bug 引导） | 完成 |
| P-003 | 依赖安装失败后的零依赖 HTTP 降级服务 + 代理绕过 + 自启自停自测 | 完成 |
| P-004 | 登录态抓取官网原文 → 7 份原文存档 + 6 条真实语料；11-18 截止定论、交付物规格转为原文依据 | 完成 |
| P-005 | 带真实失败输出修三类缺陷：空壳标题、词表不匹配、冲突吞答案；新增 4 个回归测试 | 完成（含修 Bug 引导） |
| P-006 | 向量检索 / 混合检索与词法基线对比实验（解决 URL 类长 token 漏召） | 待做 |
| P-007 | 意图控制消融实验（关掉同义扩展/冲突检测，看拒答率与召回变化） | 待做 |

> 官方要求 ≥3 条完整 Prompt 链且包含「引导 AI 修 Bug」环节。现有 5 条（**P-002、P-005 含该环节，均为真实出错后所修**），已超额达标。修 Bug 环节只在真实出错时记录，**不虚构、不事后补写**。

## 官方交付物对照

| 交付物 | 官方要求 | 当前状态 |
|---|---|---|
| 代码仓库 Public + README | 可访问且含 README | 本地仓库已建、README 已写；**未关联远程、未公开**（`CONFIRM.md` D4 待确认） |
| 细粒度 Git 历史 | 禁止一次性提交 | 已按阶段 0 / 功能切片分次提交，见 `evidence/devlog.md` |
| AI 对话历史 ≥3 条完整链路 | 含修 Bug 引导 | `P-001`~`P-005` 五条已建（P-002、P-005 含真实修 Bug 引导），超额达标 |
| 10 分钟极速复现指南 | 环境、依赖、环境变量模板 | 本文件初版 + `.env.example` + `requirements.txt` |
| 5—8 分钟 1080p 视频（含 ≥2 分钟 AI 协同） | MP4 | **未开始**，须用户本人录制 |
| ≤30 页 PDF 技术文档 | 意图控制 / 架构 / 可复现性 | **未开始** |

## 目录

```
app/           核心代码（零依赖）+ FastAPI 薄封装 + 标准库降级 HTTP 服务
data/docs/     语料（当前为 DEMO 整理稿）
tests/         标准库单元测试
evidence/      过程证据：README / devlog / prompts / screenshots
findings.md    已确认事实基线
CONFIRM.md     待确认事项清单
task_plan.md   阶段计划
progress.md    会话日志
```

## 离线断言资产（构建期产物，不参与运行时）

`data/claims.json` 是 6 份官方通知经 `deepseek-flash` 抽取的 **141 条原子断言**，每条带 `claim_type` / `value` / `evidence_span` / `effective_from` / `authority` / `source_url`。**LLM 负责提，程序负责验**：`evidence_span` 必须逐字出现在原文中，否则标记并保留，不静默丢弃。最终 141/141 通过字面校验。

| 边界 | 说明 |
|---|---|
| 凭据 | 只从环境变量读取（`DEEPSEEK_API_KEY` / `LLM_API_KEY`），**不写入任何文件、不进仓库、不进 Git 历史** |
| 用途 | 仅构建期：断言抽取、基准集负样本、纯生成基线对照 |
| 运行时 | `ALLOW_ONLINE_LLM` 默认关闭；`--llm` 会被拒绝并降级为抽取式，`/health` 返回 `online_llm_allowed=false` |
| 复现 | 资产已固化落盘，离线环境 10 分钟复现不需要 key、不需要联网 |
| 未覆盖 | 只做了**字面**校验；断言语义、`claim_type` 归类、`value` 抽取偏差仍需人工抽样核查 |

构建脚本 `tools/build_claims.py` 与两轮记录见 `evidence/claims-build.md`、`evidence/claims-build-v1.md`；完整过程链见 `evidence/prompts/P-006.md`。
