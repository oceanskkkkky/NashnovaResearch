#!/usr/bin/env python3
"""Deterministic sector scoring for stock-almanac-daily.

Input JSON:
{
  "sectors": [
    {
      "name": "贵金属",
      "return_1d": 1.2,
      "return_5d": 4.8,
      "return_20d": 12.0,
      "flow_1d": 0.8,
      "flow_5d": 1.9,
      "flow_20d": 3.1,
      "breadth": 75,
      "attention": 80,
      "catalyst": 70,
      "fundamental": 60,
      "rsi_pct": 92,
      "turnover_pct": 88,
      "share_pct": 81,
      "crowding_5d_ago": 68
    }
  ]
}

Returns and flows are raw, same-unit values across one consistent sector universe.
The script converts them to cross-sectional percentile scores before fitting the
orthogonal flow residual. Other scores are expected in [0, 100].
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import fmean
from typing import Any

HORIZON_WEIGHTS = {"1d": 0.20, "5d": 0.35, "20d": 0.45}
MIN_SECTORS = 20
MIN_COVERAGE = 0.80
EPS = 1e-12


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def percentile_scores(values: list[float | None]) -> list[float | None]:
    """Return average-rank percentiles in [0, 100], preserving missing values."""
    valid = [(idx, float(value)) for idx, value in enumerate(values) if is_number(value)]
    result: list[float | None] = [None] * len(values)
    if not valid:
        return result
    if len(valid) == 1:
        result[valid[0][0]] = 50.0
        return result

    ordered = sorted(valid, key=lambda pair: pair[1])
    pos = 0
    while pos < len(ordered):
        end = pos + 1
        while end < len(ordered) and ordered[end][1] == ordered[pos][1]:
            end += 1
        average_rank = (pos + end - 1) / 2
        score = average_rank / (len(ordered) - 1) * 100
        for idx, _ in ordered[pos:end]:
            result[idx] = score
        pos = end
    return result


def weighted_horizon_score(rows: list[dict[str, Any]], prefix: str) -> list[float | None]:
    per_horizon: dict[str, list[float | None]] = {}
    for horizon in HORIZON_WEIGHTS:
        key = f"{prefix}_{horizon}"
        per_horizon[horizon] = percentile_scores([
            float(row[key]) if is_number(row.get(key)) else None for row in rows
        ])

    scores: list[float | None] = []
    for idx in range(len(rows)):
        parts = [per_horizon[h][idx] for h in HORIZON_WEIGHTS]
        if any(value is None for value in parts):
            scores.append(None)
            continue
        scores.append(sum(HORIZON_WEIGHTS[h] * float(per_horizon[h][idx]) for h in HORIZON_WEIGHTS))
    return scores


def winsorize(values: list[float], lower_q: float = 0.01, upper_q: float = 0.99) -> list[float]:
    ordered = sorted(values)
    n = len(ordered)

    def quantile(q: float) -> float:
        position = (n - 1) * q
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1 - weight) + ordered[upper] * weight

    lower_value = quantile(lower_q)
    upper_value = quantile(upper_q)
    return [max(lower_value, min(upper_value, value)) for value in values]


def zscores(values: list[float]) -> list[float] | None:
    mean = fmean(values)
    variance = fmean([(value - mean) ** 2 for value in values])
    if variance <= EPS:
        return None
    std = math.sqrt(variance)
    return [(value - mean) / std for value in values]


def orthogonalize(p_scores: list[float | None], f_scores: list[float | None]) -> dict[str, Any]:
    total = len(p_scores)
    valid_indices = [idx for idx, (p, f) in enumerate(zip(p_scores, f_scores)) if p is not None and f is not None]
    coverage = len(valid_indices) / total if total else 0.0
    result = {
        "enabled": False,
        "reason": None,
        "coverage": coverage,
        "sample_size": len(valid_indices),
        "alpha": None,
        "beta": None,
        "residual_percentiles": [None] * total,
    }

    if len(valid_indices) < MIN_SECTORS or coverage < MIN_COVERAGE:
        result["reason"] = f"样本不足或覆盖率不足（n={len(valid_indices)}, coverage={coverage:.1%}）"
        return result

    p_values = winsorize([float(p_scores[idx]) for idx in valid_indices])
    f_values = winsorize([float(f_scores[idx]) for idx in valid_indices])
    zp = zscores(p_values)
    zf = zscores(f_values)
    if zp is None or zf is None:
        result["reason"] = "横截面方差近零"
        return result

    mean_zp = fmean(zp)
    mean_zf = fmean(zf)
    denominator = sum((value - mean_zp) ** 2 for value in zp)
    if denominator <= EPS:
        result["reason"] = "价格动量横截面方差近零"
        return result

    beta = sum((x - mean_zp) * (y - mean_zf) for x, y in zip(zp, zf)) / denominator
    alpha = mean_zf - beta * mean_zp
    residuals = [y - alpha - beta * x for x, y in zip(zp, zf)]
    residual_pct = percentile_scores(residuals)
    mapped: list[float | None] = [None] * total
    for local_idx, row_idx in enumerate(valid_indices):
        mapped[row_idx] = residual_pct[local_idx]

    result.update({
        "enabled": True,
        "alpha": alpha,
        "beta": beta,
        "residual_percentiles": mapped,
    })
    return result


def score_or_default(row: dict[str, Any], key: str, default: float = 50.0) -> tuple[float, bool]:
    value = row.get(key)
    if is_number(value):
        return clamp(float(value)), False
    return default, True


def crowding(row: dict[str, Any]) -> dict[str, Any]:
    components = {
        "rsi_pct": (row.get("rsi_pct"), 0.35),
        "turnover_pct": (row.get("turnover_pct"), 0.35),
        "share_pct": (row.get("share_pct"), 0.30),
    }
    valid = {key: (clamp(float(value)), weight) for key, (value, weight) in components.items() if is_number(value)}
    degraded = len(valid) < 3
    warnings: list[str] = []

    if len(valid) >= 2:
        weight_sum = sum(weight for _, weight in valid.values())
        mean_score = sum(value * weight for value, weight in valid.values()) / weight_sum
        max_score = max(value for value, _ in valid.values())
        c_score = 0.75 * mean_score + 0.25 * max_score
    else:
        mean_score = 50.0
        max_score = 50.0
        c_score = 50.0
        warnings.append("拥挤度数据不足，按C=50降级，不能声称低拥挤")

    previous = row.get("crowding_5d_ago")
    delta = c_score - float(previous) if is_number(previous) and len(valid) >= 2 else None
    level_penalty = 16 * c_score / 100
    if delta is None or delta < 5:
        acceleration_penalty = 0.0
    elif delta < 10:
        acceleration_penalty = 1.0
    elif delta < 20:
        acceleration_penalty = 2.5
    else:
        acceleration_penalty = 4.0
    penalty = min(20.0, level_penalty + acceleration_penalty)

    if c_score >= 90 or penalty >= 18:
        warnings.append("严重拥挤，追高风险")
    elif c_score >= 80:
        warnings.append("高拥挤，仅观察回调，不追高")
    elif c_score >= 70:
        warnings.append("拥挤升温，注意波动放大")
    if delta is not None and delta >= 10:
        warnings.append("拥挤加速")
    for key, (value, _) in valid.items():
        if value >= 95:
            warnings.append(f"{key}达到近一年极端分位")

    return {
        "component_scores": {key: value for key, (value, _) in valid.items()},
        "weighted_mean": mean_score,
        "crowding_score": c_score,
        "delta_5d": delta,
        "level_penalty": level_penalty,
        "acceleration_penalty": acceleration_penalty,
        "penalty": penalty,
        "degraded": degraded,
        "warnings": warnings,
    }


def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("sectors")
    if not isinstance(rows, list) or not rows:
        raise ValueError("输入必须包含非空 sectors 数组")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("sectors 中每一项必须是对象")

    p_scores = weighted_horizon_score(rows, "return")
    f_scores = weighted_horizon_score(rows, "flow")
    regression = orthogonalize(p_scores, f_scores)
    residual_scores = regression["residual_percentiles"]

    scored_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        name = str(row.get("name") or row.get("code") or f"sector-{idx + 1}")
        p_score = p_scores[idx]
        f_score = f_scores[idx]
        residual_score = residual_scores[idx]
        warnings: list[str] = []
        degraded_reasons: list[str] = []

        if p_score is None:
            trend_score = None
            degraded_reasons.append("价格动量数据不完整")
        elif f_score is None:
            trend_score = min(p_score, 50.0)
            degraded_reasons.append("资金数据缺失，趋势确认上限50")
        elif regression["enabled"] and residual_score is not None:
            trend_score = 0.70 * p_score + 0.30 * residual_score
            if p_score >= 70 and residual_score <= 20:
                warnings.append("量价背离：上涨缺少增量资金确认")
            if p_score <= 50 and residual_score >= 80:
                warnings.append("资金先行潜伏，等待价格确认")
            residual_5d_ago = row.get("residual_pct_5d_ago")
            if p_score >= 70 and is_number(residual_5d_ago) and float(residual_5d_ago) - residual_score >= 20:
                warnings.append("趋势仍强但资金边际退潮")
        else:
            trend_score = 0.65 * p_score + 0.35 * min(p_score, f_score)
            degraded_reasons.append(f"正交化降级：{regression['reason']}")

        crowd = crowding(row)
        warnings.extend(crowd["warnings"])
        if crowd["degraded"]:
            degraded_reasons.append("拥挤度数据不完整")

        breadth, breadth_missing = score_or_default(row, "breadth")
        attention, attention_missing = score_or_default(row, "attention")
        catalyst, catalyst_missing = score_or_default(row, "catalyst")
        fundamental, fundamental_missing = score_or_default(row, "fundamental")
        if any((breadth_missing, attention_missing, catalyst_missing, fundamental_missing)):
            degraded_reasons.append("非趋势分项存在缺失，按50分处理")

        if trend_score is None:
            core_heat = None
            sector_heat = None
        else:
            core_heat = (
                0.35 * trend_score
                + 0.15 * breadth
                + 0.10 * attention
                + 0.10 * catalyst
                + 0.10 * fundamental
            )
            sector_heat = clamp(core_heat + 20 - crowd["penalty"])

        severe_crowding = crowd["crowding_score"] >= 90 or crowd["penalty"] >= 18
        severe_allowed = bool(
            severe_crowding
            and sector_heat is not None
            and sector_heat >= 70
            and residual_score is not None
            and residual_score >= 50
        )

        scored_rows.append({
            "name": name,
            "price_momentum_p": p_score,
            "fund_flow_f": f_score,
            "orthogonal_flow_r": residual_score,
            "trend_confirmation_t": trend_score,
            "crowding": crowd,
            "core_heat": core_heat,
            "sector_heat": sector_heat,
            "warnings": list(dict.fromkeys(warnings)),
            "degraded_reasons": list(dict.fromkeys(degraded_reasons)),
            "severe_crowding_can_remain": severe_allowed,
        })

    scored_rows.sort(key=lambda row: row["sector_heat"] if row["sector_heat"] is not None else -1, reverse=True)
    return {
        "method": "cross_sectional_price_flow_orthogonalization_v2",
        "regression": {key: value for key, value in regression.items() if key != "residual_percentiles"},
        "sectors": scored_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="计算板块量价正交热度与拥挤度预警")
    parser.add_argument("input", type=Path, help="输入JSON文件")
    parser.add_argument("--output", type=Path, help="输出JSON文件；省略时写到标准输出")
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = calculate(payload)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
