# -*- coding: utf-8 -*-
"""
V2 vs V3 大样本前瞻回测（离线历史重建版）

做法：
1. 复用 2026-08-28 完整流水线的成份股名单；
2. 抓取 29 板块与沪深指数全历史日K（2025-06-01起）、
   全部成份股日K（2026-06-15起，用于广度）、
   全部成份股资金流（2026-06-01起，用于 flow_1/5/20）；
3. 对每个可评分交易日（资金流满20日起，至 08-27）按生产口径重建板块输入：
   - return/flow 原始值；RSI14/换手roll5/占比roll5 的365日分位；
   - breadth=当日上涨成份占比；attention=板块5日均成交额横截面分位；
   - catalyst/fundamental=null（与生产一致按50处理）；
4. 逐日分别跑 V3（导入生产脚本 calculate）与 V2（复刻旧公式）评分；
5. 对照其后真实板块涨跌（T+1 / T+5）与 Top5 板块成份股等权收益，
   输出 IC、t值、ICIR、Top5超额与胜率、配对差异检验。

缓存：evidence/backtest-cache.json（增量保存，可断点续跑）
输出：evidence/2026-08-29-v2-vs-v3-backtest-full.md / .json
"""
import importlib.util
import json
import math
import os
import statistics
import subprocess
import sys
import time
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "evidence")
PACKAGE = "westock-data-skillhub@1.0.5"
CACHE_PATH = os.path.join(EV, "backtest-cache.json")
END = "2026-08-28"          # 最后有真实数据的交易日
SECTOR_KLINE_START = "2025-06-01"
STOCK_KLINE_START = "2026-06-15"
FUND_START = "2026-06-01"
MIN_FLOW_DAYS = 20
REPORT_MD = os.path.join(EV, "2026-08-29-v2-vs-v3-backtest-full.md")
REPORT_JSON = os.path.join(EV, "2026-08-29-v2-vs-v3-backtest-full.json")

# 导入生产 V3 评分器
spec = importlib.util.spec_from_file_location(
    "sector_score",
    os.path.join(ROOT, ".workbuddy/skills/stock-almanac-daily/scripts/calculate_sector_score.py"))
sector_score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sector_score)


# ---------------- 数据获取 ----------------

def westock(*args, retries=3):
    cmdline = subprocess.list2cmdline(["npx", "-y", PACKAGE, *args])
    last = ""
    for attempt in range(retries + 1):
        p = subprocess.run(["cmd.exe", "/d", "/c", cmdline],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode == 0 and p.stdout.strip():
            try:
                return json.loads(p.stdout)
            except json.JSONDecodeError:
                last = "JSON decode error"
        else:
            last = (p.stderr or p.stdout or "")[-300:]
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"westock {args[:2]} failed: {last}")


def load_cache():
    if os.path.exists(CACHE_PATH):
        return json.load(open(CACHE_PATH, encoding="utf-8"))
    return {"sector_klines": {}, "index_amount": {}, "stock_closes": {}, "fund": {}}


def save_cache(cache):
    json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"))


def fetch_all(cache, sector_codes, stock_codes):
    # 1) 板块K线（全历史）
    missing = [c for c in sector_codes if c not in cache["sector_klines"]]
    if missing:
        print(f"[fetch] sector klines: {len(missing)}", flush=True)
        data = westock("kline", ",".join(missing), "--period", "day",
                       "--start", SECTOR_KLINE_START, "--end", END, "--raw")
        for r in data:
            code = r.get("symbol")
            if code:
                cache["sector_klines"].setdefault(code, {})[r["date"]] = {
                    "last": float(r["last"]), "amount": float(r.get("amount") or 0),
                    "exchange": float(r.get("exchange") or 0)}
        save_cache(cache)

    # 2) 指数成交额
    if not cache["index_amount"]:
        print("[fetch] index klines", flush=True)
        data = westock("kline", "sh000001,sz399001", "--period", "day",
                       "--start", SECTOR_KLINE_START, "--end", END, "--raw")
        for r in data:
            amt = float(r.get("amount") or 0)
            cache["index_amount"][r["date"]] = cache["index_amount"].get(r["date"], 0) + amt
        save_cache(cache)

    # 3) 成份股日K（广度 + 个股层验证）
    missing = [c for c in stock_codes if c not in cache["stock_closes"]]
    for i in range(0, len(missing), 40):
        batch = missing[i:i + 40]
        print(f"[fetch] stock klines {i + 1}-{i + len(batch)}/{len(missing)}", flush=True)
        try:
            data = westock("kline", ",".join(batch), "--period", "day",
                           "--start", STOCK_KLINE_START, "--end", END, "--raw")
            got = set()
            for r in data:
                code = r.get("symbol")
                if code:
                    got.add(code)
                    cache["stock_closes"].setdefault(code, {})[r["date"]] = float(r["last"])
            for c in batch:  # 标记无数据代码，避免重复抓取
                cache["stock_closes"].setdefault(c, {})
        except RuntimeError as exc:
            print(f"  batch failed: {exc}", flush=True)
        if i % 200 == 0:
            save_cache(cache)
    save_cache(cache)

    # 4) 成份股资金流
    missing = [c for c in stock_codes if c not in cache["fund"]]
    for i in range(0, len(missing), 60):
        batch = missing[i:i + 60]
        print(f"[fetch] fund flow {i + 1}-{i + len(batch)}/{len(missing)}", flush=True)
        try:
            data = westock("fund", "flow", ",".join(batch),
                           "--start", FUND_START, "--end", END, "--raw")
            for r in data:
                code = r.get("code") or r.get("symbol")
                if code and r.get("date"):
                    try:
                        v = float(r.get("MainNetFlow"))
                    except (TypeError, ValueError):
                        continue
                    cache["fund"].setdefault(code, {})[r["date"]] = v
            for c in batch:
                cache["fund"].setdefault(c, {})
        except RuntimeError as exc:
            print(f"  batch failed: {exc}", flush=True)
        if i % 300 == 0:
            save_cache(cache)
    save_cache(cache)


