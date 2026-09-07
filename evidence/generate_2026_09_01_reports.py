from __future__ import annotations

import json
from pathlib import Path

TARGET = "2026-09-01"
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
hot = market["dragon_tiger_and_hotspots"]["hotspot_summary"]
score = market_score["result"]["total_score"]
state = market_score["result"]["market_state"]
reg = sector_score["regression"]
sectors = sector_score["sectors"]
top_sectors = sectors[:5]
qualified = [
    x
    for x in sectors
    if x["sector_heat"] >= 65
    and (x["crowding"]["crowding_score"] < 90 or x.get("severe_crowding_can_remain"))
]

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
    "gate_detail": [
        {
            "sector": x["name"],
            "sector_heat": round(x["sector_heat"], 2),
            "orthogonal_flow_r": round(x["orthogonal_flow_r"], 2),
            "price_momentum_p": round(x["price_momentum_p"], 2),
            "trend_confirmation_t": round(x["trend_confirmation_t"], 2),
            "crowding_score": round(x["crowding"]["crowding_score"], 2),
            "crowding_delta_5d": round(x["crowding"]["delta_5d"], 2),
            "severe_crowding_can_remain": bool(x.get("severe_crowding_can_remain")),
            "verdict": verdict,
        }
        for x, verdict in (
            (
                top_sectors[0],
                "未过65分门槛；且拥挤度98.83属严重拥挤，按规则需SectorHeat>=70且R>=50，均不满足，排除",
            ),
            (top_sectors[1], "未过65分门槛；价格P=48.94偏弱、趋势T=62.13不足，仅作资金潜伏观察"),
            (top_sectors[2], "未过65分门槛；当日板块下跌，趋势T=60.94不足"),
            (top_sectors[3], "未过65分门槛；拥挤度65.03且5日加速+12.70，需跟踪"),
            (top_sectors[4], "未过65分门槛；趋势T=76.79较强，但拥挤88.48且5日加速+18.53，扣分17.86后不足"),
        )
    ],
    "candidate_pool": [],
    "deep_verified": [],
    "selected": [],
    "zero_recommendation_reason": (
        "29行业完整横截面中最高得分为种植业58.97，未达到65分门槛；榜首板块同时处于严重拥挤区"
        "（拥挤度98.83，RSI/换手率/成交占比三项均达近一年极端分位），按V3规则不可保留。"
        "因此本期不建立个股候选池，不强行凑股。"
    ),
}
(EV / f"{TARGET}-stock-candidates.json").write_text(
    json.dumps(candidate_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
(EV / f"{TARGET}-stock-deep-raw.json").write_text(
    json.dumps(
        {"as_of_date": TARGET, "skipped": True, "reason": candidate_payload["zero_recommendation_reason"]},
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
(EV / f"{TARGET}-stock-deep-summary.json").write_text(
    json.dumps(
        {
            "as_of_date": TARGET,
            "verified": [],
            "selected": [],
            "reason": candidate_payload["zero_recommendation_reason"],
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)


def fmt(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def format_crowding_warnings(warnings: list[str]) -> str:
    if not warnings:
        return "未触发额外拥挤预警"
    text = "；".join(warnings)
    replacements = {
        "rsi_pct": "RSI强度",
        "turnover_pct": "换手率",
        "share_pct": "成交占比",
        "严重拥挤，追高风险": "严重拥挤，追高风险",
    }
    for raw, label in replacements.items():
        text = text.replace(raw, label)
    return text


def sector_rows() -> str:
    rows = []
    for x in top_sectors:
        c = x["crowding"]
        warnings = format_crowding_warnings(c["warnings"])
        rows.append(
            f"<tr><td><b>{x['name']}</b></td><td>{fmt(x['price_momentum_p'])}</td>"
            f"<td>{fmt(x['fund_flow_f'])}</td><td>{fmt(x['orthogonal_flow_r'])}</td>"
            f"<td>{fmt(x['trend_confirmation_t'])}</td><td>{fmt(c['crowding_score'])}</td>"
            f"<td>{c['delta_5d']:+.2f}</td><td>{fmt(c['penalty'])}</td>"
            f"<td><b>{fmt(x['sector_heat'])}</b></td><td>{warnings}</td></tr>"
        )
    return "".join(rows)


SECTOR_NOTES = {
    "种植业": "量价双强但拥挤度接近极限，热度被扣掉19.53分，属典型的极致抱团脉冲。",
    "汽车零部件": "独立资金残差92.86居前，价格动量仅48.94，属资金先行、价格未确认的潜伏型。",
    "消费电子": "资金与价格均为中位偏弱，当日板块下跌2.07%，缺乏趋势确认。",
    "工业金属": "价格动量66.60尚可，但拥挤度65.03且5日加速+12.70，需防追高。",
    "保险Ⅱ": "趋势T=76.79为前五最强，但拥挤88.48且5日加速+18.53，扣分17.86最多之一。",
}


def sector_cards() -> str:
    cards = []
    for x in top_sectors[:3]:
        c = x["crowding"]
        warning = format_crowding_warnings(c["warnings"])
        cards.append(
            f"<article class='sector-card'><h3>{x['name']} {x['sector_heat']:.2f}</h3>"
            f"<p>{SECTOR_NOTES.get(x['name'], '结构性轮动方向，仍未达到正式入选门槛。')}</p>"
            f"<div class='line'><span>价格动量P</span><b>{x['price_momentum_p']:.2f}</b></div>"
            f"<div class='line'><span>资金强度F</span><b>{x['fund_flow_f']:.2f}</b></div>"
            f"<div class='line'><span>独立资金R</span><b>{x['orthogonal_flow_r']:.2f}</b></div>"
            f"<div class='line'><span>趋势确认T</span><b>{x['trend_confirmation_t']:.2f}</b></div>"
            f"<div class='line'><span>拥挤C / 扣分</span><b>{c['crowding_score']:.2f} / {c['penalty']:.2f}</b></div>"
            f"<p class='note'>{warning}</p></article>"
        )
    return "".join(cards)


theme_text = "、".join(f"{t['theme']}{t['count']}" for t in hot["top_reason_tokens"][:8])
top_boards = "；".join(
    f"{b['name']} {b.get('continuous_days', b.get('days', ''))}板"
    for b in hot.get("highest_continuation", [])[:3]
) or "当日无连板数据"

market_summary = (
    f"上证{idx['上证指数']['change_pct']:+.2f}%、深证{idx['深证成指']['change_pct']:+.2f}%、"
    f"创业板{idx['创业板指']['change_pct']:+.2f}%；上涨{breadth['CNT_RED']}家、"
    f"下跌{breadth['CNT_GREEN']}家，两市成交{turnover['amount_100m_cny']:.0f}亿元。"
)

css = """
:root{--paper:#f3efe6;--deep:#e8e0d0;--ink:#18332d;--body:#293631;--red:#a83e32;--green:#17705e;--gold:#b98532;--line:rgba(24,51,45,.22);--card:#fffdf7;--muted:#68736d;--serif:STSong,SimSun,serif;--sans:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}*{box-sizing:border-box}body{margin:0;background:var(--deep);color:var(--body);font:14px/1.68 var(--sans)}.topbar{background:var(--ink);color:#f8f2e5;border-bottom:3px solid var(--gold)}.topin,.page{width:1220px;margin:auto}.topin{min-height:72px;display:flex;align-items:center;justify-content:space-between}.brand{font:700 23px var(--serif)}.badge,.tag{border:1px solid var(--line);padding:6px 9px}.topbar .badge{border-color:#8d947f;color:#e8c887}.seal{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;margin-right:10px;border:1px solid #e8c887;color:#e8c887;font:700 20px var(--serif)}.page{background:var(--paper);padding:34px 24px 48px}.hero{display:grid;grid-template-columns:1.45fr .75fr;gap:20px}.hero h1{font:700 45px/1.15 var(--serif);color:var(--ink);margin:8px 0}.eyebrow,.kicker{color:var(--gold);font-weight:700;letter-spacing:.12em;font-size:11px}.dark{background:var(--ink);color:#f8f2e5;padding:22px;border-left:5px solid var(--gold)}.dark h2{font:700 25px var(--serif);color:#e8c887}.section{margin-top:18px}.card{background:var(--card);border:1px solid var(--line);padding:20px}.head{display:flex;justify-content:space-between;align-items:center}.head h2{font:700 29px var(--serif);color:var(--ink);margin:2px 0 12px}.grid{display:grid;gap:12px}.g4{grid-template-columns:repeat(4,1fr)}.g3{grid-template-columns:repeat(3,1fr)}.metric,.panel,.sector-card{padding:13px;border:1px solid var(--line);background:#fffaf0}.metric span{display:block;color:var(--muted);font-size:12px}.metric b{font-size:18px;color:var(--ink)}.up{color:var(--red)}.down{color:var(--green)}.muted,.note{color:var(--muted)}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid var(--line);text-align:left;font-size:13px}th{color:var(--ink);font-weight:700}.sector-card h3{font:700 20px var(--serif);color:var(--ink);margin:0 0 6px}.sector-card .line{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px dashed var(--line);font-size:13px}.empty{border-left:4px solid var(--gold);background:#fffaf0;padding:16px}.risk{border-left:4px solid var(--red)}.risk ul{margin:8px 0;padding-left:20px}footer{background:var(--ink);color:#d7ddd4;text-align:center;padding:18px;font-size:12px}details{margin-top:18px;padding:14px;border:1px solid var(--line);background:var(--card)}
"""

desktop = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta name='description' content='2026年9月1日A股盘后研究日报，量价正交V3行业评分'><title>A股选股日报｜{TARGET}</title><style>{css}</style></head><body><header class="topbar"><div class='topin'><div class='brand'><span class="seal">历</span>股市老黄历 · A股研究</div><span class='badge'>盘后 · V3</span></div></header><main class='page'><header id='cover' class='hero'><div><div class='eyebrow'>评分交易日 {TARGET} · 北京时间盘后</div><h1>个股涨多跌少，<span class='down'>量能仍是短板</span></h1><p>{market_summary} 指数分化回落，但上涨占比{breadth['RATIO_UP']:.2f}%，赚钱效应集中在中小市值与题材方向。</p><p><b>宜</b> 等资金延续与拥挤回落　<b>忌</b> 追极度拥挤的脉冲品种</p><p class='note'>标题仅为栏目包装，正文为数据研究；仅供研究参考，不构成投资建议。</p></div><aside class='dark'><div>数据截至 {TARGET} 收盘</div><h2>{state} · 今日零推荐</h2><p>环境分{score:.1f}。29个行业中最高热度为{top_sectors[0]['name']} {top_sectors[0]['sector_heat']:.2f}，未达到65分门槛，且榜首处于严重拥挤区，不建立个股候选池。</p></aside></header>
<section id='executive-summary' class='section card'><div class='head'><div><div class='kicker'>00 / brief</div><h2>行情摘要</h2></div><span class='tag'>结论先行</span></div><div class='grid g4'><div class='metric'><span>市场状态</span><b>{state} {score:.1f}</b></div><div class='metric'><span>市场宽度</span><b>涨{breadth['CNT_RED']} / 跌{breadth['CNT_GREEN']}</b></div><div class='metric'><span>两市成交</span><b>{turnover['amount_100m_cny']:.0f}亿元</b></div><div class='metric'><span>最高行业热度</span><b>{top_sectors[0]['name']} {top_sectors[0]['sector_heat']:.2f}</b></div></div><p>指数回调但个股涨多跌少，涨停{breadth['CNT_REACH_UPLIMIT']}家、跌停{breadth['CNT_REACH_DNLIMIT']}家，宽度明显强于指数。问题是成交仅约{turnover['amount_100m_cny']:.0f}亿元，为20日均量的{turnover['vs_twenty_day_average_pct']:.2f}%，增量资金不足。行业横截面最高分仍未过65，今日不给出个股推荐。</p></section>
<section id='macro' class='section card'><div class='head'><div><div class='kicker'>01 / macro</div><h2>宏观大势</h2></div><span class='tag'>流动性 · 增长动能</span></div><div class='grid g4'><div class='metric'><span>资金成本（截至08-31）</span><b>DR007 1.41%</b></div><div class='metric'><span>M2 / M1（07-31）</span><b>+7.7% / +4.0%</b></div><div class='metric'><span>社融存量（07-31）</span><b>+7.4%</b></div><div class='metric'><span>制造业PMI（08-31）</span><b>49.8</b></div></div><div class='grid g3' style='margin-top:12px'><div class='panel'><b>资金面偏松</b><p>DR007报1.41%，SHIBOR隔夜1.413%，短端资金成本处于低位区间，对估值形成支撑，但尚未转化为成交量放大。</p></div><div class='panel'><b>信用扩张仍偏弱</b><p>M2同比+7.7%、M1同比+4.0%，M1-M2剪刀差-3.7；社融存量+7.4%，当月新增2.225万亿元、同比-7.25%。宽货币到宽信用的传导仍慢。</p></div><div class='panel'><b>景气度边际改善但未回扩张</b><p>8月制造业PMI 49.8（环比+0.81），新订单50.6、生产50.4回到荣枯线上方，非制造业商务活动49.0、综合49.5仍偏弱。</p></div></div><div class='grid g3' style='margin-top:12px'><div class='panel'><b>A股传导</b><p>流动性宽松利好高久期成长与题材估值，但信用扩张偏弱限制顺周期与总量链的弹性，市场更易呈现结构轮动而非普涨。</p></div><div class='panel'><b>受益 / 承压方向</b><p>受益：对资金成本敏感的高研发成长、题材与小盘；承压：依赖信用扩张的地产链、传统投资品与部分顺周期。</p></div><div class='panel'><b>后续跟踪点</b><p>跟踪社融当月新增同比能否转正、M1增速能否继续回升、PMI新订单能否连续两月站稳50以上，以及成交量能否回到20日均量之上。</p></div></div><p class='note'>宏观为低频数据，实际数据日截至2026-08-31；工业利润累计同比+17.6%、工业增加值+5.3%（07-31），二季度GDP累计同比+4.7%，CPI +0.5%、核心CPI +0.9%、CPI-PPI剪刀差-3.0。</p></section>
<section id='market' class='section card'><div class='head'><div><div class='kicker'>02 / market</div><h2>大盘判断</h2></div><span class='tag'>{TARGET} 收盘</span></div><div class='grid g4'><div class='metric'><span>上证指数</span><b>{idx['上证指数']['close']:.2f} <i class='down'>{idx['上证指数']['change_pct']:+.2f}%</i></b></div><div class='metric'><span>深证成指</span><b>{idx['深证成指']['close']:.2f} <i class='down'>{idx['深证成指']['change_pct']:+.2f}%</i></b></div><div class='metric'><span>创业板指</span><b>{idx['创业板指']['close']:.2f} <i class='down'>{idx['创业板指']['change_pct']:+.2f}%</i></b></div><div class='metric'><span>成交/20日均量</span><b>{turnover['vs_twenty_day_average_pct']:.2f}%</b></div></div><div class='grid g3' style='margin-top:12px'><div class='panel'><b>宽度明显强于指数</b><p>上涨占比{breadth['RATIO_UP']:.2f}%，涨停{breadth['CNT_REACH_UPLIMIT']}家、跌停{breadth['CNT_REACH_DNLIMIT']}家；5日新高{breadth['CNT_HIGH5']}家对新低{breadth['CNT_LOW5']}家，20日新高{breadth['CNT_HIGH20']}家对新低{breadth['CNT_LOW20']}家。</p></div><div class='panel'><b>量能是主要短板</b><p>两市成交约{turnover['amount_100m_cny']:.0f}亿元，为5日均量的99.67%、20日均量的{turnover['vs_twenty_day_average_pct']:.2f}%，中期均量之上占比更低，增量资金不足。</p></div><div class='panel'><b>指数分化、中期未修复</b><p>上证5日+2.33%、20日+4.12%相对抗跌，深证20日-0.10%、创业板20日-2.74%，60日维度深证-6.40%、创业板-10.98%，中期修复远未完成。</p></div></div><div class='grid g3' style='margin-top:12px'><div class='panel'><b>情绪面：涨停结构</b><p>涨停池{hot['limit_up_pool_count']}家，主题分布：{theme_text}。</p></div><div class='panel'><b>最高连板</b><p>{top_boards}。</p></div><div class='panel'><b>估值位置</b><p>中证全指PE-TTM 20.67，处10年81.71%分位、5年80.08%分位、3年66.80%分位，整体不便宜（数据日08-31）。</p></div></div><p class='note'>涨停与宽度存在口径差异：带日期的market-overview为涨{breadth['CNT_RED']}/跌{breadth['CNT_GREEN']}、涨停{breadth['CNT_REACH_UPLIMIT']}，changedist实时口径为涨1627/跌3812、涨停47；正式评分采用带目标日期的market-overview，实时口径仅作复核，不取平均。</p></section>
<section id='sectors' class='section card'><div class='head'><div><div class='kicker'>03 / sectors</div><h2>板块筛选</h2></div><span class='tag'>{len(qualified)}个方向达标</span></div><table><thead><tr><th>行业</th><th>价格P</th><th>资金F</th><th>正交R</th><th>趋势T</th><th>拥挤C</th><th>ΔC5</th><th>扣分</th><th>热度</th><th>预警</th></tr></thead><tbody>{sector_rows()}</tbody></table><div class='grid g3' style='margin-top:12px'>{sector_cards()}</div><p class='note'>29行业完整横截面回归：样本{reg['sample_size']}、覆盖率{reg['coverage']:.0%}、beta={reg['beta']:.4f}、R²={reg['r_squared']:.4f}。最高热度{top_sectors[0]['sector_heat']:.2f}仍低于65分门槛，因此只列观察方向，不下钻个股。</p></section>
<section id='picks' class='section card'><div class='head'><div><div class='kicker'>04 / picks</div><h2>今日结论</h2></div><span class='tag'>零推荐</span></div><div class='empty'><h3>本期不建立个股推荐榜</h3><p>原因不是数据缺失，而是29行业完整横截面没有任何方向达到65分。{top_sectors[0]['name']}量价双强但拥挤度{top_sectors[0]['crowding']['crowding_score']:.2f}接近极限，被扣{top_sectors[0]['crowding']['penalty']:.2f}分后仅剩{top_sectors[0]['sector_heat']:.2f}；{top_sectors[1]['name']}独立资金R={top_sectors[1]['orthogonal_flow_r']:.2f}很靠前，但价格P={top_sectors[1]['price_momentum_p']:.2f}未确认；{top_sectors[4]['name']}趋势T={top_sectors[4]['trend_confirmation_t']:.2f}最强，却因拥挤加速被扣{top_sectors[4]['crowding']['penalty']:.2f}分。按规则停止向个股层下钻。</p><p><b>重启条件：</b>需同时看到（1）行业热度重新站上65分；（2）独立资金残差R保持在50以上且不再依赖单一拥挤驱动；（3）拥挤度C回落至70以下或5日加速度转负。三条同时满足才重启候选池。</p></div></section>
<section id='risks' class='section card risk'><div class='kicker'>05 / risks</div><h2>风险提示</h2><ul><li>{top_sectors[0]['name']}热度{top_sectors[0]['sector_heat']:.2f}，拥挤度{top_sectors[0]['crowding']['crowding_score']:.2f}（RSI强度、换手率、成交占比三项均达近一年极端分位），20日涨幅已达+24.90%，波动放大风险显著。</li><li>{top_sectors[1]['name']}与{top_sectors[3]['name']}的拥挤度5日变化分别为{top_sectors[1]['crowding']['delta_5d']:+.2f}和{top_sectors[3]['crowding']['delta_5d']:+.2f}，资金拥挤正在加速而非缓解。</li><li>{top_sectors[4]['name']}趋势T={top_sectors[4]['trend_confirmation_t']:.2f}较强但拥挤{top_sectors[4]['crowding']['crowding_score']:.2f}、5日加速{top_sectors[4]['crowding']['delta_5d']:+.2f}，属于趋势好但交易已不便宜。</li><li>成交持续低于20日、60日、120日与250日均量，若量能不能修复，宽度优势难以转化为指数级别的持续性行情。</li><li>全球风险、目标日两融余额与股债风险溢价缺少统一时点数据，按中性降级处理，不代表外部风险低。</li></ul><p><b>免责声明</b>：以上内容基于公开与授权数据，仅供研究参考，不构成投资建议。市场有风险，投资需谨慎。</p></section>
<details id='methodology'><summary>方法与数据降级说明</summary><p>市场环境=30%指数与风格趋势+25%市场宽度和情绪+20%成交与流动性+15%国内宏观流动性+10%全球风险，本期为0.30×47.0+0.25×70.7+0.20×49.3+0.15×59.5+0.10×50.0={score:.1f}。</p><p>行业采用量价正交V3：P=20%×P1+35%×P5+45%×P20，F同权重；对zF~zP做横截面回归取残差分位R；T=70%×P+30%×R；CoreHeat=35%×T+15%×广度+10%×关注度+10%×催化+10%×基本面；Opportunity=CoreHeat/0.8；SectorHeat=Opportunity-CrowdPenalty，拥挤惩罚最高20分且低拥挤不加分。</p><p>绝对方向约束：5日与20日收益同时非正时T上限55，5日与20日资金强度同时非正时R上限50。硬上限：P≤50且R≥80为资金潜伏，P≥70且R≤20为量价背离，两类情形SectorHeat均不高于60。</p><p>催化与基本面缺少统一可审计的行业横截面证据，按50分降级；北交所成份股不在资金接口支持范围，未补造；外部信息只作定性核验，缺失项不补造。所有分数用于同一横截面相对排序，不是收益概率。</p></details></main><footer class='footer'>数据来源：WeStock、hithink-finance与公开资料复核｜评分日 {TARGET}｜证据台账 {TARGET}-evidence.md｜仅供研究参考，不构成投资建议</footer></body></html>"""

mobile_css = """
:root{--paper:#f7f3ea;--m-ink:#18332d;--ink:var(--m-ink);--body:#293631;--red:#a83e32;--green:#17705e;--m-gold:#b98532;--gold:var(--m-gold);--line:#e1d9ca;--card:#fffdf7;--muted:#746f65;--serif:STSong,SimSun,serif;--sans:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}*{box-sizing:border-box}body{margin:0;background:#e7e0d2;color:var(--body);font:15px/1.65 var(--sans)}.m-shell{max-width:460px;margin:auto;background:var(--paper);padding-bottom:24px}.top{background:var(--ink);color:#f8f2e5;padding:16px;border-bottom:3px solid var(--gold)}.top b{font:700 19px var(--serif)}.m-seal{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;margin-right:8px;border:1px solid #e8c887;color:#e8c887;font:700 18px var(--serif)}.cover{padding:18px 15px}.date,.kicker{color:var(--gold);font-size:10px;font-weight:700;letter-spacing:.11em}.cover h1{font:700 30px/1.2 var(--serif);color:var(--ink);margin:8px 0}.state{background:var(--ink);color:#f8f2e5;border-left:4px solid var(--gold);padding:12px}.state b{color:#e8c887}.sec{margin:12px;background:var(--card);border:1px solid var(--line);padding:14px}.sec h2{font:700 23px var(--serif);color:var(--ink);margin:3px 0 9px}.line,.kv{display:flex;gap:10px;justify-content:space-between;padding:6px 0;border-bottom:1px dashed var(--line)}.kv{align-items:flex-start}.k{color:var(--muted);min-width:70px}.up{color:var(--red)}.down{color:var(--green)}.stock{margin-top:10px;border-top:3px solid var(--gold);padding-top:10px}.stock h3{font:700 21px var(--serif);color:var(--ink);margin:0}.note{color:var(--muted);font-size:12px}.risk{border-left:4px solid var(--red)}.risk ul{margin:8px 0;padding-left:20px}details{margin:12px;padding:12px;border:1px solid var(--line)}footer{text-align:center;padding:18px;background:var(--ink);color:#d7ddd4;font-size:12px}
"""

mobile_sector_cards = "".join(
    f"<div class='stock'><h3>{x['name']} {x['sector_heat']:.2f}</h3>"
    f"<p>{SECTOR_NOTES.get(x['name'], '结构性轮动方向，未达入选门槛。')}</p>"
    f"<div class='line'><span class='k'>价格P / 资金F</span><span>{x['price_momentum_p']:.2f} / {x['fund_flow_f']:.2f}</span></div>"
    f"<div class='line'><span class='k'>独立资金R</span><span>{x['orthogonal_flow_r']:.2f}</span></div>"
    f"<div class='line'><span class='k'>趋势T</span><span>{x['trend_confirmation_t']:.2f}</span></div>"
    f"<div class='line'><span class='k'>拥挤C / 扣分</span><span>{x['crowding']['crowding_score']:.2f} / {x['crowding']['penalty']:.2f}</span></div>"
    f"<p class='note'>{format_crowding_warnings(x['crowding']['warnings'])}</p></div>"
    for x in top_sectors[:3]
)

mobile_caveats = (
    "<section id='caveats' class='sec'>"
    "<div class='kicker'>06 / caveats</div>"
    "<h2>数据可信度与跟踪点</h2>"
    "<div class='kv'><span class='k'>宽度口径</span><span>带日期口径涨3386/跌2040/涨停80，实时口径涨1627/跌3812/涨停47；评分采用带日期口径。</span></div>"
    "<div class='kv'><span class='k'>未补造项</span><span>北交所96只成份股资金缺失、目标日两融余额、全球风险与股债风险溢价均按中性降级。</span></div>"
    "<div class='kv'><span class='k'>量价验证</span><span>榜首种植业K线、估值、资金覆盖均已核验；2026-09-02盘中板块已回撤-5.39%，与严重拥挤判定一致。</span></div>"
    "<div class='kv'><span class='k'>跟踪触发</span><span>社融同比转正、M1连续回升、PMI站稳50、成交回到20日均量之上、任意板块热度≥65且拥挤&lt;70，五条任一发生即重评。</span></div>"
    "<p class='note'>所有分数用于同一横截面相对排序，不是收益概率；外部信息仅作定性核验。</p>"
    "</section>"
)

mobile = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta name='description' content='2026年9月1日A股盘后研究日报移动版'><title>行情老黄历｜{TARGET}</title><style>{mobile_css}</style></head><body><div class="m-shell"><header class='top'><b><span class="m-seal">历</span>行情老黄历 · A股研究</b></header><header id='cover' class='cover'><div class='date'>评分交易日 {TARGET}</div><h1>个股涨多跌少，量能仍是短板</h1><p><b>宜</b> 等资金延续与拥挤回落　<b>忌</b> 追极度拥挤的脉冲</p><div class='state'><b>{state} · 今日零推荐</b><br>环境分{score:.1f}，行业最高热度{top_sectors[0]['sector_heat']:.2f}，未达65分门槛。</div><p class='note'>标题仅为栏目包装，正文为数据研究。<br>仅供研究参考，不构成投资建议。</p></header><section id='executive-summary' class='sec'><div class='kicker'>00 / brief</div><h2>行情摘要</h2><div class='line'><span class='k'>指数</span><span>上证{idx['上证指数']['change_pct']:+.2f}%｜创业板{idx['创业板指']['change_pct']:+.2f}%</span></div><div class='line'><span class='k'>宽度</span><span>涨{breadth['CNT_RED']} / 跌{breadth['CNT_GREEN']}，涨停{breadth['CNT_REACH_UPLIMIT']}</span></div><div class='line'><span class='k'>成交</span><span>{turnover['amount_100m_cny']:.0f}亿元（20日均量{turnover['vs_twenty_day_average_pct']:.0f}%）</span></div><div class='line'><span class='k'>结论</span><span>29行业均未过65分门槛</span></div><p>宽度强于指数，但量能不足、行业最高分仍偏低，本期不给出个股推荐。</p><p><b>仅供研究参考，不构成投资建议。</b></p></section><section id='macro' class='sec'><div class='kicker'>01 / macro</div><h2>宏观大势</h2><div class='kv'><span class='k'>资金面</span><span>DR007 1.41%，短端资金成本偏低（08-31）。</span></div><div class='kv'><span class='k'>信用</span><span>M2 +7.7%、M1 +4.0%，社融存量+7.4%，当月新增同比-7.25%（07-31）。</span></div><div class='kv'><span class='k'>景气</span><span>制造业PMI 49.8，新订单50.6、生产50.4回到扩张区（08-31）。</span></div><div class='kv'><span class='k'>A股传导</span><span>宽货币支撑题材与高久期成长，信用偏弱限制顺周期弹性，市场更易结构轮动。</span></div><div class='kv'><span class='k'>跟踪点</span><span>社融同比转正、M1继续回升、PMI站稳50、成交回到20日均量上方。</span></div></section><section id='market' class='sec'><div class='kicker'>02 / market</div><h2>大盘判断</h2><div class='line'><span class='k'>上证</span><span>{idx['上证指数']['close']:.2f} <span class='down'>{idx['上证指数']['change_pct']:+.2f}%</span></span></div><div class='line'><span class='k'>深证</span><span>{idx['深证成指']['close']:.2f} <span class='down'>{idx['深证成指']['change_pct']:+.2f}%</span></span></div><div class='line'><span class='k'>创业板</span><span>{idx['创业板指']['close']:.2f} <span class='down'>{idx['创业板指']['change_pct']:+.2f}%</span></span></div><div class='line'><span class='k'>成交</span><span>{turnover['amount_100m_cny']:.0f}亿元，为20日均量{turnover['vs_twenty_day_average_pct']:.0f}%</span></div><p>指数分化回落，但上涨占比{breadth['RATIO_UP']:.0f}%、涨停{breadth['CNT_REACH_UPLIMIT']}家无跌停，宽度明显强于指数；短板是成交低于20日以上各期均量，增量资金不足。涨停主题集中在{theme_text}。</p><p class='note'>宽度存在口径差异：带日期口径涨{breadth['CNT_RED']}/跌{breadth['CNT_GREEN']}，实时口径涨1627/跌3812；正式评分采用带日期口径。</p></section><section id='sectors' class='sec'><div class='kicker'>03 / sectors</div><h2>板块观察</h2>{mobile_sector_cards}<p class='note'>29行业横截面回归：样本{reg['sample_size']}、覆盖率{reg['coverage']:.0%}、R²={reg['r_squared']:.2f}。最高{top_sectors[0]['sector_heat']:.2f}分，未过65分门槛，只列观察方向。</p></section><section id='picks' class='sec'><div class='kicker'>04 / picks</div><h2>今日结论</h2><p>29个行业完整横截面中，没有方向达到65分门槛，因此本期不建立个股推荐榜，也不为凑数量放宽规则。</p><p><b>重启条件：</b>行业热度站上65分、独立资金R保持50以上、拥挤度回落到70以下或5日加速转负，三条同时满足才重启筛选。</p></section><section id='risks' class='sec risk'><div class='kicker'>05 / risks</div><h2>风险提示</h2><ul><li>{top_sectors[0]['name']}拥挤度{top_sectors[0]['crowding']['crowding_score']:.0f}，20日涨幅+24.90%，追高风险大。</li><li>{top_sectors[1]['name']}、{top_sectors[3]['name']}拥挤度5日加速明显。</li><li>成交持续低于各期均量，宽度优势难转化为持续行情。</li><li>全球风险与部分高频字段缺失，按中性处理。</li></ul><p class='note'>仅供研究参考，不构成投资建议。市场有风险，投资需谨慎。</p></section>{mobile_caveats}<details id='methodology'><summary>方法与数据降级说明</summary><p>市场环境=30%指数趋势+25%宽度情绪+20%成交流动性+15%宏观流动性+10%全球风险，本期{score:.1f}分（中性）。</p><p>行业量价正交V3：资金对价格回归取残差分位R，T=70%P+30%R，SectorHeat=CoreHeat/0.8-拥挤惩罚（最高20分，低拥挤不加分）。</p><p>催化与基本面按50分降级；北交所成份股资金缺失未补造；外部信息仅作定性核验。</p></details><footer>数据来源：WeStock、hithink-finance｜评分日 {TARGET}<br>仅供研究参考，不构成投资建议</footer></div></body></html>"""

note = f"""# 9月1日A股复盘｜涨多跌少，但量能和拥挤度都不支持追高

上证{idx['上证指数']['change_pct']:+.2f}%、深证{idx['深证成指']['change_pct']:+.2f}%、创业板{idx['创业板指']['change_pct']:+.2f}%。
上涨{breadth['CNT_RED']}家、下跌{breadth['CNT_GREEN']}家，涨停{breadth['CNT_REACH_UPLIMIT']}家、跌停{breadth['CNT_REACH_DNLIMIT']}家，两市成交{turnover['amount_100m_cny']:.0f}亿元。

今日宜：等资金延续、等拥挤回落。
今日忌：追已经极度拥挤的脉冲品种。

**三个关键事实**

1. 宽度强于指数：上涨占比{breadth['RATIO_UP']:.0f}%，涨停{breadth['CNT_REACH_UPLIMIT']}家且无跌停，说明赚钱效应还在，只是不在权重股上。
2. 量能是短板：成交{turnover['amount_100m_cny']:.0f}亿元，只有20日均量的{turnover['vs_twenty_day_average_pct']:.0f}%，中长期均量占比更低，增量资金不足。
3. 宏观偏松但信用偏弱：DR007 1.41%（08-31）；M2 +7.7%、M1 +4.0%、社融存量+7.4%但当月新增同比-7.25%（07-31）；制造业PMI 49.8，新订单50.6、生产50.4回到扩张区（08-31）。

**板块观察（量价正交V3，29个行业完整横截面）**

1. {top_sectors[0]['name']} {top_sectors[0]['sector_heat']:.2f}：价格P={top_sectors[0]['price_momentum_p']:.0f}、资金F={top_sectors[0]['fund_flow_f']:.0f}都是满分，但拥挤度{top_sectors[0]['crowding']['crowding_score']:.0f}接近极限，被扣{top_sectors[0]['crowding']['penalty']:.1f}分；20日涨幅+24.90%，属于极致抱团脉冲。
2. {top_sectors[1]['name']} {top_sectors[1]['sector_heat']:.2f}：独立资金R={top_sectors[1]['orthogonal_flow_r']:.0f}很靠前，但价格P={top_sectors[1]['price_momentum_p']:.0f}还没确认，属于资金先行。
3. {top_sectors[2]['name']} {top_sectors[2]['sector_heat']:.2f}：价格与资金都在中位，当日板块下跌，趋势T={top_sectors[2]['trend_confirmation_t']:.0f}不足。
4. {top_sectors[4]['name']} {top_sectors[4]['sector_heat']:.2f}：趋势T={top_sectors[4]['trend_confirmation_t']:.0f}是前五最强，但拥挤{top_sectors[4]['crowding']['crowding_score']:.0f}且5日还在加速，被扣{top_sectors[4]['crowding']['penalty']:.1f}分。

**今日结论**

29个行业里没有任何一个达到65分门槛，所以本期不给个股推荐，也不为了凑数量放宽规则。

重启条件：行业热度站上65分 + 独立资金R保持50以上 + 拥挤度回落到70以下或5日加速转负，三条同时满足才重启。

**风险提醒**

- 拥挤度接近极限的板块，回撤往往比上涨更快，不宜在加速段追入。
- 成交持续低于各期均量，宽度优势很难转化为持续性行情。
- 全球风险与部分高频字段缺失，按中性处理，不代表风险低。

仅供研究参考，不构成投资建议。市场有风险，投资需谨慎。

#A股 #股票复盘 #行业研究 #每日复盘 #行情分析
"""

sector_lines = []
for rank, x in enumerate(top_sectors, 1):
    c = x["crowding"]
    sector_lines.append(
        f"| {rank} | {x['name']} | {x['price_momentum_p']:.2f} | {x['fund_flow_f']:.2f} | "
        f"{x['orthogonal_flow_r']:.2f} | {x['trend_confirmation_t']:.2f} | {c['crowding_score']:.2f} | "
        f"{c['delta_5d']:+.2f} | {c['penalty']:.2f} | {x['sector_heat']:.2f} | {x.get('confidence', 0):.0f}% |"
    )

evidence = f"""# {TARGET} 股市老黄历证据台账

- 评分交易日：{TARGET}，盘后；时区：Asia/Shanghai。
- 生成时间：2026-09-02 盘中，因此采用最近已完整收盘交易日 {TARGET}，不使用盘中或未收盘数据。
- 产物：桌面HTML、移动HTML、小红书笔记。
- 数据原则：结构化行情优先；冲突并列披露；缺失不补造；外部搜索仅作定性核验。

## 一、市场环境

MarketEnvironment = {score:.1f}，状态为{state}。

| 维度 | 分数 | 权重 | 加权贡献 |
|---|---:|---:|---:|
| 指数与风格趋势 | 47.0 | 30% | 14.1 |
| 市场宽度和情绪 | 70.7 | 25% | 17.7 |
| 成交与流动性 | 49.3 | 20% | 9.9 |
| 国内宏观流动性 | 59.5 | 15% | 8.9 |
| 全球风险 | 50.0 | 10% | 5.0 |

计算：0.30×47.0 + 0.25×70.7 + 0.20×49.3 + 0.15×59.5 + 0.10×50.0 = {score:.1f}。

- 上证指数{idx['上证指数']['close']:.2f}（{idx['上证指数']['change_pct']:+.2f}%）；深证成指{idx['深证成指']['close']:.2f}（{idx['深证成指']['change_pct']:+.2f}%）；创业板指{idx['创业板指']['close']:.2f}（{idx['创业板指']['change_pct']:+.2f}%）。
- 区间收益：上证5日+2.33%、20日+4.12%、60日+0.52%、120日-3.47%、250日+5.67%；深证20日-0.10%、60日-6.40%；创业板20日-2.74%、60日-10.98%。
- 上涨{breadth['CNT_RED']}、下跌{breadth['CNT_GREEN']}、平盘{breadth['CNT_ZERO']}，上涨占比{breadth['RATIO_UP']:.2f}%；涨停{breadth['CNT_REACH_UPLIMIT']}、跌停{breadth['CNT_REACH_DNLIMIT']}。
- 新高/新低：5日 {breadth['CNT_HIGH5']}/{breadth['CNT_LOW5']}，20日 {breadth['CNT_HIGH20']}/{breadth['CNT_LOW20']}，60日 {breadth['CNT_HIGH60']}/{breadth['CNT_LOW60']}，250日 {breadth['CNT_HIGH250']}/{breadth['CNT_LOW250']}。
- 两市成交{turnover['amount_100m_cny']:.2f}亿元，为5日均量99.67%、10日均量99.14%、20日均量{turnover['vs_twenty_day_average_pct']:.2f}%、60日均量76.89%、120日均量77.40%、250日均量82.63%。
- 技术面：MA5 3957.49、MA20 3932.78、MA60 3957.52、MA250 3985.51；MACD dif 11.04 / dea 1.95；RSI6 67.56。
- 估值（中证全指，数据日2026-08-31）：PE-TTM 20.67，10年分位81.71%、5年80.08%、3年66.80%；PB 1.78。

### 宏观（低频，实际数据日 20260831）

- 资金成本：DR007(FDR007) 1.41%；SHIBOR 隔夜1.413%、1M 1.4168%、1Y 1.48%。
- 货币信用：M2 +7.7%、M1 +4.0%、剪刀差-3.7；社融存量+7.4%，当月新增2.225万亿元、同比-7.25%（截至20260731）。
- 增长动能：制造业PMI 49.8（环比+0.81）、新订单50.6、生产50.4、非制造业商务活动49.0、综合49.5；二季度GDP累计同比+4.7%。
- 盈利与价格：工业利润累计同比+17.6%（有色+91.8、化学原料+56.6、煤炭+50.4）、工业增加值+5.3%（高技术+13.8、TMT+15.4）；CPI +0.5%、核心CPI +0.9%、CPI-PPI剪刀差-3.0。

## 二、行业量价正交 V3

- 方法标识：`{sector_score['method']}`（生成前已校验）。
- 分类：固定29个申万二级行业完整横截面。
- 回归：enabled={str(reg['enabled']).lower()}，sample_size={reg['sample_size']}，coverage={reg['coverage']:.0%}，beta={reg['beta']:.10f}，R²={reg['r_squared']:.4f}。
- 公式：P=20%×P1+35%×P5+45%×P20；F同权重；对zF~zP回归取残差分位R；T=70%×P+30%×R；CoreHeat=35%×T+15%×广度+10%×关注度+10%×催化+10%×基本面；Opportunity=CoreHeat/0.8；SectorHeat=Opportunity-CrowdPenalty。
- 方向约束：5日与20日收益同时非正时T上限55；5日与20日资金强度同时非正时R上限50。
- 硬上限：P≤50且R≥80为资金潜伏，P≥70且R≤20为量价背离，两类情形SectorHeat均不高于60。
- 拥挤惩罚：C≤50不奖不罚，C>50线性扣分最高20分；拥挤加速度额外扣分；C≥70、ΔC5≥10或子指标达近一年95分位必须预警。
- 严重拥挤保留规则：仅当SectorHeat≥70且R≥50时可保留1个。

| 排名 | 行业 | P | F | R | T | C | ΔC5 | 扣分 | SectorHeat | 置信度 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(sector_lines)}

正式过线：{len(qualified)}个。前五均未达到65分，最高为{top_sectors[0]['name']} {top_sectors[0]['sector_heat']:.2f}。

### 榜首人工核验（种植业）

- K线（板块代码 pt01801016）：2026-09-01 收2803.25，前收2615.18，单日+7.19%，成交额149.62亿元；20日累计+24.90%。
- 估值：PE-TTM 84.103（近10年分位86.16%）、PB 2.8401（分位52.54%）。
- 资金覆盖：1日20/22只（2只北交所不支持），K线覆盖率100%（307行，2025-06-03至2026-09-01）。
- 后续跟踪：2026-09-02 盘中已回撤至2652.05（-5.39%），与“严重拥挤+追高风险”判定一致，数据非异常。

## 三、候选池与个股结论

- 行业门槛未通过，候选池构建与个股深度核验按规则跳过。
- 逐行业门槛判定见 `2026-09-01-stock-candidates.json` 的 `gate_detail`。
- 零推荐不代表市场没有上涨股票，而是当前证据不足以通过统一门槛。

## 四、冲突、降级与限制

- 市场宽度与涨停家数：带日期的market-overview为涨{breadth['CNT_RED']}/跌{breadth['CNT_GREEN']}、涨停{breadth['CNT_REACH_UPLIMIT']}/跌停{breadth['CNT_REACH_DNLIMIT']}；changedist实时口径为涨1627/跌3812、涨停47/跌停3；hithink涨停池80家。正式评分采用带目标日期的market-overview，实时口径仅作复核，不取平均。
- WeStock changedist为查询时点实时截面且不接受历史日期，与带日期口径存在样本范围差异。
- 两融余额：market-overview --type margin --date 2026-09-01 返回“后端今日尚未更新”，该分项按中性50分降级。
- 北交所成份股不在WeStock个股资金接口支持范围（本期96只），未替代或补造。
- 成分股资金聚合：29行业、1820只唯一成份股、1724只受支持、55,156条资金记录，22个批次全部成功、0失败。
- catalyst与fundamental没有统一可审计的行业横截面结构化证据，sector input保持null并按50分降级。
- 全球风险、股债风险溢价缺少统一时点，按50分降级，不解释为低风险。
- 宏观为低频数据，实际数据日截至20260831，部分月度指标截至20260731、季度指标截至20260630。
- 所有分数用于同一横截面相对排序，不是收益概率。

## 五、涨停与热点（定性补充，不参与评分）

- 涨停池{hot['limit_up_pool_count']}家；主题分布：{theme_text}。
- 最高连板：{top_boards}。

## 六、小红书发布前自检

- 移动HTML与小红书笔记未出现个股名称、代码或精确买入/止盈/止损价格。
- 正文可见位置保留“仅供研究参考，不构成投资建议”。
- 未使用收益承诺、绝对化预测、指令性买卖、导流或诱导互动话术。
- 未使用天干地支、五行、生肖、卦象或吉时对行情做推演，栏目名称仅作包装。
- 本期零推荐，已明确说明规则与重启条件。
- 自动化只填充待发布内容并保存截图，不点击发布按钮，最终由人工确认发布。
"""

files = {
    f"{TARGET}-stock-almanac.html": desktop,
    f"{TARGET}-stock-almanac-mobile.html": mobile,
    f"{TARGET}-xiaohongshu-note.md": note,
    f"{TARGET}-evidence.md": evidence,
}
for name, text in files.items():
    (OUT / name).write_text(text, encoding="utf-8")
print(
    json.dumps(
        {
            "generated": [str(OUT / name) for name in files],
            "qualified_sectors": len(qualified),
            "market_score": score,
            "top_sector": top_sectors[0]["name"],
            "top_heat": round(top_sectors[0]["sector_heat"], 2),
        },
        ensure_ascii=False,
        indent=2,
    )
)
