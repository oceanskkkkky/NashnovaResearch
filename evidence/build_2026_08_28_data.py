from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import fmean

ROOT = Path("E:/WS/NashnovaResearch")
EVIDENCE = ROOT / "evidence"
TARGET = "2026-08-28"
KLINE_START = "2025-06-01"
FUND_START = "2026-07-20"
NPX = "C:/Users/tizytian/.workbuddy/binaries/node/versions/22.22.2-1/npx.cmd"
PACKAGE = "westock-data-skillhub@1.0.5"
HITHINK = "C:/Users/tizytian/.workbuddy/binaries/node/versions/22.22.2-1/hithink-finance"
TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")

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
REQUESTED_NAMES = [name for name, _ in SECTORS]
COMMANDS: list[dict] = []
FAILURES: list[dict] = []
LOCK = threading.Lock()
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def decode_stdout(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def decode_stderr(data: bytes) -> str:
    for enc in ("utf-8", "gb18030"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def parse_json_output(text: str):
    clean = ANSI.sub("", text).replace("\x07", "")
    decoder = json.JSONDecoder()
    starts = [m.start() for m in re.finditer(r"(?m)^[ \t]*[\[{]", clean)]
    candidates = []
    for start in starts:
        try:
            obj, consumed = decoder.raw_decode(clean[start:].lstrip())
            candidates.append((consumed, obj))
        except json.JSONDecodeError:
            continue
    if candidates:
        return max(candidates, key=lambda item: item[0])[1]
    raise ValueError("CLI 输出中未找到可解析 JSON")


def record_command(command: str, started: str, ended: str, attempts: int, rc: int, ok: bool, rows=None, error=None):
    item = {
        "command": command,
        "started_at": started,
        "ended_at": ended,
        "attempts": attempts,
        "exit_code": rc,
        "ok": ok,
    }
    if rows is not None:
        item["row_count"] = rows
    if error:
        item["error"] = error
    with LOCK:
        COMMANDS.append(item)
        if not ok:
            FAILURES.append(item.copy())


def execute(argv: list[str], retries: int = 2, json_output: bool = True):
    started = now_iso()
    command = subprocess.list2cmdline(argv)
    last_error = None
    last_rc = -1
    for attempt in range(1, retries + 2):
        try:
            p = subprocess.run(argv, capture_output=True, timeout=180)
            last_rc = p.returncode
            stdout = decode_stdout(p.stdout)
            stderr = decode_stderr(p.stderr)
            if p.returncode == 0:
                if json_output:
                    obj = parse_json_output(stdout)
                    record_command(command, started, now_iso(), attempt, p.returncode, True, row_count(obj))
                    return obj
                record_command(command, started, now_iso(), attempt, p.returncode, True)
                return stdout
            last_error = (stderr or stdout)[-1200:]
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt <= retries:
            time.sleep(2 * attempt)
    record_command(command, started, now_iso(), retries + 1, last_rc, False, error=last_error)
    raise RuntimeError(last_error or f"命令失败，退出码 {last_rc}")


def westock(*args: str, retries: int = 2):
    cmdline = subprocess.list2cmdline([NPX, "-y", PACKAGE, *args])
    return execute(["cmd.exe", "/d", "/c", cmdline], retries=retries)


def hithink(*args: str, retries: int = 2):
    cmdline = subprocess.list2cmdline([HITHINK, *args])
    return execute(["cmd.exe", "/d", "/c", cmdline], retries=retries)


def row_count(obj) -> int:
    if isinstance(obj, list):
        return sum(row_count(x) if isinstance(x, list) else 1 for x in obj)
    if isinstance(obj, dict):
        if isinstance(obj.get("sections"), list):
            return sum(row_count(x) for x in obj["sections"])
        if isinstance(obj.get("data"), list):
            return len(obj["data"])
        data = obj.get("data")
        if isinstance(data, dict) and isinstance(data.get("item"), list):
            return len(data["item"])
    return 1


def flatten_rows(obj) -> list[dict]:
    rows: list[dict] = []
    if isinstance(obj, list):
        for item in obj:
            rows.extend(flatten_rows(item))
    elif isinstance(obj, dict):
        if "sections" in obj:
            rows.extend(flatten_rows(obj["sections"]))
        elif isinstance(obj.get("data"), list):
            rows.extend(flatten_rows(obj["data"]))
        elif isinstance(obj.get("data"), dict) and isinstance(obj["data"].get("item"), list):
            rows.extend(flatten_rows(obj["data"]["item"]))
        elif isinstance(obj.get("row"), dict):
            rows.append(obj)
        else:
            rows.append(obj)
    return rows


def finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def rounded(value, digits=6):
    return None if value is None else round(float(value), digits)


def percentile(values: list[float | None], index: int) -> float | None:
    target = values[index]
    valid = [(i, float(v)) for i, v in enumerate(values) if v is not None and math.isfinite(float(v))]
    if target is None or not valid:
        return None
    if len(valid) == 1:
        return 50.0
    ordered = sorted(valid, key=lambda pair: pair[1])
    pos = 0
    while pos < len(ordered):
        end = pos + 1
        while end < len(ordered) and ordered[end][1] == ordered[pos][1]:
            end += 1
        if any(i == index for i, _ in ordered[pos:end]):
            return ((pos + end - 1) / 2) / (len(ordered) - 1) * 100
        pos = end
    return None


def rolling_mean(values: list[float | None], window: int) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        part = values[max(0, i - window + 1):i + 1]
        out.append(fmean(part) if len(part) == window and all(v is not None for v in part) else None)
    return out


def rolling_share(sector_amounts: list[float | None], market_amounts: list[float | None], window: int) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(sector_amounts)):
        sa = sector_amounts[max(0, i - window + 1):i + 1]
        ma = market_amounts[max(0, i - window + 1):i + 1]
        if len(sa) == window and all(v is not None for v in sa) and all(v is not None for v in ma) and sum(ma) != 0:
            out.append(sum(sa) / sum(ma))
        else:
            out.append(None)
    return out


def wilder_rsi(closes: list[float | None], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period or any(v is None for v in closes[: period + 1]):
        return out
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = float(closes[i]) - float(closes[i - 1])
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = fmean(gains)
    avg_loss = fmean(losses)
    out[period] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, len(closes)):
        if closes[i] is None or closes[i - 1] is None:
            avg_gain = avg_loss = 0.0
            continue
        delta = float(closes[i]) - float(closes[i - 1])
        avg_gain = (avg_gain * (period - 1) + max(delta, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-delta, 0.0)) / period
        out[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return out


def trailing_percentile(dates: list[str], values: list[float | None], index: int) -> float | None:
    end = date.fromisoformat(dates[index])
    start = end - timedelta(days=365)
    indices = [i for i, d in enumerate(dates[: index + 1]) if date.fromisoformat(d) >= start]
    subset = [values[i] for i in indices]
    local_index = len(indices) - 1
    return percentile(subset, local_index)


def crowding(rsi_pct, turnover_pct, share_pct):
    if any(v is None for v in (rsi_pct, turnover_pct, share_pct)):
        return None
    momentum = 0.35 * rsi_pct + 0.35 * turnover_pct + 0.30 * share_pct
    return 0.75 * momentum + 0.25 * max(rsi_pct, turnover_pct, share_pct)


def get_sections(obj):
    if isinstance(obj, dict) and isinstance(obj.get("sections"), list):
        return obj["sections"]
    return []


def run_main():
    generated_at = now_iso()
    codes = [code for _, code in SECTORS]

    trade_calendar = westock("trade-calendar", "--date", TARGET, "--raw")
    market_overview = westock("market-overview", "--type", "all", "--date", TARGET, "--raw")
    changedist = westock("changedist", "--raw")
    lhb = westock("lhb", "--date", TARGET, "--raw")
    macro = westock("macro", "indicator", "cn_core", "--date", TARGET, "--raw")

    constituents_raw = westock("sector", "constituent", ",".join(codes), "--raw")
    constituent_map: dict[str, list[dict]] = {code: [] for code in codes}
    sections = get_sections(constituents_raw)
    if sections:
        for section in sections:
            for row in flatten_rows(section):
                sector_code = row.get("SectorCode")
                if sector_code in constituent_map:
                    constituent_map[sector_code].append(row)
    else:
        for row in flatten_rows(constituents_raw):
            sector_code = row.get("SectorCode")
            if sector_code in constituent_map:
                constituent_map[sector_code].append(row)

    sector_kline_raw = westock("kline", ",".join(codes), "--period", "day", "--start", KLINE_START, "--end", TARGET, "--raw")
    sector_klines: dict[str, list[dict]] = defaultdict(list)
    for row in flatten_rows(sector_kline_raw):
        symbol = row.get("symbol")
        if symbol in codes and row.get("date"):
            sector_klines[symbol].append(row)

    market_kline_raw = westock("kline", "sh000001,sz399001", "--period", "day", "--start", KLINE_START, "--end", TARGET, "--raw")
    market_parts: dict[str, dict[str, float]] = defaultdict(dict)
    for row in flatten_rows(market_kline_raw):
        if row.get("symbol") in ("sh000001", "sz399001") and row.get("date"):
            amount = finite(row.get("amount"))
            if amount is not None:
                market_parts[row["date"]][row["symbol"]] = amount
    market_amount = {
        d: parts["sh000001"] + parts["sz399001"]
        for d, parts in market_parts.items()
        if "sh000001" in parts and "sz399001" in parts
    }
    market_dates = sorted(market_amount)
    if not market_dates or market_dates[-1] != TARGET:
        raise RuntimeError(f"市场成交额序列未覆盖目标日：{market_dates[-1] if market_dates else None}")

    unique_constituents = sorted({row.get("code") for rows in constituent_map.values() for row in rows if row.get("code")})
    supported = [code for code in unique_constituents if code.startswith(("sh", "sz"))]
    unsupported = [code for code in unique_constituents if code not in supported]
    batch_size = 80
    batches = [supported[i:i + batch_size] for i in range(0, len(supported), batch_size)]
    fund_rows: list[dict] = []
    failed_batches: dict[str, str] = {}

    def fetch_fund(batch_index: int, batch: list[str]):
        try:
            data = westock("fund", "flow", ",".join(batch), "--start", FUND_START, "--end", TARGET, "--raw")
            rows = [r for r in flatten_rows(data) if r.get("code") and r.get("date")]
            return batch_index, rows, None
        except Exception as exc:
            return batch_index, [], str(exc)

    with ThreadPoolExecutor(max_workers=4) as pool:
        future_map = {pool.submit(fetch_fund, i + 1, batch): i + 1 for i, batch in enumerate(batches)}
        for future in as_completed(future_map):
            idx, rows, error = future.result()
            if error:
                failed_batches[str(idx)] = error
            else:
                fund_rows.extend(rows)
            print(f"资金批次 {idx}/{len(batches)}：{len(rows)} 行" + (f"，失败：{error}" if error else ""), flush=True)

    flow_by_code_date: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in fund_rows:
        flow_by_code_date[row["code"]][row["date"]] = row

    sector_results = []
    for name, code in SECTORS:
        rows = sorted(sector_klines.get(code, []), key=lambda r: r["date"])
        anomalies: list[str] = []
        if not rows:
            anomalies.append("板块K线缺失")
        dates = [r["date"] for r in rows]
        closes = [finite(r.get("last")) for r in rows]
        amounts = [finite(r.get("amount")) for r in rows]
        turnovers = [finite(r.get("exchange")) for r in rows]
        market_aligned = [market_amount.get(d) for d in dates]
        rsi = wilder_rsi(closes)
        turnover5 = rolling_mean(turnovers, 5)
        share5 = rolling_share(amounts, market_aligned, 5)

        latest_idx = dates.index(TARGET) if TARGET in dates else None
        if latest_idx is None:
            anomalies.append("板块K线未覆盖目标交易日")

        def ret(horizon: int):
            if latest_idx is None or latest_idx < horizon:
                return None
            current, prior = closes[latest_idx], closes[latest_idx - horizon]
            return None if current is None or prior in (None, 0) else (current / prior - 1) * 100

        current_rsi_pct = trailing_percentile(dates, rsi, latest_idx) if latest_idx is not None else None
        current_turnover_pct = trailing_percentile(dates, turnover5, latest_idx) if latest_idx is not None else None
        current_share_pct = trailing_percentile(dates, share5, latest_idx) if latest_idx is not None else None
        ago_idx = latest_idx - 5 if latest_idx is not None and latest_idx >= 5 else None
        ago_rsi_pct = trailing_percentile(dates, rsi, ago_idx) if ago_idx is not None else None
        ago_turnover_pct = trailing_percentile(dates, turnover5, ago_idx) if ago_idx is not None else None
        ago_share_pct = trailing_percentile(dates, share5, ago_idx) if ago_idx is not None else None
        ago_crowding = crowding(ago_rsi_pct, ago_turnover_pct, ago_share_pct)

        constituents = constituent_map.get(code, [])
        constituent_codes = [r["code"] for r in constituents if r.get("code")]
        supported_sector = [c for c in constituent_codes if c.startswith(("sh", "sz"))]
        unsupported_sector = [c for c in constituent_codes if c not in supported_sector]
        if unsupported_sector:
            anomalies.append(f"{len(unsupported_sector)}只北交所/非沪深成份股不受资金接口支持，保持缺失")

        target_pos = market_dates.index(TARGET)
        prev_date = market_dates[target_pos - 1] if target_pos > 0 else None
        breadth_observed = breadth_up = 0
        for stock_code in constituent_codes:
            today_row = flow_by_code_date.get(stock_code, {}).get(TARGET)
            prev_row = flow_by_code_date.get(stock_code, {}).get(prev_date) if prev_date else None
            today_close = finite(today_row.get("ClosePrice")) if today_row else None
            prev_close = finite(prev_row.get("ClosePrice")) if prev_row else None
            if today_close is not None and prev_close not in (None, 0):
                breadth_observed += 1
                if today_close > prev_close:
                    breadth_up += 1
        breadth = breadth_up / breadth_observed * 100 if breadth_observed else None

        daily_fund = []
        sector_date_to_amount = {r["date"]: finite(r.get("amount")) for r in rows}
        relevant_dates = [d for d in market_dates if FUND_START <= d <= TARGET]
        for d in relevant_dates:
            values = []
            zero_count = 0
            for stock_code in constituent_codes:
                item = flow_by_code_date.get(stock_code, {}).get(d)
                value = finite(item.get("MainNetFlow")) if item else None
                if value is not None:
                    values.append(value)
                    if value == 0:
                        zero_count += 1
            expected = len(constituent_codes)
            observed = len(values)
            amount = sector_date_to_amount.get(d)
            net_sum = sum(values) if values else None
            daily_fund.append({
                "date": d,
                "main_net_flow_sum": rounded(net_sum, 2),
                "sector_amount": rounded(amount, 2),
                "flow_strength": rounded(net_sum / amount, 10) if net_sum is not None and amount not in (None, 0) else None,
                "covered_constituents": observed,
                "expected_constituents": expected,
                "coverage": rounded(observed / expected, 6) if expected else None,
                "zero_flow_records": zero_count,
            })

        coverage_by_horizon = {}
        flow_strengths = {}
        for horizon in (1, 5, 20):
            selected = daily_fund[-horizon:]
            observed = sum(x["covered_constituents"] for x in selected)
            expected = len(constituent_codes) * horizon
            values = [x["main_net_flow_sum"] for x in selected if x["main_net_flow_sum"] is not None]
            denoms = [x["sector_amount"] for x in selected if x["sector_amount"] is not None]
            net_sum = sum(values) if values else None
            amount_sum = sum(denoms) if len(denoms) == horizon else None
            coverage_by_horizon[str(horizon)] = {
                "observed_stock_days": observed,
                "expected_stock_days": expected,
                "coverage": rounded(observed / expected, 6) if expected else None,
                "net_flow_sum": rounded(net_sum, 2),
                "sector_amount_sum": rounded(amount_sum, 2),
            }
            flow_strengths[horizon] = net_sum / amount_sum if net_sum is not None and amount_sum not in (None, 0) else None

        all_zero_codes = []
        for stock_code in supported_sector:
            values = [finite(r.get("MainNetFlow")) for r in flow_by_code_date.get(stock_code, {}).values()]
            values = [v for v in values if v is not None]
            if values and all(v == 0 for v in values):
                all_zero_codes.append(stock_code)

        matching_dates = sum(1 for d in dates if d in market_amount)
        kline_coverage = {
            "rows": len(rows),
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None,
            "expected_market_dates": len(market_dates),
            "matching_market_dates": matching_dates,
            "coverage": rounded(matching_dates / len(market_dates), 6) if market_dates else None,
        }
        latest_amounts = [v for v in amounts[max(0, (latest_idx or 0) - 4):(latest_idx or 0) + 1] if v is not None] if latest_idx is not None else []
        avg_amount_5d = fmean(latest_amounts) if len(latest_amounts) == 5 else None
        summary = {
            "returns_pct": {"1d": rounded(ret(1)), "5d": rounded(ret(5)), "20d": rounded(ret(20))},
            "flow_strength": {"1": rounded(flow_strengths[1], 10), "5": rounded(flow_strengths[5], 10), "20": rounded(flow_strengths[20], 10)},
            "latest_rsi14": rounded(rsi[latest_idx]) if latest_idx is not None else None,
            "rsi_pct": rounded(current_rsi_pct),
            "latest_turnover_rolling5": rounded(turnover5[latest_idx]) if latest_idx is not None else None,
            "turnover_pct": rounded(current_turnover_pct),
            "latest_share_rolling5": rounded(share5[latest_idx], 10) if latest_idx is not None else None,
            "share_pct": rounded(current_share_pct),
            "five_trading_days_ago": {
                "date": dates[ago_idx] if ago_idx is not None else None,
                "rsi_pct": rounded(ago_rsi_pct),
                "turnover_pct": rounded(ago_turnover_pct),
                "share_pct": rounded(ago_share_pct),
                "crowding": rounded(ago_crowding),
            },
            "breadth": rounded(breadth),
            "breadth_observed": breadth_observed,
            "breadth_up": breadth_up,
            "avg_amount_5d": rounded(avg_amount_5d, 2),
            "daily_fund_aggregation": daily_fund,
        }
        sector_results.append({
            "name": name,
            "code": code,
            "constituents": {
                "count": len(constituent_codes),
                "codes": constituent_codes,
                "unsupported_fund_codes": unsupported_sector,
            },
            "kline_coverage": kline_coverage,
            "fund_coverage": coverage_by_horizon,
            "all_zero_flow_codes": all_zero_codes,
            "raw_aggregate_summary": summary,
            "anomalies": anomalies,
        })

    attention_values = [s["raw_aggregate_summary"]["avg_amount_5d"] for s in sector_results]
    attentions = [percentile(attention_values, i) for i in range(len(attention_values))]
    input_sectors = []
    source_notes = [
        "行业代码沿用2026-08-24文件中的固定29个申万二级行业清单；本次重新调用sector constituent --raw校验并拉取成份股",
        f"板块日线由kline --period day --start {KLINE_START} --end {TARGET} --raw重新获取",
        f"资金由成份股批量fund flow --start {FUND_START} --end {TARGET} --raw重新获取并按行业/交易日汇总MainNetFlow",
        "资金强度=行业成份股主力净流入合计/板块同期成交额合计",
        "breadth=可获得相邻两交易日收盘价的成份股中当日上涨占比",
        "catalyst/fundamental无同口径结构化证据，设为null",
    ]
    for i, sector in enumerate(sector_results):
        summary = sector["raw_aggregate_summary"]
        item = {
            "name": sector["name"],
            "code": sector["code"],
            "return_1d": summary["returns_pct"]["1d"],
            "return_5d": summary["returns_pct"]["5d"],
            "return_20d": summary["returns_pct"]["20d"],
            "flow_1d": summary["flow_strength"]["1"],
            "flow_5d": summary["flow_strength"]["5"],
            "flow_20d": summary["flow_strength"]["20"],
            "breadth": summary["breadth"],
            "attention": rounded(attentions[i]),
            "catalyst": None,
            "fundamental": None,
            "rsi_pct": summary["rsi_pct"],
            "turnover_pct": summary["turnover_pct"],
            "share_pct": summary["share_pct"],
            "crowding_5d_ago": summary["five_trading_days_ago"]["crowding"],
            "data_quality": {
                "constituent_count": sector["constituents"]["count"],
                "kline": sector["kline_coverage"],
                "fund_flow": sector["fund_coverage"],
                "breadth": {
                    "observed": summary["breadth_observed"],
                    "expected": sector["constituents"]["count"],
                    "coverage": rounded(summary["breadth_observed"] / sector["constituents"]["count"], 6) if sector["constituents"]["count"] else None,
                },
                "anomalies": sector["anomalies"],
            },
            "source_notes": source_notes,
        }
        input_sectors.append(item)

    raw_payload = {
        "as_of_date": TARGET,
        "generated_at": generated_at,
        "source": {
            "skill": "westockdata",
            "cli": NPX,
            "package": PACKAGE,
            "fund_period": [FUND_START, TARGET],
            "kline_period": [KLINE_START, TARGET],
        },
        "universe": {
            "requested_names": REQUESTED_NAMES,
            "resolved_count": len(SECTORS),
            "included_count": len(sector_results),
            "search_errors": {},
            "constituent_errors": {code: "无成份股返回" for _, code in SECTORS if not constituent_map.get(code)},
            "sector_kline_errors": {code: "无K线返回" for _, code in SECTORS if not sector_klines.get(code)},
            "market_kline_errors": {},
        },
        "market_amount_coverage": {
            "rows": len(market_dates),
            "first_date": market_dates[0],
            "last_date": market_dates[-1],
            "definition": "sh000001.amount + sz399001.amount",
        },
        "fund_flow_batch_manifest": {
            "unique_constituents": len(unique_constituents),
            "supported_sh_sz_codes": len(supported),
            "unsupported_codes": unsupported,
            "batch_size": batch_size,
            "batch_count": len(batches),
            "successful_batches": len(batches) - len(failed_batches),
            "failed_batches": failed_batches,
            "raw_rows": len(fund_rows),
        },
        "calculation_notes": {
            "return": "close_t / close_t-n - 1, expressed as percent",
            "rsi": "Wilder RSI(14), calculated on all returned sector closes",
            "historical_percentile": "average-rank percentile in [0,100] within trailing 365 calendar days ending at observation date",
            "turnover": "rolling mean of five sector kline exchange values",
            "share": "rolling-five sector amount sum divided by rolling-five (sh000001.amount + sz399001.amount) sum",
            "crowding": "C=75%*M+25%*max; M=35%*rsi_pct+35%*turnover_pct+30%*share_pct",
            "attention": "cross-sectional average-rank percentile of current sector five-day average amount",
            "missing_policy": "retain returned zeros; do not impute missing market data; catalyst and fundamental remain null",
        },
        "sectors": sector_results,
    }
    input_payload = {
        "as_of_date": TARGET,
        "generated_at": generated_at,
        "method": "sector_input_v2_data_engineering",
        "sectors": input_sectors,
    }

    target_dt = datetime.fromisoformat(TARGET).replace(tzinfo=TZ)
    date_ms = str(int(target_dt.timestamp() * 1000))
    try:
        limit_up = hithink("special", "limit-up-pool", "--date-ms", date_ms, "--page", "1", "--size", "200", "--format", "json")
    except Exception as exc:
        limit_up = {"ok": False, "error": str(exc)}
    try:
        dragon_tiger = hithink("special", "dragon-tiger", "--format", "json")
    except Exception as exc:
        dragon_tiger = {"ok": False, "error": str(exc)}

    overview_by_type = {}
    if isinstance(market_overview, list):
        for item in market_overview:
            if isinstance(item, dict):
                kind = item.get("info", {}).get("type")
                if kind:
                    overview_by_type[kind] = item
    trade_row = overview_by_type.get("trade", {}).get("row") or {}
    updown_row = overview_by_type.get("updown", {}).get("row") or {}
    rotation = overview_by_type.get("rotation", {})

    changedist_rows = flatten_rows(changedist)
    changedist_row = changedist_rows[0] if changedist_rows else changedist
    lhb_sections = get_sections(lhb)
    lhb_labels = ["institution", "active_seat", "high_win_buy", "high_win_seat"]
    lhb_summary = {
        label: {"count": len(section) if isinstance(section, list) else 0, "top_rows": section[:10] if isinstance(section, list) else []}
        for label, section in zip(lhb_labels, lhb_sections)
    }

    macro_rows = flatten_rows(macro)
    macro_effective = []
    for row in macro_rows:
        dates_found = {k: v for k, v in row.items() if k.endswith("_END_DATE") or k.endswith("_INFO_DATE")}
        if dates_found:
            macro_effective.append(dates_found)

    limit_items = []
    limit_pagination = None
    if isinstance(limit_up, dict) and isinstance(limit_up.get("data"), dict):
        limit_items = limit_up["data"].get("item") or []
        limit_pagination = limit_up["data"].get("pagination")
    theme_counter = Counter()
    for item in limit_items:
        reason = item.get("limit_up_reason") or ""
        for token in re.split(r"[+、/（）()]+", reason):
            token = token.strip()
            if token:
                theme_counter[token] += 1

    conflicts = []
    if updown_row and isinstance(changedist_row, dict):
        overview_tuple = (updown_row.get("CNT_RED"), updown_row.get("CNT_GREEN"), updown_row.get("CNT_ZERO"), updown_row.get("CNT_REACH_UPLIMIT"), updown_row.get("CNT_REACH_DNLIMIT"))
        changed_tuple = (changedist_row.get("upCount"), changedist_row.get("downCount"), changedist_row.get("flatCount"), changedist_row.get("upLimitCount"), changedist_row.get("downLimitCount"))
        if overview_tuple != changed_tuple:
            conflicts.append({
                "topic": "市场宽度与涨跌停家数",
                "market_overview": {"上涨": overview_tuple[0], "下跌": overview_tuple[1], "平盘": overview_tuple[2], "涨停": overview_tuple[3], "跌停": overview_tuple[4]},
                "changedist": changedist_row,
                "handling": "分别保留，不静默合并；主证据采用带目标日期的market-overview，changedist作为盘后实时口径复核",
            })
    if limit_pagination and updown_row.get("CNT_REACH_UPLIMIT") != limit_pagination.get("total"):
        conflicts.append({
            "topic": "涨停数量",
            "market_overview": updown_row.get("CNT_REACH_UPLIMIT"),
            "hithink_limit_up_pool": limit_pagination.get("total"),
            "handling": "保留供应商口径差异；hithink池用于热点样本，不替代全市场统计",
        })

    hithink_trade_date = None
    if isinstance(dragon_tiger, dict) and isinstance(dragon_tiger.get("data"), dict):
        hithink_trade_date = dragon_tiger["data"].get("trade_date")
    if hithink_trade_date and hithink_trade_date != TARGET:
        FAILURES.append({
            "command": f"{HITHINK} special dragon-tiger --format json",
            "ok": False,
            "error": f"接口成功但trade_date={hithink_trade_date}，滞后于目标日{TARGET}",
            "handling": f"不作为当日龙虎榜；改用WeStock lhb --date {TARGET} --raw",
        })

    market_payload = {
        "as_of_date": TARGET,
        "query_context": {
            "timezone": "Asia/Shanghai",
            "requested_at": generated_at,
            "generated_at": generated_at,
            "market_state": "盘后",
            "completeness_basis": f"目标日为交易日，且市场总览和板块K线均覆盖{TARGET}收盘",
        },
        "trade_date_confirmation": trade_calendar,
        "indices": {
            "上证指数": {"close": trade_row.get("CLOSE_PRICE_SZZS"), "change_pct": trade_row.get("CHANGE_PCT_SZZS")},
            "深证成指": {"close": trade_row.get("CLOSE_PRICE_SZCZ"), "change_pct": trade_row.get("CHANGE_PCT_SZCZ")},
            "创业板指": {"close": trade_row.get("CLOSE_PRICE_CYBZ"), "change_pct": trade_row.get("CHANGE_PCT_CYBZ")},
            "source": "WeStock market-overview trade",
            "date": overview_by_type.get("trade", {}).get("date"),
        },
        "turnover": {
            "amount_100m_cny": trade_row.get("MONEY"),
            "five_day_average_100m_cny": trade_row.get("MONEY_5DAVG"),
            "twenty_day_average_100m_cny": trade_row.get("MONEY_20DAVG"),
            "vs_twenty_day_average_pct": trade_row.get("MONEY_20DAVG_RATIO"),
            "source": "WeStock market-overview trade",
        },
        "market_breadth": {
            "dated_market_overview": updown_row,
            "realtime_changedist": changedist_row,
        },
        "limit_status": {
            "market_overview": {"limit_up": updown_row.get("CNT_REACH_UPLIMIT"), "limit_down": updown_row.get("CNT_REACH_DNLIMIT")},
            "changedist": changedist_row,
            "hithink_limit_up_pool": {"pagination": limit_pagination, "items": limit_items},
        },
        "style": rotation,
        "macro": {
            "query_date": TARGET,
            "latest_actual_data_date": 20260824,
            "latest_release_date": 20260824,
            "latest_monthly_period_end": 20260731,
            "latest_quarterly_period_end": 20260630,
            "effective_period_note": "最新实际高频数据截至2026-08-24；月度指标主要截至2026-07-31，季度指标截至2026-06-30。FORECAST_END_DATE与尚未到期的MLF_END_DATE不计入最新实际数据日。",
            "latest_effective_periods": macro_effective,
            "raw": macro,
        },
        "dragon_tiger_and_hotspots": {
            "westock_lhb": lhb_summary,
            "hithink_dragon_tiger": dragon_tiger,
            "hotspot_summary": {
                "limit_up_pool_count": len(limit_items),
                "top_reason_tokens": [{"theme": k, "count": v} for k, v in theme_counter.most_common(20)],
                "highest_continuation": sorted(limit_items, key=lambda x: (x.get("continue_day_cnt") or 0, x.get("seal_money") or 0), reverse=True)[:10],
            },
        },
        "source_raw": {
            "market_overview": market_overview,
            "changedist": changedist,
        },
        "commands": sorted(COMMANDS, key=lambda x: x["started_at"]),
        "failures": FAILURES,
        "data_conflicts": conflicts,
        "limitations": [
            "WeStock changedist为查询时点实时口径且不接受历史日期，与带日期的market-overview可能存在样本范围差异",
            f"hithink-finance龙虎榜接口返回{hithink_trade_date or '未知日期'}，若不等于{TARGET}则不作为当日龙虎榜使用",
            "北交所成份股不在WeStock个股资金接口支持范围内，未替代或补造",
            "catalyst和fundamental没有统一可审计的行业横截面结构化证据，sector input保持null",
        ],
    }

    input_path = EVIDENCE / f"{TARGET}-sector-input-v2.json"
    raw_path = EVIDENCE / f"{TARGET}-sector-raw-v2.json"
    market_path = EVIDENCE / f"{TARGET}-market-raw.json"
    input_path.write_text(json.dumps(input_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    market_path.write_text(json.dumps(market_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "input": str(input_path),
        "raw": str(raw_path),
        "market": str(market_path),
        "sectors": len(input_sectors),
        "unique_constituents": len(unique_constituents),
        "supported": len(supported),
        "unsupported": len(unsupported),
        "fund_rows": len(fund_rows),
        "failed_batches": failed_batches,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        run_main()
    except Exception as exc:
        print(f"FATAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
