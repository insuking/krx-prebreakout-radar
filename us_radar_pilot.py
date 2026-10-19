"""US Radar pilot: KIS overseas daily OHLCV, observation-only, no orders.
The KIS dailyprice response schema and coverage are validated before publication.
"""
import os,json,datetime as dt,time
from pathlib import Path
from zoneinfo import ZoneInfo
import requests,pandas as pd
STOCKS={"NAS":{"AAPL":"Apple","MSFT":"Microsoft","NVDA":"NVIDIA","AMZN":"Amazon","GOOGL":"Alphabet","META":"Meta","TSLA":"Tesla","AMD":"AMD","AVGO":"Broadcom","PLTR":"Palantir","NFLX":"Netflix","COST":"Costco","AMAT":"Applied Materials","MU":"Micron","QCOM":"Qualcomm"},"NYS":{"JPM":"JPMorgan","V":"Visa","MA":"Mastercard","UNH":"UnitedHealth","XOM":"Exxon Mobil","WMT":"Walmart","BRK.B":"Berkshire Hathaway","GE":"GE Aerospace","CAT":"Caterpillar","LLY":"Eli Lilly"}}
BASE="https://openapi.koreainvestment.com:9443"
KEY=os.getenv("KIS_APP_KEY") or os.getenv("KIS_APPKEY")
SECRET=os.getenv("KIS_APP_SECRET") or os.getenv("KIS_APPSECRET")
ROOT=Path("site/us_radar");ROOT.mkdir(parents=True,exist_ok=True)
if not KEY or not SECRET:raise SystemExit("Missing KIS credentials: configure Actions secrets")
s=requests.Session()
r=s.post(BASE+"/oauth2/tokenP",json={"grant_type":"client_credentials","appkey":KEY,"appsecret":SECRET},timeout=25);r.raise_for_status()
token=r.json().get("access_token")
if not token:raise SystemExit("KIS token absent")
headers={"authorization":"Bearer "+token,"appkey":KEY,"appsecret":SECRET,"tr_id":"HHDFS76240000","custtype":"P"}
today=dt.datetime.now(ZoneInfo("America/New_York")).date()
results=[];errors=[]
def numeric(x):
    return pd.to_numeric(str(x).replace(",",""),errors="coerce")
for exch,items in STOCKS.items():
  for symbol,name in items.items():
    try:
      r=s.get(BASE+"/uapi/overseas-price/v1/quotations/dailyprice",headers=headers,
        params={"AUTH":"","EXCD":exch,"SYMB":symbol,"GUBN":"0","BYMD":today.strftime("%Y%m%d"),"MODP":"1"},timeout=25)
      r.raise_for_status();obj=r.json()
      if obj.get("rt_cd")!="0":raise ValueError("KIS rejected query: "+str(obj.get("msg_cd","unknown")))
      records=obj.get("output2")
      if not isinstance(records,list) or not records:raise ValueError("No daily price rows")
      rows=[]
      for x in records:
        d=str(x.get("xymd",""));close=numeric(x.get("clos"));volume=numeric(x.get("tvol"))
        if len(d)!=8 or not d.isdigit() or pd.isna(close) or pd.isna(volume) or close<=0 or volume<0:continue
        rows.append({"date":dt.datetime.strptime(d,"%Y%m%d").date().isoformat(),"close_usd":float(close),"volume_shares":int(volume)})
      if not rows:raise ValueError("Response lacks valid xymd/clos/tvol rows")
      path=ROOT/(symbol.replace(".","_")+".csv")
      df=pd.DataFrame(rows)
      if path.exists():
        old=pd.read_csv(path,dtype={"date":str})
        df=pd.concat([old,df],ignore_index=True)
      df=df.drop_duplicates("date",keep="last").sort_values("date")
      if df["date"].duplicated().any() or (df["close_usd"]<=0).any():raise ValueError("Data validation failed")
      df.to_csv(path,index=False,encoding="utf-8-sig")
      row={"symbol":symbol,"name":name,"exchange":exch,"asof":df.iloc[-1]["date"],"days":len(df),"close_usd":float(df.iloc[-1]["close_usd"]),"status":"INSUFFICIENT_HISTORY"}
      if len(df)>=61:
        close=df["close_usd"];vol=df["volume_shares"]
        rvol=float(vol.iloc[-1]/vol.iloc[-21:-1].mean()) if vol.iloc[-21:-1].mean()>0 else None
        ret20=float((close.iloc[-1]/close.iloc[-21]-1)*100)
        ret60=float((close.iloc[-1]/close.iloc[-61]-1)*100)
        high20=float(close.iloc[-20:].max())
        risk=float((close.iloc[-1]/high20-1)*100)
        row.update({"rvol_20d":round(rvol,2) if rvol is not None else None,
        "return_20d_pct":round(ret20,2),"return_60d_pct":round(ret60,2),
        "distance_from_20d_high_pct":round(risk,2),"status":"SCREENABLE"})
      results.append(row)
    except Exception as exc:errors.append({"symbol":symbol,"reason":str(exc)[:140]})
    time.sleep(0.4)
report={"market":"US","source":"KIS overseas dailyprice HHDFS76240000","asof_ny":today.isoformat(),
"mode":"research_only_no_orders","symbols_target":sum(map(len,STOCKS.values())),"symbols_valid":len(results),
"symbols_screenable":sum(x["status"]=="SCREENABLE" for x in results),
"stocks":results,"errors":errors,
"disclaimer":"Pilot watchlist, not full US market; no investor-category flows. Historical data may be limited."}
(ROOT/"summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("US PILOT",len(results),"valid,",report["symbols_screenable"],"screenable;",len(errors),"errors")
if not results:raise SystemExit("No verified US data")
