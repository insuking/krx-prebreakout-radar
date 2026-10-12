import csv,json,datetime as dt
from pathlib import Path
import FinanceDataReader as fdr
import pandas as pd
root=Path("history");root.mkdir(exist_ok=True)
site=Path("site")
ledger=root/"recommendations.csv"
cols=["date","code","name","group","score","close","d1","d3","d5","status"]
def read(p):
 if not p.exists():return []
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def write(p,rows):
 with p.open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
rows=read(ledger)
status=json.loads((site/"run_status.json").read_text())
date=status.get("data_date")
seen={(r["date"],r["code"]) for r in rows}
for group in ["A","B"]:
 picks=sorted((r for r in read(site/"all_scores.csv") if r["group"]==group and r["date"]==date),key=lambda r:float(r["score"]),reverse=True)[:3]
 for r in picks:
  if (date,r["code"]) in seen:continue
  rows.append(dict(date=date,code=r["code"],name=r["name"],group=group,score=r["score"],close=r["close"],d1="",d3="",d5="",status="PENDING"))
  seen.add((date,r["code"]))
errors=[]
for r in rows:
 if r["status"]=="MATURED":continue
 try:
  start=(dt.date.fromisoformat(r["date"])+dt.timedelta(days=1)).isoformat()
  end=(dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()+dt.timedelta(days=1)).isoformat()
  d=fdr.DataReader(r["code"],start,end).sort_index()
  d=d[d.index.date>dt.date.fromisoformat(r["date"])]
  for n in [1,3,5]:
   if len(d)>=n and not r["d"+str(n)]:
    r["d"+str(n)]=str(round((float(d.Close.iloc[n-1])/float(r["close"])-1)*100,3))
  if len(d)>=5:r["status"]="MATURED"
 except Exception as e:errors.append(dict(code=r["code"],error=str(e)[:120]))
write(ledger,rows);write(site/"performance.csv",rows)
summary={"total":len(rows),"matured":sum(r["status"]=="MATURED" for r in rows),"errors":errors[:20],"forward_only":True}
for n in [1,3,5]:
 vals=[float(r["d"+str(n)]) for r in rows if r["d"+str(n)]]
 summary["d"+str(n)]={"n":len(vals),"avg_pct":round(sum(vals)/len(vals),2) if vals else None,"win_rate_pct":round(100*sum(x>0 for x in vals)/len(vals),1) if vals else None}
(site/"performance_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
