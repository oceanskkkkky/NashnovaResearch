from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("E:/WS/NashnovaResearch")
EVIDENCE = ROOT / "evidence"
TARGET = "2026-08-25"
KLINE_START = "2025-06-01"
FUND_START = "2026-07-27"
TZ = timezone(timedelta(hours=8))
NPX = "C:/Users/tizytian/.workbuddy/binaries/node/versions/22.22.2-1/npx.cmd"
HITHINK = "C:/Users/tizytian/.workbuddy/binaries/node/versions/22.22.2-1/hithink-finance"
PACKAGE = "westock-data-skillhub@1.0.5"
SECTORS = [
    ("贵金属", "pt01801053"), ("焦炭Ⅱ", "pt01801952"),
    ("煤炭开采", "pt01801951"), ("种植业", "pt01801016"),
    ("保险Ⅱ", "pt01801194"), ("农商行Ⅱ", "pt01801785"),
    ("白酒Ⅱ", "pt01801125"), ("工业金属", "pt01801055"),
    ("化学原料", "pt01801033"), ("半导体", "pt01801081"),
    ("通信设备", "pt01801102"), ("生物制品", "pt01801152"),
    ("普钢", "pt01801044"), ("水泥", "pt01801711"),
    ("工程机械", "pt01801077"), ("房地产开发", "pt01801181"),
    ("炼化及贸易", "pt01801963"), ("汽车零部件", "pt01801093"),
    ("白色家电", "pt01801111"), ("食品加工", "pt01801124"),
    ("饮料乳品", "pt01801127"), ("软件开发", "pt01801104"),
    ("计算机设备", "pt01801101"), ("光伏设备", "pt01801735"),
    ("消费电子", "pt01801085"), ("电力", "pt01801161"),
    ("燃气Ⅱ", "pt01801163"), ("证券Ⅱ", "pt01801193"),
    ("化学制药", "pt01801151"),
]
commands: list[dict] = []
failures: list[dict] = []


def command_text(args: list[str]) -> str:
    return " ".join(f'"{arg}"' if " " in arg else arg for arg in args)


def run_json(args: list[str], label: str, required: bool = True):
    started = datetime.now(TZ).isoformat(timespec="seconds")
    t0 = time.monotonic()
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.monotonic() - t0, 3)
    record = {
        "label": label,
        "command": command_text(args),
        "started_at": started,
        "elapsed_seconds": elapsed,
        "exit_code": proc.returncode,
        "stdout_sha256": hashlib.sha256(proc.stdout.encode("utf-8")).hexdigest(),
    }
    commands.append(record)
    if proc.returncode != 0:
        error = {**record, "stderr": proc.stderr[-2000:]}
        failures.append(error)
        if required:
            raise RuntimeError(f"{label}失败: {proc.stderr[-500:]}")
        return None
    text = proc.stdout.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        error = {**record, "error": f"JSON解析失败: {exc}", "stdout_tail": text[-1000:]}
        failures.append(error)
        if required:
            raise RuntimeError(f"{label} JSON解析失败: {exc}")
        return None


def westock(*args: str, label: str, required: bool = True):
    return run_json([NPX, "-y", PACKAGE, *args], label, required)


def hithink(*args: str, label: str, required: bool = True):
    payload = run_json([HITHINK, *args, "--format", "json"], label, required)
    if payload is not None and payload.get("ok") is not True:
        error = {"label": label, "command": command_text([HITHINK, *args, "--format", "json"]), "error": "ok不为true"}
        failures.append(error)
        if required:
            raise RuntimeError(f"{label}返回ok!=true")
    return payload


def finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def rounded(value, digits=6):
    return None if value is None else round(float(value), digits)


def percentile(values: list[float], target: float):
    valid = sorted(float(v) for v in values if v is not None and math.isfinite(float(v)))
    if not valid:
        return None
    if len(valid) == 1:
        return 50.0
    less = sum(v < target for v in valid)
    equal = sum(v == target for v in valid)
    average_rank = less + (equal - 1) / 2
    return average_rank / (len(valid) - 1) * 100


def cross_percentiles(values: list[float | None]):
    valid = [(i, float(v)) for i, v in enumerate(values) if v is not None]
    out = [None] * len(values)
    if len(valid) == 1:
        out[valid[0][0]] = 50.0
        return out
    ordered = sorted(valid, key=lambda x: x[1])
    p = 0
    while p < len(ordered):
        e = p + 1
        while e < len(ordered) and ordered[e][1] == ordered[p][1]:
            e += 1
        score = ((p + e - 1) / 2) / (len(ordered) - 1) * 100
        for idx, _ in ordered[p:e]:
            out[idx] = score
        p = e
    return out


