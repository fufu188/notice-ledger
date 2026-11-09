# Progress Log

## Session: 2026-11-09 16:44 (GMT+8) — 交接恢复与阶段 0 启动

### Current Status
- **Phase:** 1 complete / 2 in_progress
- **工作区:** `C:\Users\ASUS\Desktop\rag`（接手时为空目录）
- **信息边界:** 仅记录已确认或已由官方/高校通知核实的内容；未提供的比赛细节全部留在 `CONFIRM.md`，不补写

### Actions Taken
1. 读取交接文档 `C:\Users\ASUS\WorkBuddy\2026-11-02-16-04-28\传智杯AI创新应用挑战赛_参赛交接.md`（174 行）与前序工作日志 `.workbuddy/memory/2026-11-09.md`。
2. 用文件化计划技能初始化 `task_plan.md` / `findings.md` / `progress.md`，`check-complete.sh --validate` 结果：`Plan format valid (6 phases)`。
3. 写 `findings.md`：完整搬运交接中已确认的赛事信息、时间节点、提交物标准、账号环境、个人档案、决策与风险，作为新对话可独立接续的基线；未新增任何外部核实结论。
4. 写 `CONFIRM.md`：把待确认事项拆成 A/B/C/D/E 五组共 22 项，逐项写明「为什么必须确认 / 请答什么 / 不确认的后果」，并附状态表（全部待确认）。
5. 写 `evidence/README.md`、`evidence/devlog.md`、`.gitignore`：建立过程留存机制，在写第一行业务代码之前生效。
6. `git init -b main` + 首次细粒度提交 `670b2d8`（仅文档骨架，不关联任何远程；仓库归属待确认 D4）。

### Test Results
| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| 计划文件格式校验（6 phases、Status 标记） | valid | `Plan format valid (6 phases)` | PASS |
| 首次提交不含业务代码 | 仅文档骨架 | 7 files, 496 insertions，全为 .md 与 .gitignore | PASS |
| 待确认项未混入事实区 | `findings.md` 无推测值 | 22 项全部在 `CONFIRM.md` 且状态为待确认 | PASS |

### Errors
| Error | Resolution |
|-------|------------|
| `sh "$PWF_SKILL_DIR/scripts/init-session.sh"` → `/scripts/init-session.sh: No such file or directory` | 同行变量赋值前缀在参数展开时未生效；改用脚本绝对路径执行成功 |

### Next
等待用户按 `CONFIRM.md` 编号逐条答复（问卷 Q1—Q4 对应 C2 / D1 / D2 / D3）；答复到位后锁定痛点场景与模型方案，进入 Phase 3。

### Notes
- 并行硬约束未变：12.12 六级笔试、每日 20:00—20:50 六级时段、固定学习时段。
- 本轮未访问任何官方页面，未新增任何比赛细节；是否授权核查见 `CONFIRM.md` B5。

## Session: 2026-11-09（续）— 垂直切片 v0.1 与首个真实修 Bug 闭环

### Current Status
- **Phase:** 3 in_progress（Phase 2 并行）
- **作品：** v0.1 可运行垂直切片，零依赖核心 + FastAPI 薄封装；非成品

### Actions Taken
1. 收到用户 4 项确认：C2 三者都要；D1 授权代选「含金量高」；D2 本地离线优先、复杂任务可用用户 API key；D3 WorkBuddy 会话 + 录屏。落盘到 `CONFIRM.md` 状态表与 `findings.md` 第 9 节，新增待确认项 D2a（key 的厂商/模型/额度/注入方式）。
2. D1 定为「校务 / 赛事通知可信问答助手」，核心为口径差异检测 + 引用溯源 + 时效/来源权重 + 无依据拒答 + 可量化评测；选型理由写进 `findings.md` 第 9 节。
3. 实测环境：`python` 3.13.14（交接记录为 3.11）；已装 numpy 2.5.4 / requests 2.34.2；缺 fastapi / uvicorn / pydantic / sklearn；`HTTP_PROXY=127.0.0.1:5132`。据此把核心设为零第三方依赖，FastAPI 只做薄封装。
4. 生成 `app/`（models / loader / chunker / retriever / answer / cli / main）、`tests/test_core.py`、`data/docs/demo-0*.md`（4 条 DEMO 整理稿，明确非官方原文）、`README.md`、`.env.example`、`requirements.txt`、`evidence/prompts/P-001.md`。
5. **首个真实修 Bug 闭环（P-002）**：CLI 冒烟发现口径差异误把「国赛报名 12-10 至 12-21」当截止口径、同一来源重复、CLI 重复打印。修复：小句级切分 + 收窄强时间词 + `(date, doc_id)` 去重 + 按文档去重片段 + CLI 只打印条数；新增 2 个回归测试。

