"""Import independently downloaded KRX investor data without KRX login/API.
Place CSV files in data/foreign_cycle_import/<ticker>.csv.
Columns: date,close_krw,foreign_net_krw,institution_net_krw[,pension_category_net_krw]
Amounts MUST be KRW, net purchases signed (+ buy, - sell).
"""
import json
import datetime as dt
from pathlib import Path
import pandas as pd

SRC=Path("data/foreign_cycle_import")
OUT=Path("site/foreign_cycle")
OUT.mkdir(parents=True,exist_ok=True)
errors=[]; stocks=[]
for p in sorted(SRC.glob("*.csv")) if SRC.exists() else []:
    try:
        if not (p.stem.isdigit() and len(p.stem)==6): raise ValueError("expected six-digit ticker filename")
        df=pd.read_csv(p,encoding="utf-8-sig",dtype={"date":str})
        required=["date","close_krw","foreign_net_krw","institution_net_krw"]
        if any(c not in df.columns for c in required): raise ValueError("required columns missing")
        df["date"]=pd.to_datetime(df["date"],errors="raise")
        for c in required[1:]:
            df[c]=pd.to_numeric(df[c],errors="raise")
        if "pension_category_net_krw" not in df:
            df["pension_category_net_krw"]=float("nan")
        else:
            df["pension_category_net_krw"]=pd.to_numeric(df["pension_category_net_krw"],errors="coerce")
        df=df.sort_values("date").drop_duplicates("date",keep="last")
        if len(df)<120: raise ValueError("need at least 120 trading-day records")
        if (df["close_krw"]<=0).any(): raise ValueError("invalid closing prices")
        for w in [5,20,60,120]:
            df[f"foreign_{w}d_net_krw"]=df["foreign_net_krw"].rolling(w).sum()
            df[f"institution_{w}d_net_krw"]=df["institution_net_krw"].rolling(w).sum()
            df[f"price_return_{w}d_pct"]=(df["close_krw"]/df["close_krw"].shift(w)-1)*100
        df.to_csv(OUT/f"{p.stem}.csv",index=False,encoding="utf-8-sig")
        latest=df.iloc[-1]
        stocks.append({"code":p.stem,"asof":str(latest["date"].date()),"trading_days":len(df),
                       "foreign_20d_net_krw":int(latest["foreign_20d_net_krw"]),
                       "foreign_60d_net_krw":int(latest["foreign_60d_net_krw"]),
                       "institution_20d_net_krw":int(latest["institution_20d_net_krw"]),
                       "source":"user-supplied KRX CSV (requires provenance validation)"})
    except Exception as e: errors.append({"file":p.name,"error":str(e)})
payload={"status":"OK" if stocks and not errors else "PARTIAL" if stocks else "NO_DATA",
         "source":"manual CSV import","stocks":stocks,"errors":errors,
         "warning":"Not NPS-specific, not evidence of collusion. Validate dates, units and original source."}
(OUT/"summary.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
if not stocks: raise SystemExit("No valid imported CSV; refusing to publish invented values.")