# ---------------- 指标计算 ----------------

def rsi_series(closes, period=14):
    result = [None] * len(closes)
    if len(closes) <= period:
        return result
    gains, losses = [], []
    for i in range(1, period + 1):
        ch = closes[i] - closes[i - 1]
        gains.append(max(ch, 0.0)); losses.append(max(-ch, 0.0))
    ag, al = statistics.fmean(gains), statistics.fmean(losses)
    result[period] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(period + 1, len(closes)):
        ch = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + max(ch, 0.0)) / period
        al = (al * (period - 1) + max(-ch, 0.0)) / period
        result[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return result


def avg_rank_pct(history, value):
    vals = [v for v in history if v is not None]
    if not vals:
        return None
    less = sum(1 for v in vals if v < value)
    equal = sum(1 for v in vals if v == value)
    return (less + (equal - 1) / 2) / (len(vals) - 1) * 100 if len(vals) > 1 else 50.0


def trailing_pct(series_dates, series_vals, d, lookback_days=365):
    """series_dates 升序；返回 d 日值在 trailing 365 日窗口内的平均秩分位"""
    if d not in series_vals or series_vals[d] is None:
        return None
    cutoff = (date.fromisoformat(d) - timedelta(days=lookback_days)).isoformat()
    history = [series_vals[x] for x in series_dates if cutoff <= x <= d]
    return avg_rank_pct(history, series_vals[d])


def crowd_c(rsi_pct, turnover_pct, share_pct):
    parts = [(rsi_pct, 0.35), (turnover_pct, 0.35), (share_pct, 0.30)]
    valid = [(v, w) for v, w in parts if v is not None]
    if len(valid) < 2:
        return None
    ws = sum(w for _, w in valid)
    mean = sum(v * w for v, w in valid) / ws
    return 0.75 * mean + 0.25 * max(v for v, _ in valid)


def v2_calculate(rows):
    """复刻 V2：无绝对约束/上限；SectorHeat = CoreHeat + 20 - min(20, 16*C/100 + accel)"""
    p_scores = sector_score.weighted_horizon_score(rows, "return")
    f_scores = sector_score.weighted_horizon_score(rows, "flow")
    reg = sector_score.orthogonalize(p_scores, f_scores)
    out = []
    for idx, row in enumerate(rows):
        p, f, r = p_scores[idx], f_scores[idx], reg["residual_percentiles"][idx]
        if p is None:
            out.append({"name": row["name"], "sector_heat": None})
            continue
        if reg["enabled"] and r is not None and f is not None:
            t = 0.70 * p + 0.30 * r
        elif f is not None:
            t = 0.65 * p + 0.35 * min(p, f)
        else:
            t = min(p, 50.0)
        c = crowd_c(row.get("rsi_pct"), row.get("turnover_pct"), row.get("share_pct"))
        if c is None:
            c = 50.0
        prev = row.get("crowding_5d_ago")
        delta = c - prev if isinstance(prev, (int, float)) else None
        accel = 0.0 if delta is None or delta < 5 else (1.0 if delta < 10 else (2.5 if delta < 20 else 4.0))
        penalty = min(20.0, 16.0 * c / 100 + accel)
        breadth = row.get("breadth")
        attention = row.get("attention")
        core = (0.35 * t + 0.15 * (breadth if breadth is not None else 50)
                + 0.10 * (attention if attention is not None else 50) + 0.10 * 50 + 0.10 * 50)
        heat = max(0.0, min(100.0, core + 20 - penalty))
        out.append({"name": row["name"], "sector_heat": heat})
    out.sort(key=lambda x: x["sector_heat"] if x["sector_heat"] is not None else -1, reverse=True)
    return out


# ---------------- 统计 ----------------

def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs); vy = sum((y - my) ** 2 for y in ys)
    return cov / math.sqrt(vx * vy) if vx > 0 and vy > 0 else None


