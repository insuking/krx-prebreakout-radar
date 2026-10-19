"""Full-market historical US breakout research on licensed daily OHLCV flat files.

Input files in data/us_daily/*.csv or *.csv.gz, with columns:
ticker,date,open,high,low,close,volume (unadjusted or consistently split-adjusted).
Each file may hold many tickers for one date. Provider must include delisted
tickers and corporate actions; verify point-in-time metadata independently.
"""
import os,glob,json,datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd

BASE=Path("data/us_daily");OUT=Path("site/us_research");OUT.mkdir(parents=True,exist_ok=True)
files=sorted(glob.glob(str(BASE/"*.csv"))+glob.glob(str(BASE/"*.csv.gz")))
if not files:raise SystemExit("No historical daily market files; refusing fabricated analysis")
chunks=[]
for path in files:
  x=pd.read_csv(path,dtype={"ticker":str})
  need={"ticker","date","open","high","low","close","volume"}
  if not need.issubset(x.columns):raise SystemExit("Missing columns in "+path)
  chunks.append(x[list(need)])
data=pd.concat(chunks,ignore_index=True)
data["date"]=pd.to_datetime(data["date"],errors="raise")
for c in ("open","high","low","close","volume"):data[c]=pd.to_numeric(data[c],errors="raise")
if data.duplicated(["ticker","date"]).any():raise SystemExit("Duplicate ticker/date observations")
if (data[["open","high","low","close"]]<=0).any().any() or (data["volume"]<0).any():raise SystemExit("Invalid OHLCV")
data=data.sort_values(["ticker","date"])
# Lagged context features: market-wide participation, breadth and sector not inferred.
data["ret1"]=data.groupby("ticker")["close"].pct_change()
market=data.groupby("date").agg(market_breadth=("ret1",lambda v:float((v>0).mean())),market_dispersion=("ret1","std"),market_count=("ticker","nunique"))
market["market_breadth_prev"]=market["market_breadth"].shift(1)
market["market_dispersion_prev"]=market["market_dispersion"].shift(1)
frames=[]
for ticker,d in data.groupby("ticker",sort=False):
  d=d.copy().reset_index(drop=True)
  if len(d)<180:continue
  c=d["close"];v=d["volume"];r=c.pct_change()
  d["rvol"]=v/v.shift(1).rolling(20).mean()
  d["ret5"]=c.pct_change(5);d["ret20"]=c.pct_change(20)
  d["vol20"]=r.rolling(20).std()
  d["compression"]=d["vol20"]/r.shift(20).rolling(40).std()
  d["distance_high20"]=c/c.shift(1).rolling(20).max()-1
  d["dollar_vol20"]=(c*v).shift(1).rolling(20).mean()
  d["event5"]=(c.shift(-5)/c-1>=.15).where(c.shift(-5).notna())
  d["event10"]=(c.shift(-10)/c-1>=.20).where(c.shift(-10).notna())
  frames.append(d[["ticker","date","close","rvol","ret5","ret20","vol20","compression","distance_high20","dollar_vol20","event5","event10"]])
if not frames:raise SystemExit("Insufficient observations for research")
x=pd.concat(frames,ignore_index=True).merge(market[["market_breadth_prev","market_dispersion_prev"]],left_on="date",right_index=True,how="left")
features=["rvol","ret5","ret20","vol20","compression","distance_high20","dollar_vol20","market_breadth_prev","market_dispersion_prev"]
x=x.replace([np.inf,-np.inf],np.nan).dropna(subset=features)
x=x[(x["dollar_vol20"]>=2_000_000)&(x["close"]>=1)]
latest=x.sort_values("date").groupby("ticker").tail(1).copy()
x=x.dropna(subset=["event10","event5"])
dates=sorted(x["date"].unique())
if len(dates)<300:raise SystemExit("Require >=300 market dates for temporal validation")
train_end=dates[int(len(dates)*.6)];valid_end=dates[int(len(dates)*.8)]
# 30 calendar-day embargo prevents labels in train from reaching validation.
train=x[x["date"]<train_end-pd.Timedelta(days=30)]
valid=x[(x["date"]>=train_end)&(x["date"]<valid_end-pd.Timedelta(days=30))]
test=x[x["date"]>=valid_end]
if min(len(train),len(valid),len(test))<200:raise SystemExit("Insufficient independent samples")
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score,brier_score_loss,precision_score
report={"data_files":len(files),"universe_symbols":int(data["ticker"].nunique()),"days":len(dates),
"train_end":str(pd.Timestamp(train_end).date()),"test_start":str(pd.Timestamp(valid_end).date()),
"validation":"chronological holdout with train/validation embargo",
"features":features,"models":{},"asof":str(data["date"].max().date()),
"warnings":["Verify delisted security inclusion and historical point-in-time universe with provider",
"Market context is lagged one trading day; no point-in-time industry or SEC fundamentals included",
"Unadjusted corporate actions can generate spurious events; input must be normalized",
"Daily-close feature uses end-of-day knowledge; no same-close fill assumption",
"Model is research-only; no intraday VWAP, execution, slippage or portfolio backtest"]}
for label in ("event5","event10"):
  a=train[label].astype(int);b=valid[label].astype(int);y=test[label].astype(int)
  if a.nunique()<2 or b.nunique()<2 or y.nunique()<2:continue
  model=HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=12,l2_regularization=10,learning_rate=.05,random_state=42)
  model.fit(train[features],a)
  pv=model.predict_proba(valid[features])[:,1]
  # Threshold selected exclusively on validation period; min signals guard.
  thresholds=np.linspace(.1,.9,17)
  candidates=[(float(precision_score(b,pv>=t,zero_division=0)),t,int((pv>=t).sum())) for t in thresholds if (pv>=t).sum()>=20]
  threshold=max(candidates,key=lambda z:(z[0],z[2]))[1] if candidates else .5
  pt=model.predict_proba(test[features])[:,1]
  report["models"][label]={"test_rows":len(test),"test_base_rate":round(float(y.mean()),5),
   "test_average_precision":round(float(average_precision_score(y,pt)),5),
   "test_brier":round(float(brier_score_loss(y,pt)),5),
   "validation_selected_threshold":threshold,
   "test_signals":int((pt>=threshold).sum()),
   "test_precision_at_threshold":round(float(precision_score(y,pt>=threshold,zero_division=0)),5)}
  # Refit for prospective research on all historically labeled rows (not test metrics).
  eligible=x[x["date"]<=data["date"].max()-pd.Timedelta(days=20)]
  if eligible[label].astype(int).nunique()<2:continue
  model.fit(eligible[features],eligible[label].astype(int))
  latest[label+"_estimated_probability"]=model.predict_proba(latest[features])[:,1]
latest=latest.sort_values("event10_estimated_probability",ascending=False) if "event10_estimated_probability" in latest else latest
latest[["ticker","date","close"]+[c for c in latest if c.endswith("_estimated_probability")]].to_csv(OUT/"daily_research_candidates.csv",index=False)
(OUT/"model_validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("FULL MARKET STUDY",report["universe_symbols"],"symbols",len(dates),"days",report["models"])
if not report["models"]:raise SystemExit("No label passed validation")
