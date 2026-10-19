"""Daily foreign/institutional capital-cycle collector.
Data are NEVER synthesized. Missing investor breakdown is explicitly flagged.
Requires pykrx (KRX data endpoints may change or throttle).
"""
from __future__ import annotations
import datetime as dt
import json
import os
import time
from pathlib import Path
import pandas as pd
from pykrx import stock

CODES = {
    "005930": "삼성전자", "000660": "SK하이닉스",
    "005380": "현대차", "000270": "기아", "035420": "NAVER",
    "068270": "셀트리온", "105560": "KB금융", "055550": "신한지주",
    "012450": "한화에어로스페이스", "373220": "LG에너지솔루션",
}
KST = dt.timezone(dt.timedelta(hours=9))
END = dt.datetime.now(KST).date()
START = END - dt.timedelta(days=430)
ROOT = Path("site/foreign_cycle")
ROOT.mkdir(parents=True, exist_ok=True)
errors = []
summary = []

def normalize_index(df):
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    return df.sort_index()

def fetch_one(code, name):
    a, b = START.strftime("%Y%m%d"), END.strftime("%Y%m%d")
    price = normalize_index(stock.get_market_ohlcv_by_date(a, b, code))
    flow = normalize_index(stock.get_market_trading_value_by_date(a, b, code))
    if price.empty or flow.empty:
        raise ValueError("price or investor-flow series empty")
    required = ["종가", "거래량"]
    if any(c not in price.columns for c in required):
        raise ValueError("OHLCV columns changed")
    # KRX aggregates '기관합계'; '연기금 등' is a category, NOT NPS-only.
    foreign = next((c for c in ["외국인", "외국인합계"] if c in flow.columns), None)
    institutional = next((c for c in ["기관합계", "기관"] if c in flow.columns), None)
    pension = next((c for c in ["연기금 등", "연기금"] if c in flow.columns), None)
    if not foreign or not institutional:
        raise ValueError(f"required investor columns missing: {list(flow.columns)}")
    df = pd.DataFrame(index=price.index)
    df["close_krw"] = pd.to_numeric(price["종가"], errors="coerce")
    df["volume_shares"] = pd.to_numeric(price["거래량"], errors="coerce")
    df["foreign_net_krw"] = pd.to_numeric(flow[foreign], errors="coerce")
    df["institution_net_krw"] = pd.to_numeric(flow[institutional], errors="coerce")
    df["pension_category_net_krw"] = pd.to_numeric(flow[pension], errors="coerce") if pension else float("nan")
    df = df.dropna(subset=["close_krw", "foreign_net_krw", "institution_net_krw"])
    df = df[df["close_krw"] > 0]
    if len(df) < 60:
        raise ValueError(f"insufficient aligned trading days: {len(df)}")
    for window in [5, 20, 60, 120]:
        df[f"foreign_{window}d_net_krw"] = df["foreign_net_krw"].rolling(window, min_periods=window).sum()
        df[f"institution_{window}d_net_krw"] = df["institution_net_krw"].rolling(window, min_periods=window).sum()
        df[f"price_return_{window}d_pct"] = (df["close_krw"] / df["close_krw"].shift(window) - 1) * 100
    df.index.name = "date"
    df.to_csv(ROOT / f"{code}.csv", encoding="utf-8-sig", float_format="%.4f")
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    f20 = latest["foreign_20d_net_krw"]
    f60 = latest["foreign_60d_net_krw"]
    prev20 = prev["foreign_20d_net_krw"]
    # Signal requires persistent accumulation, not one positive day.
    if pd.notna(f20) and pd.notna(f60) and f20 > 0 and f60 > 0:
        phase = "MULTI_HORIZON_INFLOW"
    elif pd.notna(f20) and pd.notna(prev20) and f20 > prev20 and latest["foreign_net_krw"] > 0:
        phase = "EARLY_IMPROVEMENT_UNCONFIRMED"
    else:
        phase = "NO_CONFIRMED_INFLOW"
    return {
        "code": code, "name": name, "asof": str(df.index[-1].date()),
        "trading_days": len(df), "phase": phase,
        "close_krw": int(latest["close_krw"]),
        "foreign_5d_net_krw": None if pd.isna(latest["foreign_5d_net_krw"]) else int(latest["foreign_5d_net_krw"]),
        "foreign_20d_net_krw": None if pd.isna(f20) else int(f20),
        "foreign_60d_net_krw": None if pd.isna(f60) else int(f60),
        "foreign_120d_net_krw": None if pd.isna(latest["foreign_120d_net_krw"]) else int(latest["foreign_120d_net_krw"]),
        "institution_20d_net_krw": None if pd.isna(latest["institution_20d_net_krw"]) else int(latest["institution_20d_net_krw"]),
        "pension_category_20d_net_krw": None if pd.isna(df["pension_category_net_krw"].tail(20).sum(min_count=20)) else int(df["pension_category_net_krw"].tail(20).sum()),
        "pension_disclaimer": "KRX 연기금 등 category is NOT National Pension Service-specific trading",
        "foreign_ownership_available": False,
        "quota_attribution": "NOT_IDENTIFIABLE_FROM_TRADING_FLOWS",
    }

for code, name in CODES.items():
    try:
        summary.append(fetch_one(code, name))
        print("OK", code, name)
    except Exception as exc:
        errors.append({"code": code, "name": name, "error": str(exc)[:300]})
        print("ERROR", code, str(exc)[:200])
    time.sleep(1.0)
payload = {
    "generated_at_kst": dt.datetime.now(KST).isoformat(),
    "start_requested": START.isoformat(), "end_requested": END.isoformat(),
    "source": "pykrx/KRX public data",
    "units": "KRW; positive=net buy, negative=net sell",
    "status": "OK" if len(summary) == len(CODES) else ("PARTIAL" if summary else "FAILED"),
    "successful": len(summary), "requested": len(CODES),
    "stocks": summary, "errors": errors,
    "warning": "Historical public KRX investor groups do not disclose each fund's country quota or identify NPS trades individually. Not an order signal.",
}
(ROOT / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
if not summary:
    raise SystemExit("No valid investor series collected; do not publish success.")
