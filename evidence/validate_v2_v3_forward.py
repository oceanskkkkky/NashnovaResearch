# -*- coding: utf-8 -*-
"""
V2 vs V3 评分前瞻收益验证：
- 用 2026-08-24..08-27 的板块评分，对照其后至 08-28 的真实板块涨跌
- 指标：Spearman/Pearson IC、Top5-Bottom5 价差、Top5 胜率与超额
- 个股层：对各版 Top5 板块成份股做等权前瞻收益验证
输出：evidence/2026-08-29-v2-vs-v3-validation.md + validation JSON
"""
import json
import math
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "evidence")
PACKAGE = "westock-data-skillhub@1.0.5"
SCORE_DATES = ["2026-08-24", "2026-08-25", "2026-08-26", "2026-08-27"]
END_DATE = "2026-08-28"
KLINE_START = "2026-08-18"
RAW_OUT = os.path.join(EV, "2026-08-29-validation-klines.json")
REPORT_OUT = os.path.join(EV, "2026-08-29-v2-vs-v3-validation.md")


def westock(*args, retries=2):
    cmdline = subprocess.list2cmdline(["npx", "-y", PACKAGE, *args])
    last = None
    for attempt in range(retries + 1):
        p = subprocess.run(["cmd.exe", "/d", "/c", cmdline],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode == 0 and p.stdout.strip():
            return json.loads(p.stdout)
        last = (p.stderr or p.stdout or "")[-500:]
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"westock failed: {args}: {last}")


def normalize_klines(obj):
    """返回 {code: {date: close}}；多代码返回为带 symbol 的扁平记录列表"""
    out = {}
    if isinstance(obj, dict):
        for key, val in obj.items():
            if isinstance(val, list):
                for r in val:
                    if isinstance(r, dict) and "date" in r and r.get("last") is not None:
                        out.setdefault(r.get("symbol") or key, {})[r["date"]] = float(r["last"])
        return out
    if isinstance(obj, list):
        for r in obj:
            if isinstance(r, dict) and "date" in r and r.get("last") is not None:
                code = r.get("symbol") or r.get("code") or "__single__"
                out.setdefault(code, {})[r["date"]] = float(r["last"])
    return out


def fetch_klines(codes, start, end, cache, label):
    missing = [c for c in codes if c not in cache]
    if missing:
        print(f"  fetch {label}: {len(missing)} codes", flush=True)
        for i in range(0, len(missing), 40):
            batch = missing[i:i + 40]
            data = westock("kline", ",".join(batch), "--period", "day",
                           "--start", start, "--end", end, "--raw")
            parsed = normalize_klines(data)
            if "__single__" in parsed and len(batch) == 1:
                parsed[batch[0]] = parsed.pop("__single__")
            cache.update(parsed)
    return cache


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
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    return cov / math.sqrt(vx * vy)


def spearman(xs, ys):
    return pearson(ranks(xs), ranks(ys))


def fwd_return(closes, d0, d1):
    if d0 in closes and d1 in closes and closes[d0]:
        return (closes[d1] / closes[d0] - 1) * 100
    return None


