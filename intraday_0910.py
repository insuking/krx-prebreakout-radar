"""09:10 KST public quote verification. Fail closed: never issue BUY."""
import csv,datetime as dt,json,re,time
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
KST=ZoneInfo("Asia/Seoul")
now=dt.datetime.now(KST)
root=Path("site");root.mkdir(exist_ok=True)
def parse_price(x):
    s=str(x or "").replace(",","").replace("+","").strip()
    if not re.fullmatch(r"-?\d+(?:\.\d+)?",s):return None
    return float(s)
def read_candidates():
    p=Path("history/recommendations.csv")
    if not p.exists():return []
    with p.open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    if not rows:return []
    day=max(r["date"] for r in rows)
    return [r for r in rows if r["date"]==day]
results=[]
for row in read_candidates():
    code=row["code"]; outcome=dict(code=code,name=row["name"],group=row["group"],base_date=row["date"],base_close=row["close"],checked_at=now.isoformat(),status="WATCH",verified_gates=0,required_gates=5,errors=[])
    try:
        url=f"https://m.stock.naver.com/api/stock/{code}/basic"
        response=requests.get(url,timeout=12,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
        response.raise_for_status()
        obj=response.json()
        price=parse_price(obj.get("closePrice"))
        # Public endpoints may be delayed and lack a reliable quote timestamp.
        if price is None or price<=0:raise ValueError("invalid quote or changed provider schema")
        outcome["public_display_price"]=price
        outcome["quote_timestamp"]=obj.get("localTradedAt") or obj.get("tradeDate") or "미제공"
        outcome["quote_source"]="Naver mobile public endpoint (may be delayed)"
        outcome["price_vs_previous_close_pct"]=round((price/float(row["close"])-1)*100,2)
        outcome["errors"].append("실시간성/거래일 확인 불가: 매수 신호 불허")
    except Exception as e:outcome["errors"].append(str(e)[:180])
    outcome["gates"]={"quote_freshness":"UNVERIFIED","opening_support":"UNVERIFIED","vwap":"UNVERIFIED","intraday_rvol":"UNVERIFIED","investor_flow_and_relative_strength":"UNVERIFIED"}
    results.append(outcome)
    time.sleep(0.4)
data={"run_at_kst":now.isoformat(),"market_open_window":now.weekday()<5 and (9,10)<= (now.hour,now.minute) <=(15,30),"mode":"public_quote_observation_only","message":"Public quote observations are not verified real-time trades. BUY disabled.","results":results}
(root/"intraday_0910.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
print("09:10 watch-only observation:",len(results))
