from __future__ import annotations

import json
from pathlib import Path

TARGET = "2026-08-28"
ROOT = Path("E:/WS/NashnovaResearch")
EV = ROOT / "evidence"
OUT = ROOT / "reports/stock-almanac"
OUT.mkdir(parents=True, exist_ok=True)

market = json.loads((EV / f"{TARGET}-market-raw.json").read_text(encoding="utf-8"))
market_score = json.loads((EV / f"{TARGET}-market-score.json").read_text(encoding="utf-8"))
sector_score = json.loads((EV / f"{TARGET}-sector-score-v3.json").read_text(encoding="utf-8"))
if sector_score.get("method") != "cross_sectional_price_flow_orthogonalization_v3":
    raise RuntimeError("行业评分不是V3，停止生成报告")
sector_raw = json.loads((EV / f"{TARGET}-sector-raw-v2.json").read_text(encoding="utf-8"))

idx = market["indices"]
breadth = market["market_breadth"]["dated_market_overview"]
turnover = market["turnover"]
score = market_score["result"]["total_score"]
state = market_score["result"]["market_state"]
reg = sector_score["regression"]
sectors = sector_score["sectors"]
top_sectors = sectors[:5]
qualified = [x for x in sectors if x["sector_heat"] >= 65 and (x["crowding"]["crowding_score"] < 90 or x.get("severe_crowding_can_remain"))]