def main():
    trade_days = ["2026-08-21", "2026-08-24", "2026-08-25",
                  "2026-08-26", "2026-08-27", "2026-08-28"]

    inp = json.load(open(os.path.join(EV, "2026-08-28-sector-input-v2.json"), encoding="utf-8"))
    sectors = [(s["name"], s["code"]) for s in inp["sectors"]]
    code2name = dict((c, n) for n, c in sectors)

    cache = {}
    if os.path.exists(RAW_OUT):
        cache = json.load(open(RAW_OUT, encoding="utf-8")).get("closes", {})

    print("[1] 板块K线", flush=True)
    fetch_klines([c for _, c in sectors], KLINE_START, END_DATE, cache, "sector")

    sector_closes = {code2name.get(c, c): v for c, v in cache.items() if c in code2name}

    # ---- 板块层验证 ----
    results = {"sector_level": {}, "constituent_level": {}}
    top5_union = set()
    for d in SCORE_DATES:
        i0 = trade_days.index(d)
        horizons = {"T+1": trade_days[i0 + 1], "T+end": END_DATE}
        day_res = {}
        for ver in ("v2", "v3"):
            sc = json.load(open(os.path.join(EV, f"{d}-sector-score-{ver}.json"), encoding="utf-8"))
            scores = {s["name"]: s["sector_heat"] for s in sc["sectors"]
                      if s.get("sector_heat") is not None}
            top5 = [s["name"] for s in sc["sectors"] if s.get("sector_heat") is not None][:5]
            top5_union.update(top5)
            for hname, d1 in horizons.items():
                names, xs, ys = [], [], []
                for n, v in scores.items():
                    fr = fwd_return(sector_closes.get(n, {}), d, d1)
                    if fr is not None:
                        names.append(n); xs.append(v); ys.append(fr)
                order = sorted(range(len(xs)), key=lambda i: -xs[i])
                top_idx, bot_idx = order[:5], order[-5:]
                top_ret = [ys[i] for i in top_idx]
                bot_ret = [ys[i] for i in bot_idx]
                uni_mean = sum(ys) / len(ys)
                day_res.setdefault(ver, {})[hname] = {
                    "n": len(xs),
                    "ic_spearman": spearman(xs, ys),
                    "ic_pearson": pearson(xs, ys),
                    "top5_names": [names[i] for i in top_idx],
                    "top5_avg_ret": sum(top_ret) / len(top_ret),
                    "bot5_avg_ret": sum(bot_ret) / len(bot_ret),
                    "spread": sum(top_ret) / len(top_ret) - sum(bot_ret) / len(bot_ret),
                    "top5_hit": sum(1 for r in top_ret if r > 0) / len(top_ret),
                    "universe_avg_ret": uni_mean,
                    "top5_excess": sum(top_ret) / len(top_ret) - uni_mean,
                }
        results["sector_level"][d] = day_res

    # ---- 个股层验证：Top5 并集板块成份股等权前瞻收益 ----
    print("[2] 成份股K线", flush=True)
    raws = {}
    for d in ["2026-08-28"]:
        raws[d] = json.load(open(os.path.join(EV, f"{d}-sector-raw-v2.json"), encoding="utf-8"))
    consti_map = {}
    for s in raws["2026-08-28"]["sectors"]:
        if s["name"] in top5_union:
            codes = [c for c in s["constituents"]["codes"]
                     if c[:2].lower() in ("sh", "sz")][:30]
            consti_map[s["name"]] = codes
    all_codes = sorted({c for codes in consti_map.values() for c in codes})
    fetch_klines(all_codes, KLINE_START, END_DATE, cache, "constituent")
    json.dump({"closes": cache}, open(RAW_OUT, "w", encoding="utf-8"), ensure_ascii=False)

    for d in SCORE_DATES:
        i0 = trade_days.index(d)
        d1 = END_DATE
        uni_rets = []
        for n, closes in sector_closes.items():
            fr = fwd_return(closes, d, d1)
            if fr is not None:
                uni_rets.append(fr)
        uni_mean = sum(uni_rets) / len(uni_rets)
        for ver in ("v2", "v3"):
            sc = json.load(open(os.path.join(EV, f"{d}-sector-score-{ver}.json"), encoding="utf-8"))
            top5 = [s["name"] for s in sc["sectors"] if s.get("sector_heat") is not None][:5]
            stock_rets = []
            per_sector = {}
            for n in top5:
                rets = []
                for c in consti_map.get(n, []):
                    fr = fwd_return(cache.get(c, {}), d, d1)
                    if fr is not None:
                        rets.append(fr)
                if rets:
                    per_sector[n] = {"n": len(rets),
                                     "avg": sum(rets) / len(rets),
                                     "hit": sum(1 for r in rets if r > 0) / len(rets)}
                    stock_rets.extend(rets)
            if stock_rets:
                results["constituent_level"].setdefault(d, {})[ver] = {
                    "top5": top5,
                    "stock_count": len(stock_rets),
                    "avg_ret": sum(stock_rets) / len(stock_rets),
                    "hit": sum(1 for r in stock_rets if r > 0) / len(stock_rets),
                    "excess_vs_sector_universe": sum(stock_rets) / len(stock_rets) - uni_mean,
                    "per_sector": per_sector,
                }

    json.dump(results, open(os.path.join(EV, "2026-08-29-v2-vs-v3-validation.json"), "w",
                            encoding="utf-8"), ensure_ascii=False, indent=2)

    # ---- 汇总报告 ----
    L = ["# V2 vs V3 前瞻收益验证（评分日 08-24~08-27，验证至 08-28）", ""]
    for d in SCORE_DATES:
        L.append(f"## 评分日 {d}")
        for hname in ("T+1", "T+end"):
            L.append(f"### 板块层 {hname}")
            L.append("| 版本 | IC(Spearman) | IC(Pearson) | Top5收益% | Bottom5收益% | 价差% | Top5胜率 | 超额% |")
            L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
            for ver in ("v2", "v3"):
                r = results["sector_level"][d][ver][hname]
                ic_s = f"{r['ic_spearman']:+.3f}" if r["ic_spearman"] is not None else "-"
                ic_p = f"{r['ic_pearson']:+.3f}" if r["ic_pearson"] is not None else "-"
                L.append(f"| {ver.upper()} | {ic_s} | {ic_p} | {r['top5_avg_ret']:+.2f} | "
                         f"{r['bot5_avg_ret']:+.2f} | {r['spread']:+.2f} | "
                         f"{r['top5_hit']*100:.0f}% | {r['top5_excess']:+.2f} |")
            L.append("")
        cl = results["constituent_level"].get(d, {})
        if cl:
            L.append("### 个股层（Top5板块成份股等权，至08-28）")
            L.append("| 版本 | 样本股数 | 平均收益% | 胜率 | 对板块池超额% |")
            L.append("|---|---:|---:|---:|---:|")
            for ver in ("v2", "v3"):
                r = cl.get(ver)
                if r:
                    L.append(f"| {ver.upper()} | {r['stock_count']} | {r['avg_ret']:+.2f} | "
                             f"{r['hit']*100:.0f}% | {r['excess_vs_sector_universe']:+.2f} |")
            L.append("")

    # 汇总均值
    L.append("## 汇总均值")
    L.append("| 指标 | V2 | V3 |")
    L.append("|---|---:|---:|")
    for hname in ("T+1", "T+end"):
        for key, label in (("ic_spearman", f"IC(Spearman) {hname}"),
                           ("top5_excess", f"Top5超额% {hname}"),
                           ("top5_hit", f"Top5胜率 {hname}"),
                           ("spread", f"价差% {hname}")):
            vals = {}
            for ver in ("v2", "v3"):
                xs = [results["sector_level"][d][ver][hname][key]
                      for d in SCORE_DATES
                      if results["sector_level"][d][ver][hname][key] is not None]
                vals[ver] = sum(xs) / len(xs) if xs else None
            f = (lambda v: f"{v:+.3f}" if v is not None and abs(v) < 10 else
                 (f"{v:+.2f}" if v is not None else "-"))
            if key == "top5_hit":
                f = lambda v: f"{v*100:.0f}%" if v is not None else "-"
            L.append(f"| {label} | {f(vals['v2'])} | {f(vals['v3'])} |")
    for key, label in (("avg_ret", "个股层平均收益%"), ("hit", "个股层胜率"),
                       ("excess_vs_sector_universe", "个股层超额%")):
        vals = {}
        for ver in ("v2", "v3"):
            xs = [results["constituent_level"][d][ver][key]
                  for d in SCORE_DATES if ver in results["constituent_level"].get(d, {})]
            vals[ver] = sum(xs) / len(xs) if xs else None
        if key == "hit":
            f = lambda v: f"{v*100:.0f}%" if v is not None else "-"
        else:
            f = lambda v: f"{v:+.2f}" if v is not None else "-"
        L.append(f"| {label} | {f(vals['v2'])} | {f(vals['v3'])} |")

    open(REPORT_OUT, "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
