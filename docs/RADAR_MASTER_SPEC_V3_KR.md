# KRX + US PRE-BREAKOUT RADAR — MASTER DEVELOPMENT SPEC v3.0
작성일: 2026-10-19
상태: 개발 명세 / 실제 데이터 및 수익성 검증과 구별
원칙: FREE_ONLY, RESEARCH_ONLY, FAIL_CLOSED, NO_FABRICATED_RECOMMENDATIONS

## 0. 절대 원칙
1. 목적은 투자 대가의 공식을 복제하는 것이 아니라 급등 전후의 실증 패턴을 데이터로 발견하는 것이다.
2. 과거 급등주만 선별해 학습하지 않는다. 동일 날짜 전체 시장의 비급등·하락·상장폐지 종목을 음성 사례로 포함한다.
3. 정보의 '발생일'과 '실제로 공개된 시각(available_at)'을 분리한다. 모델 입력은 신호시각 이전에 공개된 정보만 사용한다.
4. 현재 상장 목록은 역사적 상장 목록이 아니다. 상장폐지 이력이 없는 기간의 백테스트에는 생존편향 경고를 표시한다.
5. 무료 공개 데이터라도 이용약관·API 호출 제한·재배포 권한을 확인한다. 유료 API는 기본 실행 경로에서 사용하지 않는다.
6. 투자 주문 기능은 기본적으로 비활성화한다. 실제 체결 가격을 확인하기 전에는 '매수 완료'를 표시하지 않는다.
7. 실시간, 장전, 지연, 종가, 수정종가, 추정값을 명확히 구별한다.
8. 추천 정확도·수익률은 관측값이 있을 때만 표시한다.

## 1. 시장·종목 범위
- 한국: KOSPI + KOSDAQ. KIS API 인증·일별/장중 데이터 활용, 접근 가능한 투자자 수급 별도 수집.
- 미국: NASDAQ + NYSE + NYSE American 및 공개 목록으로 확인되는 적격 종목.
- 현재 목록: Nasdaq Trader nasdaqlisted.txt, otherlisted.txt. 날짜별 스냅샷을 저장하여 이후의 상장/상장폐지 이력을 누적한다.
- 과거 전체 목록: 무료 소스에서 확보한 과거 티커·상장·상장폐지·티커 변경 이벤트를 별도 테이블로 관리. 무료 소스로 누락 시 coverage_gap으로 표기.
- ETF, ETN, 우선주, 워런트, SPAC, ADR, 보통주를 분류하고 전략별 포함 정책을 명시한다. 유동성이 낮은 주식은 연구 데이터에서는 보존하고 실전 후보 필터에서만 제외한다.
- 고정된 대형주 25개 목록은 회귀테스트용으로만 유지한다. 전체 시장의 대체물이 아니다.

## 2. 무료 데이터 소스
1. 종목 디렉터리: Nasdaq Trader 공개 파일. 현재 시점 스냅샷.
2. 한국 시세: KIS 해외/국내 주식 API 중 계정 권한으로 무료 이용 가능한 엔드포인트. KIS 해외 데이터의 종목·기간·호출 제한 검증.
3. 미국 일별 시세: 무료로 접근 가능한 허용된 공급원(예: Stooq 또는 계정이 허용하는 KIS 시세)을 어댑터 방식으로 사용. 공급원별 누락, 수정주가, 분할·배당 조정 여부를 검증한다. 무료 공급원만으로 수년치 전체 종목/상장폐지 이력을 확보하지 못하면 coverage에 기록한다.
4. 미국 공시: SEC EDGAR submissions, companyfacts, filing metadata. User-Agent, 이용규칙 준수. 공시 게시 시각 기준 point-in-time join.
5. 거시환경: FRED 공개 시계열(필요시 무료 API 키), 지수·금리·수익률곡선·고용·물가. 발표 지연 및 개정값을 구별.
6. 시장/섹터: 무료로 확인 가능한 주요 ETF 및 지수의 가격과 거래량. ETF의 과거 종목구성 정보가 없으면 과거 섹터 구성으로 오인하지 않는다.
7. 기업 이벤트: 8-K, 10-Q, 10-K, Form 4, 증자·분할·합병·거래정지, 실적발표 시각.
8. 뉴스: 무료로 합법적으로 수집 가능한 제목·공개시각·원문 링크만 수집. 전체 본문 무단 복제 금지.
9. 유료 Massive/Polygon 등은 기본 워크플로에서 제외. 키가 없다는 이유로 자동 유료 결제나 구독을 유도하지 않는다.

