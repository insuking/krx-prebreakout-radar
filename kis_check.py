"""KIS credential and price-read smoke test. No orders; no secrets printed."""
import os,json,datetime as dt
from pathlib import Path
import requests
out={"checked_at":dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),"auth":"NOT_RUN","quote":"NOT_RUN","trading_enabled":False}
key=os.getenv("KIS_APP_KEY");secret=os.getenv("KIS_APP_SECRET")
try:
    if not key or not secret:raise RuntimeError("KIS_APP_KEY or KIS_APP_SECRET missing")
    base="https://openapi.koreainvestment.com:9443"
    r=requests.post(base+"/oauth2/tokenP",json={"grant_type":"client_credentials","appkey":key,"appsecret":secret},timeout=15)
    r.raise_for_status()
    token=r.json().get("access_token")
    if not token:raise RuntimeError("No access token returned")
    out["auth"]="SUCCESS"
    r=requests.get(base+"/uapi/domestic-stock/v1/quotations/inquire-price",params={"FID_COND_MRKT_DIV_CODE":"J","FID_INPUT_ISCD":"005930"},headers={"authorization":"Bearer "+token,"appkey":key,"appsecret":secret,"tr_id":"FHKST01010100","custtype":"P"},timeout=15)
    r.raise_for_status()
    obj=r.json()
    if str(obj.get("rt_cd"))!="0":raise RuntimeError("Quote rejected: "+str(obj.get("msg_cd")))
    quote=obj.get("output") or {}
    out["quote"]="SUCCESS" if quote.get("stck_prpr") else "MISSING_PRICE"
    out["sample_code"]="005930"
    out["sample_price"]=quote.get("stck_prpr")
except Exception as e:
    out["error_type"]=type(e).__name__
    out["error"]="KIS verification failed; check permissions and workflow logs (credentials redacted)"
Path("site").mkdir(exist_ok=True)
Path("site/kis_status.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("KIS auth:",out["auth"],"quote:",out["quote"])