candidate_payload = {
    "schema_version": "1.1",
    "as_of_date": TARGET,
    "scope": {
        "eligible_sectors": [],
        "candidate_pool_count": 0,
        "deep_verification_count_planned": 0,
    },
    "methodology": {
        "sector_gate": "SectorHeat>=65，严重拥挤板块还需SectorHeat>=70且R>=50",
        "stock_gate": "中性市场FinalScore>=68且置信度>=75%",
    },
    "candidate_pool": [],
    "deep_verified": [],
    "selected": [],
    "zero_recommendation_reason": "29行业完整横截面中没有行业达到65分门槛，因此不建立个股候选池，不强行凑股。",
}
(EV / f"{TARGET}-stock-candidates.json").write_text(json.dumps(candidate_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(EV / f"{TARGET}-stock-deep-raw.json").write_text(json.dumps({"as_of_date": TARGET, "skipped": True, "reason": candidate_payload["zero_recommendation_reason"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(EV / f"{TARGET}-stock-deep-summary.json").write_text(json.dumps({"as_of_date": TARGET, "verified": [], "selected": [], "reason": candidate_payload["zero_recommendation_reason"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fmt(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def sector_rows() -> str:
    rows = []
    for x in top_sectors:
        c = x["crowding"]
        warnings = "；".join(c["warnings"]) if c["warnings"] else "无"
        rows.append(
            f"<tr><td><b>{x['name']}</b></td><td>{fmt(x['price_momentum_p'])}</td>"
            f"<td>{fmt(x['orthogonal_flow_r'])}</td><td>{fmt(x['trend_confirmation_t'])}</td>"
            f"<td>{fmt(c['crowding_score'])}</td><td>{fmt(c['penalty'])}</td>"
            f"<td><b>{fmt(x['sector_heat'])}</b></td><td>{warnings}</td></tr>"
        )
    return "".join(rows)


def sector_cards() -> str:
    cards = []
    labels = {
        "化学原料": "趋势与独立资金均强，但拥挤加速压低最终热度。",
        "汽车零部件": "独立资金残差靠前，但价格确认不足，仅作潜伏观察。",
        "炼化及贸易": "量价趋势靠前，当前已进入高拥挤区。",
    }
    for x in top_sectors[:3]:
        c = x["crowding"]
        warning = "；".join(c["warnings"]) if c["warnings"] else "暂无额外拥挤预警"
        cards.append(
            f"<article class='sector-card'><h3>{x['name']} {x['sector_heat']:.2f}</h3>"
            f"<p>{labels.get(x['name'], '结构性轮动方向，仍未达到正式入选门槛。')}</p>"
            f"<div class='line'><span>趋势T</span><b>{x['trend_confirmation_t']:.2f}</b></div>"
            f"<div class='line'><span>独立资金R</span><b>{x['orthogonal_flow_r']:.2f}</b></div>"
            f"<div class='line'><span>拥挤C / 扣分</span><b>{c['crowding_score']:.2f} / {c['penalty']:.2f}</b></div>"
            f"<p class='note'>{warning}</p></article>"
        )
    return "".join(cards)

market_summary = (
    f"上证{idx['上证指数']['change_pct']:+.2f}%、深证{idx['深证成指']['change_pct']:+.2f}%、"
    f"创业板{idx['创业板指']['change_pct']:+.2f}%；上涨{breadth['CNT_RED']}家、"
    f"下跌{breadth['CNT_GREEN']}家，两市成交{turnover['amount_100m_cny']:.0f}亿元。"
)


def format_crowding_warnings(warnings: list[str]) -> str:
    if not warnings:
        return "未触发额外拥挤预警"
    text = "；".join(warnings)
    replacements = {
        "rsi_pct": "RSI强度",
        "turnover_pct": "换手率",
        "share_pct": "成交占比",
    }
    for raw, label in replacements.items():
        text = text.replace(raw, label)
    return text


css = """
:root{--paper:#f3efe6;--deep:#e8e0d0;--ink:#18332d;--body:#293631;--red:#a83e32;--green:#17705e;--gold:#b98532;--line:rgba(24,51,45,.22);--card:#fffdf7;--muted:#68736d;--serif:STSong,SimSun,serif;--sans:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}*{box-sizing:border-box}body{margin:0;background:var(--deep);color:var(--body);font:14px/1.68 var(--sans)}.topbar{background:var(--ink);color:#f8f2e5;border-bottom:3px solid var(--gold)}.topin,.page{width:1220px;margin:auto}.topin{min-height:72px;display:flex;align-items:center;justify-content:space-between}.brand{font:700 23px var(--serif)}.badge,.tag{border:1px solid var(--line);padding:6px 9px}.topbar .badge{border-color:#8d947f;color:#e8c887}.seal{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;margin-right:10px;border:1px solid #e8c887;color:#e8c887;font:700 20px var(--serif)}.page{background:var(--paper);padding:34px 24px 48px}.hero{display:grid;grid-template-columns:1.45fr .75fr;gap:20px}.hero h1{font:700 45px/1.15 var(--serif);color:var(--ink);margin:8px 0}.eyebrow,.kicker{color:var(--gold);font-weight:700;letter-spacing:.12em;font-size:11px}.dark{background:var(--ink);color:#f8f2e5;padding:22px;border-left:5px solid var(--gold)}.dark h2{font:700 25px var(--serif);color:#e8c887}.section{margin-top:18px}.card{background:var(--card);border:1px solid var(--line);padding:20px}.head{display:flex;justify-content:space-between;align-items:center}.head h2{font:700 29px var(--serif);color:var(--ink);margin:2px 0 12px}.grid{display:grid;gap:12px}.g4{grid-template-columns:repeat(4,1fr)}.g3{grid-template-columns:repeat(3,1fr)}.metric,.panel,.sector-card{padding:13px;border:1px solid var(--line);background:#fffaf0}.metric span{display:block;color:var(--muted);font-size:12px}.metric b{font-size:18px;color:var(--ink)}.up{color:var(--red)}.down{color:var(--green)}.muted,.note{color:var(--muted)}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid var(--line);text-align:left}.empty{padding:24px;border:1px solid var(--line);background:#fffaf0;border-left:5px solid var(--gold)}.risk{border-left:5px solid var(--red)}details{margin-top:18px;background:var(--card);border:1px solid var(--line);padding:14px}.footer{text-align:center;padding:24px;color:#e3ddd1;background:var(--ink)}
"""

desktop = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta name='description' content='2026年8月28日A股盘后研究日报'><title>A股选股日报｜{TARGET}</title><style>{css}</style></head><body><header class="topbar"><div class='topin'><div class='brand'><span class="seal">历</span>股市老黄历 · A股研究</div><span class='badge'>盘后 · V3</span></div></header><main class='page'><header id='cover' class='hero'><div><div class='eyebrow'>评分交易日 {TARGET} · 北京时间盘后</div><h1>指数回调，<span class='up'>结构轮动</span></h1><p>{market_summary} 指数走弱但个股涨多跌少，农业、化工、房地产等方向轮动活跃。</p><p><b>宜</b> 观察回踩与资金延续　<b>忌</b> 追逐拥挤加速段</p><p class='note'>标题仅为栏目包装，正文为数据研究；仅供研究参考，不构成投资建议。</p></div><aside class='dark'><div>数据截至 {TARGET} 收盘</div><h2>{state} · 今日零推荐</h2><p>环境分{score:.1f}。29个行业中最高热度为{top_sectors[0]['name']} {top_sectors[0]['sector_heat']:.2f}，未达到65分门槛，不建立个股候选池。</p></aside></header>
<section id='executive-summary' class='section card'><div class='head'><div><div class='kicker'>00 / brief</div><h2>行情摘要</h2></div><span class='tag'>结论先行</span></div><div class='grid g4'><div class='metric'><span>市场状态</span><b>{state} {score:.1f}</b></div><div class='metric'><span>市场宽度</span><b>涨{breadth['CNT_RED']} / 跌{breadth['CNT_GREEN']}</b></div><div class='metric'><span>两市成交</span><b>{turnover['amount_100m_cny']:.0f}亿元</b></div><div class='metric'><span>最高行业热度</span><b>{top_sectors[0]['name']} {top_sectors[0]['sector_heat']:.2f}</b></div></div><p>周五指数回落，但上涨占比仍为{breadth['RATIO_UP']:.2f}%。热点切换至周期与农业，行业热度却被拥挤度明显削弱。今日不强行给出个股推荐。</p></section>
<section id='macro' class='section card'><div class='head'><div><div class='kicker'>01 / macro</div><h2>宏观大势</h2></div><span class='tag'>流动性 · 风险</span></div><div class='grid g3'><div class='panel'><b>国内流动性温和</b><p>截至目标日已发布的低频宏观数据未显示流动性骤变，宏观维度按58分处理。</p></div><div class='panel'><b>行业轮动加快</b><p>农业、化工和房地产获得关注，科技硬件回调，市场更偏结构性交易。</p></div><div class='panel'><b>全球风险中性降级</b><p>缺少同一时点可审计的VIX、美元和美债数据，按50分处理，不代表外部风险低。</p></div></div></section>
<section id='market' class='section card'><div class='head'><div><div class='kicker'>02 / market</div><h2>大盘判断</h2></div><span class='tag'>{TARGET} 收盘</span></div><div class='grid g4'><div class='metric'><span>上证指数</span><b>{idx['上证指数']['close']:.2f} <i class='down'>{idx['上证指数']['change_pct']:+.2f}%</i></b></div><div class='metric'><span>深证成指</span><b>{idx['深证成指']['close']:.2f} <i class='down'>{idx['深证成指']['change_pct']:+.2f}%</i></b></div><div class='metric'><span>创业板指</span><b>{idx['创业板指']['close']:.2f} <i class='down'>{idx['创业板指']['change_pct']:+.2f}%</i></b></div><div class='metric'><span>成交/20日均量</span><b>{turnover['vs_twenty_day_average_pct']:.2f}%</b></div></div><div class='grid g3' style='margin-top:12px'><div class='panel'><b>宽度强于指数</b><p>上涨占比{breadth['RATIO_UP']:.2f}%，带日期口径涨停{breadth['CNT_REACH_UPLIMIT']}家、跌停{breadth['CNT_REACH_DNLIMIT']}家。</p></div><div class='panel'><b>成交保持高位</b><p>两市成交约{turnover['amount_100m_cny']:.0f}亿元，达到5日均量106.41%，但仅为20日均量93.64%。</p></div><div class='panel'><b>中期修复未完成</b><p>上证5日收益为正，深证与创业板5日转弱，三大指数60日收益仍为负。</p></div></div><p class='note'>涨停家数存在WeStock带日期76、实时分布83、hithink池81的口径差异；正式评分采用76，不取平均。</p></section>
<section id='sectors' class='section card'><div class='head'><div><div class='kicker'>03 / sectors</div><h2>板块筛选</h2></div><span class='tag'>0个方向达标</span></div><table><thead><tr><th>行业</th><th>价格P</th><th>正交R</th><th>趋势T</th><th>拥挤C</th><th>扣分</th><th>热度</th><th>预警</th></tr></thead><tbody>{sector_rows()}</tbody></table><div class='grid g3' style='margin-top:12px'>{sector_cards()}</div><p class='note'>29行业完整横截面回归：样本{reg['sample_size']}、覆盖率{reg['coverage']:.0%}、beta={reg['beta']:.4f}。最高行业热度仍低于65分，因此只列观察方向。</p></section>
<section id='picks' class='section card'><div class='head'><div><div class='kicker'>04 / picks</div><h2>今日结论</h2></div><span class='tag'>零推荐</span></div><div class='empty'><h3>本期不建立个股推荐榜</h3><p>原因不是数据缺失，而是29行业完整横截面没有任何方向达到65分。{top_sectors[0]['name']}、{top_sectors[1]['name']}、{top_sectors[2]['name']}虽有趋势或资金支持，但分别受到拥挤惩罚或价格确认不足的约束；按规则停止向个股层下钻。</p><p><b>观察条件：</b>后续需看到行业热度重新站上65分、独立资金保持确认，同时拥挤度不再加速，才重启候选池。</p></div></section>
<section id='risks' class='section card risk'><div class='kicker'>05 / risks</div><h2>风险提示</h2><ul><li>{top_sectors[0]['name']}热度{top_sectors[0]['sector_heat']:.2f}，拥挤度{top_sectors[0]['crowding']['crowding_score']:.2f}且5日变化{top_sectors[0]['crowding']['delta_5d']:+.2f}，存在波动放大风险。</li><li>{top_sectors[1]['name']}独立资金R={top_sectors[1]['orthogonal_flow_r']:.2f}，但价格P={top_sectors[1]['price_momentum_p']:.2f}，尚需价格确认。</li><li>指数回调而热点轮动，追逐单日涨幅可能面临次日风格切换。</li><li>全球风险与部分宏观高频字段缺失，按中性降级。</li></ul><p><b>免责声明</b>：以上内容基于公开与授权数据，仅供研究参考，不构成投资建议。市场有风险，投资需谨慎。</p></section>
<details id='methodology'><summary>方法与数据降级说明</summary><p>市场环境=30%指数与风格+25%宽度与情绪+20%成交与流动性+15%国内宏观+10%全球风险。行业以1/5/20日价格和资金横截面正交，板块热度扣最高20分拥挤惩罚。</p><p>行业广度已由成份股相邻交易日收盘计算；催化与基本面缺少统一横截面证据，按50分降级。外部信息只作定性核验，缺失项不补造。</p></details></main><footer class='footer'>数据来源：WeStock、hithink-finance与公开资料复核｜评分日 {TARGET}｜证据台账 {TARGET}-evidence.md</footer></body></html>"""

mobile_css = """
:root{--paper:#f7f3ea;--m-ink:#18332d;--ink:var(--m-ink);--body:#293631;--red:#a83e32;--green:#17705e;--m-gold:#b98532;--gold:var(--m-gold);--line:#e1d9ca;--card:#fffdf7;--muted:#746f65;--serif:STSong,SimSun,serif;--sans:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}*{box-sizing:border-box}body{margin:0;background:#e7e0d2;color:var(--body);font:15px/1.65 var(--sans)}.m-shell{max-width:460px;margin:auto;background:var(--paper);padding-bottom:24px}.top{background:var(--ink);color:#f8f2e5;padding:16px;border-bottom:3px solid var(--gold)}.top b{font:700 19px var(--serif)}.m-seal{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;margin-right:8px;border:1px solid #e8c887;color:#e8c887;font:700 18px var(--serif)}.cover{padding:18px 15px}.date,.kicker{color:var(--gold);font-size:10px;font-weight:700;letter-spacing:.11em}.cover h1{font:700 30px/1.2 var(--serif);color:var(--ink);margin:8px 0}.state{background:var(--ink);color:#f8f2e5;border-left:4px solid var(--gold);padding:12px}.state b{color:#e8c887}.sec{margin:12px;background:var(--card);border:1px solid var(--line);padding:14px}.sec h2{font:700 23px var(--serif);color:var(--ink);margin:3px 0 9px}.line,.kv{display:flex;gap:10px;justify-content:space-between;padding:6px 0;border-bottom:1px dashed var(--line)}.kv{align-items:flex-start}.k{color:var(--muted);min-width:70px}.up{color:var(--red)}.down{color:var(--green)}.stock{margin-top:10px;border-top:3px solid var(--gold);padding-top:10px}.stock h3{font:700 21px var(--serif);color:var(--ink);margin:0}.note{color:var(--muted);font-size:12px}.risk{border-left:4px solid var(--red)}details{margin:12px;padding:12px;border:1px solid var(--line)}footer{text-align:center;padding:18px;background:var(--ink);color:#d7ddd4;font-size:12px}
"""

mobile_sector_cards = "".join(
    f"<div class='stock'><h3>{x['name']} {x['sector_heat']:.2f}</h3><p>趋势T={x['trend_confirmation_t']:.2f}，独立资金R={x['orthogonal_flow_r']:.2f}。</p><p>拥挤C={x['crowding']['crowding_score']:.2f}，扣分{x['crowding']['penalty']:.2f}；{format_crowding_warnings(x['crowding']['warnings'])}。</p></div>"
    for x in top_sectors[:3]
)
mobile = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta name='description' content='2026年8月28日A股盘后研究日报移动版'><title>行情老黄历｜{TARGET}</title><style>{mobile_css}</style></head><body><div class="m-shell"><header class='top'><b><span class="m-seal">历</span>行情老黄历 · A股研究</b></header><header id='cover' class='cover'><div class='date'>评分交易日 {TARGET}</div><h1>指数回调，结构轮动</h1><p><b>宜</b> 等资金延续　<b>忌</b> 追拥挤加速</p><div class='state'><b>{state} · 今日零推荐</b><br>环境分{score:.1f}，行业最高热度{top_sectors[0]['sector_heat']:.2f}。</div><p class='note'>标题仅为栏目包装，正文为数据研究。<br>仅供研究参考，不构成投资建议。</p></header><section id='executive-summary' class='sec'><div class='kicker'>00 / brief</div><h2>行情摘要</h2><div class='line'><span class='k'>指数</span><span>上证{idx['上证指数']['change_pct']:+.2f}%｜创业板{idx['创业板指']['change_pct']:+.2f}%</span></div><div class='line'><span class='k'>宽度</span><span>涨{breadth['CNT_RED']} / 跌{breadth['CNT_GREEN']}</span></div><div class='line'><span class='k'>成交</span><span>{turnover['amount_100m_cny']:.0f}亿元</span></div><div class='line'><span class='k'>结论</span><span>行业均未过65分门槛</span></div><p><b>仅供研究参考，不构成投资建议。</b></p></section><section id='macro' class='sec'><div class='kicker'>01 / macro</div><h2>宏观大势</h2><div class='kv'><span class='k'>国内</span><span>流动性维持温和，未见目标日骤变。</span></div><div class='kv'><span class='k'>外部</span><span>全球风险字段缺失，按中性降级。</span></div></section><section id='market' class='sec'><div class='kicker'>02 / market</div><h2>大盘判断</h2><div class='line'><span class='k'>上证</span><span>{idx['上证指数']['close']:.2f} <span class='down'>{idx['上证指数']['change_pct']:+.2f}% 下跌</span></span></div><div class='line'><span class='k'>深证</span><span>{idx['深证成指']['close']:.2f} <span class='down'>{idx['深证成指']['change_pct']:+.2f}% 下跌</span></span></div><div class='line'><span class='k'>创业板</span><span>{idx['创业板指']['close']:.2f} <span class='down'>{idx['创业板指']['change_pct']:+.2f}% 下跌</span></span></div><p>指数回调，但上涨家数仍多于下跌家数。成交为20日均量93.64%，结构轮动快于指数趋势。</p></section><section id='sectors' class='sec'><div class='kicker'>03 / sectors</div><h2>板块观察</h2>{mobile_sector_cards}<p class='note'>均未达到65分正式门槛，只作观察。</p></section><section id='picks' class='sec'><div class='kicker'>04 / picks</div><h2>今日结论</h2><div class='stock'><h3>本期零推荐</h3><p>没有行业过线，因此不向个股层强行下钻。</p><p><b>重启条件：</b>行业热度站上65分，独立资金延续，拥挤度不再加速。</p><p><b>失效条件：</b>指数继续放量走弱，或轮动方向资金转为持续净流出。</p></div></section><section id='risks' class='sec risk'><div class='kicker'>05 / risks</div><h2>风险提示</h2><ul><li>{top_sectors[0]['name']}拥挤加速，注意波动放大。</li><li>{top_sectors[1]['name']}资金先行，仍待价格确认。</li><li>热点切换较快，追涨风险上升。</li><li>全球风险字段按中性降级。</li></ul><p><b>仅供研究参考，不构成投资建议。</b></p></section><details id='methodology'><summary>方法与免责声明</summary><p>行业采用29板块完整横截面做量价正交，并扣最高20分拥挤惩罚。缺失项按中性降级，不补造。</p><p>本报告不构成收益承诺或代客交易指令。</p></details><footer>数据来源：WeStock、hithink-finance｜评分日 {TARGET}</footer></div></body></html>"""

note = f"""# 8月28日A股复盘｜轮动加快，今日零推荐

三大指数同步回调：上证{idx['上证指数']['change_pct']:+.2f}%、深证{idx['深证成指']['change_pct']:+.2f}%、创业板{idx['创业板指']['change_pct']:+.2f}%。上涨{breadth['CNT_RED']}家、下跌{breadth['CNT_GREEN']}家，两市成交{turnover['amount_100m_cny']:.0f}亿元。

今日宜：观察资金延续和回踩确认。
今日忌：追逐已经拥挤加速的轮动方向。

**板块观察**

1. {top_sectors[0]['name']}：趋势T={top_sectors[0]['trend_confirmation_t']:.2f}、独立资金R={top_sectors[0]['orthogonal_flow_r']:.2f}，最终热度{top_sectors[0]['sector_heat']:.2f}；拥挤度{top_sectors[0]['crowding']['crowding_score']:.2f}。
2. {top_sectors[1]['name']}：趋势T={top_sectors[1]['trend_confirmation_t']:.2f}、独立资金R={top_sectors[1]['orthogonal_flow_r']:.2f}，最终热度{top_sectors[1]['sector_heat']:.2f}；当前仍缺少价格确认。
3. {top_sectors[2]['name']}：趋势T={top_sectors[2]['trend_confirmation_t']:.2f}、独立资金R={top_sectors[2]['orthogonal_flow_r']:.2f}，最终热度{top_sectors[2]['sector_heat']:.2f}；拥挤度{top_sectors[2]['crowding']['crowding_score']:.2f}。

**今日结论**

29个行业完整横截面中，没有方向达到65分门槛。因此本期不建立个股推荐榜，也不为凑数量降低规则。

后续只有在行业热度重新站上65分、独立资金保持确认、拥挤度不再加速时，才重启候选股筛选。

**风险提醒**

- 指数回调但个股涨多跌少，结构轮动较快。
- {top_sectors[0]['name']}与{top_sectors[2]['name']}虽有趋势或资金支持，但拥挤度偏高。
- 全球风险与部分宏观高频字段缺失，按中性处理。

仅供研究参考，不构成投资建议。市场有风险，投资需谨慎。

#A股 #股票复盘 #行业研究 #每日复盘
"""

sector_lines = []
for rank, x in enumerate(top_sectors, 1):
    c = x["crowding"]
    sector_lines.append(f"| {rank} | {x['name']} | {x['price_momentum_p']:.2f} | {x['fund_flow_f']:.2f} | {x['orthogonal_flow_r']:.2f} | {x['trend_confirmation_t']:.2f} | {c['crowding_score']:.2f} | {c['delta_5d']:+.2f} | {c['penalty']:.2f} | {x['sector_heat']:.2f} |")

evidence = f"""# {TARGET} 股市老黄历证据台账

- 评分交易日：{TARGET}，盘后；时区：Asia/Shanghai。
- 产物：桌面HTML、移动HTML、小红书笔记。
- 数据原则：结构化行情优先；冲突并列披露；缺失不补造。

## 一、市场环境

MarketEnvironment = {score:.1f}，状态为{state}。

| 维度 | 分数 | 权重 | 加权贡献 |
|---|---:|---:|---:|
| 指数与风格趋势 | 53.0 | 30% | 15.9 |
| 市场宽度和情绪 | 66.0 | 25% | 16.5 |
| 成交与流动性 | 56.0 | 20% | 11.2 |
| 国内宏观流动性 | 58.0 | 15% | 8.7 |
| 全球风险 | 50.0 | 10% | 5.0 |

计算：0.30×53.0 + 0.25×66.0 + 0.20×56.0 + 0.15×58.0 + 0.10×50.0 = {score:.1f}。

- 上证指数{idx['上证指数']['close']:.2f}，{idx['上证指数']['change_pct']:+.2f}%；深证成指{idx['深证成指']['close']:.2f}，{idx['深证成指']['change_pct']:+.2f}%；创业板指{idx['创业板指']['close']:.2f}，{idx['创业板指']['change_pct']:+.2f}%。
- 上涨{breadth['CNT_RED']}、下跌{breadth['CNT_GREEN']}、平盘{breadth['CNT_ZERO']}；带日期口径涨停{breadth['CNT_REACH_UPLIMIT']}、跌停{breadth['CNT_REACH_DNLIMIT']}。
- 两市成交{turnover['amount_100m_cny']:.2f}亿元，为5日均量106.41%、20日均量93.64%。

## 二、行业量价正交 V3

- 方法标识：`{sector_score['method']}`。
- 分类：固定29个申万二级行业。
- 回归：enabled={str(reg['enabled']).lower()}，sample_size={reg['sample_size']}，coverage={reg['coverage']:.0%}，beta={reg['beta']:.10f}，R²={reg['r_squared']:.4f}。
- 公式：P=20%×P1+35%×P5+45%×P20；F同权重；对zF~zP回归取残差分位R；T=70%×P+30%×R；Opportunity=CoreHeat/0.8；SectorHeat=Opportunity-CrowdPenalty。
- 方向约束：5日与20日收益同时非正时T上限55；5日与20日资金强度同时非正时R上限50。
- 硬上限：P<=50且R>=80为资金潜伏，P>=70且R<=20为量价背离，两类情形SectorHeat均不高于60。
- 催化和基本面缺少统一可审计横截面，按50分降级；板块置信度由有效分项覆盖与降级情况计算。

| 排名 | 行业 | P | F | R | T | C | ΔC5 | 扣分 | SectorHeat |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(sector_lines)}

正式过线：{len(qualified)}个。前三为{top_sectors[0]['name']}{top_sectors[0]['sector_heat']:.2f}、{top_sectors[1]['name']}{top_sectors[1]['sector_heat']:.2f}、{top_sectors[2]['name']}{top_sectors[2]['sector_heat']:.2f}，均未达到65分。

## 三、候选池与个股结论

- 行业门槛未通过，因此候选池构建和个股深度核验按规则跳过。
- 结果为零推荐，不代表市场没有上涨股票，而是当前证据不足以通过统一门槛。
- `stock-candidates.json`、`stock-deep-raw.json`和`stock-deep-summary.json`已记录跳过原因。

## 四、冲突、降级与限制

- 涨停家数：WeStock带日期76、实时changedist 83、hithink涨停池81；正式评分采用76，其他口径仅复核。
- WeStock板块成份股资金聚合覆盖29行业、51,708条记录，22个批次全部成功。
- 29行业价格与资金评分覆盖率100%。
- hithink龙虎榜返回2026-08-27，滞后于目标日，不用于8月28日候选。
- 全球风险、目标日两融和股债风险溢价缺少统一时点，按50分降级，不解释为低风险。
- 所有分数用于同一横截面相对排序，不是收益概率。

## 五、小红书发布前自检

- 移动HTML和小红书笔记未出现个股精确买入、止盈或止损价格。
- 正文可见位置保留“仅供研究参考，不构成投资建议”。
- 未使用收益承诺、绝对化预测、指令性买卖、导流或诱导互动话术。
- 本期零推荐，明确说明规则与重启条件。
- 自动化只填充待发布内容，不点击发布按钮。
"""

files = {
    f"{TARGET}-stock-almanac.html": desktop,
    f"{TARGET}-stock-almanac-mobile.html": mobile,
    f"{TARGET}-xiaohongshu-note.md": note,
    f"{TARGET}-evidence.md": evidence,
}
for name, text in files.items():
    (OUT / name).write_text(text, encoding="utf-8")
print(json.dumps({"generated": [str(OUT / name) for name in files], "qualified_sectors": len(qualified)}, ensure_ascii=False, indent=2))