## 3. 데이터 스키마
### securities
security_id, ticker, exchange, issuer_name, asset_type, currency, listing_date, delisting_date, valid_from, valid_to, source, observed_at, confidence.
ticker를 영구 식별자로 사용하지 말고 security_id를 기본키로 사용한다.
### daily_bars
security_id, session_date, open, high, low, close, volume, turnover, currency, adjustment_basis, source, retrieved_at, quality_flags.
### corporate_actions
security_id, action_type, ex_date, effective_date, split_ratio, cash_amount, announcement_at, source.
### filings
security_id, filing_type, accession_no, period_end, accepted_at, available_at, url, parsed_features, revision_id.
### market_context
session_date, market, benchmark_return_1d/5d/20d, market_breadth, new_highs, new_lows, realized_vol, vix, treasury_2y, treasury_10y, sector_returns, available_at.
### events
security_id, anchor_date, event_definition, forward_horizon, future_return, future_max_runup, future_max_drawdown, liquidity_bucket, label_available_at.
### predictions
prediction_id, security_id, market, signal_time, data_cutoff, model_version, universe_version, horizon, probability_raw, probability_calibrated, confidence_interval, expected_return, downside_risk, risk_flags, status.
### outcomes
prediction_id, observed_date, fill_assumption, actual_return, maximum_adverse_excursion, maximum_favorable_excursion, fees, slippage, evaluation_status.

## 4. 급등 사건(Event) 정의
복수 사건 정의를 병행하며 결과를 혼합하지 않는다.
A: 다음 1거래일 종가 +8% 이상
B: 다음 3거래일 종가 +12% 이상
C: 다음 5거래일 종가 +15% 이상
D: 다음 10거래일 종가 +20% 이상
E: 다음 20거래일 중 최고가 +30% 이상(장중 최고가 기준, 체결 가능성과 구분)
- 액면분할·역분할·배당·합병에 따른 기계적 가격변동을 보정한다.
- 같은 종목에서 겹치는 사건은 중복 표본으로 취급하지 않거나 클러스터 그룹을 부여한다.
- 1달러 미만 초저가주, 저유동성 종목, 대형주를 분리 평가한다.
- 이벤트 발생 뒤 발표된 기사나 공시를 원인으로 사후 단정하지 않는다. 설명은 '확인된 촉매'와 '통계적 연관'을 구분한다.

## 5. 급등 이전 역산 특징
### 가격·거래량
- 수익률 1/3/5/10/20/60일, 갭, 변동성, ATR, 거래량 RVOL, 거래대금, 체결 가능한 유동성.
- 변동성 압축 5/10/20/60일, 고점 대비 거리, 신고가 접근, 추세 기울기, VWAP(분봉이 있을 때만).
- 급등 전 1/3/5/10/20/60거래일의 특징을 시점별 스냅샷으로 저장.
### 시장환경
- SPY/QQQ/IWM 수익률, VIX 변화, 금리 수준과 방향, 시장 상승종목 비율, 섹터 ETF 상대강도.
- 시장 전체 상승·하락·변동성 급등 구간(Regime) 구분.
### 기업환경
- 실적 서프라이즈, 매출/이익 증가율, 자금조달, 공시 이벤트, 내부자 매매 공시, 기업행동.
- 과거에 공개된 숫자만 사용; 보고기간 말일을 공개일로 잘못 취급하지 않는다.
### 상대적 특징
- 동일 섹터 동반 급등 빈도, 업종 대비 상대강도, 선행 종목의 확산, 시장과의 비동조.
### 위험
- 거래량 부족, 갭 과열, 가격 급등 후 추격, 희석 위험, 역분할, 거래정지, 급락 변동성.

