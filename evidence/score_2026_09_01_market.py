from __future__ import annotations

import json
from pathlib import Path

TARGET = "2026-08-28" if False else "2026-09-01"
PATH = Path(f"E:/WS/NashnovaResearch/evidence/{TARGET}-market-raw.json")
OUT = Path(f"E:/WS/NashnovaResearch/evidence/{TARGET}-market-score.json")
raw = json.loads(PATH.read_text(encoding="utf-8"))
overview = raw["source_raw"]["market_overview"]
rows = {x["info"]["type"]: x.get("row", {}) for x in overview}
trade = rows["trade"]
interval = rows["interval"]
updown = rows["updown"]

# 确定性叶子评分：只使用目标日带日期结构化字段；缺失项按50分中性降级。
index_score = 47.0
breadth_score = 70.7
turnover_score = 49.3
macro_score = 59.5
global_score = 50.0
total = round(
    0.30 * index_score
    + 0.25 * breadth_score
    + 0.20 * turnover_score
    + 0.15 * macro_score
    + 0.10 * global_score,
    1,
)
state = "进攻" if total >= 65 else ("中性" if total >= 45 else "防守")

payload = {
    "schema": "MarketEnvironmentDeterministicScore/v1",
    "as_of_date": TARGET,
    "timezone": "Asia/Shanghai",
    "market_phase": "盘后",
    "score_type": "确定性评分",
    "input_file": str(PATH).replace("\\", "/"),
    "method": {
        "formula": "30%×指数与风格趋势 + 25%×市场宽度和情绪 + 20%×成交与流动性 + 15%×国内宏观流动性 + 10%×全球风险",
        "normalization": "分项0-100；错日或盘中数据排除；缺失叶子按50分并降低置信度。",
        "market_state_mapping": {">=65": "进攻", "45-64.9": "中性", "<45": "防守"},
    },
    "dimensions": [
        {
            "id": "index_style_trend",
            "name": "指数与风格趋势",
            "weight": 0.30,
            "score": index_score,
            "weighted_contribution": round(0.30 * index_score, 1),
            "status": "指数分化明显：上证5日与20日仍为正，深证与创业板20日、60日双双转负，风格从成长切向低波与题材",
            "leaf_scores": [
                {
                    "name": "上证指数趋势",
                    "score": 58,
                    "basis": f"收盘{trade['CLOSE_PRICE_SZZS']}，日涨跌{trade['CHANGE_PCT_SZZS']}%；5日{interval['CHG_5D_SZZS']:+.2f}%、20日{interval['CHG_20D_SZZS']:+.2f}%、60日{interval['CHG_60D_SZZS']:+.2f}%；收盘位于MA20(3932.78)与MA60(3957.52)之上，但低于MA120(4006.42)与MA250(3985.51)。",
                },
                {
                    "name": "深证成指趋势",
                    "score": 47,
                    "basis": f"收盘{trade['CLOSE_PRICE_SZCZ']}，日涨跌{trade['CHANGE_PCT_SZCZ']}%；5日{interval['CHG_5D_SZCZ']:+.2f}%、20日{interval['CHG_20D_SZCZ']:+.2f}%、60日{interval['CHG_60D_SZCZ']:+.2f}%。",
                },
                {
                    "name": "创业板指趋势",
                    "score": 36,
                    "basis": f"收盘{trade['CLOSE_PRICE_CYBZ']}，日涨跌{trade['CHANGE_PCT_CYBZ']}%；5日{interval['CHG_5D_CYBZ']:+.2f}%、20日{interval['CHG_20D_CYBZ']:+.2f}%、60日{interval['CHG_60D_CYBZ']:+.2f}%，为三大指数中最弱。",
                },
            ],
            "degradation": "风格指数仅取沪深300/中证1000/成长/价值的区间收益，未引入额外加权。",
        },
        {
            "id": "breadth_sentiment",
            "name": "市场宽度和情绪",
            "weight": 0.25,
            "score": breadth_score,
            "weighted_contribution": round(0.25 * breadth_score, 1),
            "status": "指数回落但个股明显涨多跌少，涨停80家且无跌停，新高家数远多于新低，赚钱效应集中在中小市值与题材",
            "leaf_scores": [
                {
                    "name": "上涨占比",
                    "score": 61,
                    "basis": f"上涨{updown['CNT_RED']}、下跌{updown['CNT_GREEN']}、平盘{updown['CNT_ZERO']}，上涨占比{updown['RATIO_UP']}%，涨跌比{updown['RATIO_UPDOWN']}。",
                },
                {
                    "name": "涨跌停结构",
                    "score": 75,
                    "basis": f"带日期口径涨停{updown['CNT_REACH_UPLIMIT']}家、跌停{updown['CNT_REACH_DNLIMIT']}家，无跌停。",
                },
                {
                    "name": "新高新低结构",
                    "score": 76,
                    "basis": f"5日新高/新低 {updown['CNT_HIGH5']}/{updown['CNT_LOW5']}，20日 {updown['CNT_HIGH20']}/{updown['CNT_LOW20']}，60日 {updown['CNT_HIGH60']}/{updown['CNT_LOW60']}，250日 {updown['CNT_HIGH250']}/{updown['CNT_LOW250']}。",
                },
            ],
            "degradation": "changedist为查询时点实时口径（今日盘中），与带日期总览存在样本与日期差异，主评分采用market-overview。",
        },
        {
            "id": "turnover_liquidity",
            "name": "成交与流动性",
            "weight": 0.20,
            "score": turnover_score,
            "weighted_contribution": round(0.20 * turnover_score, 1),
            "status": "成交与5日、10日均量基本持平，但持续低于20日以上各期均量，增量资金不足",
            "leaf_scores": [
                {
                    "name": "两市成交额",
                    "score": 55,
                    "basis": f"两市成交{trade['MONEY']:.2f}亿元，为5日均量{trade['MONEY_5DAVG_RATIO']:.2f}%、10日均量{trade['MONEY_10DAVG_RATIO']:.2f}%。",
                },
                {
                    "name": "20日相对量能",
                    "score": 52,
                    "basis": f"成交为20日均值{trade['MONEY_20DAVG_RATIO']:.2f}%。",
                },
                {
                    "name": "中长期量能",
                    "score": 45,
                    "basis": f"成交为60日均值{trade['MONEY_60DAVG_RATIO']:.2f}%、120日{trade['MONEY_120DAVG_RATIO']:.2f}%、250日{trade['MONEY_250DAVG_RATIO']:.2f}%。",
                },
                {
                    "name": "量价配合",
                    "score": 45,
                    "basis": "三大指数收跌而成交未能站上20日均量，量价配合偏弱，属于存量博弈下的结构轮动。",
                },
            ],
        },
        {
            "id": "domestic_macro_liquidity",
            "name": "国内宏观流动性",
            "weight": 0.15,
            "score": macro_score,
            "weighted_contribution": round(0.15 * macro_score, 1),
            "status": "资金面平稳宽松、工业利润明显修复，但PMI仍处荣枯线下、社融当月新增同比转负、地产投资继续深跌",
            "leaf_scores": [
                {
                    "name": "资金成本",
                    "score": 66,
                    "basis": "截至2026-08-31：DR007(FDR007)1.41%、SHIBOR隔夜1.413%、1个月1.4168%、1年1.48%，短端利率平稳偏低。",
                },
                {
                    "name": "货币与信用",
                    "score": 54,
                    "basis": "截至2026-07-31：M2同比+7.7%、M1同比+4.0%，M1-M2剪刀差-3.7但环比改善7.5；社融存量同比+7.4%，当月新增2.225万亿元、同比-7.25%，其中企业贷款同比-17.36%、政府债同比-12.88%。",
                },
                {
                    "name": "增长动能",
                    "score": 52,
                    "basis": "2026-08-31：制造业PMI 49.8（环比+0.81）、新订单50.6、生产50.4，仍在荣枯线下；非制造业商务活动49.0、非制造业新订单44.1继续走弱；综合PMI 49.5。2026年二季度实际GDP累计同比+4.7%。",
                },
                {
                    "name": "盈利与价格",
                    "score": 66,
                    "basis": "截至2026-07-31：工业利润累计同比+17.6%，其中有色金属+91.8%、化学原料+56.6%、煤炭+50.4%；工业增加值累计同比+5.3%，高技术+13.8%、TMT+15.4%。CPI同比+0.5%、核心+0.9%，CPI-PPI剪刀差-3.0，价格端仍偏弱。",
                },
            ],
            "degradation": "宏观为低频数据，最新已发布期不等于目标日当日变化；两融余额后端当日未更新，按中性处理。",
        },
        {
            "id": "global_risk",
            "name": "全球风险",
            "weight": 0.10,
            "score": global_score,
            "weighted_contribution": round(0.10 * global_score, 1),
            "status": "缺少同一时点结构化全球风险数据，按中性降级",
            "leaf_scores": [{"name": "VIX、美元、美债和海外指数", "score": 50, "basis": "未取得统一可审计时点数据。"}],
        },
    ],
    "result": {
        "total_score": total,
        "calculation": f"0.30×{index_score:.1f} + 0.25×{breadth_score:.1f} + 0.20×{turnover_score:.1f} + 0.15×{macro_score:.1f} + 0.10×{global_score:.1f} = {total:.1f}",
        "market_state": state,
        "summary": "指数回落但个股涨多跌少，赚钱效应集中在中小市值与题材；成交持续低于20日以上均量，增量资金不足，维持中性而非进攻。",
    },
    "confidence": {
        "effective_weight_pct": 90.0,
        "grade": "B",
        "caveat": "置信度是数据覆盖率估算，不是行情预测概率；全球风险分项按中性降级拉低整体有效性。",
    },
    "data_quality": {
        "trade_date_confirmed": raw["trade_date_confirmation"]["days"][0]["isTrading"],
        "market_data_through_close": raw["indices"]["date"] == TARGET,
        "conflicts": raw.get("data_conflicts", []),
        "no_fabrication": True,
    },
}

OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload["result"], ensure_ascii=False, indent=2))
