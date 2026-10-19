"""US Radar actionable watch/entry signal sheet from completed daily bars.
No intraday feed: signals never claim a live executed BUY.
"""
import json,datetime as dt
from pathlib import Path
p=Path("site/us_full_scan")
dashboard=p/"dashboard.json"
if not dashboard.exists():raise SystemExit("No full-market scan dashboard")
data=json.loads(dashboard.read_text(encoding="utf-8"))
signals=[]
for r in data.get("research_watchlist",[]):
 price=float(r["close"]);rvol=float(r["rvol20"])
 mom=float(r["return_20d_pct"]);dist=float(r["distance_prior_20d_high_pct"])
 if price<=0:continue
 if dist>=0 and dist<=3 and rvol>=1.5 and 0<mom<=25:
  signal="BREAKOUT_WATCH";why="20-day closing-high breakout with >=1.5x daily volume"
 elif -3<=dist<0 and mom>0:
  signal="NEAR_BREAKOUT";why="Near prior 20-day closing high; wait for price and volume confirmation"
 else:
  signal="WAIT";why="No sufficient breakout confirmation or extended setup"
 stop=round(price*.94,2);target=round(price+2*(price-stop),2)
 signals.append({"symbol":r["symbol"],"name":r.get("name",""),
  "asof":r["asof"],"reference_close_usd":price,
  "signal":signal,"signal_basis":why,"rvol20":rvol,
  "return_20d_pct":mom,"distance_prior_high_pct":dist,
  "reference_entry_usd":price,"reference_stop_usd":stop,
  "reference_target_2r_usd":target,
  "intraday_entry_confirmed":False,"live_vwap_confirmed":False,
  "recommendation_type":"RESEARCH_WATCH_ONLY","trade_execution_enabled":False})
order={"BREAKOUT_WATCH":0,"NEAR_BREAKOUT":1,"WAIT":2}
signals.sort(key=lambda r:(order[r["signal"]],-r["rvol20"],-r["return_20d_pct"]))
out={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
 "market":"US","coverage_status":data.get("status"),
 "symbols_attempted":data.get("symbols_attempted",0),
 "symbols_with_usable_prices":data.get("symbols_with_usable_prices",0),
 "intraday_data_available":False,"verified_live_buy_signals":0,
 "signals":signals,
 "important":"Prices are historical completed daily closes, NOT current executable prices. Confirm live price, VWAP, spread, liquidity and risk before trading."}
(p/"signals.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("Radar signals",len(signals),"breakout watch",sum(x["signal"]=="BREAKOUT_WATCH" for x in signals))