## 6. 패턴 발견 방법
1. 기술통계: 사건별 조건부 분포, 분위수, 비사건 대조군과 차이.
2. 연관 규칙: 단일 지표가 아닌 특징 조합을 탐색하되 다중검정 오류와 데이터 스누핑을 관리.
3. 비지도 학습: 급등 직전 경로 클러스터링, DTW/시계열 특징, UMAP 등은 시각화·탐색용.
4. 지도 학습: 로지스틱 회귀(기준선), 랜덤포레스트, 히스토그램 그래디언트 부스팅.
5. 확률 보정: 학습과 분리된 검증 기간에서 isotonic/sigmoid calibration, reliability curve, Brier.
6. 모델 해석: permutation importance, SHAP(가능 시), 국소적 설명과 교란 요인 확인.
7. 과거의 유명 투자자 전략은 비교용 기준선이며 모델의 사전 정답으로 사용하지 않는다.
8. 신호는 '급등 가능성'과 '추격 위험'을 분리한다.

## 7. 편향·검증
- 5~10년 데이터 확보 시 연도별 walk-forward: 학습→검증→다음 기간 테스트→한 칸 이동.
- 시간 순서 분리, 레이블 기간 이상의 purge/embargo, 동일 사건 중복 제거.
- 종목별·시장규모별·유동성별·섹터별·시장 국면별 성능 공개.
- 검증 시 전체 상장종목의 실제 존재 시점과 상장폐지 이력을 반영한다. 미확보 시 '생존편향 있는 파일럿'이라고 표시.
- 주요 지표: precision@10/@20, recall, PR-AUC, ROC-AUC(보조), Brier, calibration error, 기대수익, 최대낙폭, 승률, 거래비용 후 수익률.
- 일일 추천 0건 허용. 충분한 데이터와 신뢰도 없는 날은 NO_SIGNAL.
- 유의미한 표본 수·신뢰구간을 공개한다. 검증된 수익률이 없으면 숫자를 만들지 않는다.
- 종가 시그널은 같은 날 종가 체결을 가정하지 않는다. 익일 시초가 또는 현실적인 지정가·슬리피지 가정으로 평가한다.

## 8. 일일 추천 카드
시장, 종목명/티커, 거래소, 신호 기준시각(KST/ET), 최근 실제 가격과 지연상태,
1/3/5/10일 급등 확률(검증 완료 모델만), 같은 조건의 과거 표본 수,
패턴 유사 사례 수, 근거 상위 3개, 시장/섹터 상황, 과열/유동성/희석 위험,
관심 진입구간, 손절·목표(가정과 손익비 명시), 실제 장중 5게이트 확인 상태,
데이터 커버리지, 모델 버전, 과거 예측 성과, 최종 상태:
RESEARCH_ONLY / WATCH / ENTRY_GATE_PENDING / ELIGIBLE / NO_SIGNAL.
실제 주문과 별도. 근거 없는 확률을 출력하지 않는다.

## 9. 장중 5게이트
1. 가격이 사전 정의한 진입구간에 위치
2. VWAP 위 또는 회복 확인(분봉 데이터 있는 경우)
3. 상대 거래량 기준 충족
4. 호가/스프레드/유동성 기준 충족(실시간 데이터 있을 때)
5. 시장·섹터 위험 조건 충족
확인할 수 없는 게이트는 UNKNOWN, 통과로 처리하지 않는다.

## 10. 데이터·작업 파이프라인
A. universe_discovery: 상장종목 목록 매일 갱신, 차분 스냅샷.
B. history_backfill: 무료 공급원별 API 어댑터, 일별/종목별 분할·재시도·체크포인트.
C. quality_gate: 결측/중복/극단치/기업행동/시차/티커 매핑 검증.
D. context_ingest: SEC/FRED/ETF 시장환경, available_at 관리.
E. event_mining: 미래 레이블과 사전 특징 생성.
F. pattern_research: 클러스터·통계 비교·기준선.
G. train_walkforward: 시계열 모델 검증과 확률 보정.
H. daily_rank: 당일 전수 스캔, 신뢰도 조건을 충족한 종목만 WATCH.
I. intraday_gate: 가능 시 장중 5게이트.
J. outcome_tracker: 추천 이후 1/3/5/10일 성과 누적.
K. dashboard: KR/US 탭, 발견 패턴, 예측 성과, 오류 및 데이터 품질.

