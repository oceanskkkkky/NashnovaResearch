from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path("E:/WS/NashnovaResearch")
EVIDENCE = ROOT / "evidence"
TARGET = "2026-08-26"
CODES = ["sh601212", "sz000603", "sz000426", "sz300328", "sh601020"]
THSCODES = ["601212.SH", "000603.SZ", "000426.SZ", "300328.SZ", "601020.SH"]

spec = importlib.util.spec_from_file_location("daily_data", EVIDENCE / "build_2026_08_26_data.py")
daily = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(daily)


def safe(label, fn):
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
        "finance": safe("finance", lambda: daily.westock("finance", csv, "--num", "4", "--raw")),
        "risk": safe("risk", lambda: daily.westock("risk", csv, "--raw")),
        "reports": safe("reports", lambda: daily.westock("report", "list", csv, "--limit", "5", "--raw")),
        "notices": safe("notices", lambda: daily.westock("notice", "list", csv, "--limit", "10", "--raw")),
        "valuation": safe("valuation", lambda: daily.hithink("valuation", "snapshot", "--thscodes", ths, "--format", "json")),
        "commands": daily.COMMANDS,
        "failures": daily.FAILURES,
    }
    out = EVIDENCE / "2026-08-26-stock-deep-raw.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "status": {k: v.get("ok") for k, v in payload.items() if isinstance(v, dict) and "ok" in v}, "failures": daily.FAILURES}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
