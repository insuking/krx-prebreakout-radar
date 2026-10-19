"""Run 100-symbol batches; promote to whole-universe cycles only after quality gates."""
import json,os,subprocess,sys
from pathlib import Path
root=Path("site/us_full_scan")
statefile=root/"rollout_state.json"
def state():
 try:return json.loads(statefile.read_text(encoding="utf-8"))
 except (OSError,ValueError):return {"mode":"PILOT","next_offset":0,"passing_batches":0}
s=state()
universe=json.loads(Path("site/us_universe/universe.json").read_text(encoding="utf-8"))
count=len(universe["symbols"])
if count<1000:raise SystemExit("Universe not ready")
manual=os.getenv("US_SCAN_MANUAL_OFFSET","").strip()
# Never bypass 100-symbol verification by manually supplying a larger batch.
max_batches=min(100,(count+99)//100) if os.getenv("US_SCAN_ALL","0")=="1" else (1 if s.get("mode")!="FULL_AUTO" else min(100,(count+99)//100))
for i in range(max_batches):
 s=state()
 offset=int(manual) if manual and i==0 else int(s.get("next_offset",0))
 os.environ["US_SCAN_OFFSET"]=str(offset)
 os.environ["US_SCAN_BATCH_SIZE"]="100"
 subprocess.run([sys.executable,"us_free_full_scan.py"],check=True)
 batch=json.loads((root/("batch_%05d.json"%offset)).read_text(encoding="utf-8"))
 if batch.get("source_denied"):
  print("DATA SOURCE DENIED: stopping scan to avoid unnecessary requests")
  break
 s["last_batch"]=offset
 statefile.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8")
 subprocess.run([sys.executable,"us_scan_rollout.py"],check=True)
 updated=state()
 print("Rollout:",updated.get("mode"),"passed:",updated.get("last_quality",{}).get("passed"))
 if not updated.get("last_quality",{}).get("passed"):
  if os.getenv("US_SCAN_ALL","0")=="1":
   # Continue coverage despite failed quality, but never promote rollout state.
   next_offset=offset+100
   if next_offset>=count:break
   updated["next_offset"]=next_offset
   statefile.write_text(json.dumps(updated,ensure_ascii=False,indent=2),encoding="utf-8")
  else:break
 if updated.get("cycle_complete"):break
