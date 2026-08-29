from __future__ import annotations

import html
import json
from pathlib import Path

TARGET = "2026-08-27"
ROOT = Path("E:/WS/NashnovaResearch")
EV = ROOT / "evidence"
OUT = ROOT / "reports/stock-almanac"
OUT.mkdir(parents=True, exist_ok=True)
market = json.loads((EV / f"{TARGET}-market-raw.json").read_text(encoding="utf-8"))
market_score = json.loads((EV / f"{TARGET}-market-score.json").read_text(encoding="utf-8"))
sector_score = json.loads((EV / f"{TARGET}-sector-score-v2.json").read_text(encoding="utf-8"))
sector_raw = json.loads((EV / f"{TARGET}-sector-raw-v2.json").read_text(encoding="utf-8"))
stocks = json.loads((EV / f"{TARGET}-stock-candidates.json").read_text(encoding="utf-8"))
deep = json.loads((EV / f"{TARGET}-stock-deep-summary.json").read_text(encoding="utf-8"))

idx = market["indices"]
breadth = market["market_breadth"]["dated_market_overview"]
turnover = market["turnover"]
score = market_score["result"]["total_score"]
state = market_score["result"]["market_state"]
reg = sector_score["regression"]
sectors = sector_score["sectors"]
top_sectors = sectors[:5]
raw_by_name = {x["name"]: x for x in sector_raw["sectors"]}
selected = stocks["selected"]
verified = stocks["deep_verified"]


def f(v, digits=2):
    return "—" if v is None else f"{v:.{digits}f}"


def money(v):
    return "—" if v is None else f"{v/100000000:.2f}亿元"


def stock_table_rows():
    rows = []
    for x in verified:
        cls = "up" if x["eligible_for_selection"] else "muted"
        rows.append(f"<tr><td><b>{html.escape(x['name'])} {x['a_share_code'][:6]}</b></td><td>{x['sector_name']}</td><td>{x['stock_score']:.1f}</td><td class='{cls}'><b>{x['final_score']:.1f}</b></td><td>{x['confidence']}%</td><td>{html.escape(x['decision'])}</td></tr>")
    return "".join(rows)


def sector_rows():
    rows = []
    for x in top_sectors:
        c = x["crowding"]
        cls = "up" if x["sector_heat"] >= 65 else "muted"
        rows.append(f"<tr><td><b>{x['name']}</b></td><td>{f(x['price_momentum_p'])}</td><td>{f(x['fund_flow_f'])}</td><td>{f(x['orthogonal_flow_r'])}</td><td>{f(x['trend_confirmation_t'])}</td><td>{f(c['crowding_score'])}</td><td>{f(c['penalty'])}</td><td class='{cls}'><b>{f(x['sector_heat'])}</b></td></tr>")
    return "".join(rows)


def selected_cards(desktop=True):
    cards = []
    for x in selected:
        valuation = x.get("valuation") or {}
        finance = x.get("finance_latest") or {}
        revenue = float(finance.get("OperatingRevenue") or 0) / 100000000
        profit = float(finance.get("NPParentCompanyOwners") or 0) / 100000000
        if desktop:
            observe = f"不设置立即追价区间。优先等待价格回到MA60约{x['technical']['ma60']:.2f}元附近缩量企稳，并在后续交易日重新获得资金净流入确认。"
            invalid = f"连续收盘跌破MA60约{x['technical']['ma60']:.2f}元，或半年报增长逻辑、光纤需求出现新的重大不利证据。"
        else:
            observe = "等待回踩中期均线附近缩量企稳，并由后续资金重新转入确认。"
            invalid = "连续跌破中期均线，或半年报增长逻辑与光纤需求出现重大不利变化。"
        cards.append(f"""<article class='stock'><div class='stock-head'><div><h3>{x['name']} {x['a_share_code'][:6]}</h3><p class='note'>{x['sector_name']}｜FinalScore {x['final_score']:.1f}｜置信度{x['confidence']}%</p></div><span class='pill'>{html.escape(x['decision'])}</span></div><dl><dt>逻辑</dt><dd>{html.escape(x['logic'])}</dd><dt>关键事实</dt><dd>{finance.get('date','最新期')}营收约{revenue:.2f}亿元、归母净利润约{profit:.2f}亿元；评分日收盘{x['close']:.2f}元，近20日涨{x['returns_pct']['20']:.2f}%，20日资金净流入{money(x['flow']['main_net_cny']['20'])}；PE-TTM约{f(valuation.get('pe_ttm'))}倍。</dd><dt>当前建议</dt><dd>{html.escape(x['decision'])}。</dd><dt>观察确认</dt><dd>{observe}</dd><dt>减仓触发</dt><dd>冲高后放量滞涨，或5日资金由净流入转为持续净流出。</dd><dt>失效条件</dt><dd>{invalid}</dd><dt>风险</dt><dd>{'、'.join(x['risk_notes'])}。</dd></dl></article>""")
    return "".join(cards)


