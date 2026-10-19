"""Rank 10 major Korean stocks using verified daily program-trading CSVs.

Input: data/program_trading/{ticker}.csv
Required columns: date, close_krw, program_net_krw
Optional columns: foreign_net_krw, institution_net_krw, program_buy_krw, program_sell_krw
All flow amounts must be KRW, not shares or thousand-KRW.
"""
import json
from pathlib import Path
import pandas as pd

STOCKS={"005930":"삼성전자","000660":"SK하이닉스","005380":"현대차",
"000270":"기아","035420":"NAVER","068270":"셀트리온",
"105560":"KB금융","055550":"신한지주",
"012450":"한화에어로스페이스","373220":"LG에너지솔루션"}
ROOT=Path("data/program_trading")
OUT=Path("site/program_trading")
OUT.mkdir(parents=True,exist_ok=True)
results=[];errors=[]
for code,name in STOCKS.items():
    path=ROOT/f"{code}.csv"
    if not path.exists():
        errors.append({"code":code,"reason":"missing daily CSV"})
        continue
    try:
        df=pd.read_csv(path,dtype={"date":str})
        needed={"date","close_krw","program_net_krw"}
        if not needed.issubset(df.columns):raise ValueError("missing required columns")
        df["date"]=pd.to_datetime(df["date"],errors="raise")
        if df["date"].duplicated().any():raise ValueError("duplicate dates")
        for col in needed-{"date"}:
            df[col]=pd.to_numeric(df[col],errors="raise")
        if (df["close_krw"]<=0).any():raise ValueError("invalid prices")
        df=df.sort_values("date")
        if len(df)<20:raise ValueError("fewer than 20 trading days")
        row={"code":code,"name":name,"first_date":df["date"].iloc[0].date().isoformat(),
        "last_date":df["date"].iloc[-1].date().isoformat(),"trading_days":len(df)}
        for days in (5,20,60,120,240):
            sample=df.tail(days)
            if len(sample)<days:continue
            row[f"program_net_{days}d_krw"]=int(sample["program_net_krw"].sum())
            row[f"program_buy_days_{days}d"]=int((sample["program_net_krw"]>0).sum())
            if len(df)>days:
                row[f"price_return_{days}d_pct"]=round((df["close_krw"].iloc[-1]/df["close_krw"].iloc[-days-1]-1)*100,3)
        if len(df)>=21:
            daily_return=df["close_krw"].pct_change()
            row["program_price_corr_20d"]=round(float(df["program_net_krw"].tail(20).corr(daily_return.tail(20))),4) if df["program_net_krw"].tail(20).nunique()>1 else None
        for col in ("foreign_net_krw","institution_net_krw"):
            if col in df:
                series=pd.to_numeric(df[col],errors="raise")
                row[col.replace("_net_krw","_20d_net_krw")]=int(series.tail(20).sum())
        results.append(row)
    except Exception as exc:
        errors.append({"code":code,"reason":str(exc)})
results.sort(key=lambda r:r.get("program_net_20d_krw",float("-inf")),reverse=True)
report={"source":"verified user-provided daily KIS/KRX exports","units":"KRW",
"scope":"program trades; not equivalent to all foreign or institution trades",
"coverage":len(results),"target":len(STOCKS),"stocks":results,"errors":errors,
"warning":"Co-movement does not prove coordinated trading or manipulation."}
(OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
print(f"VALIDATED {len(results)}/{len(STOCKS)} stocks; missing/invalid={len(errors)}")
if not results:raise SystemExit("No verified program-trading data; refusing to publish invented rankings")
