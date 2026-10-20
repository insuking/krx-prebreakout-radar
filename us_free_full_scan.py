"""Free-only, resumable full-US-universe daily screener.

Universe: Nasdaq Trader current listings. Prices: Stooq public daily CSV endpoint,
subject to availability, source terms, and coverage. NO paid API, no orders.
This is a heuristic research watchlist, not a validated probability forecast.
"""
import csv, io, json, os, time, datetime as dt
from pathlib import Path
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

ROOT=Path("site/us_full_scan")
ROOT.mkdir(parents=True,exist_ok=True)
UNIVERSE=Path("site/us_universe/universe.json")
if not UNIVERSE.exists():
    raise SystemExit("Universe snapshot missing; run us_full_universe.py first")
u=json.loads(UNIVERSE.read_text(encoding="utf-8"))
symbols=[r for r in u.get("symbols",[]) if r.get("symbol")]
if len(symbols)<1000:raise SystemExit("Universe too small for full-market mode")
limit=max(1,min(int(os.getenv("US_SCAN_BATCH_SIZE","100")),500))
offset=max(0,int(os.getenv("US_SCAN_OFFSET","0")))
selected=symbols[offset:offset+limit]
ny=dt.datetime.now(ZoneInfo("America/New_York"))
last_completed=ny.date()
if ny.weekday()<5 and ny.time()<dt.time(18):
    last_completed-=dt.timedelta(days=1)
while last_completed.weekday()>=5:last_completed-=dt.timedelta(days=1)
start=last_completed-dt.timedelta(days=95)
API_KEY=os.getenv("STOOQ_API_KEY","").strip()
# Stooq key is optional; public access may be limited. Always emit batch diagnostics.
source_denied=threading.Event()
results=[];failures=[]
def score(rows):
    rows=[r for r in rows if start<=r[0]<=last_completed]
    rows.sort()
    if len(rows)<25:return None,"INSUFFICIENT_BARS"
    dates=[r[0] for r in rows]
    if (last_completed-dates[-1]).days>5:return None,"STALE_LAST_BAR"
    close=[r[1] for r in rows];vol=[r[2] for r in rows]
    if any(v<=0 for v in close) or any(v<0 for v in vol):return None,"INVALID_OHLCV"
    if not any(vol[-21:-1]):return None,"NO_BASELINE_VOLUME"
    av=sum(vol[-21:-1])/20
    if av<=0:return None,"NO_BASELINE_VOLUME"
    rvol=vol[-1]/av
    ret20=close[-1]/close[-21]-1
    prevhigh=max(close[-21:-1])
    breakout=close[-1]/prevhigh-1
    liquidity=sum(close[i]*vol[i] for i in range(-20,0))/20
    if liquidity<2_000_000 or close[-1]<2:return None,"LOW_LIQUIDITY"
    # Separate momentum from overextension. No unverified prediction probabilities.
    momentum=max(0,min(25,(ret20+0.05)*100))
    proximity=max(0,25-min(abs(breakout)*100,10)*5)
    volume=max(0,min(25,(rvol-0.8)*20))
    risk=25 if ret20>0.30 or breakout>0.10 else 0
    points=round(momentum+proximity+volume-risk,2)
    return {"asof":str(dates[-1]),"close":round(close[-1],4),
      "return_20d_pct":round(ret20*100,2),"rvol20":round(rvol,2),
      "distance_prior_20d_high_pct":round(breakout*100,2),
      "average_dollar_volume_20d":round(liquidity),
      "heuristic_score":points,"status":"RESEARCH_WATCH" if points>=45 else "PASS",
      "verified_prediction":False,"trade_execution_enabled":False},None
def fetch_one(item):
    sym=item["symbol"]
    if source_denied.is_set():return None,{"symbol":sym,"error":"SOURCE_DENIED_SKIPPED"}
    if not all(ch.isalnum() or ch in ".-" for ch in sym):
        return None,{"symbol":sym,"error":"UNSUPPORTED_SYMBOL_FORMAT"}
    try:
        q=requests.get("https://stooq.com/q/d/l/",params={"s":sym.lower()+".us","i":"d",**({"apikey":API_KEY} if API_KEY else {}),
            "d1":start.strftime("%Y%m%d"),"d2":last_completed.strftime("%Y%m%d")},
            timeout=(5,12),headers={"User-Agent":"Mozilla/5.0 (compatible; FreeRadarResearch/1.0)"})
        if q.status_code in (403,429):
            source_denied.set()
            return None,{"symbol":sym,"error":"SOURCE_DENIED_HTTP_"+str(q.status_code)}
        q.raise_for_status()
        head=q.text[:1500].lower()
        if any(t in head for t in ("daily hits limit","too many requests","apikey required","proof of work","captcha","<html")):
            source_denied.set()
            return None,{"symbol":sym,"error":"SOURCE_DENIED_BODY"}
        if not q.text.startswith("Date,Open,High,Low,Close,Volume"):
            raise ValueError("NO_CSV_DATA_OR_RATE_LIMIT")
        rows=[]
        for r in csv.DictReader(io.StringIO(q.text)):
            date=dt.date.fromisoformat(r["Date"])
            rows.append((date,float(r["Close"]),float(r["Volume"])))
        scored,error=score(rows)
        if error:return None,{"symbol":sym,"error":error}
        return {"symbol":sym,"name":item.get("name",""),**scored},None
    except Exception as exc:
        return None,{"symbol":sym,"error":str(exc)[:90]}
workers=max(1,min(int(os.getenv("US_SCAN_WORKERS","4")),8))
with ThreadPoolExecutor(max_workers=workers) as pool:
    futures=[pool.submit(fetch_one,item) for item in selected]
    for future in as_completed(futures):
        good,bad=future.result()
        if good:results.append(good)
        if bad:failures.append(bad)
out={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
 "universe_snapshot_utc":u.get("snapshot_utc"),"market":"US",
 "mode":"FREE_ONLY_RESEARCH","source":"Stooq daily public CSV",
 "source_denied":source_denied.is_set(),"source_coverage_unverified":True,"historical_delistings_included":False,
 "universe_count":len(symbols),"batch_offset":offset,"batch_requested":len(selected),
 "batch_success":len(results),"batch_failed":len(failures),"workers":workers,
 "last_completed_session_estimate":str(last_completed),
 "candidates":sorted(results,key=lambda r:r["heuristic_score"],reverse=True),
 "failures":failures,"warnings":["Current listings only; not point-in-time delisted universe",
 "Stooq data license, completeness and adjustment basis not independently validated",
 "Heuristic scores are NOT calibrated probabilities",
 "US market holiday handling is approximate; stale bars are rejected",
 "Do not trade based solely on this screen"]}
p=ROOT/("batch_%05d.json"%offset)
p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("US FULL UNIVERSE BATCH",offset,"/",len(symbols),"success",len(results),"fail",len(failures),"output",p)