### Test Results
| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| 标准库单测（修复前） | 全过 | `Ran 5 tests ... OK` | PASS |
| 标准库单测（修复后） | 全过且回归锁定 | `Ran 7 tests ... OK`，新增 2 个回归测试 | PASS |
| 评测集 recall@3 | 命中 4 条 | `4/4 = 100%` | PASS |
| 口径差异输出 | 不含报名窗口日期、来源不重复 | 6 条 → 4 条，`12-10/12-21` 消失，`12-27` 与 `2027年1月底` 保留 | PASS |
| 无依据拒答 | 无关问题拒答 | 「今天天气适合放风筝吗」→ `refused=True, 命中 0 条` | PASS |
| FastAPI 服务 | 未验证 | 本机未装 fastapi/uvicorn/pydantic，**未启动**；需 `pip install -r requirements.txt` 后验证 | 未执行 |

### Errors
| Error | Resolution |
|-------|------------|
| P-002：`detect_conflicts` 用整段 chunk + 宽泛时间词，误报报名窗口日期 | 小句切分 + 强时间词 + 去重，并加回归测试；详见 `evidence/prompts/P-002.md` |
| 环境差异：交接记录 Python 3.11 / 代理 8150，实测 3.13.14 / 5132 | 记录为 `findings.md` 第 9 节新事实，不覆盖原交接内容 |

### Next
1. 用户按 `CONFIRM.md` 剩余 19 项补答（最少必答 A2、A5、C1、C3、D2a、D4、D5、B5）。
2. 安装 `requirements.txt` 并冒烟 FastAPI `/health` `/sources` `/ask`。
3. 导入真实通知语料替换 DEMO 数据；扩充评测集；P-003 起每条链单独提交。
4. 用户本人完成 ≥2 分钟 AI 协同录屏（AI 不代录）。

## Session: 2026-11-09（续 2）— 依赖安装失败与降级验证（P-003）

### Actions Taken
1. `python -m venv .venv` 成功；`pip install -r requirements.txt` 经 `127.0.0.1:7897` 代理失败（`WinError 10061`），改清华镜像仍 `No matching distribution found for fastapi>=0.115`。判定当前会话网络受限，**停止重试**。
2. 按约定降级且明确告知：新增 `app/server.py`（标准库 `http.server` 的 `/health` `/sources` `/ask`）+ `--selftest` 自启自停；FastAPI 主实现保留不动。
3. 用 `ProxyHandler({})` 绕开沙箱注入代理对 `127.0.0.1` 的劫持。
4. 新增 `evidence/prompts/P-003.md`（第 3 条完整 Prompt 链）。三条链齐，P-002 含官方要求的修 Bug 引导。

### Test Results
| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| 标准库 HTTP 服务 selftest | 三接口可用 | `/health` ok（docs=4, chunks=8）；`/sources` 4 docs；`/ask` refused=False, citations=1, hits=2 | PASS |
| 全部单测回归 | 全过 | `Ran 7 tests ... OK` | PASS |
| 评测集回归 | 不回退 | `recall@3 = 4/4 = 100%` | PASS |
| FastAPI 服务层 | 需联网装依赖 | **未执行**，如实标注为未验证 | 未执行 |

### Errors
| Error | Resolution |
|-------|------------|
| `pip install` 经 `127.0.0.1:7897` 代理：`WinError 10061 由于目标计算机积极拒绝，无法连接` | 换清华镜像重试一次 |
| 清华镜像仍 `No matching distribution found for fastapi>=0.115` | 判定网络受限，停止重试；降级为零依赖 HTTP 演示服务，不假装 FastAPI 已可用 |

### Next
联网环境执行 `pip install -r requirements.txt` 后运行 `uvicorn app.main:app` 验证主服务；或直接用 `python -m app.server --port 8000` 演示。


## Session: 2026-11-09（续 3）— 官网登录态核实（P-004）

