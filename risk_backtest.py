"""Walk-forward diagnostic of price-based chase filter, not a trading P&L backtest."""
import csv,json,datetime as dt
from pathlib import Path
import pandas as pd
import FinanceDataReader as fdr
from risk_model import risk_metrics
ROOT=Path("site");ROOT.mkdir(exist_ok=True)
source=ROOT/"all_scores.csv"
rows=list(csv.DictReader(source.open(encoding="utf-8-sig"))) if source.exists() else []
out=[]; failures=[]
for row in rows:
    try:
        code=row["code"]; end=dt.date.today()+dt.timedelta(days=1)
        start=end-dt.timedelta(days=390)
        d=fdr.DataReader(code,start.isoformat(),end.isoformat()).sort_index()
        d=d.dropna(subset=["Close","High","Low","Volume"])
        if len(d)<90:continue
        for i in range(45,len(d)-5,5):
            hist=d.iloc[:i+1]
            risk=risk_metrics(hist.Close,hist.High,hist.Low)
            future=float(d.Close.iloc[i+5]/d.Close.iloc[i]-1)*100
            out.append({"code":code,"signal_date":str(d.index[i].date()),"risk_score":risk["risk_score"],"blocked":bool(risk["risk_flags"]),"forward_5d_pct":round(future,3)})
    except Exception as e:failures.append({"code":row.get("code"),"error":str(e)[:120]})
pd.DataFrame(out,columns=["code","signal_date","risk_score","blocked","forward_5d_pct"]).to_csv(ROOT/"risk_backtest.csv",index=False,encoding="utf-8-sig")
def summary(a):
    return {"n":len(a),"mean_5d_pct":round(sum(x["forward_5d_pct"] for x in a)/len(a),3) if a else None,"negative_rate_pct":round(100*sum(x["forward_5d_pct"]<0 for x in a)/len(a),2) if a else None}
report={"method":"Historical 5-day forward returns of current scanner survivors; NOT full-universe unbiased backtest; sampled every five bars; close-to-close; no fees.","unfiltered":summary(out),"retained":summary([x for x in out if not x["blocked"]]),"excluded":summary([x for x in out if x["blocked"]]),"errors":failures[:30]}
(ROOT/"risk_backtest_summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False)[:1000])
