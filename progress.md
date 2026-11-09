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