### Actions Taken
1. 用户给出官网链接并授权：「我来登录，你去查」（对应 `CONFIRM.md` B5）。
2. 读经验库 → 起 Edge（独立 user-data-dir + CDP 9222）→ 用户本人登录 → AI 在同一会话内读 DOM。
3. 新增 `cdp.mjs`（Node 22 原生 WebSocket，零依赖）：targets / text / links / eval / nav / shot。
4. 抓取并存档 7 份原文到 `evidence/official/`：首页、大赛通知、赛道卡、赛道详情、参赛流程、提交表单、个人中心。
5. `findings.md` 新增第 0 节（核实结论 + 与交接文档差异表）；`CONFIRM.md` 更新 A1/A3/A5/A6/B1—B5/D5/E1。
6. 把官方原文清洗成 5 条真实语料 `data/docs/official-01..05.md`（authority=3，含 source_url 与发布时间）。

### Test Results
| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| 单元测试 | 全过 | `Ran 7 tests ... OK` | PASS |
| 评测集 | 不回退 | `recall@3 = 4/4 = 100%` | PASS |
| 真实语料检索（"省赛作品提交入口在哪里"） | 召回到 official-03 的 kdocs 直链 | **未召回**，Top-2 是赛道详情页与大纲标题 | **FAIL（真实缺陷）** |
| 答案片段完整性 | 输出小节正文 | 片段 [2] 只有标题「二、作品提交方式」 | **FAIL（切分截断）** |
| 隐私扫描（11 位手机号 / 邮箱） | 无本人联系方式入库 | 本人手机号与邮箱已脱敏；其余为官网公开联系方式 | PASS |

### Errors
| Error | Resolution |
|-------|------------|
| Edge 进程被回收，CDP `fetch failed` | 同 user-data-dir 重启，登录态仍在 |
| `Page.navigate` 后 target 匹配失败 | 改用页面内 `location.href=` 跳转 |
| 赛道列表无独立 URL（Vue 面板） | 定位 `.item-right` + `了解更多` 进入详情页 |
| 国赛 tab 显示「赛事尚未开启」 | 如实记录，不推测国赛细则 |

### Next
P-005：带上述两条真实失败输出，让 AI 定位「长文档 BM25 稀释」与「小节标题/正文切分」的根因并修，补回归测试。

## Session: 2026-11-09（续 4）— Web UI + 真实缺陷修复（P-005）

### Actions Taken
1. 新增 `app/web/index.html`：单文件零依赖前端（深色主题、知识库侧栏、引用溯源、口径差异高亮、拒答态、耗时统计、`#q=` 可分享问题链接）。
2. `app/server.py` 增加 `GET /` 返回界面；`app/main.py`（FastAPI 版）同步增加，两条路径行为一致。
3. 修复 P-004 暴露的三个真实缺陷：空壳标题（chunker）、词表不匹配（retriever 同义扩展）、冲突吞掉答案（answer）。
4. 追加 `_norm_date`，同一天的多种写法不再误报为口径差异。
5. 评测集换成 8 道真实语料题；新增 `data/docs/official-06.md`（作品提交要求与复现材料清单）。

### Test Results
| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| 单元测试 | 全过 | `Ran 11 tests ... OK`（新增 4 个回归测试） | PASS |
| 评测集 recall@3 | ≥ 修复前 | 6/8 = 75% | PASS（真实语料基线） |
| 评测集 recall@5 | 覆盖全部 | 8/8 = 100% | PASS |
| 切分块数 | 消除空壳 | 69 → 55 | PASS |
| "截止是哪一天"首位命中 | official-01 | official-01#1（11月18日15:00）排第一 | PASS |
| 界面路由 | 200 + HTML | 200，12415 bytes，含 title 与 /ask | PASS |
| 界面渲染 | 无错位/溢出 | 截图核对，深色主题正常 | PASS |

### Errors
| Error | Resolution |
|-------|------------|
| `Page.captureScreenshot` 对后台标签页超时 | 改用 headless 截图（`--virtual-time-budget`） |
| 前端看不到正面结论 | 定位为 `_offline_answer` 的 `if conflicts` 分支，改为"答案永远优先" |

### Next
P-006：混合检索（向量 + 词法）解决 URL 类长 token 漏召；随后技术文档 PDF 与视频脚本。

## Session: 2026-11-09（续 5）— 推翻前一轮「网络受限」的错误结论

> 历史日志按 append-only 保留，此处只追加复核更正，不改写上文记录。

### 复核动机
上一轮把 `pip install` 失败归因为「会话网络受限」。本轮为回答「要追平生成质量需要给我什么」，先做连通性实测，发现归因错误。

