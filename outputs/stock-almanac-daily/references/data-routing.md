# 数据路由与时间窗口

## 原则

为每个事实指定唯一主来源。不要用两个来源查询同一数字后选择更符合观点的一项，也不要重复计分。

## 代码格式

| 标的 | WeStock | hithink-finance |
|---|---|---|
| 沪市股票 | `sh600519` | `600519.SH` |
| 深市股票 | `sz000001` | `000001.SZ` |
| 上证指数 | `sh000001` | `000001.SH` |

名称不确定时先用 `westock search <名称>` 或 `hithink-finance symbol search --q <名称>`。仅接受沪深A股；北交所、境外证券、基金或其他资产不进入本Skill分析范围。

## 阶段路由

### 交易日与大盘

```bash
westock trade-calendar --date <YYYY-MM-DD>
westock market-overview --type all --date <analysis_session>
westock quote sh000001,sz399001,sz399006 --date <analysis_session>
westock changedist
```

`changedist`是实时截面；只有返回时点与评分日一致时才参与评分。优先提取：三大指数、成交额相对20日均值、上涨占比、涨跌停、新高新低、MA20/60、两融变化、全市场估值分位和风格轮动。

### 宏观与全球风险

先确认有效短名：

```bash
westock macro list --region cn
westock macro list --region us
```

再查询中国核心宏观、货币供给、社融、资金成本、期限利差、股债风险溢价，以及VIX、美元、美联储流动性和海外主要指数。宏观数据同时记录所属期和发布日期，不用新闻数字替代结构化宏观。

全球事件只检索对A股有明确传导路径的事项，用WebSearch检索过去72小时的全球金融、货币政策和大宗商品事件，以及影响A股的主要财经事件；记录链接与发布日期，只作定性证据。

最多保留3个真正影响风险偏好、汇率、利率、商品或中国行业政策的事件，过滤泛资讯。

### 板块

```bash
westock sector ranking
westock hot sector
westock search <板块名> --type sector
westock sector constituent <板块代码>
westock sector info <板块代码>
westock sector valuation <板块代码>
westock report list <板块代码> --limit 8
```

板块/题材行情与成份可用hithink-finance指数接口交叉（`index catalog` 按类别列出同花顺指数，`index snapshot`/`index constituents` 查行情与成份）；市场热度可叠加 `special hot-stock`（当前热股榜）与 `special limit-up-ladder`（30日连板天梯）。

仅对文档明确支持的申万行业调用：

```bash
westock sector forecast <申万行业代码>
westock sector finance <申万行业代码>
westock fund north-holding <申万行业代码>
```

板块语义研究：用WebSearch检索"<板块>近期催化、价格、产业趋势和风险"（7日窗口）与"<板块>景气、盈利预期、估值和主要分歧"（60日窗口），只核实定性事件，不补造数据。

拥挤度三项分位（评分规则见 `scoring.md`）的数据来源：板块指数近一年日K（计算 RSI(14) 当前值在近一年中的分位）；换手率与成交额占全市场比重取近5日均值，与近一年分布比较得分位。板块指数历史K线接口不可用时，可用板块成交额前5的头部成份股对应指标加权近似，并在台账注明近似口径；三项均不可得时按中性50%分位处理并降低置信度。

仅保留能影响收入、利润、估值或资金偏好的信息。不把重复转载和单一情绪化标题计作多重催化。

### 候选股与个股

优先批量获取，最终入围后再逐只深挖：

```bash
westock quote <codes> --date <analysis_session>
westock technical <codes>
westock finance <codes> --limit 4
westock consensus <codes>
westock events <codes>
westock risk <codes>
westock fund flow <codes>
westock fund lhb <codes> --start <date> --end <analysis_session>
westock fund margin <codes>
westock fund block <codes>
westock fund north-holding <codes>
westock news list <codes> --limit 8
westock notice list <codes> --limit 8
westock report list <code> --limit 8
```

严格区分：

- `westock lhb`：全市场龙虎榜。仅支持 `--date` 指定单日，不支持 `--start/--end` 区间；多日需逐日查询。
- `westock fund lhb <代码>`：指定股票龙虎榜明细，支持 `--start/--end` 区间。
- `westock fund flow`：主力和大小单资金，不等于机构资金。
- `westock fund north-holding`：季度持仓，不等于昨日流入。
- `westock fund margin`：杠杆资金，不等于机构观点。
- `westock fund block`：大宗交易，不自动代表看多或看空。

hithink-finance补充结构化数据（全部加 `--format json`，多代码用逗号分隔 `--thscodes`）：

```bash
hithink-finance market snapshot --thscodes <600519.SH,...> --format json
hithink-finance market history --thscodes <600519.SH> --format json
hithink-finance financials indicators --thscodes <600519.SH> --format json
hithink-finance valuation snapshot --thscodes <600519.SH,...> --format json
hithink-finance special dragon-tiger --format json
hithink-finance special limit-up-pool --format json
hithink-finance special anomaly-stock --thscodes <600519.SH,...> --format json
```

公司语义证据（业绩、订单、公告、监管、风险、产业链关系核查）用WebSearch检索公开报道与公司公告，只核实定性事件并记录链接与日期，不补造数据。

研报机构归因以标题和正文为准；只有不可靠broker字段时写“一份研报”。产业链关系优先引用公司公告、年报或投资者关系记录；只有研报映射时标记“市场映射，待公告确认”。

## 默认窗口

| 数据 | 窗口 |
|---|---|
| 行情、大盘、板块 | 最近完整交易日 |
| 技术 | 60日，必要时扩展到120/250日 |
| 主力资金 | 1/5/20个交易日 |
| 龙虎榜 | 评分日及最近5个交易日 |
| 全球新闻 | 72小时 |
| 板块、公司新闻 | 7日 |
| 研报 | 60日 |
| 公告与事实核查 | 180日 |
| 大宗交易 | 20个交易日 |
| 宏观 | 最新已公开期 |
| 北向持仓 | 最新季与次新季 |

## 证据记录

hithink-finance：记录完整命令、`--format json` 信封的 `ok`/`error` 字段、数据日期和口径。精确数值从JSON输出读取，不从截断摘要计算；密钥不写入命令参数、日志或项目文件。

WeStock：记录命令、字段、返回日期、所属期、发布日期和口径。空结果区分“不支持、无披露、无事件、接口故障”，不要将空结果解释为利好或利空。

WebSearch：仅用于定性事件核实（新闻、公告、事实核查），记录链接与发布日期；不得用网页结果补造结构化数值。
