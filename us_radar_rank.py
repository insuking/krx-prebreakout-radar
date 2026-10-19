"""Evidence-gated US pre-breakout ranking. No trading orders.

Reads site/us_radar/*.csv, writes site/us_radar/recommendations.json.
A WATCH signal is not a verified intraday BUY signal.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import numpy as np
import pandas as pd

ROOT=Path("site/us_radar")
ROOT.mkdir(parents=True,exist_ok=True)
summary_file=ROOT/"summary.json"
if not summary_file.exists():raise SystemExit("Missing KIS source summary")
summary=json.loads(summary_file.read_text(encoding="utf-8"))
records=[]
for meta in summary.get("stocks",[]):
    symbol=meta["symbol"]
    path=ROOT/(symbol.replace(".","_")+".csv")
    if not path.exists():continue
    try:
        d=pd.read_csv(path)
        if not {"date","close_usd","volume_shares"}.issubset(d):continue
        d["date"]=pd.to_datetime(d["date"],errors="raise")
        if d["date"].duplicated().any():continue
        d=d.sort_values("date")
        c=pd.to_numeric(d["close_usd"],errors="raise")
        v=pd.to_numeric(d["volume_shares"],errors="raise")
        if len(d)<121 or (c<=0).any() or (v<0).any():continue
        if d["date"].iloc[-1].date().isoformat()!=meta["asof"]:continue
        ret=c.pct_change()
        daily_vol=ret.rolling(20).std()
        compression=float(daily_vol.iloc[-1]/daily_vol.iloc[-61:-20].median()) if daily_vol.iloc[-61:-20].median()>0 else 99.
        ma20=float(c.iloc[-20:].mean());ma60=float(c.iloc[-60:].mean())
        rvol=float(v.iloc[-1]/v.iloc[-21:-1].mean()) if v.iloc[-21:-1].mean()>0 else 0.
        high20=float(c.iloc[-21:-1].max())
        distance=(float(c.iloc[-1])/high20-1)*100
        momentum20=(float(c.iloc[-1])/float(c.iloc[-21])-1)*100
        momentum60=(float(c.iloc[-1])/float(c.iloc[-61])-1)*100
        liquid=float((c.iloc[-20:]*v.iloc[-20:]).mean())
        # All scores use information available at the last daily close.
        score=(20 if ma20>ma60 else 0)+(20 if c.iloc[-1]>ma20 else 0)
        score+=20 if 0.65<=compression<=1.0 else (10 if compression<1.3 else 0)
        score+=20 if rvol>=1.5 else (10 if rvol>=1.1 else 0)
        score+=20 if 0<=momentum20<=15 else (10 if -3<=momentum20<0 else 0)
        chase_risk= (35 if distance>8 else 15 if distance>3 else 0)
        chase_risk+=25 if rvol>4 else 0
        chase_risk+=25 if momentum20>25 else 0
        chase_risk+=15 if compression>2 else 0
        price=float(c.iloc[-1])
        stop=round(min(ma20,price*0.94),2)
        risk=price-stop
        target=round(price+2*risk,2)
        eligible=bool(score>=70 and chase_risk<=35 and liquid>=5_000_000 and risk>0)
        records.append({"symbol":symbol,"name":meta["name"],"exchange":meta["exchange"],
        "asof":meta["asof"],"last_close_usd":round(price,4),
        "prebreakout_score":score,"chase_risk_score":chase_risk,
        "rvol":round(rvol,3),"volatility_compression_ratio":round(compression,3),
        "momentum_20d_pct":round(momentum20,3),"momentum_60d_pct":round(momentum60,3),
        "average_dollar_volume_20d":round(liquid),
        "reference_entry_usd":round(price,2),"reference_stop_usd":stop,
        "reference_target_2r_usd":target,"signal":"WATCH" if eligible else "PASS",
        "entry_status":"NOT_VERIFIED_INTRADAY","trade_execution_enabled":False,
        "reason":"Reference levels based on historical close; intraday confirmation required."})
    except Exception as exc:
        print("SKIP",symbol,type(exc).__name__,str(exc)[:100])
records.sort(key=lambda r:(r["signal"]=="WATCH",r["prebreakout_score"],-r["chase_risk_score"]),reverse=True)
out={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"market":"US",
"source":"KIS overseas daily historical prices; no verified live quotes",
"eligible_watch_count":sum(r["signal"]=="WATCH" for r in records),
"scored_count":len(records),"universe_count":summary.get("symbols_target"),
"data_asof":max((r["asof"] for r in records),default=None),
"status":"RESEARCH_ONLY","recommendations":records,
"limitations":["No live VWAP or order book","No intraday 5-gate confirmation",
"Pilot universe only, not all US listed equities","Backtest and walk-forward validation pending",
"Targets and stops are hypothetical reference levels, not guaranteed fills"]}
(ROOT/"recommendations.json").write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
print("US RADAR: scored",len(records),"watch",out["eligible_watch_count"])
if not records:raise SystemExit("Insufficient validated history for any US stock; no recommendations published")