top = top_sectors[0]
top_raw = raw_by_name[top["name"]]["raw_aggregate_summary"]
market_summary = f"上证{idx['上证指数']['change_pct']:+.2f}%、深证{idx['深证成指']['change_pct']:+.2f}%、创业板{idx['创业板指']['change_pct']:+.2f}%；上涨{breadth['CNT_RED']}家、下跌{breadth['CNT_GREEN']}家，两市成交{turnover['amount_100m_cny']:.0f}亿元。"

css = """
:root{--paper:#f3efe6;--deep:#e8e0d0;--ink:#18332d;--body:#293631;--red:#a83e32;--green:#17705e;--gold:#b98532;--line:rgba(24,51,45,.22);--card:#fffdf7;--muted:#68736d;--serif:STSong,SimSun,serif;--sans:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}*{box-sizing:border-box}body{margin:0;background:var(--deep);color:var(--body);font:14px/1.68 var(--sans)}.topbar{background:var(--ink);color:#f8f2e5;border-bottom:3px solid var(--gold)}.topin,.page{width:1220px;margin:auto}.topin{min-height:72px;display:flex;align-items:center;justify-content:space-between}.brand{font:700 23px var(--serif)}.badge,.tag,.pill{border:1px solid var(--line);padding:6px 9px}.topbar .badge{border-color:#8d947f;color:#e8c887}.seal{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;margin-right:10px;border:1px solid #e8c887;color:#e8c887;font:700 20px var(--serif)}.page{background:var(--paper);padding:34px 24px 48px}.hero{display:grid;grid-template-columns:1.45fr .75fr;gap:20px}.hero h1{font:700 45px/1.15 var(--serif);color:var(--ink);margin:8px 0}.eyebrow,.kicker{color:var(--gold);font-weight:700;letter-spacing:.12em;font-size:11px}.dark{background:var(--ink);color:#f8f2e5;padding:22px;border-left:5px solid var(--gold)}.dark h2{font:700 25px var(--serif);color:#e8c887}.section{margin-top:18px}.card{background:var(--card);border:1px solid var(--line);padding:20px}.head{display:flex;justify-content:space-between;align-items:center}.head h2{font:700 29px var(--serif);color:var(--ink);margin:2px 0 12px}.grid{display:grid;gap:12px}.g4{grid-template-columns:repeat(4,1fr)}.g3{grid-template-columns:repeat(3,1fr)}.metric,.panel{padding:13px;border:1px solid var(--line);background:#fffaf0}.metric span{display:block;color:var(--muted);font-size:12px}.metric b{font-size:18px;color:var(--ink)}.up{color:var(--red)}.down{color:var(--green)}.muted,.note{color:var(--muted)}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid var(--line);text-align:left}.stock{margin-top:14px;border:1px solid var(--line);border-top:3px solid var(--gold);padding:16px}.stock-head{display:flex;justify-content:space-between}.stock h3{font:700 24px var(--serif);color:var(--ink);margin:0}dl{display:grid;grid-template-columns:90px 1fr;margin:10px 0 0}dt,dd{padding:7px 0;border-bottom:1px dashed var(--line)}dt{color:var(--muted)}dd{margin:0}.risk{border-left:5px solid var(--red)}.disclaimer{background:#efe8da;padding:12px}.footer{text-align:center;padding:22px;background:var(--ink);color:#d7ddd4}details{margin-top:18px;padding:14px;border:1px solid var(--line);background:#eee7d8}body{min-width:1268px}
"""

