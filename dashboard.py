"""Mobile-first Radar report: reads verified scanner outputs, never fabricates quotes."""
import csv, datetime as dt, html, json, collections
from pathlib import Path

root=Path("site")
status=json.loads((root/"run_status.json").read_text(encoding="utf-8"))
def read_csv(name):
    p=root/name
    if not p.exists() or p.stat().st_size==0:return []
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
all_rows=read_csv("all_scores.csv")
failures=read_csv("failures.csv")
def esc(v):return html.escape(str(v),quote=True)
def num(v):
    try:return f"{float(v):,.0f}"
    except (ValueError,TypeError):return "—"
def pct(v):
    try:return f"{float(v):+.1f}%"
    except (ValueError,TypeError):return "—"
def fnum(v):
    try:return float(v)
    except (ValueError,TypeError):return 0
def group_cards(group):
    chosen=sorted((r for r in all_rows if r.get("group")==group),key=lambda r:fnum(r.get("score")),reverse=True)[:3]
    if not chosen:return '<div class="empty">조건을 충족한 후보가 없습니다.</div>'
    parts=[]
    for r in chosen:
        entry=fnum(r.get("entry")); stop=fnum(r.get("stop"))
        t1=fnum(r.get("target1"));t2=fnum(r.get("target2"))
        risk=(entry-stop)/entry*100 if entry else 0
        rr1=(t1-entry)/(entry-stop) if entry>stop else 0
        ret1=(t1-entry)/entry*100 if entry else 0
        ret2=(t2-entry)/entry*100 if entry else 0
        parts.append(f"""<article class="stock">
          <div class="stockhead"><div><div class="ticker">{esc(r.get('name',''))} <small>{esc(r.get('code',''))}</small></div>
          <div class="meta">{esc(r.get('market',''))} · 시세일 {esc(r.get('date','미확인'))}</div></div>
          <span class="watch">WATCH</span></div>
          <div class="stats"><div><label>확인된 종가</label><strong>{num(r.get('close'))}원</strong></div>
          <div><label>모형 점수</label><strong>{esc(r.get('score','—'))}/100</strong></div>
          <div><label>상대거래량</label><strong>{fnum(r.get('rvol')):.2f}배</strong></div></div>
          <div class="prices"><div><label>조건부 진입</label><b>{num(entry)}원</b></div>
          <div><label>손절 기준</label><b>{num(stop)}원</b><small>위험 {risk:.1f}%</small></div>
          <div><label>1차 목표</label><b>{num(t1)}원</b><small>{pct(ret1)}</small></div>
          <div><label>2차 목표</label><b>{num(t2)}원</b><small>{pct(ret2)}</small></div></div>
          <div class="gate">장중 진입 게이트 <b>0/5 확인</b> · 목표 1 손익비 {rr1:.2f}:1</div>
          <div class="foot">가격은 종가 기준 가상 시나리오입니다. VWAP·시초가 지지·실시간 RVOL·외국인/프로그램 수급·상대강도 검증 전 매수 금지.</div>
          </article>""")
    return "".join(parts)
def failure_summary():
    counts=collections.Counter()
    for r in failures:
        e=r.get("error","").lower()
        if "insufficient" in e:counts["데이터 부족"]+=1
        elif "timeout" in e or "connection" in e or "http" in e:counts["연결/공급원"]+=1
        elif "bad latest" in e:counts["거래량·시세 이상"]+=1
        elif r.get("code")=="SYSTEM":counts["전체 수집 오류"]+=1
        else:counts["기타/확인 필요"]+=1
    return " · ".join(f"{esc(k)} {v}건" for k,v in counts.items()) or "없음"
