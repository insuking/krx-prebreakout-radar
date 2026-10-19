"""Fail-closed public US Radar recommendations publisher.

Only publishes verified candidates when independently produced QA evidence exists.
Research/watchlist data never becomes a verified recommendation by default.
"""
import json,datetime as dt
from pathlib import Path

ROOT=Path("site/us_radar")
ROOT.mkdir(parents=True,exist_ok=True)
EVIDENCE=Path("site/us_research/release_evidence.json")
OUTPUT=ROOT/"verified_recommendations.json"
REQUIRED=("full_universe_history_verified","delisted_history_verified",
          "corporate_actions_verified","market_context_verified",
          "walk_forward_validated","model_calibrated","fresh_market_data_verified")
report={"generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "market":"US","status":"NO_VERIFIED_SIGNAL","verified_count":0,
        "recommendations":[],"trade_execution_enabled":False,
        "note":"Only independently validated model candidates are published; research WATCH is excluded."}
try:
    evidence=json.loads(EVIDENCE.read_text(encoding="utf-8"))
    missing=[key for key in REQUIRED if evidence.get(key) is not True]
    if missing:
        report["blocked_by"]=missing
    else:
        # Evidence must be created by a separate, audited validation pipeline.
        # A boolean alone is not sufficient to publish.
        manifest=evidence.get("manifest",{})
        if not all(manifest.get(k) for k in ("model_version","data_asof","validation_report_sha256","universe_snapshot_id")):
            report["blocked_by"]=["missing_provenance_manifest"]
        else:
            report["status"]="VALIDATION_READY_NO_SIGNALS"
            report["blocked_by"]=["no_independently_validated_candidate_feed"]
except (OSError,ValueError,TypeError) as exc:
    report["blocked_by"]=["validation_evidence_missing_or_invalid"]
OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("Verified Radar:",report["status"],"published:",report["verified_count"],"blocked:",report.get("blocked_by"))
