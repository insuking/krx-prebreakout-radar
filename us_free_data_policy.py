"""Free-only US Radar configuration. No paid market-data endpoints.
Use current listing directory and optional free public historical datasets.
Never claim delisted-history completeness or calibrated predictive accuracy.
"""
import json,datetime as dt
from pathlib import Path
root=Path("site/us_research");root.mkdir(parents=True,exist_ok=True)
sources=[
 {"name":"NASDAQ Trader Symbol Directory","cost_usd":0,"purpose":"current exchange-listed symbols","limitations":"not a historical delisted universe"},
 {"name":"SEC EDGAR submissions and companyfacts","cost_usd":0,"purpose":"dated company filings and fundamentals","limitations":"point-in-time publication and amendments must be tracked"},
 {"name":"FRED","cost_usd":0,"purpose":"rates, macroeconomic series","limitations":"API key may be required; revisions and release timestamps matter"},
 {"name":"Stooq or other permitted public daily datasets","cost_usd":0,"purpose":"historical price pilot","limitations":"coverage, license, split adjustment and delisted symbols must be verified"}]
config={"mode":"FREE_ONLY","paid_api_enabled":False,"orders_enabled":False,
"universe_discovery":"us_full_universe.py",
"full_market_history_status":"NOT_ACQUIRED",
"delisted_history_status":"NOT_VERIFIED",
"live_full_market_recommendations":"DISABLED_UNTIL_DATA_VALIDATED",
"data_sources":sources,"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat()}
(root/"free_data_policy.json").write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding="utf-8")
print("FREE_ONLY policy active; no paid data source enabled")
