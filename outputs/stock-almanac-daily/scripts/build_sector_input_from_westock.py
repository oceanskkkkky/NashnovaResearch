#!/usr/bin/env python3
"""Build the daily sector scoring input from WeStock board history.

The script calls the installed westock-data CLI once per sector, parses its
Markdown table, and derives 1/5/20-day price and flow strength plus crowding
proxies from a consistent cross-section.

Breadth is left null when the board endpoint does not return valid advancing /
declining counts. The scoring script then applies its documented neutral
fallback instead of inventing breadth.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


CHINA_STANDARD_TIME = timezone(timedelta(hours=8), name="Asia/Shanghai")


def parse_cell(value: str) -> Any:
    value = value.strip()
    if value in {"", "-", "null", "None"}:
        return None
    try:
        return float(value)
    except ValueError:
        return value


def parse_markdown_table(text: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        raise ValueError("WeStock output did not contain a Markdown table")
    headers = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows: list[dict[str, Any]] = []
    for line in lines[2:]:
        cells = [parse_cell(cell) for cell in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def percentile_rank(history: list[float], value: float) -> float | None:
    valid = sorted(item for item in history if math.isfinite(item))
    if not valid:
        return None
    lower = sum(item < value for item in valid)
    equal = sum(item == value for item in valid)
    return 100.0 * (lower + 0.5 * equal) / len(valid)


def rolling_mean(values: list[float | None], window: int) -> list[float | None]:
    result: list[float | None] = []
    for index in range(len(values)):
        sample = values[max(0, index - window + 1) : index + 1]
        valid = [float(item) for item in sample if isinstance(item, (int, float))]
        result.append(statistics.fmean(valid) if len(valid) == window else None)
    return result


def rsi_series(closes: list[float], period: int = 14) -> list[float | None]:
    result: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return result
    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, period + 1):
        change = closes[index] - closes[index - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = statistics.fmean(gains)
    avg_loss = statistics.fmean(losses)
    result[period] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for index in range(period + 1, len(closes)):
        change = closes[index] - closes[index - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0.0)) / period
        result[index] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return result


def historical_percentile(series: list[float | None], index: int, lookback: int = 250) -> float | None:
    value = series[index]
    if value is None:
        return None
    start = max(0, index - lookback + 1)
    history = [float(item) for item in series[start : index + 1] if item is not None]
    return percentile_rank(history, float(value))


def crowd_score(rsi_pct: float | None, turnover_pct: float | None, share_pct: float | None) -> float | None:
    parts = [(rsi_pct, 0.35), (turnover_pct, 0.35), (share_pct, 0.30)]
    valid = [(float(value), weight) for value, weight in parts if value is not None]
    if len(valid) < 2:
        return None
    weight_sum = sum(weight for _, weight in valid)
    weighted_mean = sum(value * weight for value, weight in valid) / weight_sum
    return 0.75 * weighted_mean + 0.25 * max(value for value, _ in valid)


def pct_return(closes: list[float], horizon: int) -> float | None:
    if len(closes) <= horizon or closes[-1 - horizon] == 0:
        return None
    return (closes[-1] / closes[-1 - horizon] - 1.0) * 100.0


def ratio_sum(rows: list[dict[str, Any]], horizon: int) -> float | None:
    sample = rows[-horizon:]
    flows = [row.get("mainNetFlow") for row in sample]
    amounts = [row.get("turnoverValue") for row in sample]
    if any(not isinstance(value, (int, float)) for value in flows + amounts):
        return None
    denominator = sum(float(value) for value in amounts)
    return sum(float(value) for value in flows) / denominator if denominator else None


def fetch_history(node: str, cli: str, code: str, start: str, end: str) -> tuple[list[dict[str, Any]], str]:
    completed = subprocess.run(
        [node, cli, "market", code, start, end],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{code}: westock-data exited {completed.returncode}: {completed.stderr.strip()}")
    rows = parse_markdown_table(completed.stdout)
    rows = [row for row in rows if isinstance(row.get("date"), str)]
    rows.sort(key=lambda row: row["date"])
    if not rows or rows[-1]["date"] != end:
        raise RuntimeError(f"{code}: last row is not target date {end}")
    return rows, completed.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description="Build stock-almanac sector input from WeStock")
    parser.add_argument("--date", required=True)
    parser.add_argument("--previous-input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--westock-cli", required=True)
    parser.add_argument("--start", default="2025-06-01")
    parser.add_argument("--attention-json", type=Path)
    args = parser.parse_args()

    previous = json.loads(args.previous_input.read_text(encoding="utf-8"))
    attention: dict[str, float] = {}
    if args.attention_json and args.attention_json.exists():
        attention = json.loads(args.attention_json.read_text(encoding="utf-8"))

    raw_payload: dict[str, Any] = {
        "as_of_date": args.date,
        "generated_at": datetime.now(CHINA_STANDARD_TIME).isoformat(timespec="seconds"),
        "source": "westock-data market <sector> <start> <end>",
        "sectors": [],
    }
    sectors: list[dict[str, Any]] = []

    for seed in previous["sectors"]:
        rows, raw_text = fetch_history(args.node, args.westock_cli, seed["code"], args.start, args.date)
        closes = [float(row["closePrice"]) for row in rows]
        turnover = [float(row["turnoverRate"]) if isinstance(row.get("turnoverRate"), (int, float)) else None for row in rows]
        amounts = [float(row["turnoverValue"]) if isinstance(row.get("turnoverValue"), (int, float)) else None for row in rows]
        rsi = rsi_series(closes)
        turnover_5 = rolling_mean(turnover, 5)
        amount_5 = rolling_mean(amounts, 5)
        last_index = len(rows) - 1
        prior_index = max(0, last_index - 5)

        rsi_pct = historical_percentile(rsi, last_index)
        turnover_pct = historical_percentile(turnover_5, last_index)
        share_pct = historical_percentile(amount_5, last_index)
        previous_crowd = crowd_score(
            historical_percentile(rsi, prior_index),
            historical_percentile(turnover_5, prior_index),
            historical_percentile(amount_5, prior_index),
        )

        last = rows[-1]
        adv = last.get("advancingCount")
        dec = last.get("decliningCount")
        breadth = None
        if isinstance(adv, (int, float)) and isinstance(dec, (int, float)) and adv + dec > 0:
            breadth = 100.0 * float(adv) / (float(adv) + float(dec))

        sector = {
            "name": seed["name"],
            "code": seed["code"],
            "return_1d": float(last["changePct"]) if isinstance(last.get("changePct"), (int, float)) else pct_return(closes, 1),
            "return_5d": pct_return(closes, 5),
            "return_20d": pct_return(closes, 20),
            "flow_1d": ratio_sum(rows, 1),
            "flow_5d": ratio_sum(rows, 5),
            "flow_20d": ratio_sum(rows, 20),
            "breadth": breadth,
            "attention": attention.get(seed["code"], 0.0),
            "catalyst": None,
            "fundamental": None,
            "rsi_pct": rsi_pct,
            "turnover_pct": turnover_pct,
            "share_pct": share_pct,
            "crowding_5d_ago": previous_crowd,
            "data_quality": {
                "rows": len(rows),
                "first_date": rows[0]["date"],
                "last_date": rows[-1]["date"],
                "price_flow_complete": all(
                    value is not None
                    for value in (
                        pct_return(closes, 1), pct_return(closes, 5), pct_return(closes, 20),
                        ratio_sum(rows, 1), ratio_sum(rows, 5), ratio_sum(rows, 20),
                    )
                ),
                "breadth_degraded": breadth is None,
                "crowding_proxy": "板块5日平均成交额自身历史分位替代全市场成交占比分位",
            },
            "source_notes": [
                "价格与主力资金均来自WeStock板块历史接口，单次运行统一口径",
                "资金强度=板块主力净流入/板块成交额",
                "板块接口未返回有效涨跌家数时breadth留空，由评分脚本按50分中性降级",
                "share_pct使用板块5日平均成交额自身近一年历史分位近似，证据台账显式披露",
            ],
        }
        sectors.append(sector)
        raw_payload["sectors"].append({
            "name": seed["name"],
            "code": seed["code"],
            "rows": rows,
            "raw_stdout": raw_text,
        })
        print(f"fetched {seed['name']} ({seed['code']}): {len(rows)} rows", flush=True)

    output = {
        "as_of_date": args.date,
        "generated_at": raw_payload["generated_at"],
        "method": "westock_sector_history_v1",
        "sectors": sectors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.raw_output.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
