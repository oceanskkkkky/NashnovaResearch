from __future__ import annotations

import importlib.util
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median, pstdev

ROOT = Path("E:/WS/NashnovaResearch")
EVIDENCE = ROOT / "evidence"
TARGET = "2026-08-26"
SECTOR_NAME = "工业金属"
SECTOR_CODE = "pt01801055"
START = "2026-04-01"
FUND_START = "2026-07-20"

spec = importlib.util.spec_from_file_location("daily_data", EVIDENCE / "build_2026_08_26_data.py")
daily = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(daily)


def finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def pct(values, index):
    valid = [(i, float(v)) for i, v in enumerate(values) if v is not None and math.isfinite(float(v))]
    if not valid or values[index] is None:
        return None
    if len(valid) == 1:
        return 50.0
    ordered = sorted(valid, key=lambda x: x[1])
    pos = 0
    while pos < len(ordered):
        end = pos + 1
        while end < len(ordered) and ordered[end][1] == ordered[pos][1]:
            end += 1
        if any(i == index for i, _ in ordered[pos:end]):
            return ((pos + end - 1) / 2) / (len(ordered) - 1) * 100
        pos = end
    return None


def ema(values, period):
    alpha = 2 / (period + 1)
    out = []
    current = None
    for value in values:
        if value is None:
            out.append(current)
            continue
        current = value if current is None else alpha * value + (1 - alpha) * current
        out.append(current)
    return out


def a_share_code(code):
    return f"{code[2:]}.{'SH' if code.startswith('sh') else 'SZ'}"


