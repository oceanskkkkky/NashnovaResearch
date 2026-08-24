# 项目长期记忆（NashnovaResearch）

## 金融数据 CLI（hithink-finance 同花顺）

本工作区默认用 hithink-finance（同花顺）取金融数据；NashNova 已弃用（本机未安装，原路径属另一台机器 tizyt）。

- Skill 位于 `C:\Users\tizytian\.workbuddy\skills\hithink-finance\`（SkillHub 安装，已扁平化为标准结构）
- CLI 完整路径：`C:\Users\tizytian\.workbuddy\binaries\node\versions\22.22.2-1\hithink-finance`
- 统一凭据：环境变量 `HITHINK_FINANCE_API_KEY` → `%APPDATA%\hithink-finance\credentials.env`；Key 申请 https://fuyao.aicubes.cn/admin；密钥不拼命令参数/不落项目文件
- 常用命令（均加 `--format json`）：`symbol search`、`market snapshot/history/calendar`、`index catalog/constituents/snapshot/history`、`financials income/balance-sheet/cash-flow/indicators`、`valuation snapshot`、`special limit-up-pool/limit-up-ladder/dragon-tiger/anomaly-stock/hot-stock`
- 代码格式：股票 `600519.SH`/`000001.SZ`，上证指数 `000001.SH`
- 能力边界：不提供新闻、研报语义、宏观、资金流向——这些归 WeStock + WebSearch（只核实定性事件，不补造数据）
- 判定失败：退出码非0或信封 `ok!=true`；401/403 = 检查凭据，不重试
- Git Bash 下 `skillhub`/`hithink-finance` 裸命令可能因 PATH 失效，用完整路径调用

## 股市老黄历日报设计

- Skill 位于项目级：`E:\WS\NashnovaResearch\.workbuddy\skills\stock-almanac-daily\`（WorkBuddy 实际加载）；`outputs/stock-almanac-daily\` 为发布镜像，改动后必须全量同步。2026-08-24 已补齐 mobile-spec、移动端骨架和评分脚本，当前两目录完全一致。
- Prompt 文件：`outputs/stock-almanac-skill-prompt.md`。
- 老黄历只用于标题和一行宜/忌，金融评分不含玄学；推荐范围仅为沪深A股，不分析ETF。
- V1 使用热点板块成份、龙虎榜、资金榜、研报及自选构成可追溯候选池，不做全A股扫描。
- 2026-08-24 起数据源为 hithink-finance 与 WeStock 按能力域分工（hithink 管行情/指数/板块/财报/估值/特色数据，WeStock 管交易日历/大盘/宏观/资金/公告/风险，新闻研报事实核查走 WeStock+WebSearch），禁止同一事实双源重复计分；弱市允许零推荐。
- 2026-08-24 板块评分 V2：原价格30%+资金25%改为35%量价正交趋势因子（完整板块横截面回归 `zF=α+βzP+ε`，以残差分位R提取独立资金信息），释放20分为拥挤风险预算；拥挤度由RSI/换手率/成交占比分位及5日加速度构成，最高扣20分并触发70/80/90三级预警。确定性实现为 `scripts/calculate_sector_score.py`。
- 输出固定宽度桌面端常规金融研报网页，正文言简意赅，默认10分钟内读完。
- 2026-08-23 起 skill 支持 `format=desktop|mobile|both`：mobile 为 460px 竖屏卡片流（可见预算≤1500单位、emoji≤15）+ 小红书笔记文案 `.md`，骨架 `assets/report-shell-mobile.html`，校验用 `--format mobile`。
- 2026-08-23 规则更新：摘要栏目标题固定为「行情摘要」（id 仍为 executive-summary）；证据区不进产物，台账存 `YYYY-MM-DD-evidence.md` 旁车文件，正文禁止 `[E01]` 编号；入榜门槛放宽为常规≥65/中性≥68/防守≥70，选股上限5只。
- 个性化股票建议可给出有数据条件的买入观察、持有、减仓、止盈或回避意见，必须同时给确认条件、失效位与风险。
- “宏观大势”作为独立栏目固定置于“大盘判断”上方，可加入最多3条重点新闻跟进；每条必须说明A股传导、受益/承压方向和后续跟踪点。
- 前端视觉采用 `trading-almanac-ui` 的纸墨体系：1220px固定桌面宽度、深墨绿页头、米纸纹理、朱砂/金色点缀、宋体标题和直角细框卡片；保持静态无JS，并按A股习惯使用红涨绿跌。
- 2026-08-24 skill 新增 `references/xhs-preflight.md`：移动端HTML与小红书笔记文案生成时强制做合规微调——个股不写精确买卖价位（用均线/形态条件表达），免责声明必须出现在可见正文（行情摘要或页脚），绝对化措辞改为带数据口径陈述，禁止导流/诱导互动/收益承诺/指令性买卖话术，话题标签用中性研究词（#A股 #股票复盘 等）；桌面端研报不受此规则约束保留完整点位。
- 2026-08-24 移动端个股卡片顺序改为：逻辑 → 关键事实 → 当前建议 → 观察确认（形态描述）→ 止盈/减仓触发（形态描述）→ 失效条件（均线/支撑位描述）→ 催化/风险；不再出现「买入观察区间」/「止盈/减仓」/「失效位」精确价格小节。
- 2026-08-24 数据降级：本机 `user = tizytian` 没有安装 NashNova CLI（按原 memory 路径在另一台机器 `user = tizyt`）；同时 westock-premarket fetch 需 `SNP_MCP_TOKEN` 未配置。降级路径：用 WeStock 结构化数据 + WebSearch 公开报道核实定性事件（仅核实事件、不补造数据），台账显式记录降级披露。
- 2026-08-24 小红书发布链路：skill 自带 `social-auto-upload` 是 Linux 环境（`/root/clawd`），本机 Windows 不可用；临时方案 `outputs/xhs-publish.js` + `outputs/xhs-shoot.js`（Playwright 持久化 profile 位于 `E:\WS\NashnovaResearch\.workbuddy\xhs-profile`），发布流程：弹出 headful Chromium → 轮询等待 URL 脱离 /login → 直达 `/publish/publish?type=image` → 找 `input[type=file][multiple]` 一次传 8 张图（否则单文件 input 逐张循环）→ 填 `input[placeholder*="标题"]` + `[contenteditable="true"]` → 截 `xhs-final.png` 给用户审核 → **不点发布**，由用户人工点击。