def rolling_mean(values: list[float | None], window=5):
    out = []
    for i in range(len(values)):
        chunk = values[max(0, i - window + 1):i + 1]
        out.append(sum(chunk) / window if len(chunk) == window and all(v is not None for v in chunk) else None)
    return out


def rolling_sum(values: list[float | None], window=5):
    out = []
    for i in range(len(values)):
        chunk = values[max(0, i - window + 1):i + 1]
        out.append(sum(chunk) if len(chunk) == window and all(v is not None for v in chunk) else None)
    return out


def wilder_rsi(closes: list[float], period=14):
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    avg_gain = sum(max(x, 0) for x in changes[:period]) / period
    avg_loss = sum(max(-x, 0) for x in changes[:period]) / period

    def score(gain, loss):
        if loss == 0:
            return 100.0 if gain > 0 else 50.0
        return 100 - 100 / (1 + gain / loss)

    out[period] = score(avg_gain, avg_loss)
    for i in range(period + 1, len(closes)):
        change = changes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0)) / period
        out[i] = score(avg_gain, avg_loss)
    return out


def trailing_percentile(dates: list[str], values: list[float | None], idx: int):
    target = values[idx]
    if target is None:
        return None
    cutoff = datetime.fromisoformat(dates[idx]).date() - timedelta(days=365)
    sample = [v for d, v in zip(dates[:idx + 1], values[:idx + 1]) if datetime.fromisoformat(d).date() >= cutoff and v is not None]
    return percentile(sample, target)


def crowding_score(rsi_pct, turnover_pct, share_pct):
    if any(x is None for x in (rsi_pct, turnover_pct, share_pct)):
        return None
    mean = 0.35 * rsi_pct + 0.35 * turnover_pct + 0.30 * share_pct
    return 0.75 * mean + 0.25 * max(rsi_pct, turnover_pct, share_pct)


