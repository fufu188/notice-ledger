# 官方信息抓取存档

抓取时间：**2026-11-09 18:40 ~ 19:10 (GMT+8)**
抓取方式：用户本人在 Edge 窗口登录 `boxuegu.com` 后，通过 CDP 在同一会话内读取页面 DOM 文本（天然带登录态，未提取或保存任何 cookie / 密码）。
范围授权：用户在本轮明确指示「打开链接、我来登录、你去查」，对应 `CONFIRM.md` B5。

## 存档文件与来源

| 文件 | 来源 URL | 页面标题 | 抓取时是否需登录 |
|---|---|---|---|
| `raw-home.txt` | https://www.boxuegu.com/match/ | 传智杯大赛官网-全国大学生计算机应用能力与数字素养大赛 | 是（未登录会跳 passport） |
| `raw-notice.txt` | https://www.boxuegu.com/matchNotice/ | 传智杯大赛-大赛通知 | 是 |
| `raw-track-ai.txt` | https://www.boxuegu.com/match/ 赛道简介面板（`.item-right`） | AI创新应用挑战赛 赛道卡 | 是 |
| `raw-track-detail.txt` | https://www.boxuegu.com/matchTrack/detail/?id=10039 | 传智杯大赛-赛道详情 | 是 |
| `raw-process.txt` | https://xuexi.boxuegu.com/matchProcess/?id=186752 | 传智杯大赛-参赛流程（AI 赛项，省赛 tab） | 是（个人中心） |
| `raw-center.txt` | https://xuexi.boxuegu.com/matchCenter/ | 传智杯大赛-个人中心（我的竞赛） | 是（个人中心） |

## 抓取说明

- 文本为 `document.body.innerText` 原样输出，**未做改写、未做摘要**；仅 `raw-track-ai.txt` 取的是赛道面板容器。
- 页面为 Vue 单页应用，部分 tab（如「国赛」）点击后显示 **「赛事尚未开启」**，即国赛阶段内容尚未上线。
- 未抓取：任何需要额外授权的页面、任何含支付/身份证明的页面。
- 原文中的措辞差异（例如省赛提交入口「kdocs 链接」与「缴费后个人中心查看」并存）**照原样保留**，未做统一。

## 与既有文档的关系

`findings.md` 第 2 节据此重写；`CONFIRM.md` 中由本轮核实解决的条目已更新状态。凡本目录未覆盖的内容，仍按「待确认」处理。
