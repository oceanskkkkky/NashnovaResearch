from __future__ import annotations

import json
from pathlib import Path

TARGET = "2026-08-28"
P = Path(f"E:/WS/NashnovaResearch/evidence/{TARGET}-stock-deep-raw.json")
OUT = Path(f"E:/WS/NashnovaResearch/evidence/{TARGET}-stock-deep-summary.json")


def flatten(x):
    out = []
    if isinstance(x, list):
        for y in x:
            out.extend(flatten(y))
    elif isinstance(x, dict):
        if isinstance(x.get("sections"), list):
            out.extend(flatten(x["sections"]))
        elif isinstance(x.get("item"), list):
            out.extend(flatten(x["item"]))
        elif isinstance(x.get("data"), list):
            out.extend(flatten(x["data"]))
        elif isinstance(x.get("data"), dict) and isinstance(x["data"].get("item"), list):
            out.extend(flatten(x["data"]["item"]))
        else:
            out.append(x)
    return out


def normalize_code(value):
    raw = str(value or "").strip().lower()
    if raw.startswith(("sh", "sz")) and len(raw) >= 8:
        return raw[:8]
    if raw.endswith((".sh", ".sz")):
        ticker, market = raw.split(".", 1)
        return f"{market}{ticker}"
    if raw.isdigit() and len(raw) == 6:
        return ("sh" if raw.startswith(("5", "6", "9")) else "sz") + raw
    return raw


def main():
    d = json.loads(P.read_text(encoding="utf-8"))
    codes = d["codes"]
    fin = flatten(d["finance"].get("data")) if d["finance"]["ok"] else []
    risk = flatten(d["risk"].get("data")) if d["risk"]["ok"] else []
    reports = flatten(d["reports"].get("data")) if d["reports"]["ok"] else []
    notices = flatten(d["notices"].get("data")) if d["notices"]["ok"] else []
    val = flatten(d["valuation"].get("data", {}).get("data")) if d["valuation"]["ok"] else []
    result = {}
    for code in codes:
        def related(rows):
            return [r for r in rows if normalize_code(r.get("code") or r.get("symbol") or r.get("SecuCode") or r.get("thscode") or r.get("ticker")) == normalize_code(code)]
        fs = related(fin)
        fs.sort(key=lambda r: str(r.get("date") or r.get("_date") or r.get("EndDate") or ""), reverse=True)
        latest = fs[0] if fs else {}
        keep_fin = {k: latest.get(k) for k in ["date", "EndDate", "InfoPublDate", "OperatingRevenue", "OperatingRevenueTTM", "NPParentCompanyOwners", "NPParentCompanyOwnersTTM", "BasicEPS", "NetCashFlowFromOperating", "TotalAssets", "TotalLiability"] if k in latest}
        rr, rp, nn, vv = related(risk), related(reports), related(notices), related(val)
        result[code] = {
            "finance_latest": keep_fin,
            "finance_rows": len(fs),
            "risks_count": len(rr),
            "risks": rr[:12],
            "reports_count": len(rp),
            "reports": [{k: r.get(k) for k in r if any(x in k.lower() for x in ["title", "date", "time", "rating", "target", "id", "org", "author"])} for r in rp[:5]],
            "notices_count": len(nn),
            "notices": [{k: r.get(k) for k in r if any(x in k.lower() for x in ["title", "date", "time", "type", "id"])} for r in nn[:10]],
            "valuation": vv[:3],
        }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
