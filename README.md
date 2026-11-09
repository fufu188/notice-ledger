# 校务 / 赛事通知可信问答助手（场景化轻量 RAG 知识库）

第九届传智杯「AI 创新应用挑战赛」参赛作品（个人赛 / B 组）。
**当前状态：v1.0，可运行、可演示、材料齐备，达到可交付状态。** 35 个单测全过；真实官方语料上 `recall@3 = 6/8 (75%)`、`recall@5 = 8/8 (100%)`。已修三类真实缺陷（空壳标题挤占排名、词表不匹配漏召、冲突吞掉答案），过程见 `evidence/prompts/P-002` 与 `P-005`。定位与已核实信息见 `findings.md`；确认状态见 `CONFIRM.md`。

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
| Web 界面 | 单文件零依赖前端：三栏骨架 + 10 个交互模块（见 `docs/ui-modules.md`），`#q=` / `#tab=` 分享链接 | `app/web/index.html` |
| 证据侧栏 | 右栏「证据 / 脉络 / 评测」三 Tab：检索链路四步、证据强度三因子拆解、命中分数条、通知时间轴、基准指标与消融 | `app/web/index.html`、`app/panels.py` |
| 内联引用联动 | 正文 `[n]` 渲染为可点芯片，点击滚到右栏对应片段并高亮；引用列表与面板双向联动 | `app/web/index.html` |
| 证据强度 | 由首位 BM25、问题词项覆盖、是否落地三因子算出并公开拆解；**明确标注不评价答案正确性** | `app/answer.py` `evidence_strength()` |
| 口径冲突矩阵 | 有差异时渲染「值 / 出处 / 权威」三列表格，不做合并裁定 | `app/web/index.html` |
| 截止倒计时 | 空态 SVG 进度环 + 顶栏常驻胶囊，秒级跳动，可导出 `.ics` | `app/panels.py`、`app/card.py` |
| 命令面板 | `Ctrl/⌘+K` 模糊检索问题、面板与文档，`↑↓/Enter/Esc` 全键盘操作 | `app/web/index.html` |
| 科技粒子动态视觉 | Canvas 星座粒子（视口自适应、鼠标连线、慢帧自动降密度、reduced-motion 禁用）+ 玻璃拟态 + 青紫霓虹 token | `app/web/index.html` |
| 服务接口 | FastAPI 与标准库降级服务**同一套端点**：`/health` `/sources` `/api/overview` `/ask` | `app/main.py`、`app/server.py` |

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
- 尚无文档导入接口与增量更新；前端不做多轮上下文记忆（每问独立检索，避免把上一轮结论当成依据）。
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


## 交付物与文档（v1.0）

| 文件 | 用途 | 官方要求对应 |
|---|---|---|
| `docs/technical.pdf` | 技术文档，**14 页**（pdfplumber 校验） | PDF ≤30 页；意图控制 / 架构设计 / 可复现性论证三主题齐备 |
| `docs/intro.pdf` | 作品介绍文档，**8 页** | 表单第 6 项 7 小节逐项对应，含真实界面截图 |
| `docs/video-script.md` | 6 分 30 秒演示视频分镜 | 5–8 分钟 1080p，含 **2 分 10 秒 AI 协同复现** |
| `docs/pain-points.md` | 需求证据 → 痛点 → 功能映射 | 「痛点定义清晰、面向真实场景」 |
| `docs/notice-deadline.ics` | RFC 5545 截止提醒样例 | 五要素卡片附带的本地日历工件 |
| `evidence/submission-checklist.md` | 表单 7 字段逐项核对 | 提交物齐备 |
| `evidence/research/README.md` | 12 项一手资料逐字摘录索引 | 需求证据可核查 |
| `evidence/prompts/P-001…P-009.md` | 9 条完整 Prompt 链（5 条含真实修 Bug） | ≥3 条且含修 Bug 引导 |
| `dist/notice-ledger-v1.1.zip` | 源码 + 文档 + 证据的本地打包 | 供网盘上传（表单第 5 项） |

## 10 分钟复现（裸 Python，无需 key / 联网 / 第三方包）

1. `python -m unittest discover -s tests -q` → 35 个测试通过。
2. `python -m app.cli --eval` → `recall@3 = 6/8 (75%)`、`recall@5 = 8/8 (100%)`。
3. `python -m app.cli "省赛作品提交截止是哪一天？"` → 裁决结论 + 原文片段 + 引用。
4. `python -m app.server --port 8000` → 打开 `http://127.0.0.1:8000/`，可试五要素卡片、`.ics` 下载、`#q=` 分享链接。
5. 可选：`EVAL_REUSE_BASELINE=1 python tools/run_eval_v1.py && python tools/score_eval.py` 复跑 24 题基准集与 10 组消融。

FastAPI 版需 `pip install -r requirements.txt`；本会话用离线 wheel 装齐并实测 `/health` `/sources` `/api/overview` `/` `/docs` `/ask` 全 200。标准库服务同样提供 `/api/overview`，两套服务对外字段一致（`tools/probe_ui.py`、`tools/probe_fastapi.py` 可复验）。
`ALLOW_ONLINE_LLM` 默认关闭，DeepSeek key 仅用于离线断言构建与对照组。

## 诚实边界

修复后与纯生成基线结论正确率持平（66.7%），错误口径采信率 12.5% 仍高于基线 8.3%；语义拒答阈值为本基准集经验值，换语料需重新标定。详见 `docs/technical.pdf` 第 9 章。
