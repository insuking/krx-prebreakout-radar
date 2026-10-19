# Radar 코드 품질감사 — 2026-10-19

검사 범위: us_full_universe.py, us_radar_pilot.py, us_radar_rank.py,
us_reverse_breakout_study.py, us_full_market_research.py,
.github/workflows/us-full-universe.yml, .github/workflows/us-radar-pilot.yml.

## 판정
**RESEARCH_ONLY / NOT PRODUCTION READY**
검사 방법: GitHub 원본 소스 정적 검토 + Nasdaq Trader 공식 필드 명세 대조.
실제 API 응답, GitHub Actions 실행 로그, 실데이터 ML 학습 및 수익률은 검증하지 못함.
따라서 수집 성공률/적중률/수익률 숫자를 기재하지 않음.

## 발견
| ID | 심각도 | 내용 | 권고 |
|---|---|---|---|
| Q01 | CRITICAL | 미국 전체 5~10년 OHLCV 실데이터 없음 | 무료 데이터 어댑터 실제 연결 및 기간·종목별 커버리지 보고 |
| Q02 | CRITICAL | 상장폐지 포함 역사적 유니버스 없음 | historical membership, security_id 및 상장/상폐 이력 |
| Q03 | CRITICAL | 기업행동 미보정 시 급등 라벨 왜곡 | 분할·역분할 조정 및 품질 게이트 |
| Q04 | HIGH | 학습 코드의 실데이터 실행/정확도 미검증 | 시간순 홀드아웃, 기준선, 확률 보정 |
| Q05 | HIGH | 25종목 휴리스틱 WATCH를 학습된 확률과 혼동 위험 | 연구용 WATCH 명확 표시 |
| Q06 | HIGH | us_full_universe는 ADR을 이름 기준으로 제외할 수 있음 | asset_type 명시, 누락률 보고 |
| Q07 | HIGH | 무료 소스 사용권한/시차/기업행동 기준 미확인 | 공급원별 계약 및 메타데이터 |
| Q08 | MEDIUM | reverse study는 25종목 표본으로 전체 시장 일반화 불가 | 전체 시장 표본으로 재연구 |
| Q09 | MEDIUM | GitHub workflow가 연구 실패를 로그만 남기고 진행 | 검증 결과 status를 별도 저장, 추천 게시 중단 |
| Q10 | MEDIUM | 시장환경은 일부 breadth/dispersion만; 섹터/SEC/FRED 미결합 | available_at 기반 시점 결합 |
| Q11 | MEDIUM | 대형 일별 파일을 전부 pandas로 메모리에 적재 | DuckDB/Parquet 파티션, 메모리 상한 |
| Q12 | HIGH | 마지막 관측일이 과거인 종목도 최신 후보에 들어갈 수 있었음 | 마지막 전체시장 세션 기준 일치 필터 |

## 이번 수정
- Q03: US_CORPORATE_ACTIONS_VERIFIED=1 운영자 검증 플래그가 없으면 학습 거부.
  이 플래그는 보정 자체를 수행하지 않으며, 거짓으로 설정하면 안전을 보장하지 않음.
- Q03: open/high/low/close 가격 상하한 관계 검사 추가.
- Q12: 최신 거래일과 동일한 날짜인 종목만 후보에 포함.

## 완료 판정 게이트
1. 실제 데이터 수집: 수집 기간·종목·거래일·결측률·API 실패율 공개.
2. 기업행동: 무작위 표본 및 알려진 분할 이벤트에서 조정 검증.
3. 역사적 유니버스: 상장폐지 및 티커 변경의 포함률 공개.
4. 학습: 홀드아웃 PR-AUC/precision@20/Brier, 표본 수, 기준선, 신뢰구간 공개.
5. 운영: 7회 연속 성공 실행 및 재현 가능한 로그.
6. 추천: 데이터 최신성, 연구/검증 상태, 거래 비용 및 위험 표시.
7. 미충족 시 'NO_VERIFIED_SIGNAL' 유지.

감사 범위는 정적 코드 검토이며, 통합 테스트 통과로 오인해서는 안 됨.