def main():
    raw = json.loads((EVIDENCE / "2026-08-26-sector-raw-v2.json").read_text(encoding="utf-8"))
    sector = next(x for x in raw["sectors"] if x["name"] == SECTOR_NAME)
    codes = [c for c in sector["constituents"]["codes"] if c.startswith(("sh", "sz"))]

    constituents_raw = daily.westock("sector", "constituent", SECTOR_CODE, "--raw")
    names = {}
    for row in daily.flatten_rows(constituents_raw):
        code = row.get("code")
        if code:
            names[code] = row.get("name") or row.get("Name") or code

    code_csv = ",".join(codes)
    kline_raw = daily.westock("kline", code_csv, "--period", "day", "--start", START, "--end", TARGET, "--raw")
    fund_raw = daily.westock("fund", "flow", code_csv, "--start", FUND_START, "--end", TARGET, "--raw")

    klines = defaultdict(list)
    for row in daily.flatten_rows(kline_raw):
        if row.get("symbol") in codes and row.get("date"):
            klines[row["symbol"]].append(row)
    funds = defaultdict(dict)
    for row in daily.flatten_rows(fund_raw):
        if row.get("code") in codes and row.get("date"):
            funds[row["code"]][row["date"]] = row

    sector_returns = sector["raw_aggregate_summary"]["returns_pct"]
    prelim = []
    excluded = []
    for code in codes:
        rows = sorted(klines.get(code, []), key=lambda x: x["date"])
        rows = [r for r in rows if r["date"] <= TARGET]
        name = names.get(code, code)
        if "ST" in str(name).upper() or str(name).upper().startswith("S"):
            excluded.append({"code": code, "name": name, "reason": "特殊处理股票"})
            continue
        if len(rows) < 60 or not rows or rows[-1]["date"] != TARGET:
            excluded.append({"code": code, "name": name, "reason": "目标日或历史K线不足"})
            continue
        closes = [finite(r.get("last")) for r in rows]
        amounts = [finite(r.get("amount")) for r in rows]
        if any(v is None for v in closes[-61:]):
            excluded.append({"code": code, "name": name, "reason": "收盘价缺失"})
            continue
        median_amount = median([x for x in amounts[-20:] if x is not None]) if any(x is not None for x in amounts[-20:]) else None
        if median_amount is None or median_amount < 100_000_000:
            excluded.append({"code": code, "name": name, "reason": "20日成交额中位数低于1亿元"})
            continue

        def ret(h):
            return (closes[-1] / closes[-1-h] - 1) * 100

        returns = {"1": ret(1), "5": ret(5), "20": ret(20)}
        dates = [r["date"] for r in rows]
        selected_dates = {h: dates[-h:] for h in (1, 5, 20)}
        flow_sum = {}
        flow_strength = {}
        for h in (1, 5, 20):
            vals = [finite(funds[code].get(d, {}).get("MainNetFlow")) for d in selected_dates[h]]
            vals = [v for v in vals if v is not None]
            den = sum(finite(r.get("amount")) or 0 for r in rows[-h:])
            flow_sum[str(h)] = sum(vals) if vals else None
            flow_strength[str(h)] = (sum(vals) / den) if vals and den else None

        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes[-60:]) / 60
        rsi_series = daily.wilder_rsi(closes, 14)
        e12, e26 = ema(closes, 12), ema(closes, 26)
        dif = [a - b if a is not None and b is not None else None for a, b in zip(e12, e26)]
        dea = ema(dif, 9)
        mid = ma20
        std = pstdev(closes[-20:])
        primary = "sz399006" if code.startswith("sz30") else ("sz399001" if code.startswith("sz") else "sh000001")
        market_interval = next(x["row"] for x in json.loads((EVIDENCE / "2026-08-26-market-raw.json").read_text(encoding="utf-8"))["source_raw"]["market_overview"] if x["info"]["type"] == "interval")
        index_key = "CYBZ" if primary == "sz399006" else ("SZCZ" if primary == "sz399001" else "SZZS")
        index_returns = {"1": 0.51 if index_key == "CYBZ" else (0.69 if index_key == "SZCZ" else 0.59), "5": market_interval[f"CHG_5D_{index_key}"], "20": market_interval[f"CHG_20D_{index_key}"]}
        rel_sector = {h: returns[h] - sector_returns[f"{h}d"] for h in ("1", "5", "20")}
        rel_index = {h: returns[h] - index_returns[h] for h in ("1", "5", "20")}
        prelim.append({
            "code": code,
            "a_share_code": a_share_code(code),
            "name": name,
            "close": closes[-1],
            "change_pct": returns["1"],
            "returns_pct": returns,
            "median_amount_20d_cny": median_amount,
            "turnover_rate_pct": finite(rows[-1].get("exchange")),
            "technical": {
                "ma20": ma20,
                "ma60": ma60,
                "close_vs_ma20_pct": (closes[-1] / ma20 - 1) * 100,
                "close_vs_ma60_pct": (closes[-1] / ma60 - 1) * 100,
                "rsi14": rsi_series[-1],
                "macd_dif": dif[-1],
                "macd_dea": dea[-1],
                "macd_hist": 2 * (dif[-1] - dea[-1]),
                "boll_mid": mid,
                "boll_upper": mid + 2 * std,
                "boll_lower": mid - 2 * std,
            },
            "flow": {"main_net_cny": flow_sum, "strength_vs_amount": flow_strength, "coverage_days": len(funds[code])},
            "relative_strength_pct": {"vs_sector": rel_sector, "vs_primary_index": rel_index, "primary_index": primary},
        })

    fields = {
        "liq": [r["median_amount_20d_cny"] for r in prelim],
        "r20": [r["returns_pct"]["20"] for r in prelim],
        "r5": [r["returns_pct"]["5"] for r in prelim],
        "f20": [r["flow"]["strength_vs_amount"]["20"] for r in prelim],
        "f5": [r["flow"]["strength_vs_amount"]["5"] for r in prelim],
        "rel20": [r["relative_strength_pct"]["vs_sector"]["20"] for r in prelim],
    }
    for i, row in enumerate(prelim):
        comp = {key: pct(values, i) for key, values in fields.items()}
        row["screening_components_pct"] = comp
        row["screening_score"] = 0.20 * comp["liq"] + 0.25 * comp["r20"] + 0.15 * comp["r5"] + 0.20 * comp["f20"] + 0.10 * comp["f5"] + 0.10 * comp["rel20"]
    prelim.sort(key=lambda x: x["screening_score"], reverse=True)
    for i, row in enumerate(prelim, 1):
        row["screening_rank"] = i

    scored = json.loads((EVIDENCE / "2026-08-26-sector-score-v2.json").read_text(encoding="utf-8"))
    sector_score = next(x for x in scored["sectors"] if x["name"] == SECTOR_NAME)
    result = {
        "schema_version": "1.0",
        "as_of_date": TARGET,
        "scope": {
            "sector": f"申万二级{SECTOR_NAME}",
            "sector_code": SECTOR_CODE,
            "original_constituent_count": sector["constituents"]["count"],
            "sh_sz_count": len(codes),
            "beijing_excluded_count": len(sector["constituents"]["unsupported_fund_codes"]),
            "eligible_after_hard_filters": len(prelim),
            "candidate_pool_count": min(40, len(prelim)),
            "deep_verification_count_planned": 5,
        },
        "methodology": {
            "hard_filters": ["仅沪深A股", "排除ST/*ST/S类特殊处理", "目标日有收盘且历史交易日不少于60日", "20日成交额中位数不低于1亿元"],
            "screening_score": "20%流动性+25%近20日收益+15%近5日收益+20%近20日资金强度+10%近5日资金强度+10%相对行业20日强度，均为硬过滤后横截面分位",
            "technical_calculation": "WeStock前复权日线；MA为SMA；RSI14为Wilder；MACD为12/26/9 EMA；BOLL为20日均值±2倍总体标准差",
            "fund_flow_calculation": "MainNetFlow交易日累加；主力资金不等于机构资金",
        },
        "sector_context": {
            "sector_heat": sector_score["sector_heat"],
            "crowding": sector_score["crowding"],
            "returns_pct": {"1": sector_returns["1d"], "5": sector_returns["5d"], "20": sector_returns["20d"]},
        },
        "candidate_pool": prelim[:40],
        "excluded_summary": {"count": len(excluded), "sample": excluded[:20]},
        "commands": daily.COMMANDS,
        "failures": daily.FAILURES,
    }
    out = EVIDENCE / "2026-08-26-stock-candidates.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "eligible": len(prelim), "top5": [{"rank": r["screening_rank"], "code": r["a_share_code"], "name": r["name"], "score": round(r["screening_score"], 1)} for r in prelim[:5]], "failures": daily.FAILURES}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
