"""Batch rollout controller for the free US scanner.

Modes: PILOT -> BATCHED -> FULL_AUTO. No promotion on a single lucky batch.
The controller inspects batch coverage and quality; model verification is separate.
"""
import json,datetime as dt
from pathlib import Path
ROOT=Path("site/us_full_scan");ROOT.mkdir(parents=True,exist_ok=True)
STATE=ROOT/"rollout_state.json"
def load(path,default):
 try:return json.loads(path.read_text(encoding="utf-8"))
 except (OSError,ValueError):return default
state=load(STATE,{"mode":"PILOT","next_offset":0,"passing_batches":0,"last_batch":None})
universe=load(Path("site/us_universe/universe.json"),{})
count=len(universe.get("symbols",[]))
if count<1000:raise SystemExit("Refusing rollout: missing current full universe")
batch_size=100
last=state.get("last_batch")
if last is not None:
 report=load(ROOT/("batch_%05d.json"%last),{})
 requested=int(report.get("batch_requested",0))
 success=int(report.get("batch_success",0))
 failures=int(report.get("batch_failed",0))
 coverage=success/requested if requested else 0
 # Price validation failures are failures, not successes.
 good=(requested==batch_size and success+failures==requested and coverage>=.90
       and len(report.get("candidates",[]))==success)
 state["last_quality"]={"offset":last,"requested":requested,"success":success,
  "failed":failures,"coverage":round(coverage,4),"passed":good}
 if not good:
  state["passing_batches"]=0
  state["mode"]="PILOT" if state["mode"]=="PILOT" else "BATCHED"
  state["next_offset"]=last  # retry failed batch
 else:
  state["passing_batches"]+=1
  state["next_offset"]=last+batch_size
  if state["passing_batches"]>=3 and state["mode"]=="PILOT":
   state["mode"]="BATCHED"
  if state["passing_batches"]>=10 and state["mode"]=="BATCHED":
   state["mode"]="FULL_AUTO"
if state["next_offset"]>=count:
 state["next_offset"]=0
 state["cycle_complete"]=True
else:state["cycle_complete"]=False
state["universe_count"]=count
state["batch_size"]=batch_size
state["updated_utc"]=dt.datetime.now(dt.timezone.utc).isoformat()
STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(state,ensure_ascii=False))
