"""Combine free US full-universe scan batches without implying unscanned coverage."""
import json,datetime as dt
from pathlib import Path
p=Path("site/us_full_scan");p.mkdir(parents=True,exist_ok=True)
files=sorted(p.glob("batch_*.json"))
batches=[]
for f in files:
 try:batches.append(json.loads(f.read_text(encoding="utf-8")))
 except (OSError,ValueError):pass
if not batches:raise SystemExit("No scan batches available")
universe=max(int(x.get("universe_count",0)) for x in batches)
seen=set();candidates=[];failed=[]
for b in sorted(batches,key=lambda x:x.get("generated_utc",""),reverse=True):
 for r in b.get("candidates",[]):
  if r["symbol"] not in seen:seen.add(r["symbol"]);candidates.append(r)
 for r in b.get("failures",[]):
  if r["symbol"] not in seen:seen.add(r["symbol"]);failed.append(r)
status="PARTIAL" if len(seen)<universe else "ALL_SYMBOLS_ATTEMPTED"
out={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
 "status":status,"universe_count":universe,"symbols_attempted":len(seen),
 "symbols_with_usable_prices":len(candidates),"symbols_failed":len(failed),
 "symbols_unattempted":max(0,universe-len(seen)),
 "research_watchlist":sorted([r for r in candidates if r["status"]=="RESEARCH_WATCH"],
   key=lambda x:x["heuristic_score"],reverse=True)[:30],
 "verified_recommendations":[],"verified_count":0,
 "notice":"Research screening only; no full-universe validation or calibrated prediction."}
(p/"dashboard.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(status,len(seen),"/",universe,"research watch",len(out["research_watchlist"]))
