"""Rolling 30-calendar-day US Radar quality audit; research only."""
import json,datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
ROOT=Path("site/us_radar");ROOT.mkdir(parents=True,exist_ok=True)
now=dt.datetime.now(ZoneInfo("America/New_York"))
end=now.date();start=end-dt.timedelta(days=30)
complete_today=now.weekday()<5 and now.time()>=dt.time(18)
summary_file=ROOT/"summary.json"
result={"window_start":str(start),"window_end":str(end),"generated_at_ny":now.isoformat(),
"status":"NOT_VERIFIED","verified_recommendations":[],
"scope":"KIS pilot only; NOT full US market","symbols":[],"issues":[]}
if summary_file.exists():
  summary=json.loads(summary_file.read_text(encoding="utf-8"))
  result["pilot_target"]=summary.get("symbols_target")
  for meta in summary.get("stocks",[]):
    symbol=meta["symbol"];p=ROOT/(symbol.replace(".","_")+".csv")
    row={"symbol":symbol,"status":"REJECTED","issues":[]}
    if not p.exists():row["issues"].append("MISSING_PRICE_FILE")
    else:
      try:
        d=pd.read_csv(p)
        if not {"date","close_usd","volume_shares"}.issubset(d):raise ValueError("SCHEMA_INVALID")
        d["date"]=pd.to_datetime(d["date"],errors="raise").dt.date
        if d["date"].duplicated().any():row["issues"].append("DUPLICATE_DATES")
        d=d[(d["date"]>=start)&(d["date"]<=end)].sort_values("date")
        if not complete_today:d=d[d["date"]<end]
        if len(d)<15:row["issues"].append("INSUFFICIENT_TRADING_DAYS")
        if d.empty:row["issues"].append("NO_COMPLETED_BARS")
        else:
          if (d["close_usd"]<=0).any() or (d["volume_shares"]<=0).any():row["issues"].append("INVALID_PRICE_OR_VOLUME")
          row["completed_bars"]=len(d);row["latest_completed_bar"]=str(d.iloc[-1]["date"])
          row["latest_close_usd"]=float(d.iloc[-1]["close_usd"])
          row["return_in_window_pct"]=round(float((d.iloc[-1]["close_usd"]/d.iloc[0]["close_usd"]-1)*100),3) if len(d)>1 else None
          if len(d)>5:
            r=d["close_usd"].pct_change().abs()
            if (r>.5).any():row["issues"].append("EXTREME_DAILY_MOVE_NEEDS_CORPORATE_ACTION_CHECK")
        # 30-day price QA cannot certify full history or model quality.
        row["issues"].extend(["CORPORATE_ACTIONS_NOT_VERIFIED","DELISTED_HISTORY_NOT_VERIFIED",
                              "WALK_FORWARD_MODEL_NOT_VERIFIED"])
      except Exception as exc:row["issues"].append("DATA_READ_ERROR:"+str(exc)[:80])
    result["symbols"].append(row)
else:result["issues"].append("SUMMARY_MISSING")
result["observed_symbols"]=len(result["symbols"])
result["data_quality_pass_count"]=sum(not x["issues"] for x in result["symbols"])
result["verified_count"]=0
result["blocked_by"]=["NO_VALIDATED_MODEL","NO_CORPORATE_ACTIONS_AUDIT","NO_POINT_IN_TIME_DELISTED_UNIVERSE"]
out=Path("site/us_research");out.mkdir(parents=True,exist_ok=True)
(out/"rolling_30d_quality.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("30D QA:",result["observed_symbols"],"symbols; verified recommendations: 0")