coverage=fnum(status.get("coverage_pct"))
if not coverage and status.get("universe"):coverage=100*fnum(status.get("success"))/fnum(status.get("universe"))
st=status.get("full_scan","미실행")
quote_date=status.get("data_date") or "확인 불가"
date_warn="후보 시세일 혼재 — 종목별 기준일 확인 필요" if len(status.get("candidate_quote_dates",[]))>1 else "시세일은 종목별 카드에서 확인하세요."
document=f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0b1220"><title>KRX 급등 전조 Radar</title>
<style>
:root{{color-scheme:dark;font-family:system-ui,-apple-system,'Noto Sans KR',sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;background:#0b1220;color:#eaf0fa}}
main{{max-width:880px;margin:auto;padding:18px 14px 70px}}h1{{font-size:25px;margin:10px 0}}h2{{font-size:19px;margin:26px 0 12px}}
p{{line-height:1.6}}.muted,.meta,.foot{{color:#a7b6cb}}.meta{{font-size:12px;margin-top:5px}}
.panel,.stock{{background:#19263c;border:1px solid #354760;border-radius:17px;padding:18px;margin:12px 0}}
.status{{display:flex;justify-content:space-between;gap:12px;align-items:center}}.tag{{background:#534225;color:#ffdd88;border-radius:30px;padding:5px 10px;font-size:12px;white-space:nowrap}}
.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:15px 0}}
.metrics div,.stats div{{background:#101d30;border-radius:12px;padding:12px 9px}}label{{display:block;font-size:11px;color:#aab9ce;margin-bottom:6px}}
.metrics strong{{font-size:23px}}.progress{{height:8px;background:#334258;border-radius:10px;overflow:hidden}}
.progress>div{{height:100%;background:#53bb8b}}.stockhead{{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}}
.ticker{{font-size:18px;font-weight:750}}.ticker small{{font-size:12px;color:#b5c5d8}}.watch{{font-weight:700;color:#ffd15c}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:18px 0}}
.stats strong{{font-size:16px;white-space:nowrap}}.prices{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}
.prices>div{{background:#101d30;padding:13px;border-radius:12px}}.prices b{{font-size:18px}}
.prices small{{display:block;color:#9db0c8;margin-top:4px}}.gate{{margin:16px 0 9px;padding:10px 12px;background:#352d24;border-radius:10px;color:#ffdfaa;font-size:13px}}
.foot{{font-size:12px;line-height:1.6}}.empty{{padding:22px;border:1px dashed #415570;border-radius:12px;color:#9fb0c6}}
.links{{display:flex;gap:10px;flex-wrap:wrap}}a{{color:#9fcbff}}.links a{{padding:10px;border:1px solid #405671;border-radius:10px;text-decoration:none}}
.note{{font-size:12px;color:#c3a974}}@media(max-width:370px){{.metrics strong{{font-size:18px}}.stats strong{{font-size:13px}}}}
</style></head><body><main>
<div class="muted">KOSPI · KOSDAQ | 일봉 기반 관찰 후보</div><h1>급등 전조 Radar</h1>
<div class="muted">실행 {esc(status.get("timestamp_kst","미확인"))} · 데이터 기준 {esc(quote_date)}</div>
<section class="panel"><div class="status"><strong>전수 스캔 상태</strong><span class="tag">{esc(st)}</span></div>
<div class="metrics"><div><label>대상</label><strong>{num(status.get("universe"))}</strong></div>
<div><label>성공</label><strong>{num(status.get("success"))}</strong></div>
<div><label>실패</label><strong>{num(status.get("failed"))}</strong></div></div>
<div class="progress"><div style="width:{max(0,min(100,coverage)):.2f}%"></div></div>
<p class="muted">커버리지 {coverage:.1f}% · {esc(date_warn)}</p>
<p class="note">분석 성공과 수익 예측 정확도는 무관합니다. 실패 {num(status.get("failed"))}종목은 후보 평가에서 제외되었습니다.</p></section>
<h2>A그룹 · 유동성 우선</h2>{group_cards("A")}
<h2>B그룹 · 변동성 주의</h2>{group_cards("B")}
<section class="panel"><h2>데이터 품질·검증</h2><p>실패 분류: {failure_summary()}</p>
<p class="foot">모든 후보는 WATCH입니다. 장중 5가지 조건의 실시간 검증 기능은 연결되어 있지 않습니다. 100점은 자체 점수 상한이며 상승 확률이 아닙니다. 1차·2차 목표가는 모형 가정으로 수익을 보장하지 않습니다.</p>
<div class="links"><a href="run_status.json">실행 상세</a><a href="all_scores.csv">전체 점수</a><a href="failures.csv">실패 내역</a></div></section>
</main></body></html>"""
(root/"index.html").write_text(document,encoding="utf-8")
print("Dashboard generated:",len(all_rows),"candidates",len(failures),"failures")