## 11. 무료 인프라
- GitHub Actions: 작업 오케스트레이션. 무료 사용량·실행시간·호출량 제한을 모니터링.
- Python 3.11+, pandas, numpy, scikit-learn, requests, duckdb, pyarrow, pydantic, pytest.
- 원본 대량 데이터는 저장소에 직접 커밋하지 않는다. GitHub 저장소에는 코드·메타데이터·소형 요약만.
- 외부 저장소를 추가할 수 없으면 무료 한도 내 분할 배치/아티팩트와 로컬 보관을 사용. GitHub Actions 아티팩트는 영구 저장소가 아님.
- API 키는 GitHub Secrets, 로그 마스킹, 키 유출 금지.
- 기존 KIS 한국 Radar 운영을 중단하지 않고 미국 연구 파이프라인을 별도 구성.

## 12. 단계별 완료 조건
P0 코드 안정화: import/컴파일/pytest, 데이터 없음 시 실패 차단, 환경변수 점검.
P1 무료 전체 종목: Nasdaq Trader 파일 실제 수집, 종목 수·종목 유형·갱신 시각 출력.
P2 과거 가격: 무료 공급원 실제 연결, 1/3/5년 데이터의 종목·거래일 커버리지 수치 출력.
P3 기업행동/상장폐지: 기업행동 처리 및 누락 비율, 공급원별 이력 범위 공개.
P4 시장·산업·기업환경: SEC/FRED/ETF 데이터 실제 결합, 시각 누수 테스트 통과.
P5 급등 역추적: 이벤트별 샘플 수·대조군·환경 차이 자동 보고.
P6 ML: 시계열 홀드아웃, 기준선 대비 PR-AUC 및 precision@20 개선 여부 확인.
P7 추천: 하루 0~20종목, 후보/제외 이유, 시세 기준일, 오탐/손실 위험 표시.
P8 30거래일 가상매매: 매수 시점·거래비용·매도 규칙 고정 후 추적.
P9 전수 확대: 무료 API 호출 제한 내 전 종목 일일 갱신 완료율 확인.
P10 운영: 7일 연속 성공 실행, 오류 자동 알림, 일별 결과 아카이브.

## 13. 현재 구현 현황(2026-10-19)
- us_full_universe.py: 현재 상장종목 목록 수집 코드 등록; 실행 미검증.
- us_radar_pilot.py: KIS 해외 25종목 일별 수집 코드 등록; 실제 API 성공 미검증.
- us_radar_rank.py: 휴리스틱 점수/참고가격 연구 코드; 학습된 확률 모델 아님.
- us_reverse_breakout_study.py: 제한된 표본에 대한 역추적 코드; 실데이터 검증 미실시.
- us_full_market_research.py: 전체 시장 CSV 입력 ML 연구 코드; 전체 데이터 없음.
- us_massive_backfill.py: 유료 공급원용 코드 보관; FREE_ONLY 기본 실행에서 사용 금지.
- us_free_data_policy.py: 정책 파일; 정책 파일만으로 모든 워크플로를 차단하지는 못함.
- 기존 한국 KRX Radar 유지.
따라서 현시점에 '미국 전수 데이터 수집 완료', '실제 추천 정확도 검증 완료' 또는 '매수 추천 완료'를 선언하지 않는다.

## 14. 후속 개발자/AI 실행 지시
매 작업에서 (1) 현재 GitHub 파일·워크플로·실행 로그 확인, (2) 최소 변경으로 구현,
(3) 테스트/실제 수집 결과 확인, (4) GitHub 커밋, (5) 데이터 커버리지와 성능을 수치 보고한다.
기능 구현과 실행 검증을 별도 체크한다. 인증 실패/제한/라이선스 문제는 명확히 보고한다.
사용자가 요청하지 않은 유료 결제, 실주문, 비밀정보 노출은 금지한다.
