# 项目长期记忆（NashNova）

## 金融数据 CLI（NashNova）

本工作区默认用 NashNova 取金融数据（股票/ETF/指数/财报/电话会/新闻/研报），
Skill 位于 `C:\Users\tizyt\.workbuddy\skills\nashnova-fin\`。

- CLI 完整路径：`C:\Users\tizyt\.workbuddy\binaries\python\envs\default\Scripts\nashnova.exe`
- 运行：用完整路径或 `C:\Users\tizyt\.workbuddy\binaries\python\envs\default\Scripts\` 加到 PATH 后跑裸 `nashnova`
- 已登录 prod 环境，会话在 `%APPDATA%\nashnova\session.json`
- 常用命令：`nashnova fin quote/technical/financials/call/news/websearch/research`、`nashnova update`
- 完整响应写入 `evidence/YYYY-MM-DD/`，stdout 只是摘要；需精确数值读 evidence
- 退出码 5 = 会话失效需重新登录（Token 走 stdin，不拼命令/不落盘）

## 股市老黄历日报设计

- Skill 已迁移至项目级：`D:\UGit\nashnova\.workbuddy\skills\stock-almanac-daily\`（随仓库 git 管理；原用户级目录已删除）。
- Prompt 文件：`outputs/stock-almanac-skill-prompt.md`。
- 老黄历只用于标题和一行宜/忌，金融评分不含玄学；推荐范围仅为沪深A股，不分析ETF。
- V1 使用热点板块成份、龙虎榜、资金榜、研报及自选构成可追溯候选池，不做全A股扫描。
- NashNova与WeStock按能力域分工，禁止同一事实双源重复计分；弱市允许零推荐。
- 输出固定宽度桌面端常规金融研报网页，正文言简意赅，默认10分钟内读完。
- 2026-08-23 起 skill 支持 `format=desktop|mobile|both`：mobile 为 460px 竖屏卡片流（可见预算≤1500单位、emoji≤15）+ 小红书笔记文案 `.md`，骨架 `assets/report-shell-mobile.html`，校验用 `--format mobile`。
- 2026-08-23 规则更新：摘要栏目标题固定为「行情摘要」（id 仍为 executive-summary）；证据区不进产物，台账存 `YYYY-MM-DD-evidence.md` 旁车文件，正文禁止 `[E01]` 编号；入榜门槛放宽为常规≥65/中性≥68/防守≥70，选股上限5只。
- 个性化股票建议可给出有数据条件的买入观察、持有、减仓、止盈或回避意见，必须同时给确认条件、失效位与风险。
- “宏观大势”作为独立栏目固定置于“大盘判断”上方，可加入最多3条重点新闻跟进；每条必须说明A股传导、受益/承压方向和后续跟踪点。
- 前端视觉采用 `trading-almanac-ui` 的纸墨体系：1220px固定桌面宽度、深墨绿页头、米纸纹理、朱砂/金色点缀、宋体标题和直角细框卡片；保持静态无JS，并按A股习惯使用红涨绿跌。
