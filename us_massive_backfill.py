"""Backfill US all-market daily aggregates from a licensed Massive/Polygon API plan.
Set MASSIVE_API_KEY; optional US_BACKFILL_START/END (YYYY-MM-DD).
One date per request, resumable; no fabricated missing trading days.
"""
import os,sys,time,json,datetime as dt
from pathlib import Path
import requests,pandas as pd
key=os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY")
if not key:raise SystemExit("MASSIVE_API_KEY missing; provider connection required")
start=dt.date.fromisoformat(os.getenv("US_BACKFILL_START","2025-01-01"))
end=dt.date.fromisoformat(os.getenv("US_BACKFILL_END",str(dt.date.today())))
if start>end:raise SystemExit("Invalid date interval")
max_days=int(os.getenv("US_MAX_DAYS_PER_RUN","10"))
if not 1<=max_days<=100:raise SystemExit("US_MAX_DAYS_PER_RUN must be 1..100")
root=Path("data/us_daily");root.mkdir(parents=True,exist_ok=True)
s=requests.Session();processed=0;success=0;failures=[]
day=start
while day<=end and processed<max_days:
  if day.weekday()>=5:day+=dt.timedelta(days=1);continue
  target=root/(day.isoformat()+".csv.gz")
  if target.exists():day+=dt.timedelta(days=1);continue
  processed+=1
  url=f"https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/{day.isoformat()}"
  try:
    r=s.get(url,params={"adjusted":"false","apiKey":key},timeout=50)
    if r.status_code in (401,403,429):raise SystemExit("Provider authentication/entitlement/rate limit error: "+str(r.status_code))
    r.raise_for_status();obj=r.json()
    rows=obj.get("results",[])
    if not rows:
      # Do not silently treat API failures as exchange holidays.
      failures.append({"date":str(day),"reason":"No records returned; check holiday or entitlement"})
    else:
      df=pd.DataFrame([{"ticker":x["T"],"date":day.isoformat(),"open":x["o"],"high":x["h"],
        "low":x["l"],"close":x["c"],"volume":x["v"]} for x in rows])
      if df["ticker"].duplicated().any() or (df[["open","high","low","close"]]<=0).any().any():raise ValueError("Invalid aggregate bars")
      df.to_csv(target,index=False,compression="gzip")
      success+=1
  except (requests.RequestException,ValueError,KeyError) as exc:
    failures.append({"date":str(day),"reason":str(exc)[:140]})
  day+=dt.timedelta(days=1);time.sleep(.3)
status={"start":str(start),"end":str(end),"processed":processed,"new_files":success,"failures":failures,
"provider":"Massive grouped daily aggregates","adjusted":False,
"warning":"Raw bars need corporate action normalization before breakout labels"}
Path("site/us_research").mkdir(parents=True,exist_ok=True)
Path("site/us_research/backfill_status.json").write_text(json.dumps(status,indent=2),encoding="utf-8")
print(json.dumps(status,ensure_ascii=False))
if failures:sys.exit(1)