desktop = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta name='description' content='2026年8月27日A股盘后研究日报'><title>A股选股日报｜{TARGET}</title><style>{css}</style></head><body><header class="topbar"><div class='topin'><div class='brand'><span class="seal">历</span>股市老黄历 · A股研究</div><span class='badge'>盘后 · V2</span></div></header><main class='page'><header id='cover' class='hero'><div><div class='eyebrow'>评分交易日 {TARGET} · 北京时间盘后</div><h1>放量回升，<span class='up'>科技接力</span></h1><p>{market_summary} 29行业量价正交后，消费电子、通信设备、半导体和汽车零部件达到65分门槛。科技方向扩散，但高位个股仍需回避追价。</p><p><b>宜</b> 等回踩确认与资金延续　<b>忌</b> 追涨停和极端估值</p><p class='note'>老黄历仅为标题包装，正文为公开数据研究。</p></div><aside class='dark'><div>数据截至 {TARGET} 收盘</div><h2>{state}偏强 · 1只条件观察</h2><p>环境分{score:.1f}，仍低于进攻阈值65。长飞光纤刚好达到68分门槛，但评分日涨停且估值较高，因此只列条件观察，不构成立即买入指令。</p></aside></header>
<section id='executive-summary' class='section card'><div class='head'><div><div class='kicker'>00 / brief</div><h2>行情摘要</h2></div><span class='tag'>结论先行</span></div><div class='grid g4'><div class='metric'><span>市场状态</span><b>{state} {score:.1f}</b></div><div class='metric'><span>市场宽度</span><b>涨{breadth['CNT_RED']} / 跌{breadth['CNT_GREEN']}</b></div><div class='metric'><span>两市成交</span><b>{turnover['amount_100m_cny']:.0f}亿元</b></div><div class='metric'><span>首位板块</span><b>{top['name']} {top['sector_heat']:.2f}</b></div></div><p>核心矛盾由前一日“缩量反弹”转为“成交回升、科技扩散”，但60日趋势仍弱，且通信设备成交占比已处极端分位。策略上可提高观察优先级，但不把单日普涨等同于全面进攻。</p></section>
<section id='macro' class='section card'><div class='head'><div><div class='kicker'>01 / macro</div><h2>宏观大势</h2></div><span class='tag'>流动性 · 风险</span></div><div class='grid g3'><div class='panel'><b>国内流动性温和</b><p>截至目标日已披露的7月货币与融资数据延续温和环境，宏观流动性维度58分。</p></div><div class='panel'><b>科技催化形成传导</b><p>外部检索定性复核显示AI算力、光通信、半导体及电子元件关注度上升，与行业结构化评分方向一致。</p></div><div class='panel'><b>全球风险按中性降级</b><p>缺少同一时点可审计的VIX、美元、美债与海外指数数据，统一按50分，不代表外部风险较低。</p></div></div></section>
<section id='market' class='section card'><div class='head'><div><div class='kicker'>02 / market</div><h2>大盘判断</h2></div><span class='tag'>{TARGET} 收盘</span></div><div class='grid g4'><div class='metric'><span>上证指数</span><b>{idx['上证指数']['close']:.2f} <i class='up'>+{idx['上证指数']['change_pct']:.2f}%</i></b></div><div class='metric'><span>深证成指</span><b>{idx['深证成指']['close']:.2f} <i class='up'>+{idx['深证成指']['change_pct']:.2f}%</i></b></div><div class='metric'><span>创业板指</span><b>{idx['创业板指']['close']:.2f} <i class='up'>+{idx['创业板指']['change_pct']:.2f}%</i></b></div><div class='metric'><span>成交/20日均量</span><b>{turnover['vs_twenty_day_average_pct']:.2f}%</b></div></div><div class='grid g3' style='margin-top:12px'><div class='panel'><b>宽度显著改善</b><p>上涨占比{breadth['RATIO_UP']:.2f}%，带日期口径涨停{breadth['CNT_REACH_UPLIMIT']}家、跌停{breadth['CNT_REACH_DNLIMIT']}家。</p></div><div class='panel'><b>量价配合增强</b><p>成交较前日增加约3172亿元，达到5日均量110.11%，但仍只有20日均量93.80%。</p></div><div class='panel'><b>中期趋势未完全修复</b><p>三大指数20日收益转强，但60日收益仍为负，市场环境分停留在63.3。</p></div></div><p class='note'>涨停家数存在WeStock带日期74、实时分布78、hithink池76的口径差异；正式评分采用74，不取平均。</p></section>
<section id='sectors' class='section card'><div class='head'><div><div class='kicker'>03 / sectors</div><h2>板块筛选</h2></div><span class='tag'>4个方向达标</span></div><table><thead><tr><th>行业</th><th>价格P</th><th>资金F</th><th>正交R</th><th>趋势T</th><th>拥挤C</th><th>扣分</th><th>热度</th></tr></thead><tbody>{sector_rows()}</tbody></table><div class='grid g3' style='margin-top:12px'><div class='panel'><b>消费电子领跑</b><p>热度{top['sector_heat']:.2f}，P={top['price_momentum_p']:.2f}、R={top['orthogonal_flow_r']:.2f}，拥挤度仅{top['crowding']['crowding_score']:.2f}。</p></div><div class='panel'><b>通信设备资金确认</b><p>正交资金R=89.29，但成交占比处近一年97.11分位，板块强而不宜无条件追涨。</p></div><div class='panel'><b>半导体需辨别强弱</b><p>价格P=80.18，但独立资金R仅28.57，说明价格强度领先于不可由价格解释的资金强度。</p></div></div><p class='note'>29行业完整横截面回归：样本{reg['sample_size']}、覆盖率{reg['coverage']:.0%}、beta={reg['beta']:.4f}。催化和基本面缺少统一横截面证据，按50分降级。</p></section>
<section id='picks' class='section card'><div class='head'><div><div class='kicker'>04 / picks</div><h2>核心选股</h2></div><span class='tag'>中性市门槛 68</span></div><table><thead><tr><th>股票</th><th>行业</th><th>个股分</th><th>最终分</th><th>置信度</th><th>结论</th></tr></thead><tbody>{stock_table_rows()}</tbody></table>{selected_cards(True)}<p class='note'>剑桥科技67.5分，距门槛0.5分；飞龙股份、共达电声、长盈通因过热、估值或盈利匹配不足未入榜。</p></section>
<section id='risks' class='section card risk'><div class='kicker'>05 / risks</div><h2>风险提示</h2><ul><li>长飞光纤评分日涨停，近20日涨幅62.68%，估值与均线偏离均处高位，68分仅代表刚过筛选线。</li><li>通信设备成交占比达到近一年97.11分位，板块热度继续上升时波动也可能放大。</li><li>半导体价格强但正交资金确认不足，需防止单日行情被误判为持续主线。</li><li>市场环境分63.3，仍未进入65分以上进攻区，60日趋势和中长期成交尚未完全修复。</li></ul><p class='disclaimer'><b>免责声明</b>：以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。任何投资决策应结合个人风险承受能力、资金状况和投资目标独立判断，必要时咨询持牌专业机构。过往表现不预示未来收益。</p></section>
<details id='methodology'><summary>方法与数据降级说明</summary><p>市场环境=30%指数与风格+25%宽度与情绪+20%成交与流动性+15%国内宏观+10%全球风险。行业以1/5/20日价格和资金横截面正交，板块热度扣最高20分拥挤惩罚。个股最终分=15%市场+25%行业+60%个股-风险扣分。</p><p>外部检索只用于定性核验催化，正式评分数值采用WeStock和hithink-finance结构化数据。缺失项不补造。</p></details></main><footer class='footer'>数据来源：WeStock、hithink-finance、公司公告、研报摘要与公开报道复核｜评分日 {TARGET}｜证据台账 {TARGET}-evidence.md</footer></body></html>"""

mobile_css = """
:root{--paper:#f7f3ea;--m-ink:#18332d;--ink:var(--m-ink);--body:#293631;--red:#a83e32;--green:#17705e;--m-gold:#b98532;--gold:var(--m-gold);--line:#e1d9ca;--card:#fffdf7;--muted:#746f65;--serif:STSong,SimSun,serif;--sans:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}*{box-sizing:border-box}body{margin:0;background:#e7e0d2;color:var(--body);font:15px/1.65 var(--sans)}.m-shell{max-width:460px;margin:auto;background:var(--paper);padding-bottom:24px}.top{background:var(--ink);color:#f8f2e5;padding:16px;border-bottom:3px solid var(--gold)}.top b{font:700 19px var(--serif)}.m-seal{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;margin-right:8px;border:1px solid #e8c887;color:#e8c887;font:700 18px var(--serif)}.cover{padding:18px 15px}.date,.kicker{color:var(--gold);font-size:10px;font-weight:700;letter-spacing:.11em}.cover h1{font:700 30px/1.2 var(--serif);color:var(--ink);margin:8px 0}.state{background:var(--ink);color:#f8f2e5;border-left:4px solid var(--gold);padding:12px}.state b{color:#e8c887}.sec{margin:12px;background:var(--card);border:1px solid var(--line);padding:14px}.sec h2{font:700 23px var(--serif);color:var(--ink);margin:3px 0 9px}.line,.kv{display:flex;gap:10px;justify-content:space-between;padding:6px 0;border-bottom:1px dashed var(--line)}.kv{align-items:flex-start}.k{color:var(--muted);min-width:70px}.up{color:var(--red)}.stock{margin-top:10px;border-top:3px solid var(--gold);padding-top:10px}.stock-head{display:block}.stock h3{font:700 21px var(--serif);color:var(--ink);margin:0}.pill{display:inline-block;border:1px solid var(--line);padding:3px 6px}.note{color:var(--muted);font-size:12px}dl{margin:6px 0}dt{color:var(--muted);font-size:12px;margin-top:6px}dd{margin:0}.risk{border-left:4px solid var(--red)}details{margin:12px;padding:12px;border:1px solid var(--line)}footer{text-align:center;padding:18px;background:var(--ink);color:#d7ddd4;font-size:12px}
"""

mobile = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta name='description' content='2026年8月27日A股盘后研究日报移动版'><title>股市老黄历｜{TARGET}</title><style>{mobile_css}</style></head><body><div class="m-shell"><header class='top'><b><span class="m-seal">历</span>股市老黄历 · A股研究</b></header><header id="cover" class='cover'><div class='date'>评分交易日 {TARGET}</div><h1>放量回升，科技接力</h1><p><b>宜</b> 等回踩确认　<b>忌</b> 追涨停</p><div class='state'><b>{state}偏强 · 1只条件观察</b><br>环境分{score:.1f}，仍低于65分进攻线。</div><p class='note'>标题仅为包装，正文为数据研究。</p></header><section id='executive-summary' class='sec'><div class='kicker'>00 / brief</div><h2>行情摘要</h2><div class='line'><span class='k'>指数</span><span>上证+1.13%｜创业板+1.71%</span></div><div class='line'><span class='k'>宽度</span><span>涨3394 / 跌1944</span></div><div class='line'><span class='k'>成交</span><span>21259亿元</span></div><div class='line'><span class='k'>方向</span><span>消费电子、通信设备</span></div><p><b>仅供研究参考，不构成投资建议。</b></p></section><section id='macro' class='sec'><div class='kicker'>01 / macro</div><h2>宏观大势</h2><div class='kv'><span class='k'>国内</span><span>低频宏观与短端流动性维持温和。</span></div><div class='kv'><span class='k'>产业</span><span>AI算力、光通信、半导体关注度上升。</span></div><div class='kv'><span class='k'>外部</span><span>全球风险指标缺失，按中性降级。</span></div></section><section id='market' class='sec'><div class='kicker'>02 / market</div><h2>大盘判断</h2><div class='line'><span class='k'>上证</span><span>3956.57 <span class='up'>+1.13%</span></span></div><div class='line'><span class='k'>深证</span><span>14048.88 <span class='up'>+1.50%</span></span></div><div class='line'><span class='k'>创业板</span><span>3473.35 <span class='up'>+1.71%</span></span></div><p>上涨占比61.15%，成交较前日放大，但仍只有20日均量93.80%。中性偏强，不等于全面进攻。</p></section><section id='sectors' class='sec'><div class='kicker'>03 / sectors</div><h2>板块观察</h2><div class='stock'><h3>消费电子 74.92</h3><p>P=83.93，独立资金R=78.57，拥挤C=35.51，量价资金配合最好。</p></div><div class='stock'><h3>通信设备 69.46</h3><p>独立资金R=89.29，但成交占比处近一年极端分位，强势同时需防波动放大。</p></div><div class='stock'><h3>半导体 69.07</h3><p>价格P=80.18，独立资金R=28.57，价格强于资金确认。</p></div><p class='note'>汽车零部件65.13，同步达到门槛。</p></section><section id='picks' class='sec'><div class='kicker'>04 / picks</div><h2>核心选股</h2>{selected_cards(False)}<p class='note'>剑桥科技67.5分，未达到68分；其余前五候选也因估值、盈利或过热风险未入榜。</p></section><section id='risks' class='sec risk'><div class='kicker'>05 / risks</div><h2>风险提示</h2><ul><li>长飞光纤评分日涨停，近20日涨幅较大。</li><li>通信设备成交占比处极端分位。</li><li>半导体独立资金确认偏弱。</li><li>市场环境尚未进入进攻区。</li></ul><p><b>免责声明</b>：以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。任何决策应结合个人风险承受能力独立判断，过往表现不预示未来收益。</p></section><details id="methodology"><summary>方法与数据说明</summary><p>29行业横截面量价正交，板块再扣最高20分拥挤惩罚。外部检索仅作定性复核，缺失数据不补造。</p></details><footer>数据来源：WeStock、hithink-finance、公司公告<br>评分日 {TARGET}｜仅供研究参考</footer></div></body></html>"""

note = f"""# 8月27日A股复盘：放量回升，科技方向接力

今天三大指数同步收涨：上证+1.13%、深证+1.50%、创业板+1.71%。上涨3394家、下跌1944家，两市成交21259亿元，达到5日均量110.11%，但仍只有20日均量93.80%。

今日宜：等待回踩和资金延续确认。
今日忌：把单日普涨当成全面进攻，追逐涨停和高估值加速段。

**板块观察**

1. 消费电子：热度74.92，价格P=83.93，独立资金R=78.57，拥挤度35.51，量价资金配合最好。
2. 通信设备：热度69.46，独立资金R=89.29，但成交占比处近一年极端分位。
3. 半导体：热度69.07，价格强度高，但独立资金R仅28.57，仍需资金延续验证。
4. 汽车零部件：热度65.13，刚过门槛。

**长飞光纤 601869**

逻辑：半年报利润、光纤需求和多周期资金形成支持，但评分日涨停、近20日涨幅较大且估值较高。

当前建议：不追涨，等待高位消化后再观察。

观察确认：回踩中期均线附近缩量企稳，后续资金重新转入。

失效条件：连续跌破中期均线，或半年报增长逻辑与光纤需求出现重大不利变化。

**风险提醒**

- 长飞光纤仅以68.0分刚好过线，不代表确定性收益。
- 通信设备交易拥挤可能在强势阶段放大波动。
- 市场环境分63.3，仍低于65分进攻线。
- 全球风险与部分宏观高频字段缺失，按中性降级。

仅供研究参考，不构成投资建议。市场有风险，投资需谨慎，过往表现不预示未来收益。

#A股 #股票复盘 #行业研究 #消费电子 #光通信
"""

sector_lines = []
for rank, x in enumerate(top_sectors, 1):
    c = x["crowding"]
    sector_lines.append(f"| {rank} | {x['name']} | {x['price_momentum_p']:.2f} | {x['fund_flow_f']:.2f} | {x['orthogonal_flow_r']:.2f} | {x['trend_confirmation_t']:.2f} | {c['crowding_score']:.2f} | {c['delta_5d']:+.2f} | {c['penalty']:.2f} | {x['sector_heat']:.2f} |")
stock_lines = []
for x in verified:
    stock_lines.append(f"| {x['name']} {x['a_share_code'][:6]} | {x['sector_name']} | {x['fundamental_score']} | {x['technical_score']} | {x['fund_score']} | {x['relative_strength_score']} | {x['catalyst_score']} | {x['liquidity_score']} | {x['stock_score']:.1f} | {x['risk_penalty']} | {x['final_score']:.1f} | {x['confidence']}% | {'入榜' if x['eligible_for_selection'] else '未入榜'} |")

evidence = f"""# {TARGET} 股市老黄历证据台账

- 评分交易日：{TARGET}，盘后；时区：Asia/Shanghai。
- 产物：桌面HTML、移动HTML、小红书笔记。
- 数据原则：结构化行情和财务优先；公开检索只作定性复核；冲突并列披露；缺失不补造。

## 一、市场环境

MarketEnvironment = {score:.1f}，状态为{state}。

| 维度 | 分数 | 权重 | 加权贡献 |
|---|---:|---:|---:|
| 指数与风格趋势 | 62.0 | 30% | 18.6 |
| 市场宽度和情绪 | 77.0 | 25% | 19.25 |
| 成交与流动性 | 59.0 | 20% | 11.8 |
| 国内宏观流动性 | 58.0 | 15% | 8.7 |
| 全球风险 | 50.0 | 10% | 5.0 |

计算：0.30×62.0 + 0.25×77.0 + 0.20×59.0 + 0.15×58.0 + 0.10×50.0 = {score:.1f}。

- 上证指数3956.57，+1.13%；深证成指14048.88，+1.50%；创业板指3473.35，+1.71%。
- 上涨3394、下跌1944、平盘212；带日期口径涨停74、跌停0。
- 两市成交21259.27亿元，为5日均量110.11%、20日均量93.80%。
- 市场环境有效权重76%，置信度C；不代表预测概率。

## 二、行业量价正交 V2

- 分类：固定29个申万二级行业。
- 回归：enabled={str(reg['enabled']).lower()}，sample_size={reg['sample_size']}，coverage={reg['coverage']:.0%}，beta={reg['beta']:.10f}。
- 公式：P=20%×P1+35%×P5+45%×P20；F同权重；对zF~zP回归取残差分位R；T=70%×P+30%×R；SectorHeat=CoreHeat+20-CrowdPenalty。
- 催化和基本面缺少统一可审计横截面，按50分降级。

| 排名 | 行业 | P | F | R | T | C | ΔC5 | 扣分 | SectorHeat |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(sector_lines)}

正式过线：消费电子74.92、通信设备69.46、半导体69.07、汽车零部件65.13。种植业虽趋势强，但拥挤度95.61且热度64.16，未达门槛。

## 三、候选池与深度核验

- 四个达标行业合计599个成份关系；仅沪深A股、排除特殊处理、目标日无收盘、历史不足与20日成交额中位数低于1亿元后，合格383只。
- 初筛候选池40只；深度核验前5：长飞光纤、共达电声、飞龙股份、长盈通、剑桥科技。

| 股票 | 行业 | 基本面 | 技术 | 资金 | 相对强度 | 催化 | 流动性 | StockScore | 风险扣分 | FinalScore | 置信度 | 结论 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(stock_lines)}

### 入榜：长飞光纤 601869

- 2026H1营收约98.09亿元、归母净利润约29.25亿元，TTM归母净利润约34.43亿元。
- 评分日收盘426.82元，涨停；近20日涨62.68%，高于MA20约23.26%。
- 1/5/20日主力净流入约15.88/27.51/37.69亿元。
- PE-TTM约102.65倍、PB约21.59倍；异常波动、估值和追高风险合计扣10分。
- FinalScore=68.0，仅刚好达到中性市场门槛；结论为等待高位消化，不是立即买入。

### 未入榜要点

- 剑桥科技67.5：基本面和中期资金较强，但估值高、当日资金净流出，低于门槛0.5分。
- 飞龙股份60.8：液冷催化明确，但评分日涨停、高于布林上轨、PE-TTM约171倍。
- 共达电声60.7：20日上涨83.80%，PE-TTM约317.72倍，利润规模与估值不匹配。
- 长盈通53.0：20日上涨117.06%，PE-TTM约2269.64倍，当日资金净流出。

## 四、冲突、降级与限制

- 涨停家数：WeStock带日期74、实时changedist 78、hithink池76；正式评分采用74，其他口径仅复核。
- 全球风险、目标日两融和股债风险溢价缺少统一可审计时点，按50分降级，不解释为低风险。
- 外部检索确认科技成长、半导体、电子元件和通信设备为关注方向，但其盘中或错日数字全部排除，正式评分只使用本地结构化数据。
- hithink龙虎榜如返回非目标日，不用于当日评分。
- 所有分数用于同一候选池相对排序，不是收益概率。

## 五、小红书发布前自检

- 移动HTML和小红书笔记未出现个股精确买入、止盈或止损价格。
- 正文可见位置保留“仅供研究参考，不构成投资建议”。
- 未使用收益承诺、绝对化预测、指令性买卖、导流或诱导互动话术。
- 保留观察确认、减仓触发和失效条件，均为均线、量能、形态和资金条件。
- 本期仅生成与预审，不触发外部发布。
"""

files = {
    f"{TARGET}-stock-almanac.html": desktop,
    f"{TARGET}-stock-almanac-mobile.html": mobile,
    f"{TARGET}-xiaohongshu-note.md": note,
    f"{TARGET}-evidence.md": evidence,
}
for name, text in files.items():
    (OUT / name).write_text(text, encoding="utf-8")
print(json.dumps({"generated": [str(OUT / name) for name in files]}, ensure_ascii=False, indent=2))
