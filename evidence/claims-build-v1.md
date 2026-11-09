# 离线断言资产构建记录

- 构建时间：2026-11-09T20:50:15
- 模型：`deepseek-flash`；端点：`https://api.deepseek.com`（按官方文档，未照记忆填写）
- 凭据来源：进程环境变量，**未写入任何文件、未进入仓库**
- 文档数：6；抽取断言：157；原文校验通过：155/157
- 本次消耗：约 49986 tokens
- 用途边界：仅构建期运行；`data/claims.json` 固化落盘，运行时零依赖

## 校验规则

`evidence_span` 去空白后必须是通知原文的连续子串，否则标记 `evidence_verified=false`。未通过的条目**保留而非删除**，用于展示 LLM 会改写或编造，以及本系统如何用程序拦住它。

## 未通过项

- official-05-C01: evidence_span 未在原文找到（疑似改写/编造）
- official-06-C42: evidence_span 未在原文找到（疑似改写/编造）
