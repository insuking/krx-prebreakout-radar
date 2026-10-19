"""Each matrix worker scans disjoint 100-symbol batches and writes artifacts."""
import json,os,subprocess,sys
from pathlib import Path
u=json.loads(Path("site/us_universe/universe.json").read_text(encoding="utf-8"))
n=len(u["symbols"])
if n<1000:raise SystemExit("Universe too small")
shard=int(os.getenv("US_SHARD","0"));total=int(os.getenv("US_SHARDS","8"))
if not 0<=shard<total:raise SystemExit("Bad shard")
for offset in range(shard*100,n,total*100):
 os.environ["US_SCAN_OFFSET"]=str(offset)
 os.environ["US_SCAN_BATCH_SIZE"]="100"
 subprocess.run([sys.executable,"us_free_full_scan.py"],check=True)
print("Completed shard",shard,"of",total)
