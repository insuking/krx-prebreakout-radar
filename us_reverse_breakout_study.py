"""Retrospective US breakout study with no lookahead leakage.

Uses dated daily OHLCV observations already collected under site/us_radar.
Labels are future outcomes; features use only information at the signal date.
Does not equate backtest precision with live predictive accuracy.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path("site/us_radar")
summary=json.loads((ROOT/"summary.json").read_text(encoding="utf-8"))
frames=[]
for stock in summary.get("stocks",[]):
    symbol=stock["symbol"]
    p=ROOT/(symbol.replace(".","_")+".csv")
    if not p.exists():continue
    d=pd.read_csv(p)
    if not {"date","close_usd","volume_shares"}.issubset(d):continue
    d["date"]=pd.to_datetime(d["date"],errors="coerce")
    d=d.dropna(subset=["date"]).sort_values("date").drop_duplicates("date")
    if len(d)<180:continue
    c=pd.to_numeric(d["close_usd"],errors="coerce")
    v=pd.to_numeric(d["volume_shares"],errors="coerce")
    if c.isna().any() or v.isna().any() or (c<=0).any():continue
    ret=c.pct_change()
    rolling_volume=v.shift(1).rolling(20,min_periods=20).mean()
    features=pd.DataFrame({"date":d["date"],"symbol":symbol,
      "ret_5":c.pct_change(5),"ret_20":c.pct_change(20),
      "rvol":v/rolling_volume,
      "volatility_20":ret.rolling(20).std(),
      "compression":ret.rolling(20).std()/ret.shift(20).rolling(40).std(),
      "dist_20d_high":c/c.shift(1).rolling(20).max()-1,
      "dollar_volume_20":(c*v).shift(1).rolling(20).mean()})
    for horizon in (1,3,5,10):
        # Future close-to-close outcome, only for retrospective labels.
        features[f"future_return_{horizon}d"]=c.shift(-horizon)/c-1
        features[f"event_{horizon}d_10pct"]=(features[f"future_return_{horizon}d"]>=0.10).where(features[f"future_return_{horizon}d"].notna())
    frames.append(features)
if not frames:raise SystemExit("Insufficient verified historical OHLCV; no study published")
all_data=pd.concat(frames,ignore_index=True).dropna(subset=["ret_20","rvol","compression","dollar_volume_20"])
all_data=all_data[all_data["dollar_volume_20"]>=5_000_000]
# Calendar split, not random shuffle: train first 70%, test last 30%.
dates=sorted(all_data["date"].unique())
if len(dates)<120:raise SystemExit("Too few distinct dates for chronological validation")
cut=dates[int(len(dates)*.7)]
train=all_data[all_data["date"]<cut]
test=all_data[all_data["date"]>=cut]
# Embargo: purge train rows whose future label reaches test interval.
results=[]
for horizon in (1,3,5,10):
    col=f"event_{horizon}d_10pct"
    tr=train[(train["date"]<cut-pd.Timedelta(days=horizon*3)) & train[col].notna()]
    te=test[test[col].notna()]
    if len(tr)<100 or len(te)<40:continue
    # Predetermined candidate rules, not optimized on test outcomes.
    rules={
      "compression_rvol":lambda x:(x["compression"]<0.9)&(x["rvol"]>1.5)&(x["ret_20"]>-0.05),
      "breakout_rvol":lambda x:(x["dist_20d_high"]>0)&(x["rvol"]>1.5),
      "trend_rvol":lambda x:(x["ret_20"]>0.05)&(x["ret_20"]<0.25)&(x["rvol"]>1.2)}
    for name,fn in rules.items():
        tmask=fn(te)
        n=int(tmask.sum())
        positives=int(te.loc[tmask,col].sum()) if n else 0
        base=float(te[col].mean())
        precision=positives/n if n else None
        results.append({"horizon_days":horizon,"rule":name,"train_rows":len(tr),
          "test_rows":len(te),"test_signals":n,"test_positive_events":positives,
          "test_precision":round(precision,4) if precision is not None else None,
          "test_base_rate":round(base,4),
          "lift_vs_base":round(precision/base,3) if n and base>0 else None})
report={"method":"chronological holdout, fixed rule comparison",
"universe":"available KIS pilot stocks only; survivorship bias likely",
"cutoff_date":str(pd.Timestamp(cut).date()),"symbols":all_data["symbol"].nunique(),
"event_definition":"close-to-close gain >=10% over next N trading days",
"cautions":["Historical selected survivors are not an unbiased full-market universe",
"Daily close signal assumes execution after that close, not at same close",
"Corporate actions, delistings, slippage and fees not modeled",
"Event is a future close return, not intraday maximum price",
"Small samples are not evidence of predictive accuracy"],
"results":results}
(ROOT/"reverse_breakout_study.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("Study rows",len(all_data),"rules",len(results),"holdout",str(pd.Timestamp(cut).date()))
if not results:raise SystemExit("Insufficient holdout samples for a meaningful study")
