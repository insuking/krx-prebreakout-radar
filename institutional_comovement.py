"""Exploratory institutional/foreign co-movement diagnostics.

Co-movement is NOT evidence of coordination, manipulation, or insider dealing.
Only use observed aligned daily investor-flow CSVs from foreign_capital_cycle.py.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("site/foreign_cycle")
result = {"method": "daily rolling co-movement, not evidence of collusion",
          "warnings": [
              "Foreign and institutional net buys may reflect common macro news, benchmarks or index rebalancing.",
              "Daily aggregated data cannot identify beneficial owners, order intent or non-public communications.",
              "KRX '연기금 등' cannot be attributed solely to the National Pension Service.",
              "All signals are exploratory, not trading instructions."
          ], "stocks": [], "errors": []}

def safe_number(x):
    return None if not np.isfinite(x) else round(float(x), 4)

for path in sorted(ROOT.glob("[0-9]*.csv")):
    try:
        df = pd.read_csv(path, encoding="utf-8-sig", parse_dates=["date"])
        cols = ["date", "close_krw", "foreign_net_krw", "institution_net_krw"]
        if any(c not in df.columns for c in cols):
            raise ValueError("missing required columns")
        df = df[cols].dropna().sort_values("date").drop_duplicates("date")
        if len(df) < 120:
            raise ValueError("at least 120 observations required")
        f = df["foreign_net_krw"].astype(float)
        inst = df["institution_net_krw"].astype(float)
        ret = df["close_krw"].astype(float).pct_change()
        recent = df.tail(60)
        both_buy = int(((recent["foreign_net_krw"] > 0) & (recent["institution_net_krw"] > 0)).sum())
        both_sell = int(((recent["foreign_net_krw"] < 0) & (recent["institution_net_krw"] < 0)).sum())
        opposing = int(((recent["foreign_net_krw"] * recent["institution_net_krw"]) < 0).sum())
        f60 = f.tail(60).reset_index(drop=True)
        i60 = inst.tail(60).reset_index(drop=True)
        # Lead/lag correlation: association only; not causality.
        lag_f_to_i = f60.iloc[:-1].corr(i60.iloc[1:].reset_index(drop=True))
        lag_i_to_f = i60.iloc[:-1].corr(f60.iloc[1:].reset_index(drop=True))
        result["stocks"].append({
            "code": path.stem, "asof": str(df["date"].iloc[-1].date()),
            "observations": len(df), "last_60d_joint_buy_days": both_buy,
            "last_60d_joint_sell_days": both_sell,
            "last_60d_opposite_direction_days": opposing,
            "last_60d_same_day_flow_correlation": safe_number(f60.corr(i60)),
            "last_60d_foreign_to_institution_1d_lag_corr": safe_number(lag_f_to_i),
            "last_60d_institution_to_foreign_1d_lag_corr": safe_number(lag_i_to_f),
            "last_60d_foreign_flow_to_same_day_return_corr":
                safe_number(f.tail(60).corr(ret.tail(60))),
            "interpretation": "OBSERVATIONAL_ONLY_NO_COORDINATION_INFERENCE",
        })
    except Exception as exc:
        result["errors"].append({"file": path.name, "error": str(exc)[:250]})

result["status"] = "OK" if result["stocks"] and not result["errors"] else ("PARTIAL" if result["stocks"] else "NO_DATA")
ROOT.mkdir(parents=True, exist_ok=True)
(ROOT / "comovement_diagnostics.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
if not result["stocks"]:
    raise SystemExit("No validated investor-flow data available")
