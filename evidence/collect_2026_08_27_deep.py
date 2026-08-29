from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path("E:/WS/NashnovaResearch")
EVIDENCE = ROOT / "evidence"
TARGET = "2026-08-27"
CANDIDATES = json.loads((EVIDENCE / f"{TARGET}-stock-candidates.json").read_text(encoding="utf-8"))
TOP = CANDIDATES["candidate_pool"][:5]
CODES = [row["code"] for row in TOP]
THSCODES = [row["a_share_code"] for row in TOP]

spec = importlib.util.spec_from_file_location("daily_data", EVIDENCE / "build_2026_08_27_data.py")
daily = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(daily)


def safe(fn):
    try:
        return {"ok": True, "data": fn()}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def main():
    csv = ",".join(CODES)
    ths = ",".join(THSCODES)
    payload = {
        "as_of_date": TARGET,
        "codes": CODES,
        "top_candidates": [{"code": row["code"], "name": row["name"], "sector": row["sector_name"]} for row in TOP],
        "finance": safe(lambda: daily.westock("finance", csv, "--num", "4", "--raw")),
        "risk": safe(lambda: daily.westock("risk", csv, "--raw")),
        "reports": safe(lambda: daily.westock("report", "list", csv, "--limit", "5", "--raw")),
        "notices": safe(lambda: daily.westock("notice", "list", csv, "--limit", "10", "--raw")),
        "valuation": safe(lambda: daily.hithink("valuation", "snapshot", "--thscodes", ths, "--format", "json")),
        "commands": daily.COMMANDS,
        "failures": daily.FAILURES,
    }
    out = EVIDENCE / f"{TARGET}-stock-deep-raw.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "top": payload["top_candidates"], "status": {k: v.get("ok") for k, v in payload.items() if isinstance(v, dict) and "ok" in v}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