def spearman(xs, ys):
    return pearson(ranks(xs), ranks(ys))


def tstat(xs):
    if len(xs) < 2:
        return None
    m = statistics.fmean(xs)
    sd = statistics.stdev(xs)
    return m / (sd / math.sqrt(len(xs))) if sd > 0 else None


# ---------------- 主流程 ----------------

def main():
    cache = load_cache()
    raw = json.load(open(os.path.join(EV, "2026-08-28-sector-raw-v2.json"), encoding="utf-8"))
    sectors = [(s["name"], s["code"],
                [c for c in s["constituents"]["codes"] if c[:2].lower() in ("sh", "sz")])
               for s in raw["sectors"]]
    sector_codes = [c for _, c, _ in sectors]
    stock_codes = sorted({c for _, _, codes in sectors for c in codes})
    print(f"sectors={len(sectors)} stocks={len(stock_codes)}", flush=True)

    fetch_all(cache, sector_codes, stock_codes)

    # 市场交易日序列（指数成交额日期）
    market_days = sorted(d for d in cache["index_amount"] if d <= END)
    day_idx = {d: i for i, d in enumerate(market_days)}

    # 预计算每板块日序列
    sec_data = {}
    for name, code, members in sectors:
        kl = cache["sector_klines"].get(code, {})
        dates = [d for d in market_days if d in kl]
        closes = [kl[d]["last"] for d in dates]
        amounts = {d: kl[d]["amount"] for d in dates}
        turnover5, share5 = {}, {}
        amt_series = [amounts[d] for d in dates]
        ex_series = [kl[d]["exchange"] for d in dates]
        for i, d in enumerate(dates):
            if i >= 4:
                turnover5[d] = statistics.fmean(ex_series[i - 4:i + 1])
                mkt = sum(cache["index_amount"].get(x, 0) for x in dates[i - 4:i + 1])
                share5[d] = (sum(amt_series[i - 4:i + 1]) / mkt) if mkt > 0 else None
        rsi = rsi_series(closes)
        rsi_map = {d: rsi[i] for i, d in enumerate(dates)}
        # 资金流：逐日 主力净流入合计 / 板块成交额
        flow_daily = {}
        for d in dates:
            if d < FUND_START:
                continue
            vals = [cache["fund"].get(c, {}).get(d) for c in members]
            vals = [v for v in vals if v is not None]
            amt = amounts.get(d)
            if vals and amt:
                flow_daily[d] = sum(vals) / amt
        sec_data[name] = {"dates": dates, "close": {d: kl[d]["last"] for d in dates},
                          "amount": amounts, "turnover5": turnover5, "share5": share5,
                          "rsi": rsi_map, "flow_daily": flow_daily, "members": members}

    # 可评分日：满20个资金流日 且 有未来数据
    flow_dates = sorted(d for d in market_days if FUND_START <= d <= END)
    score_dates = flow_dates[MIN_FLOW_DAYS - 1:-1]  # 去掉末日08-28
    print(f"score_dates: {score_dates[0]}..{score_dates[-1]} n={len(score_dates)}", flush=True)

    def build_input(d):
        rows = []
        i = day_idx[d]
        # attention 需要横截面：先算各板块5日均额
        avg5 = {}
        for name, sd in sec_data.items():
            dates_le = [x for x in sd["dates"] if x <= d][-5:]
            avg5[name] = (statistics.fmean([sd["amount"][x] for x in dates_le])
                          if len(dates_le) == 5 else None)
        att_vals = [v for v in avg5.values() if v is not None]
        for name, sd in sec_data.items():
            closes_le = [(x, sd["close"][x]) for x in sd["dates"] if x <= d]
            if len(closes_le) < 21:
                continue
            c_now = closes_le[-1][1]
            def ret(n):
                return (c_now / closes_le[-1 - n][1] - 1) * 100 if closes_le[-1 - n][1] else None
            fd = sorted(x for x in sd["flow_daily"] if x <= d)
            def flow(n):
                sel = fd[-n:]
                if len(sel) < n:
                    return None
                net = sum(sd["flow_daily"][x] * sd["amount"].get(x, 0) for x in sel)
                amt = sum(sd["amount"].get(x, 0) for x in sel)
                return net / amt if amt > 0 else None
            rsi_pct = trailing_pct(sd["dates"], sd["rsi"], d)
            to_pct = trailing_pct(sd["dates"], sd["turnover5"], d)
            sh_pct = trailing_pct(sd["dates"], sd["share5"], d)
            # 广度：当日 vs 前一交易日
            prev_d = market_days[i - 1] if i > 0 else None
            up = obs = 0
            for c in sd["members"]:
                cl = cache["stock_closes"].get(c, {})
                if d in cl and prev_d in cl and cl[prev_d]:
                    obs += 1
                    up += 1 if cl[d] > cl[prev_d] else 0
            breadth = up / obs * 100 if obs else None
            # 5日前拥挤度
            d5 = market_days[i - 5] if i >= 5 else None
            c5 = None
            if d5:
                c5 = crowd_c(trailing_pct(sd["dates"], sd["rsi"], d5),
                             trailing_pct(sd["dates"], sd["turnover5"], d5),
                             trailing_pct(sd["dates"], sd["share5"], d5))
            att = avg_rank_pct(att_vals, avg5[name]) if avg5[name] is not None else None
            rows.append({"name": name, "return_1d": ret(1), "return_5d": ret(5),
                         "return_20d": ret(20), "flow_1d": flow(1), "flow_5d": flow(5),
                         "flow_20d": flow(20), "breadth": breadth, "attention": att,
                         "catalyst": None, "fundamental": None,
                         "rsi_pct": rsi_pct, "turnover_pct": to_pct, "share_pct": sh_pct,
                         "crowding_5d_ago": c5})
        return rows

    def fwd(name, d, h):
        i = day_idx.get(d)
        if i is None or i + h >= len(market_days):
            return None
        d1 = market_days[i + h]
        c0 = sec_data[name]["close"].get(d); c1 = sec_data[name]["close"].get(d1)
        return (c1 / c0 - 1) * 100 if c0 and c1 else None

    daily = []
    for d in score_dates:
        rows = build_input(d)
        if len(rows) < 20:
            print(f"  skip {d}: only {len(rows)} sectors", flush=True)
            continue
        v3 = sector_score.calculate({"sectors": [dict(r) for r in rows]})["sectors"]
        v2 = v2_calculate(rows)
        entry = {"date": d, "v2": v2, "v3": v3}
        daily.append(entry)
        print(f"  scored {d}", flush=True)

    # ---- 验证 ----
    result = {"score_dates": [e["date"] for e in daily], "horizons": {}}
    for h in (1, 5):
        hz = {}
        for ver in ("v2", "v3"):
            ics, top_excess, top_hits, qual_rets, diffs = [], [], [], [], []
            stock_avg, stock_hit_all = [], []
            for e in daily:
                d = e["date"]
                scored = [(s["name"], s["sector_heat"]) for s in e[ver]
                          if s["sector_heat"] is not None and fwd(s["name"], d, h) is not None]
                if len(scored) < 20:
                    continue
                xs = [s[1] for s in scored]
                ys = [fwd(s[0], d, h) for s in scored]
                ic = spearman(xs, ys)
                if ic is not None:
                    ics.append(ic)
                order = sorted(range(len(xs)), key=lambda i: -xs[i])
                top = order[:5]
                top_ret = [ys[i] for i in top]
                uni = sum(ys) / len(ys)
                top_excess.append(sum(top_ret) / 5 - uni)
                top_hits.append(sum(1 for r in top_ret if r > 0) / 5)
                qual = [(n, x) for (n, x) in zip((s[0] for s in scored), xs) if x >= 65]
                if qual:
                    qr = [fwd(n, d, h) for n, _ in qual]
                    qual_rets.append(sum(qr) / len(qr))
                # 个股层：Top5板块成份股等权
                i = day_idx[d]
                if i + h < len(market_days):
                    d1 = market_days[i + h]
                    rets = []
                    for ti in top:
                        name = scored[ti][0]
                        for c in sec_data[name]["members"][:30]:
                            cl = cache["stock_closes"].get(c, {})
                            if d in cl and d1 in cl and cl[d]:
                                rets.append((cl[d1] / cl[d] - 1) * 100)
                    if rets:
                        stock_avg.append(sum(rets) / len(rets))
                        stock_hit_all.append(sum(1 for r in rets if r > 0) / len(rets))
            hz[ver] = {
                "n_days": len(ics),
                "ic_mean": statistics.fmean(ics) if ics else None,
                "ic_t": tstat(ics),
                "icir": (statistics.fmean(ics) / statistics.stdev(ics)) if len(ics) > 1 and statistics.stdev(ics) > 0 else None,
                "ic_positive_ratio": sum(1 for x in ics if x > 0) / len(ics) if ics else None,
                "top5_excess_mean": statistics.fmean(top_excess) if top_excess else None,
                "top5_excess_t": tstat(top_excess),
                "top5_excess_winrate": sum(1 for x in top_excess if x > 0) / len(top_excess) if top_excess else None,
                "top5_hit": statistics.fmean(top_hits) if top_hits else None,
                "qualified_avg_ret": statistics.fmean(qual_rets) if qual_rets else None,
                "qualified_days": len(qual_rets),
                "stock_avg_ret": statistics.fmean(stock_avg) if stock_avg else None,
                "stock_hit": statistics.fmean(stock_hit_all) if stock_hit_all else None,
            }
        # 配对差异：同一日 V3-V2 Top5超额 之差
        paired = []
        for e in daily:
            d = e["date"]
            per = {}
            for ver in ("v2", "v3"):
                scored = [(s["name"], s["sector_heat"]) for s in e[ver]
                          if s["sector_heat"] is not None and fwd(s["name"], d, h) is not None]
                if len(scored) < 20:
                    break
                xs = [s[1] for s in scored]; ys = [fwd(s[0], d, h) for s in scored]
                order = sorted(range(len(xs)), key=lambda i: -xs[i])
                uni = sum(ys) / len(ys)
                per[ver] = sum(ys[i] for i in order[:5]) / 5 - uni
            if len(per) == 2:
                paired.append(per["v3"] - per["v2"])
        hz["paired_v3_minus_v2"] = {
            "n": len(paired),
            "mean_diff": statistics.fmean(paired) if paired else None,
            "t": tstat(paired),
            "win": sum(1 for x in paired if x > 0) / len(paired) if paired else None,
        }
        result["horizons"][f"T+{h}"] = hz

    json.dump(result, open(REPORT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ---- 报告 ----
    L = [f"# V2 vs V3 大样本前瞻回测（{result['score_dates'][0]} ~ {result['score_dates'][-1]}，"
         f"共{len(result['score_dates'])}个评分日）", ""]
    L.append("口径：离线重建历史输入（成分股名单以08-28为准），T+N=评分日收盘后N个交易日收益。")
    L.append("")
    for hname, hz in result["horizons"].items():
        L.append(f"## {hname}")
        L.append("| 指标 | V2 | V3 |")
        L.append("|---|---:|---:|")
        rows = [("样本天数", "n_days", "{:.0f}"), ("IC均值(Spearman)", "ic_mean", "{:+.4f}"),
                ("IC t值", "ic_t", "{:+.2f}"), ("ICIR", "icir", "{:+.3f}"),
                ("IC>0占比", "ic_positive_ratio", "{:.0%}"),
                ("Top5超额均值%", "top5_excess_mean", "{:+.3f}"),
                ("Top5超额t值", "top5_excess_t", "{:+.2f}"),
                ("Top5超额胜率", "top5_excess_winrate", "{:.0%}"),
                ("Top5上涨胜率", "top5_hit", "{:.0%}"),
                ("过线板块平均收益%", "qualified_avg_ret", "{:+.3f}"),
                ("有过线板块天数", "qualified_days", "{:.0f}"),
                ("个股层平均收益%", "stock_avg_ret", "{:+.3f}"),
                ("个股层胜率", "stock_hit", "{:.0%}")]
        for label, key, fmt in rows:
            v2v = hz["v2"].get(key); v3v = hz["v3"].get(key)
            L.append(f"| {label} | {fmt.format(v2v) if v2v is not None else '-'} "
                     f"| {fmt.format(v3v) if v3v is not None else '-'} |")
        p = hz["paired_v3_minus_v2"]
        L.append("")
        L.append(f"配对检验（V3−V2 Top5超额，n={p['n']}）：均值 "
                 f"{p['mean_diff']:+.3f}%，t={p['t']:+.2f}，V3胜出占比 {p['win']:.0%}"
                 if p["mean_diff"] is not None else "配对样本不足")
        L.append("")
    open(REPORT_MD, "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
