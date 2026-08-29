from __future__ import annotations

import json
from pathlib import Path

TARGET = "2026-08-28"
MARKET_SCORE = 63.3
INPUT = Path(f"E:/WS/NashnovaResearch/evidence/{TARGET}-stock-candidates.json")
DEEP = Path(f"E:/WS/NashnovaResearch/evidence/{TARGET}-stock-deep-summary.json")

JUDGEMENTS = {
    "sh601869": {
        "fundamental_score": 90, "technical_score": 58, "fund_score": 98, "relative_strength_score": 97, "catalyst_score": 92, "liquidity_score": 96,
        "risk_penalty": 10, "confidence": 94, "decision": "不追涨，等待高位消化后再观察",
        "logic": "半年报利润与光纤需求形成强支撑，资金和相对强度居前；但涨停、估值和均线偏离显著。",
        "reasons": ["2026H1营收约98.09亿元、归母净利润约29.25亿元，TTM归母净利润约34.43亿元。", "评分日涨停，近20日涨约62.68%，收盘高于MA20约23.26%，接近布林上轨。", "1/5/20日主力资金均净流入，PE-TTM约102.65倍、PB约21.59倍。"],
        "risk_notes": ["短期涨幅与均线偏离较大", "估值较高", "曾披露股票交易异常波动公告"],
    },
    "sz002655": {
        "fundamental_score": 45, "technical_score": 60, "fund_score": 95, "relative_strength_score": 99, "catalyst_score": 66, "liquidity_score": 82,
        "risk_penalty": 10, "confidence": 91, "decision": "暂不入榜，等待估值与价格回归",
        "logic": "资金和趋势强，但利润规模、估值和20日涨幅与基本面匹配度不足。",
        "reasons": ["2026H1营收约7.17亿元、归母净利润约1377万元，TTM归母净利润约4490万元。", "近20日涨约83.80%，收盘高于MA20约21.47%。", "1/5/20日主力资金均净流入，但PE-TTM约317.72倍、PB约16.30倍。"],
        "risk_notes": ["估值极高", "近20日涨幅过大", "利润规模偏小"],
    },
    "sz002536": {
        "fundamental_score": 62, "technical_score": 52, "fund_score": 96, "relative_strength_score": 94, "catalyst_score": 88, "liquidity_score": 90,
        "risk_penalty": 10, "confidence": 92, "decision": "不追涨，等待液冷预期消化",
        "logic": "液冷订单和资金结构形成催化，但评分日涨停、价格高于布林上轨且估值明显偏高。",
        "reasons": ["2026H1营收约22.06亿元、归母净利润约7571万元，TTM归母净利润约1.82亿元。", "评分日涨停，近5日涨约27.00%，收盘高于MA20约27.56%并高于布林上轨。", "1/5/20日资金均净流入；PE-TTM约171.08倍。"],
        "risk_notes": ["股票交易异常波动", "高于布林上轨", "估值较高"],
    },
    "sh688143": {
        "fundamental_score": 35, "technical_score": 50, "fund_score": 78, "relative_strength_score": 100, "catalyst_score": 72, "liquidity_score": 88,
        "risk_penalty": 12, "confidence": 92, "decision": "回避追高，等待盈利兑现",
        "logic": "AI光通信预期与中期资金强，但盈利规模很小，估值极端，20日涨幅翻倍。",
        "reasons": ["2026H1营收约2.16亿元、归母净利润约1501万元，TTM归母净利润约983万元。", "近20日涨约117.06%，收盘高于MA20约35.35%。", "PE-TTM约2269.64倍、PB约16.35倍，当日主力资金转为净流出。"],
        "risk_notes": ["估值极端", "近20日涨幅翻倍", "当日资金净流出"],
    },
    "sh603083": {
        "fundamental_score": 82, "technical_score": 68, "fund_score": 83, "relative_strength_score": 90, "catalyst_score": 88, "liquidity_score": 95,
        "risk_penalty": 8, "confidence": 94, "decision": "回调至短期均线后条件观察",
        "logic": "半年报盈利、高速光模块催化和中期资金结构较强；但估值高、当日资金转弱且短期位置偏高。",
        "reasons": ["2026H1营收约27.05亿元、归母净利润约3.28亿元，TTM归母净利润约4.70亿元。", "近20日涨约52.32%，收盘高于MA20约19.14%，仍在布林上轨以内。", "5/20日主力资金净流入，当日小幅净流出；PE-TTM约155.19倍。"],
        "risk_notes": ["估值较高", "短期涨幅较大", "当日主力资金净流出"],
    },
}


def stock_score(j):
    return 0.25*j["fundamental_score"] + 0.25*j["technical_score"] + 0.20*j["fund_score"] + 0.15*j["relative_strength_score"] + 0.10*j["catalyst_score"] + 0.05*j["liquidity_score"]


def main():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    deep = json.loads(DEEP.read_text(encoding="utf-8"))
    by_code = {row["code"]: row for row in data["candidate_pool"]}
    scored = []
    for code, judgement in JUDGEMENTS.items():
        row = dict(by_code[code])
        s = round(stock_score(judgement), 1)
        final = round(0.15 * MARKET_SCORE + 0.25 * row["sector_heat"] + 0.60 * s - judgement["risk_penalty"], 1)
        row.update(judgement)
        row["stock_score"] = s
        row["final_score"] = final
        row["meets_score_threshold"] = final >= 68
        row["meets_confidence_threshold"] = judgement["confidence"] >= 75
        row["eligible_for_selection"] = row["meets_score_threshold"] and row["meets_confidence_threshold"]
        row["valuation"] = deep[code]["valuation"][0] if deep[code]["valuation"] else None
        row["finance_latest"] = deep[code]["finance_latest"]
        row["score_formula"] = {"market_environment": MARKET_SCORE, "sector_heat": row["sector_heat"], "stock_score": s, "risk_penalty": judgement["risk_penalty"]}
        scored.append(row)
    scored.sort(key=lambda row: row["final_score"], reverse=True)
    selected = []
    sector_count = {}
    for row in scored:
        if not row["eligible_for_selection"] or sector_count.get(row["sector_name"], 0) >= 2:
            continue
        selected.append(row)
        sector_count[row["sector_name"]] = sector_count.get(row["sector_name"], 0) + 1
        if len(selected) >= 5:
            break
    data["deep_verified"] = scored
    data["selected"] = selected
    data["selection_rule"] = {"market_state": "中性", "final_score_threshold": 68, "confidence_threshold_pct": 75, "same_sector_max": 2, "max_selected": 5}
    data["scoring_note"] = "六维分项基于2026-08-28目标日量价资金、截至目标日已披露财报、公司公告、研报摘要及估值快照；用于候选池相对排序，不代表收益预测。"
    INPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selected": [{"name": r["name"], "code": r["a_share_code"], "sector": r["sector_name"], "final_score": r["final_score"], "confidence": r["confidence"]} for r in selected], "all": [{"name": r["name"], "sector": r["sector_name"], "final_score": r["final_score"], "stock_score": r["stock_score"], "risk_penalty": r["risk_penalty"]} for r in scored]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
