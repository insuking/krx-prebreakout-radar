"""Build transparent next-session watch/entry plans from completed daily bars."""
import json,datetime as dt
from pathlib import Path
p=Path("site/us_full_scan")
d=json.loads((p/"dashboard.json").read_text(encoding="utf-8"))
leaders={"NVDA","AAPL","MSFT","AMZN","META","GOOGL","GOOG","TSLA","AVGO","AMD","PLTR","SPY","QQQ"}
def signal(r):
 price=float(r["close"]);dist=float(r["distance_prior_20d_high_pct"])
 rvol=float(r["rvol20"]);mom=float(r["return_20d_pct"])
 if dist>8 or mom>30:return "WAIT_PULLBACK","과열/추격 위험"
 if dist>=0 and rvol>=1.3 and mom>=0:return "BREAKOUT_WATCH","전일 고점 돌파 확인 후 관심"
 if -3<=dist<0 and rvol>=1 and mom>=0:return "NEAR_BREAKOUT","20일 고점 회복 확인 필요"
 return "WATCH_ONLY","진입 조건 미충족"
rows=[]
for r in d.get("research_watchlist",[]):
 status,reason=signal(r)
 px=float(r["close"])
 # Explicitly indicative, not real-time order levels.
 rows.append({**r,"signal":status,"signal_reason":reason,
  "last_close_usd":px,"reference_entry_above_usd":round(px*1.005,2),
  "reference_stop_usd":round(px*.95,2),
  "reference_target_2r_usd":round(px*1.115,2),
  "trade_now":False,"intraday_confirmation":"REQUIRED",
  "signal_basis":"completed daily OHLCV only; reference levels are not executable orders"})
leaders_seen=[r for r in rows if r["symbol"] in leaders]
out={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
 "market":"US","status":"DAILY_RESEARCH_SIGNALS",
 "coverage":{k:d.get(k) for k in ("status","universe_count","symbols_attempted","symbols_with_usable_prices","symbols_failed","symbols_unattempted")},
 "signals":rows,"major_leaders_in_top_watchlist":leaders_seen,
 "warnings":["No verified intraday VWAP, quote or fill","No BUY_NOW assertion",
 "Entry/stop/target are illustrative daily-close reference levels",
 "Only top-ranked research watchlist was assessed for leader membership"]}
(p/"signals.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("Signals",len(rows),"leaders",len(leaders_seen))