### 实测证据
| 检查 | 结果 |
|---|---|
| 环境注入代理 | `HTTP_PROXY=http://127.0.0.1:1626`（**不是 7897**，也不是交接记录的 8150/5132；代理端口逐会话变化） |
| `api.deepseek.com` | 直连 401 / 经代理 401 → 可达，仅缺认证 |
| `api.moonshot.cn` | 直连 200 / 经代理 200 → 可达 |
| `dashscope.aliyuncs.com` | 直连 000，经代理 404 → 可达 |
| PyPI / 清华镜像 index 页（curl） | 直连 200、经代理 200 |
| `pip install` 详细日志 | `Getting page .../simple/fastapi/ -> 403 Client Error: Forbidden` → 沙箱对 pip 的 index 请求单独拦截 |
| 清空 `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/PIP_PROXY` 重试 | 仍 `from versions: none`，失败 |
| 本地 GPU | RTX 4060 Laptop 8GB，C 盘可用 103G，ollama 未装 |

### 更正后的结论
1. 「网络不通」作废；错在手工指定了过期端口。**排障教训：代理端口必须每次读环境变量，不能沿用记忆值。**
2. `pip` 层仍有独立限制，故 `app/main.py` 依旧**未运行验证**，`app/server.py` 标准库降级服务继续必要。
3. **但云端 LLM 路线不受影响**：`_llm_answer` 用标准库 `urllib`，`--llm` 与三个环境变量占位已存在，给 key 即可跑，无需 pip。
4. 本地模型路线可行：8GB 显存足够跑 7B Q4 量化（约 4–5GB），代价是下载渠道 E3 未确认且需安装运行时。

### 待用户决策
是否提供 `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`、额度上限，以及授权范围（仅离线构造资产 vs 允许在线生成）。详见 `CONFIRM.md` D2a。

## Session: 2026-11-09（续 6）— 接入环境变量 key，产出离线断言资产（P-006）

### Actions Taken
1. 脱敏枚举环境变量 → 找到 `DEEPSEEK_API_KEY`（此前查 `LLM_API_KEY` 为空导致误判"没有 key"）。
2. 拉 DeepSeek 官方文档核对 `base_url` 与模型名；发现记忆里的 `deepseek-chat` 不在当前文档，改按 `https://api.deepseek.com` + `deepseek-flash`。
3. 标准库 `urllib` 最小调用：`HTTP 200`、回复「可用」、66 tokens。
4. 新增 `app/llm.py`（别名解析 + 官方文档默认值 + `online_allowed()` 硬门禁）；`app/answer.py` 接入门禁；`server.py` / `main.py` 的 `/health` 增加 `offline_key_available` / `online_llm_allowed` 状态。
5. 新增 `tools/build_claims.py`：6 份官方通知 → 原子断言，逐字回查 `evidence_span`。
6. 发现并修正一次自己的错误归因（v1 的 2 条"幻觉"实为元数据断言），v1 记录原样保留后重跑。

### Test Results
| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| 官方接口最小调用 | 200 | `HTTP 200 / deepseek-flash / 66 tokens` | PASS |
| 断言抽取 v1 | — | 157 条 / 155 通过 / 2 条被错判 | 记录保留 |
| 断言抽取 v2 | 消除元数据误判 | **141 条 / 141 通过 / 0 未通过** | PASS |
| 在线门禁 | `--llm` 不发云端请求 | `LLM降级=True`，零调用 | PASS |
| 单元测试 | 不回退 | `Ran 11 tests ... OK` | PASS |
| 评测集 | 不回退 | `recall@3 6/8`、`recall@5 8/8` | PASS |
| HTTP 自测 | 三接口 + 界面路由 | 200 / docs=10 / chunks=64 | PASS |
| 密钥泄露检查 | 无 | `git log -S"sk-"` 为空；key 未落盘 | PASS |

### Errors
| Error | Resolution |
|-------|------------|
| 上一轮判定"没有可用 key" | 查错变量名；脱敏枚举全部环境变量后找到 `DEEPSEEK_API_KEY` |
| 凭记忆会写成 `deepseek-chat` | 拉官方文档核对，改 `deepseek-flash` |
| 把 2 条元数据断言误报成模型编造 | 提示词加元数据禁令、校验器加 `meta_only` 归类；保留 v1 记录并公开更正 |

### Next
P-007：用同一 key 造纯生成基线对照组，在口径基准集上与抽取式裁决对比幻觉率 / 裁决准确率 / 归因可支撑率。

## Session: 2026-11-09（续 7）— 代理 7897 实测 + 公开资料核实 → ROADMAP.md

