# 股市老黄历·小红书日报半自动流水线 执行记忆

## 2026-08-24 00:00 运行（部分完成）

- analysis_session=2026-08-21；nashnova update 已执行（0.2.2 最新）；trade-calendar 确认交易日，盘前版不标休市。
- 取数全部完成，证据台账已落盘：`reports/stock-almanac/2026-08-24-evidence.md`。
- 结论：市场中性（≈51）；板块仅贵金属入选（≈79）；中金黄金/山金国际=条件式参与，赤峰黄金/中际旭创=逢回调观察。
- 降级记录：NashNova fin news（72h/7d）与 fin websearch（7d）均 coverage=empty → 新闻源改用 WeStock hot news/news list（符合 Skill 降级规则）。
- 中断点：HTML 生成、validate_report.py 校验、竖版截图、小红书预填未执行（用户插入 git 推送指令）。
- 命名惯例确认：产物以运行日期为前缀（参照 2026-08-23 批次）。
- 注意：validate_report.py 禁用词包含字面 "ETF"，HTML 正文与文案中不得出现该字符串；湖南黄金 2026-08-21 停牌须硬过滤。
