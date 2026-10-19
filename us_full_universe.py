"""Discover US exchange-listed symbol universe, not a fixed mega-cap watchlist.
This is a CURRENT listing snapshot, not historical point-in-time membership.
"""
import csv,io,json,datetime as dt
from pathlib import Path
import requests
SOURCES={
"NASDAQ":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
"OTHER":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"}
out=[];errors=[]
for source,url in SOURCES.items():
    try:
        r=requests.get(url,timeout=35,headers={"User-Agent":"KRX-US-Radar research data pipeline"})
        r.raise_for_status()
        lines=[x for x in r.text.splitlines() if "|" in x and not x.startswith("File Creation Time")]
        reader=csv.DictReader(io.StringIO("\n".join(lines)),delimiter="|")
        for row in reader:
            if row.get("Test Issue","N")!="N":continue
            symbol=(row.get("Symbol") if source=="NASDAQ" else row.get("ACT Symbol")) or ""
            name=row.get("Security Name","")
            if not symbol or not name:continue
            if source=="NASDAQ" and row.get("ETF")=="Y":continue
            if source=="OTHER" and row.get("ETF")=="Y":continue
            # Exclude obvious non-common-share instruments; keep uncertain cases for classification.
            lower=name.lower()
            if any(term in lower for term in ("warrant","rights","depositary share","preferred stock","unit representing","exchange traded fund","etf","etn")):continue
            out.append({"symbol":symbol,"name":name,"exchange_source":source,
                "listing_exchange":row.get("Exchange","NASDAQ") if source=="OTHER" else "NASDAQ",
                "security_classification":"PROVISIONAL"})
    except Exception as exc:errors.append({"source":source,"error":str(exc)[:180]})
if errors:raise SystemExit("Universe incomplete; refusing to publish: "+str(errors))
if len(out)<1000:raise SystemExit("Universe unexpectedly small")
dedup={x["symbol"]:x for x in out}
root=Path("site/us_universe");root.mkdir(parents=True,exist_ok=True)
report={"snapshot_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
"source_urls":SOURCES,"count":len(dedup),"point_in_time_history":False,
"coverage":"Current NASDAQ and other-exchange listed issues; preliminary stock filtering",
"limitations":["Does not include delisted historical securities",
"Does not guarantee common-share-only classification",
"Current membership cannot be used to backtest historical full-market returns"],
"symbols":sorted(dedup.values(),key=lambda x:x["symbol"])}
(root/"universe.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("Current universe",len(dedup))