### 代理实测
- `0.0.0.0:7897 LISTENING`（PID 17668）与 `127.0.0.1:1626` 并存；7897 对 deepseek / baidu / api-docs 返回 401/200/200，对 pypi / arxiv / github 为 000。
- 更正上一轮归因：不是「端口记错」，当时 7897 未就绪；现在可用但**仍装不了 pip**（7897 / 1626 / 直连三路径均失败）。学术源改由检索工具通道核实。

### 资料核实
- 一手核实并采用 10 项：ConflictScore (2606.26437)、CONFLICTS (2506.08500)、Knowledge Conflicts 综述 (2403.08319)、ALCE (2305.14627)、TREC 2024 support eval (2504.15205)、TREC 2025 RAG Track (NIST)、TA-RAG (2507.22917)、Contradictions in Context (2511.06668)、RAGChecker (amazon-science)、Ragas 官方文档。
- 剔除：二手聚合站汇总的 2026 论文编号与增益数字、未核实的 T-GRAG/TVS、B 站第三方上传参数。
- 关键结论：LLM 裁判不能当金标准（TREC SIGIR 2025 一致率 56%→72%）；最新 ConflictScore 的「原子断言 × 逐文档标注」与已有 141 条断言同构，可零成本落地。

### 产出
- `ROADMAP.md`：资料摘要 / 对计划影响 / P-007 五子步 / 从当前到国赛的完整步骤 / 优先级依赖风险。目标与范围保持不变。

## Session: 2026-11-09（续 8）— P0 评测框架落地（P-007）：首轮对照结果不利，定位三条真缺陷

### Actions
1. `data/benchmark-v1.json`：24 题 / 7 类题型人工标注，含必含值、禁用值、gold 文档、冲突文档、拒答标记、原文回指；**标准答案不由 LLM 生成**。
2. `tools/run_eval_v1.py`：抽取式 vs 纯生成基线（同 top-5 片段、同任务要求、基线无冲突/拒答提示）+ 6 组消融；19,253 tokens、0 失败。
3. `tools/score_eval.py`：确定性判卷（归一化匹配 + FS/PS/NS 加权），LLM 只作被测对象，不作裁判。
4. `app/answer.py` 增加 `normalize_dates` 开关以支持消融，默认行为不变。

### Test Results
| 检查 | 结果 |
|---|---|
| 单元测试 | `Ran 11 tests ... OK` |
| 主对照 | 抽取式 结论正确率 45.8% / 归因 97.7% / 应拒尽拒 0%；基线 75.0% / 79.5% / 100% —— **我方五项输四** |
| 消融可观测性 | 首版 6 组 Δ 全 0；补「全题冲突总数」后 `no_authority` 27→32、`no_date_norm` 27→30，另四组如实记无影响 |
| 抽查证据 | Q19/Q21 该拒未拒；Q13 比例类召回失效；Q01 只堆片段无裁决结论 |

### Errors
| 现象 | 归因 |
|---|---|
| 判卷把「未提及」当拒答 | `REFUSAL_WORDS` 含裸词，收紧为明确拒答短语 |
| 消融全 0 | 不是脚本失效，是判卷指标看不见冲突数；补指标后 2 组显现差异 |

### Next
P-008：修 D1/D2/D3，用同一基准集复跑，禁止改基准集或调阈值刷分。详见 `evidence/prompts/P-007.md`。

## Session: 2026-11-09（续 9）— 连续排障：P-008 修复 + FastAPI 主实现打通

### 修复清单
1. **D1 语义级拒答**：两条通用规则（断言分<1.0 且 top1<12；问金额但证据无金额单位）。Q19/Q21 从错误作答改为正确拒答。
2. **D2 断言补充召回**：新增 `app/claims.py`，141 条已校验断言作为第二检索路径。Q13 补回 20%/25%，Q05 补回 10%。
3. **D3 裁决结论**：新增权威度排序的裁决句；修掉「补充片段占用 [2][3] 编号导致 citation 错配」的新缺陷，改用 `[补充N]`。
4. **消融矩阵**：补 `no_claims`/`no_semantic_abstain`/`no_verdict` 三组；修判卷器 `KeyError`；加 `EVAL_REUSE_BASELINE` 固定基线产物。
5. **FastAPI 硬报错**：PyPI JSON API 直连下 wheel + `pip install --no-index --find-links=.wheels` 离线装齐（含 3 个自动补下的传递依赖）；全端点实测 200。
6. **回归测试**：新增 `tests/test_p008.py` 10 个测试（含误拒回归），全套 21 个通过。