def main():
    generated_at = datetime.now(TZ).isoformat(timespec="seconds")
    print("拉取交易日、市场、宏观与特色数据", flush=True)
    calendar = westock("trade-calendar", "--date", TARGET, "--raw", label="交易日确认")
    overview = westock("market-overview", "--type", "all", "--date", TARGET, "--raw", label="市场总览")
    changedist = westock("changedist", "--raw", label="涨跌分布")
    macro = westock("macro", "indicator", "cn_core", "--date", TARGET, "--raw", label="中国核心宏观")
    lhb = westock("lhb", "--date", TARGET, "--raw", label="当日龙虎榜")
    hithink_lhb = hithink("special", "dragon-tiger", label="同花顺龙虎榜", required=False)
    date_ms = str(int(datetime(2026, 8, 25, tzinfo=TZ).timestamp() * 1000))
    limit_pool = hithink("special", "limit-up-pool", "--date-ms", date_ms, "--page", "1", "--size", "200", label="同花顺涨停池")

    print("重拉29个行业成份股与板块日线", flush=True)
    constituent_map: dict[str, list[dict]] = {}
    sector_klines: dict[str, list[dict]] = {}
    for i, (name, code) in enumerate(SECTORS, 1):
        constituent_map[code] = westock("sector", "constituent", code, "--raw", label=f"{name}成份股")
        rows = westock("kline", code, "--period", "day", "--start", KLINE_START, "--end", TARGET, "--raw", label=f"{name}板块日线")
        sector_klines[code] = sorted(rows, key=lambda row: row["date"])
        print(f"行业 {i}/29: {name}", flush=True)

    market_rows = westock("kline", "sh000001,sz399001", "--period", "day", "--start", KLINE_START, "--end", TARGET, "--raw", label="沪深市场成交额日线")
    market_by_symbol: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in market_rows:
        market_by_symbol[row["symbol"]][row["date"]] = row
    market_dates = sorted(set(market_by_symbol["sh000001"]) & set(market_by_symbol["sz399001"]))
    market_amount = {d: finite(market_by_symbol["sh000001"][d].get("amount")) + finite(market_by_symbol["sz399001"][d].get("amount")) for d in market_dates}

    unique_codes = sorted({row["code"] for rows in constituent_map.values() for row in rows})
    supported = [code for code in unique_codes if code.startswith(("sh", "sz"))]
    unsupported = [code for code in unique_codes if not code.startswith(("sh", "sz"))]
    print(f"拉取资金流：去重{len(unique_codes)}只，沪深{len(supported)}只，其他{len(unsupported)}只", flush=True)
    fund_rows: list[dict] = []
    batch_size = 80
    failed_batches = {}
    for start in range(0, len(supported), batch_size):
        batch = supported[start:start + batch_size]
        batch_no = start // batch_size + 1
        try:
            rows = westock("fund", "flow", ",".join(batch), "--start", FUND_START, "--end", TARGET, "--raw", label=f"资金流批次{batch_no}")
            fund_rows.extend(rows)
        except Exception as exc:
            failed_batches[str(batch_no)] = str(exc)
        print(f"资金批次 {batch_no}/{math.ceil(len(supported) / batch_size)}", flush=True)

    fund_by_code_date: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in fund_rows:
        code = row.get("symbol") or row.get("code") or row.get("SecuCode")
        date = row.get("date") or row.get("EndDate")
        if code and date:
            fund_by_code_date[code][date] = row

    sector_outputs = []
    avg_amounts = []
    for name, code in SECTORS:
        constituents = [row["code"] for row in constituent_map[code]]
        rows = sector_klines[code]
        dates = [row["date"] for row in rows]
        closes = [finite(row.get("last")) for row in rows]
        amounts = [finite(row.get("amount")) for row in rows]
        exchanges = [finite(row.get("exchange")) for row in rows]
        anomalies = []
        if not dates or dates[-1] != TARGET:
            anomalies.append(f"板块日线末日不是{TARGET}")
        returns = {}
        for horizon in (1, 5, 20):
            returns[str(horizon)] = (closes[-1] / closes[-1 - horizon] - 1) * 100 if len(closes) > horizon and closes[-1] is not None and closes[-1 - horizon] not in (None, 0) else None

        rsi = wilder_rsi(closes)
        turnover5 = rolling_mean(exchanges, 5)
        sector_amount5 = rolling_sum(amounts, 5)
        market_amount_values = [market_amount.get(d) for d in dates]
        market_amount5 = rolling_sum(market_amount_values, 5)
        share5 = [s / m if s is not None and m not in (None, 0) else None for s, m in zip(sector_amount5, market_amount5)]
        current_idx = len(dates) - 1
        previous_idx = current_idx - 5
        rsi_pct = trailing_percentile(dates, rsi, current_idx)
        turnover_pct = trailing_percentile(dates, turnover5, current_idx)
        share_pct = trailing_percentile(dates, share5, current_idx)
        previous = None
        if previous_idx >= 0:
            prev_rsi_pct = trailing_percentile(dates, rsi, previous_idx)
            prev_turnover_pct = trailing_percentile(dates, turnover5, previous_idx)
            prev_share_pct = trailing_percentile(dates, share5, previous_idx)
            previous = {
                "date": dates[previous_idx],
                "rsi_pct": rounded(prev_rsi_pct),
                "turnover_pct": rounded(prev_turnover_pct),
                "share_pct": rounded(prev_share_pct),
                "crowding": rounded(crowding_score(prev_rsi_pct, prev_turnover_pct, prev_share_pct)),
            }

        latest_dates = dates[-20:]
        daily_fund = []
        for d in latest_dates:
            records = [fund_by_code_date[c].get(d) for c in constituents]
            valid_records = [r for r in records if r is not None and "MainNetFlow" in r and finite(r.get("MainNetFlow")) is not None]
            net_sum = sum(finite(r["MainNetFlow"]) for r in valid_records)
            sector_amount = amounts[dates.index(d)]
            daily_fund.append({
                "date": d,
                "main_net_flow_sum": rounded(net_sum, 2),
                "sector_amount": rounded(sector_amount, 2),
                "flow_strength": rounded(net_sum / sector_amount, 10) if sector_amount else None,
                "covered_constituents": len(valid_records),
                "expected_constituents": len(constituents),
                "coverage": rounded(len(valid_records) / len(constituents), 6) if constituents else 0,
                "zero_flow_records": sum(finite(r.get("MainNetFlow")) == 0 for r in valid_records),
            })

        flow_strength = {}
        fund_coverage = {}
        for horizon in (1, 5, 20):
            period = daily_fund[-horizon:]
            observed = sum(r["covered_constituents"] for r in period)
            expected = len(constituents) * len(period)
            net_sum = sum(r["main_net_flow_sum"] for r in period)
            amount_sum = sum(r["sector_amount"] for r in period if r["sector_amount"] is not None)
            flow_strength[str(horizon)] = net_sum / amount_sum if amount_sum else None
            fund_coverage[str(horizon)] = {
                "observed_stock_days": observed,
                "expected_stock_days": expected,
                "coverage": rounded(observed / expected, 6) if expected else 0,
                "net_flow_sum": rounded(net_sum, 2),
                "sector_amount_sum": rounded(amount_sum, 2),
            }

        if len(dates) >= 2:
            d0, d1 = dates[-1], dates[-2]
            paired = []
            for c in constituents:
                current = fund_by_code_date[c].get(d0, {})
                prior = fund_by_code_date[c].get(d1, {})
                c0, c1 = finite(current.get("ClosePrice")), finite(prior.get("ClosePrice"))
                if c0 is not None and c1 is not None:
                    paired.append((c0, c1))
            breadth_up = sum(a > b for a, b in paired)
            breadth = breadth_up / len(paired) * 100 if paired else None
        else:
            paired, breadth_up, breadth = [], 0, None

        all_zero = []
        for c in constituents:
            vals = [finite(r.get("MainNetFlow")) for r in fund_by_code_date[c].values() if "MainNetFlow" in r]
            vals = [v for v in vals if v is not None]
            if vals and all(v == 0 for v in vals):
                all_zero.append(c)
        unsupported_sector = [c for c in constituents if c in unsupported]
        matching_dates = len(set(dates) & set(market_dates))
        kline_cov = {
            "rows": len(rows),
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None,
            "expected_market_dates": len(market_dates),
            "matching_market_dates": matching_dates,
            "coverage": rounded(matching_dates / len(market_dates), 6) if market_dates else 0,
        }
        if fund_coverage["20"]["coverage"] < 0.8:
            anomalies.append("20日资金覆盖率低于80%")
        avg_amount5 = sum(amounts[-5:]) / 5 if len(amounts) >= 5 and all(v is not None for v in amounts[-5:]) else None
        avg_amounts.append(avg_amount5)
        sector_outputs.append({
            "name": name,
            "code": code,
            "constituents": {"count": len(constituents), "codes": constituents, "unsupported_fund_codes": unsupported_sector},
            "kline_coverage": kline_cov,
            "fund_coverage": fund_coverage,
            "all_zero_flow_codes": all_zero,
            "raw_aggregate_summary": {
                "returns_pct": {k: rounded(v) for k, v in returns.items()},
                "flow_strength": {k: rounded(v, 10) for k, v in flow_strength.items()},
                "latest_rsi14": rounded(rsi[-1]),
                "rsi_pct": rounded(rsi_pct),
                "latest_turnover_rolling5": rounded(turnover5[-1]),
                "turnover_pct": rounded(turnover_pct),
                "latest_share_rolling5": rounded(share5[-1], 10),
                "share_pct": rounded(share_pct),
                "five_trading_days_ago": previous,
                "breadth": rounded(breadth),
                "breadth_observed": len(paired),
                "breadth_up": breadth_up,
                "avg_amount_5d": rounded(avg_amount5, 2),
                "daily_fund_aggregation": daily_fund,
            },
            "anomalies": anomalies,
        })

    attention = cross_percentiles(avg_amounts)
    input_rows = []
    for sector, attention_score in zip(sector_outputs, attention):
        s = sector["raw_aggregate_summary"]
        input_rows.append({
            "name": sector["name"], "code": sector["code"],
            "return_1d": s["returns_pct"]["1"], "return_5d": s["returns_pct"]["5"], "return_20d": s["returns_pct"]["20"],
            "flow_1d": s["flow_strength"]["1"], "flow_5d": s["flow_strength"]["5"], "flow_20d": s["flow_strength"]["20"],
            "breadth": s["breadth"], "attention": rounded(attention_score),
            "catalyst": None, "fundamental": None,
            "rsi_pct": s["rsi_pct"], "turnover_pct": s["turnover_pct"], "share_pct": s["share_pct"],
            "crowding_5d_ago": s["five_trading_days_ago"]["crowding"] if s["five_trading_days_ago"] else None,
            "data_quality": {
                "constituent_count": sector["constituents"]["count"],
                "kline": sector["kline_coverage"],
                "fund_flow": sector["fund_coverage"],
                "breadth": {"observed": s["breadth_observed"], "expected": sector["constituents"]["count"], "coverage": rounded(s["breadth_observed"] / sector["constituents"]["count"], 6) if sector["constituents"]["count"] else 0},
                "anomalies": sector["anomalies"],
            },
            "source_notes": [
                "行业代码固定为前一日报同一29个申万二级行业，仅复用行业标识、不复用任何数值",
                "成份股由 sector constituent --raw 于本次任务重新获取",
                f"板块日线由 kline --period day --start {KLINE_START} --end {TARGET} --raw 重新获取",
                f"资金由成份股批量 fund flow --start {FUND_START} --end {TARGET} --raw 重新获取并按行业/交易日汇总 MainNetFlow",
                "资金强度=行业成份股主力净流入合计/板块同期成交额合计",
                "breadth=可获得相邻两交易日收盘价的成份股中当日上涨占比",
                "catalyst/fundamental 无同口径结构化证据，设为 null",
            ],
        })

    raw_payload = {
        "as_of_date": TARGET,
        "generated_at": generated_at,
        "source": {"skill": "westockdata", "cli": NPX, "package": PACKAGE, "fund_period": [FUND_START, TARGET], "kline_period": [KLINE_START, TARGET]},
        "universe": {"requested_names": [name for name, _ in SECTORS], "resolved_count": len(SECTORS), "included_count": len(SECTORS), "search_errors": {}, "constituent_errors": {}, "sector_kline_errors": {}, "market_kline_errors": {}},
        "market_amount_coverage": {"rows": len(market_dates), "first_date": market_dates[0], "last_date": market_dates[-1], "definition": "sh000001.amount + sz399001.amount"},
        "fund_flow_batch_manifest": {"unique_constituents": len(unique_codes), "supported_sh_sz_codes": len(supported), "unsupported_codes": unsupported, "batch_size": batch_size, "batch_count": math.ceil(len(supported) / batch_size), "successful_batches": math.ceil(len(supported) / batch_size) - len(failed_batches), "failed_batches": failed_batches, "raw_rows": len(fund_rows)},
        "calculation_notes": {"return": "close_t / close_t-n - 1, expressed as percent", "rsi": "Wilder RSI(14), calculated on all returned sector closes", "historical_percentile": "average-rank percentile within trailing 365 calendar days ending at observation date", "turnover": "rolling mean of five sector kline exchange values", "share": "rolling-five sector amount sum divided by rolling-five (sh000001.amount + sz399001.amount) sum", "crowding": "C=75%*M+25%*max; M=35%*rsi_pct+35%*turnover_pct+30%*share_pct", "attention": "cross-sectional average-rank percentile of current sector five-day average amount", "missing_policy": "retain returned zeros; do not impute missing market data; catalyst/fundamental remain null"},
        "sectors": sector_outputs,
    }
    input_payload = {"as_of_date": TARGET, "generated_at": generated_at, "method": "sector_input_v2_data_engineering", "sectors": input_rows}

    overview_by_code = {item["info"]["code"]: item for item in overview}
    trade = overview_by_code["market_statis_daily_trade"]
    width = overview_by_code["market_statis_updown"]
    rotation = overview_by_code["market_statis_rotation"]
    valuation = overview_by_code["market_statis_valuation"]
    summary = overview_by_code["market_statis_summary"]
    macro_periods = []
    for section in macro.get("sections", []):
        for row in section:
            date_fields = {k: v for k, v in row.items() if k.endswith("_END_DATE") or k.endswith("_INFO_DATE")}
            if date_fields:
                prefix = next(iter(date_fields)).split("_")[0]
                macro_periods.append({"indicator_group": prefix, **date_fields})
    pool_data = limit_pool["data"]
    pool_items = pool_data.get("item", [])
    theme_counts: dict[str, int] = defaultdict(int)
    for item in pool_items:
        reason = item.get("limit_up_reason") or ""
        for token in reason.split("+"):
            if token:
                theme_counts[token] += 1
    top_themes = [{"theme": k, "count": v} for k, v in sorted(theme_counts.items(), key=lambda x: (-x[1], x[0]))[:12]]
    lhb_sections = lhb.get("sections", [])
    market_payload = {
        "as_of_date": TARGET,
        "generated_at": generated_at,
        "query_timezone": "Asia/Shanghai (UTC+08:00)",
        "market_state": "盘后完整收盘",
        "trading_day_confirmation": {"source": "WeStock trade-calendar", "result": calendar},
        "major_indices_and_turnover": {"source": "WeStock market-overview", "date": trade["date"], "data": trade["row"]},
        "market_breadth": {
            "primary": {"source": "WeStock market-overview/market_statis_updown", "date": width["date"], "data": width["row"]},
            "secondary": {"source": "WeStock changedist（实时快照）", "query_at": generated_at, "data": changedist},
        },
        "limit_up_down": {
            "market_overview": {"up_limit": width["row"]["CNT_REACH_UPLIMIT"], "down_limit": width["row"]["CNT_REACH_DNLIMIT"]},
            "changedist": {"up_limit": changedist.get("upLimitCount"), "down_limit": changedist.get("downLimitCount")},
            "hithink_limit_up_pool": {"date_ms": date_ms, "count": pool_data.get("pagination", {}).get("total"), "returned": len(pool_items), "items": pool_items},
        },
        "style": {"source": "WeStock market-overview/market_statis_rotation", "date": rotation["date"], "data": rotation["row"], "summary": {"date": summary["date"], "data": summary["row"]}},
        "valuation_latest_effective_period": {"source": "WeStock market-overview/market_statis_valuation", "date": valuation["date"], "data": valuation["row"]},
        "macro_latest_effective_periods": {"source": "WeStock macro indicator cn_core", "query_date": TARGET, "periods": macro_periods},
        "dragon_tiger_and_hotspots": {
            "westock": {"query_date": TARGET, "section_counts": [len(section) for section in lhb_sections], "institution_top10": lhb_sections[0][:10] if lhb_sections else [], "high_win_buy_top10": lhb_sections[2][:10] if len(lhb_sections) > 2 else []},
            "hithink": {"returned_trade_date": hithink_lhb.get("data", {}).get("trade_date") if hithink_lhb else None, "count": hithink_lhb.get("data", {}).get("count") if hithink_lhb else None, "status": "数据滞后，不作为2026-08-25龙虎榜主证据" if hithink_lhb and hithink_lhb.get("data", {}).get("trade_date") != TARGET else "日期匹配"},
            "limit_up_hotspot_summary": top_themes,
        },
        "data_conflicts": [
            {"field": "上涨/下跌/平盘家数", "market_overview": {"up": width["row"]["CNT_RED"], "down": width["row"]["CNT_GREEN"], "flat": width["row"]["CNT_ZERO"], "total": width["row"]["CNT_TOTAL"]}, "changedist": {"up": changedist.get("upCount"), "down": changedist.get("downCount"), "flat": changedist.get("flatCount"), "suspended": changedist.get("suspensionCount")}, "handling": "分别保留；market-overview作为指定交易日主口径，changedist为查询时实时快照"},
            {"field": "涨跌停家数", "market_overview": {"up_limit": width["row"]["CNT_REACH_UPLIMIT"], "down_limit": width["row"]["CNT_REACH_DNLIMIT"]}, "changedist": {"up_limit": changedist.get("upLimitCount"), "down_limit": changedist.get("downLimitCount")}, "hithink_pool": {"up_limit_pool": pool_data.get("pagination", {}).get("total")}, "handling": "不静默合并；保留供应商口径差异"},
            {"field": "龙虎榜日期", "westock_query_date": TARGET, "hithink_returned_date": hithink_lhb.get("data", {}).get("trade_date") if hithink_lhb else None, "handling": "采用WeStock当日榜，hithink标记滞后"},
        ],
        "failures": failures,
        "execution": {"command_count": len(commands), "commands": commands},
        "sector_data_linkage": {"sector_count": len(SECTORS), "unique_constituents": len(unique_codes), "supported_sh_sz_codes": len(supported), "unsupported_codes": unsupported, "fund_rows": len(fund_rows)},
    }

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / f"{TARGET}-sector-raw-v2.json").write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EVIDENCE / f"{TARGET}-sector-input-v2.json").write_text(json.dumps(input_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EVIDENCE / f"{TARGET}-market-raw.json").write_text(json.dumps(market_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sector_count": len(SECTORS), "unique_constituents": len(unique_codes), "supported": len(supported), "unsupported": len(unsupported), "fund_rows": len(fund_rows), "failures": len(failures)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise
