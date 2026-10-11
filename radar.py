import datetime as dt, json, math, os, traceback
from pathlib import Path
import pandas as pd
import numpy as np
import FinanceDataReader as fdr

OUT=Path("site"); OUT.mkdir(exist_ok=True)
now=dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
status={"timestamp_kst":now.isoformat(),"full_scan":"미실행","universe":0,"success":0,"failed":0,"source":"FinanceDataReader public feeds","data_date":None}
def save(items=[],errors=[]):
    (OUT/"run_status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
    pd.DataFrame(errors,columns=["code","error"]).to_csv(OUT/"failures.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(items).to_csv(OUT/"all_scores.csv",index=False,encoding="utf-8-sig")
    cards=""
    for r in sorted(items,key=lambda x:x["score"],reverse=True):
        if r["rank"]>3:continue
        cards+=f'<article><div class="top"><b>{r["group"]}그룹 · {r["name"]} ({r["code"]})</b><span>WATCH</span></div><p>종가 {r["close"]:,}원 · 점수 {r["score"]}/100 · 상대거래량 {r["rvol"]:.2f}배</p><p>조건부 진입 {r["entry"]:,}원 · 손절 {r["stop"]:,}원</p><p>1차 목표 {r["target1"]:,}원 · 2차 목표 {r["target2"]:,}원</p><small>일봉 후보 탐지용. 장중 진입 신호 미검증, 자동매수 아님.</small></article>'
    css='body{font-family:system-ui,sans-serif;background:#0b1220;color:#e5eefc;margin:0;padding:18px;max-width:760px;margin:auto}h1{font-size:24px}article{background:#19243a;border:1px solid #30405a;border-radius:16px;padding:17px;margin:13px 0;line-height:1.8}.top{display:flex;justify-content:space-between;gap:10px}span{color:#facc15}small,.muted{color:#a9b8cd}a{color:#93c5fd}'
    html=f'<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KRX 급등 전조 Radar</title><style>{css}</style><h1>KRX 급등 전조 Radar</h1><p class="muted">분석시각 {status["timestamp_kst"]} · 시세일 {status["data_date"] or "확인 불가"}</p><article>전수 스캔: <b>{status["full_scan"]}</b><p>대상 {status["universe"]} · 분석 성공 {status["success"]} · 실패 {status["failed"]}</p><small>출처: {status["source"]}. 종가 기준 분석으로 실시간 매수 신호가 아닙니다.</small></article>{cards or "<article>검증된 후보 없음. 매수 추천을 제공하지 않습니다.</article>"}<p><a href="run_status.json">실행 상태</a> · <a href="all_scores.csv">전체 점수 CSV</a> · <a href="failures.csv">실패 내역</a></p></html>'
    (OUT/"index.html").write_text(html,encoding="utf-8")
def tick(p):
    return 1 if p<2000 else 5 if p<5000 else 10 if p<20000 else 50 if p<50000 else 100 if p<200000 else 500 if p<500000 else 1000
def rnd(p):
    return int(round(p/tick(p))*tick(p))
items=[];errors=[]
try:
    universes=[]
    for market in ["KOSPI","KOSDAQ"]:
        d=fdr.StockListing(market)
        code="Code" if "Code" in d else "Symbol"
        if code not in d or "Name" not in d:raise RuntimeError("listing schema missing "+market)
        d=d[[code,"Name"]].rename(columns={code:"code","Name":"name"})
        d["market"]=market;universes.append(d)
    u=pd.concat(universes,ignore_index=True)
    u["code"]=u.code.astype(str).str.zfill(6)
    u=u[u.code.str.fullmatch(r"\d{6}")].drop_duplicates("code")
    u=u[~u.name.astype(str).str.contains(r"스팩|SPAC|ETF|ETN|리츠|REIT|인버스|레버리지|우선주|\d우(?:B|C)?$",case=False,regex=True)]
    status["universe"]=len(u)
    if len(u)<1500:raise RuntimeError("universe too small: "+str(len(u)))
    end=(now+dt.timedelta(days=1)).date().isoformat()
    start=(now-dt.timedelta(days=130)).date().isoformat()
    for idx,row in enumerate(u.itertuples(index=False),1):
        try:
            d=fdr.DataReader(row.code,start,end)
            if d is None or len(d)<45:raise ValueError("insufficient candles")
            d=d.sort_index().dropna(subset=["Close","High","Low","Volume"])
            if len(d)<45:raise ValueError("insufficient valid candles")
            c=d.Close.astype(float);v=d.Volume.astype(float);h=d.High.astype(float);l=d.Low.astype(float)
            if c.iloc[-1]<=0 or v.iloc[-1]<=0:raise ValueError("bad latest quote")
            last=float(c.iloc[-1]);prev=float(c.iloc[-2]);rv=float(v.iloc[-1]/max(v.iloc[-21:-1].mean(),1))
            value=last*float(v.iloc[-1]);volatility=float((h.iloc[-21:-1].max()-l.iloc[-21:-1].min())/max(l.iloc[-21:-1].min(),1))
            ret5=float(last/c.iloc[-6]-1);ret20=float(last/c.iloc[-21]-1)
            breakout=float(last/max(h.iloc[-21:-1].max(),1))
            score=round(max(0,min(100,45+min(rv,4)*9+min(ret20,0.2)*75+min(ret5,0.1)*50+(8 if 0.94<=breakout<=1.03 else -8)-(12 if volatility>0.55 else 0))),1)
            if value<500_000_000 or abs(last/prev-1)>0.08:continue
            group="A" if value>=3_000_000_000 and volatility<0.40 else "B"
            stop=rnd(last*(0.95 if group=="A" else 0.93))
            entry=rnd(last*1.01); risk=max(entry-stop,tick(entry))
            items.append(dict(code=row.code,name=row.name,market=row.market,group=group,score=score,close=int(last),rvol=rv,entry=entry,stop=stop,target1=rnd(entry+1.5*risk),target2=rnd(entry+2.5*risk),date=str(d.index[-1].date())))
        except Exception as e:errors.append((row.code,str(e)[:140]))
    status["success"]=len(u)-len(errors);status["failed"]=len(errors)
    dates={r["date"] for r in items}
    status["data_date"]=max(dates) if dates else None
    status["full_scan"]="완료" if not errors and status["success"]==len(u) else "부분 실행 (전수 완료 아님)"
    for group in ["A","B"]:
        subset=sorted((x for x in items if x["group"]==group),key=lambda x:x["score"],reverse=True)
        for n,r in enumerate(subset,1):r["rank"]=n
except Exception as e:
    status["full_scan"]="미실행";errors.append(("SYSTEM",str(e)[:300]))
finally:save(items,errors)