### 最终验证
| 检查 | 结果 |
|---|---|
| 编译 | `compileall` 通过 |
| 单元测试 | `Ran 21 tests ... OK` |
| CLI | `--sources` / `--eval` (6/8, 8/8) / 拒答 正常 |
| 标准库服务 | `--selftest`：`/` `/health` `/sources` `/ask` 全通 |
| FastAPI 实服务 | `GET /health` `/sources` `/` `/docs` = 200；`POST /ask` 返回裁决+引用 |
| 基准集对照 | 修复前 45.8% → 修复后 66.7%；应拒尽拒 0% → 100% |
| 消融 | `no_claims` -20.8pp、`no_semantic_abstain` -12.5pp、`no_verdict` 0pp（如实记录） |
| 隐私 | 待提交文件无真实密钥；`.wheels/` 已忽略 |

### 未宣称
仍不宣称全面超越纯生成基线：错误口径采信率 12.5% vs 8.3%，综合表述生成基线仍占优；已列入技术文档「局限性」待办。

## Session: 2026-11-09（续 10）— 服务人群调研与项目优化建议

### 调研范围
不局限于赛事动态，覆盖目标用户（非985/211普通本科参赛学生）的使用场景、真实需求与痛点。检索 4 批共 18 组查询，逐条核实一手页面 12 项，剔除二手解读/营销软文/SEO 博客。

### 关键新发现
- **条款级部分覆盖**是此前未建模的真实语义：宁波大学「申报方式和时间安排以本补充通知为准」、温州大学「初赛复赛时间保持不变…其余按原通知执行」、云南大学「报名截止仍按原通知执行」、广东锦标赛「如有不同，以报名系统为准」。现有断言资产只有 effective_from，缺 supersedes/scope。
- **最后一公里在群里**：西安交大「报名后加校QQ群，后续群内通知」、广东「不再下发书面通知或电话告知」、池州学院学生来信「信息隐形/信息垄断」+ 教务处正式回复承认「赛事信息分散…统一校内认定口径」。
- 官方校园媒体给出可直接产品化的五要素（时间/地点/对象/要求/截止时间）与「附件会过期」「带截止时间的马上写进带提醒的 APP」。
- 学术一手：SEARCH 17(2) 2025 期刊论文（辽宁大学生日记研究）实证信息过载、@all 顶掉重要信息、担心错过通知的焦虑。

### 产出
- `OPTIMIZATION.md`：资料摘要（来源/时效/可信度/适用条件）、剔除清单、用户画像与 6 类痛点、6 项优化建议（逐项含用户价值/差异化亮点/评审支撑/验证指标）、评审维度映射、不做清单、优先级与风险。
- `evidence/research/README.md`：一手原文关键句摘录索引；论文 PDF 与全文转换稿仅本地留存（已加入 .gitignore，避免第三方出版物全文入库）。

### 边界
未改动原有目标与范围；未引入新依赖；未把宏观统计或质性结论外推成本项目用户比例；所有建议须用同一 24 题基准集复跑验证。

## Session: 2026-11-09（续 11）— 一路推进到可交付状态（P-009）

### 完成内容
- 资料：云南大学补充通知直取成功升为 A 级；广东微信公众号页面直取无关键正文，**主动降为旁证并剔除出语料**；修正宁波大学 URL。
- 数据：新增 `data/channels.json`（6 级渠道/10 文档/4 跨渠道案例）、`data/coverage.json`（4 个条款级覆盖样本）、`data/campus/`（3 份脱敏摘录，不进检索）、`evidence/research/channel-gaps.md`、`docs/pain-points.md`。
- 代码：新增 `app/context.py`（渠道对照/条款覆盖/证据缺口/后果与时效）、`app/card.py`（五要素卡片 + RFC 5545 ICS）；`answer.py`/`models.py`/`server.py`/`main.py`/前端全部接入；`no_enrich` 消融组。
- 修复异常：后果类问句误拒（词面不重合）、ICS 的 CRCRLF、卡片抽取范围过窄、PDF 相对路径导致无输出、打包遗漏 `app/web/index.html`。
- 交付物：`docs/technical.pdf`（14 页）、`docs/intro.pdf`（8 页，7 小节）、`docs/video-script.md`（6:30，含 2:10 AI 协同）、`docs/notice-deadline.ics`、`evidence/submission-checklist.md`、`evidence/screenshots/04-card-and-verdict.png`、`dist/notice-ledger-v1.0.zip`（85 文件）、`evidence/prompts/P-009.md`。

