"""Samsung (005930) KIS confirmed daily investor net quantities.
Append and deduplicate by exchange date; never mislabel shares as KRW.
"""
import os, json, datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
import pandas as pd

ROOT=Path("site/kis_samsung");ROOT.mkdir(parents=True,exist_ok=True)
KEY=os.getenv("KIS_APP_KEY") or os.getenv("KIS_APPKEY")
SECRET=os.getenv("KIS_APP_SECRET") or os.getenv("KIS_APPSECRET")
if not KEY or not SECRET:
    raise SystemExit("Missing KIS_APP_KEY/KIS_APP_SECRET secrets")
BASE="https://openapi.koreainvestment.com:9443"
s=requests.Session()
r=s.post(BASE+"/oauth2/tokenP",json={"grant_type":"client_credentials","appkey":KEY,"appsecret":SECRET},timeout=20)
r.raise_for_status()
token=r.json().get("access_token")
if not token:raise SystemExit("KIS access token missing")
headers={"content-type":"application/json; charset=utf-8","authorization":"Bearer "+token,
         "appkey":KEY,"appsecret":SECRET,"tr_id":"FHKST01010900","custtype":"P"}
r=s.get(BASE+"/uapi/domestic-stock/v1/quotations/inquire-investor",headers=headers,
        params={"FID_COND_MRKT_DIV_CODE":"J","FID_INPUT_ISCD":"005930"},timeout=20)
r.raise_for_status()
payload=r.json()
if payload.get("rt_cd")!="0":raise SystemExit("KIS query failed: "+str(payload.get("msg_cd","unknown")))
rows=payload.get("output")
if not isinstance(rows,list) or not rows:raise SystemExit("KIS returned no daily investor rows")
parsed=[]
for row in rows:
    date=str(row.get("stck_bsop_date",""))
    if len(date)!=8 or not date.isdigit():continue
    def signed(key):
        value=str(row.get(key,"")).replace(",","").strip()
        if not value or value=="-":return None
        return int(value)
    f=signed("frgn_ntby_qty");i=signed("orgn_ntby_qty")
    close=signed("stck_clpr")
    if f is None or i is None or close is None or close<=0:continue
    parsed.append({"date":dt.datetime.strptime(date,"%Y%m%d").date().isoformat(),
                   "close_krw":close,"foreign_net_shares":f,"institution_net_shares":i})
if not parsed:raise SystemExit("No valid KIS investor observations")
path=ROOT/"005930_daily.csv"
incoming=pd.DataFrame(parsed)
if path.exists():
    old=pd.read_csv(path,dtype={"date":str})
    incoming=pd.concat([old,incoming],ignore_index=True)
incoming=incoming.drop_duplicates("date",keep="last").sort_values("date")
incoming.to_csv(path,index=False,encoding="utf-8-sig")
asof=incoming.iloc[-1]["date"]
now=dt.datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
summary={"ticker":"005930","name":"삼성전자","source":"KIS FHKST01010900",
"market":"KRX","asof":asof,"updated_at_kst":now,
"observations":len(incoming),"units":{"foreign_net_shares":"shares","institution_net_shares":"shares","close_krw":"KRW"},
"historical_coverage":"Only dates returned by KIS plus accumulated daily runs; not guaranteed 1 year",
"confirmed_intraday":False,"nps_breakdown_available":False,
"note":"This endpoint returns net share quantities, not investor net KRW; no NPS-specific breakdown."}
(ROOT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print("VALIDATED ticker=005930 observations=",len(incoming),"asof=",asof,"unit=shares")
