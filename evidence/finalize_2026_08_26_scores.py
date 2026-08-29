from __future__ import annotations

import json
from pathlib import Path

TARGET = "2026-08-26"
MARKET_SCORE = 55.8
SECTOR_HEAT = 69.038339902
INPUT = Path("E:/WS/NashnovaResearch/evidence/2026-08-26-stock-candidates.json")
DEEP = Path("E:/WS/NashnovaResearch/evidence/2026-08-26-stock-deep-summary.json")

# 基本面与催化分来自财报、公告、研报摘要的逐股核验；技术、资金、相对强度和
# 流动性分综合候选JSON中的目标日量价字段。每项均保留判断理由，避免只写总分。
JUDGEMENTS = {
    "sh601212": {
        "fundamental_score": 35,
        "technical_score": 55,
        "fund_score": 92,
        "relative_strength_score": 98,
        "catalyst_score": 60,
        "liquidity_score": 68,
        "risk_penalty": 10,
        "confidence": 84,
        "decision": "回避追高，等待盈利与价格结构重新匹配",
        "logic": "资金和相对强度突出，但短期偏离均线、异常波动与TTM亏损削弱可执行性。",
        "reasons": [
            "2026Q1归母净利润约1.50亿元，但TTM归母净利润约-5.61亿元，盈利质量未形成稳定支撑。",
            "评分日涨停，收盘高于MA20约27.22%，RSI14约75，且高于布林上轨。",
            "1/5/20日主力资金均净流入，20日相对行业强约39.94个百分点。",
        ],
        "risk_notes": ["股票交易异常波动公告", "短期显著偏离MA20", "TTM盈利为负"],
    },
    "sz000603": {
        "fundamental_score": 85,
        "technical_score": 70,
        "fund_score": 72,
        "relative_strength_score": 96,
        "catalyst_score": 90,
        "liquidity_score": 93,
        "risk_penalty": 5,
        "confidence": 92,
        "decision": "逢回调观察，不在加速段追价",
        "logic": "半年报业绩与矿山投产形成基本面支撑，但20日涨幅较大且当日资金转弱。",
        "reasons": [
            "2026H1营收约11.52亿元、归母净利润约3.90亿元，最新财务时点覆盖半年报。",
            "鸿林矿业正式投产、银都矿业90万吨/年采矿技改获核准，属于公司公告确认的硬催化。",
            "近20日涨约48.64%，高于MA20约14.74%；当日主力净流出约1.41亿元，5/20日仍为净流入。",
        ],
        "risk_notes": ["近期多次异常波动公告", "当日资金净流出", "短期涨幅较大"],
    },
    "sz000426": {
        "fundamental_score": 88,
        "technical_score": 78,
        "fund_score": 75,
        "relative_strength_score": 89,
        "catalyst_score": 82,
        "liquidity_score": 95,
        "risk_penalty": 5,
        "confidence": 89,
        "decision": "回踩20日线企稳后条件式观察",
        "logic": "盈利能力、银锡价格弹性与中期资金结构较强，安全事故和并购执行构成主要折价。",
        "reasons": [
            "2026Q1营收约21.30亿元、归母净利润约13.38亿元；TTM归母净利润约26.68亿元。",
            "评分日高于MA20约7.01%，RSI14约56.90，趋势仍强但未处于极端超买。",
            "当日主力净流出约0.93亿元，5/20日分别净流入约12.19亿元和7.38亿元。",
        ],
        "risk_notes": ["子公司安全事故进展", "收购控制权与海外项目执行风险"],
    },
    "sz300328": {
        "fundamental_score": 25,
        "technical_score": 62,
        "fund_score": 85,
        "relative_strength_score": 95,
        "catalyst_score": 65,
        "liquidity_score": 45,
        "risk_penalty": 10,
        "confidence": 91,
        "decision": "暂不入榜，等待盈利改善与过热消化",
        "logic": "医疗镁材料进展与资金流入有催化，但半年报亏损、资产减值和技术过热不匹配。",
        "reasons": [
            "2026H1营收约7.99亿元、归母净利润约-5293万元，TTM归母净利润仍为负。",
            "收盘高于MA20约17.37%，并高于布林上轨；近5日涨约22.82%。",
            "1/5/20日主力资金均净流入，但盈利与估值仍缺少安全边际。",
        ],
        "risk_notes": ["半年报亏损", "计提资产减值及核销", "短期高于布林上轨"],
    },
    "sh601020": {
        "fundamental_score": 65,
        "technical_score": 78,
        "fund_score": 88,
        "relative_strength_score": 84,
        "catalyst_score": 55,
        "liquidity_score": 50,
        "risk_penalty": 10,
        "confidence": 84,
        "decision": "等待治理风险消化，不作正式推荐",
        "logic": "价格位置和多周期资金较温和，但控制权变化、管理层离任及减持计划提高治理折价。",
        "reasons": [
            "TTM归母净利润约8.56亿元，PE-TTM约21.89倍；最新正式财务为2026Q1。",
            "收盘高于MA20约3.86%，RSI14约54.77，技术位置较前四只温和。",
            "1/5/20日主力资金均净流入，20日相对行业强约11.32个百分点。",
        ],
        "risk_notes": ["控制权发生变更", "总经理离任", "高级管理人员减持计划"],
    },
}


def stock_score(j: dict) -> float:
    return (
        0.25 * j["fundamental_score"]
        + 0.25 * j["technical_score"]
        + 0.20 * j["fund_score"]
        + 0.15 * j["relative_strength_score"]
        + 0.10 * j["catalyst_score"]
        + 0.05 * j["liquidity_score"]
    )


def main() -> None:
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    deep = json.loads(DEEP.read_text(encoding="utf-8"))
    by_code = {row["code"]: row for row in data["candidate_pool"]}
    scored = []
    for code, judgement in JUDGEMENTS.items():
        row = dict(by_code[code])
        s = round(stock_score(judgement), 1)
        final = round(0.15 * MARKET_SCORE + 0.25 * SECTOR_HEAT + 0.60 * s - judgement["risk_penalty"], 1)
        row.update(judgement)
        row["stock_score"] = s
        row["final_score"] = final
        row["meets_score_threshold"] = final >= 68
        row["meets_confidence_threshold"] = judgement["confidence"] >= 75
        row["eligible_for_selection"] = row["meets_score_threshold"] and row["meets_confidence_threshold"]
        row["valuation"] = deep[code]["valuation"][0] if deep[code]["valuation"] else None
        row["finance_latest"] = deep[code]["finance_latest"]
        row["score_formula"] = {
            "market_environment": MARKET_SCORE,
            "sector_heat": SECTOR_HEAT,
            "stock_score": s,
            "risk_penalty": judgement["risk_penalty"],
        }
        scored.append(row)

    scored.sort(key=lambda row: row["final_score"], reverse=True)
    selected = [row for row in scored if row["eligible_for_selection"]][:2]
    data["deep_verified"] = scored
    data["selected"] = selected
    data["selection_rule"] = {
        "market_state": "中性",
        "final_score_threshold": 68,
        "confidence_threshold_pct": 75,
        "same_sector_max": 2,
    }
    data["scoring_note"] = "六维分项基于2026-08-26量价资金、最新已披露财报、公司公告、研报摘要及估值快照；分数用于相对排序，不代表收益预测。"
    INPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "selected": [{"name": r["name"], "code": r["a_share_code"], "final_score": r["final_score"], "confidence": r["confidence"]} for r in selected],
        "all": [{"name": r["name"], "final_score": r["final_score"], "stock_score": r["stock_score"], "risk_penalty": r["risk_penalty"]} for r in scored],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