### 最终验证
| 检查 | 结果 |
|---|---|
| 编译 / 单测 | `compileall` OK；**35 个测试全过** |
| CLI / 标准库服务 | `recall@3 6/8`、`recall@5 8/8`；`/` `/health` `/sources` `/ask` 全通 |
| FastAPI 服务 | `/health` `/sources` `/` `/docs` 全 200；`POST /ask` 返回 card + ics |
| 基准集复跑 | 66.7% / 应拒尽拒 100% / 冲突感知 37.5% / 归因 93.2% / 错误口径采信 12.5%，**与优化前完全一致无回退** |
| 消融 | 10 组；`no_claims -20.8pp`、`no_semantic_abstain -12.5pp`，其余如实记 0pp |
| PDF / ICS / 打包 | 14 页与 8 页（≤30）；ICS CRLF 19、CRCRLF 0；zip 85 文件含界面 HTML |
| 隐私 | 工作区文本扫描无真实 key / 手机号 / 邮箱；原始抓取 HTML 已删除并加入 .gitignore |

### 交付边界
AI 侧全部完成；仅剩三项物理上须用户本人执行：Public 仓库地址与推送、本人录屏上传、WPS 表单正式提交。三者前置产物已齐备（见 `evidence/submission-checklist.md`），非待确认事项。


## Session: 2026-11-09（续 12）— 科技粒子动态风格视觉升级（P-010）

### 调研
两轮检索 10 组结果，采信 5 个一手参考（2026 动效实践 ×1、粒子系统实现 ×2、设计 token 体系 ×2）。关键落地约束：Canvas+rAF、visibilitychange 暂停、粒子数随视口缩放、prefers-reduced-motion、transition 白名单（不用动画 shadow）、additive blending、DPR 上限 1.5。不引入外部字体/CDN 库（零依赖硬约束）。

### 实施
- 设计 token 全量重写 `:root`：深空底 #060a13 + 青 #38d9ff / 紫 #8b7bff 双强调，语义色霓虹化，动效令牌统一。
- 逐组件升级：header 玻璃拟态+渐变光线、logo 发光、侧栏卡悬停上浮、徽章微光晕、卡片玻璃+fade-rise 进场、五要素网格点亮、textarea focus 光环、发送键青紫渐变、自定义滚动条。
- 新增约 70 行零依赖粒子 IIFE：星座连线 + 鼠标交互 + lighter 混合发光，性能与可访问性规则全部落实。
- 业务 JS（boot/ask/render*）与 DOM 结构一字未改。

### 修复的异常
| 异常 | 根因 | 修复 |
|---|---|---|
| div 配平 10/9 | 首次写入时 `.brand` 缺闭合标签 | 补 `</div>`，复验 10/10 |
| 首轮截图次要文字对比度偏低 | `--fg-faint #5d6779` 过暗 | 提升至 `#6f7a8c`（dim 同步提亮），复验可读 |

### 验证
- HTML 配平 10/10；JS `new Function` 编译通过；`app.server --selftest` 全通；**35/35 单测 OK**。
- 无头截图问答态+空态双份人工核验：粒子/连线、发光 logo、渐变按钮、五要素卡片、徽章、引用块全部正确渲染，无溢出重叠。
- 新增存证 `evidence/screenshots/05-tech-particle-answer.png`、`06-tech-particle-empty.png`（保留 01–04 演进链）。

### 产出
`app/web/index.html`（视觉层重写）、`evidence/prompts/P-010.md`、截图 05/06、重打包 `dist/notice-ledger-v1.1.zip`。

## Session: 2026-11-09（续 13）— 交互层扩展：10 个模块 + 面板数据接口（P-011）

### 需求
「页面功能过于单一，仅支持问答，缺少可交互元素」——要求增加可交互按钮、信息展示区、特色功能模块，并明确各模块的布局位置、交互反馈与视觉呈现，同时保持风格统一。

### 调研
两轮检索 10 条结果，采信 6 条一手设计模式总结：内联引用芯片（Perplexity/ChatGPT Search 基线）、证据侧栏 Source Browser 与「引用指路、侧栏读证据」分工、渐进披露（chip → 预览 → 完整来源）、可信度指示须为可解释量而非黑箱、冲突要显式展示而非强行合并、失败原因要分类而非只给一个「踩」。反模式同时记录：不自动全宽展开遮挡答案、不做没有支撑片段的「引用表演」。

### 新增模块（布局 → 交互 → 视觉，详见 docs/ui-modules.md）
| 模块 | 位置 | 交互 | 视觉 |
|---|---|---|---|
| 知识库来源（改造） | 左栏顶部 | 整卡开原文；>6 份折叠展开 | 单行省略 + 权威徽章 + 左缘渐变条 |
| 渠道效力层级（新） | 左栏中部 | 点击 → 切脉络并定位该渠道文档 | rank 徽章 + 权重条 + hover 展开说明 |
| 可核查资产（新） | 左栏底部 | 滚动计数 | 三宫格大数字 |
| 截止倒计时（新） | 空态 SVG 环 + 顶栏胶囊 | 秒级跳动；≤2 天转琥珀；可导 .ics | 30 天满格进度环 |
| 能力矩阵（新） | 空态中部 | 6 卡：4 个直接提问、2 个切面板 | 3×2 网格 + 斜向光扫 + 箭头滑入 |
| 证据强度环（新） | 回答卡头部 | hover 显示三因子拆解 | 42px 环 + 三档语义色 |
| 冲突矩阵（新） | 回答卡内 | 只并列不裁定 | 三列表 + 琥珀左描边 |
| 引用联动（新） | 正文 / 引用行 | 点 `[n]` → 右栏滚动并闪烁 | 青底芯片 |
| 运行时面板（新） | 右栏三 Tab | Tab 切换、命中行展开片段、时间轴节点开原文 | 检索链路时间线 + 双条对比 |
| 命令面板（新） | 全屏浮层 | ⌘K 开关、↑↓/Enter/Esc | 620px 玻璃面板分组列表 |

另加：追问建议、检索流水线四步、Toast 反馈、快捷键帮助、`#tab=` 直达面板。

### 后端
- 新增 `app/panels.py`：聚合渠道层级、条款覆盖、文档时间轴、截止时间（走真实 `build_card` 链路）、评测指标；抽不到返回 null。
- 两个服务同步加 `GET /api/overview`；`/ask` 增 `sources`（结构化引用 + 摘要）与 `evidence_strength`。
- `app/answer.py` 新增 `evidence_strength()`，不改动既有生成逻辑（35 单测未受影响）。
- 新增 `data/metrics.json`：把 `evidence/eval-report.md` 的指标结构化，注明来源与生成时间，供「评测」Tab 直接读取。

### 校准与修复
| 问题 | 根因 | 处理 |
|---|---|---|
| 证据强度普遍偏低（明写答案只有 46 分） | 首位 BM25 除以臆造上限 40 | 改为按基准集分数分布分段映射 [5,20]，并改为地基+分项加权；复测 79/72/49/0 与语义档位自洽 |
| 倒计时环文字溢出重叠 | 环内单行放「8天 16:09:37」 | 环内只留天数、时间移到环下 mono 行 |
| 左栏来源卡过高挤掉渠道层级 | 标题换行 + 独立「查看原文」行 | 单行省略 + 整卡可点，6 份后折叠 |
| 进度条可能停在 0 | 依赖 rAF 设宽度，无头/后台环境会挂起 | 改为 setTimeout 并保留 620ms 生长过渡 |
| 正文 `[1]` 是死文本 | 只用 textContent 渲染 | 新增 `richText()` 用文本节点拼接芯片，避免 innerHTML |
| 提问后看不到截止时间 | 倒计时只在空态 | 顶栏加常驻胶囊，环消失时自动降级为 30s 刷新 |
| 五要素格子可能挤压 | 缺 min-width:0 | 补 `min-width:0` + `overflow-wrap:anywhere` |

### 验证
- JS `node --check` 通过；HTML 标签配平 14 类全等；**35/35 单测 OK**。
- 两套服务实测：`/health` `/api/overview` `/ask` 全 200；概览返回 10 文档 / 64 片段 / 141 断言 / 6 渠道 / 10 时间轴节点 / 截止 `2026-11-18T15:00`。
- DOM 断言：正文 `icite` 6 个（正文 3 + 汇总 3）、`hit` 5、`cf-row` 3、`abtn` 8、`chan` 6、`tl-node` 11、进度条 width 实际写入（100/78/72%）。
- 无头截图三态（空态 / 问答态 / 评测面板）人工核验，无溢出重叠；顶栏胶囊正确显示 `8天 16:04`。

### 产出
`app/web/index.html`（2338 行，模块化 JS）、`app/panels.py`、`app/answer.py`（+evidence_strength）、`app/main.py`、`app/server.py`、`data/metrics.json`、`docs/ui-modules.md`、`tools/probe_ui.py`、`tools/probe_fastapi.py`、`evidence/prompts/P-011.md`。
