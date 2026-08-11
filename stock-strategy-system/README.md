# Codex 미국 주식 전략·알림 시스템

## 현재 결론

이 시스템은 미국 주식·ETF 분석, 기술적 매매계획, 옵션 보조분석, 보유위험 점검과 미국장 마감 후 알림을 하나의 Codex Skill로 연결합니다. 주문을 실행하거나 예약하지 않으며 모든 알림은 다음 정규 세션에 사용자가 검토할 후보입니다.

현재 운영 모드는 `leveraged_holding_risk_and_watchlist`이며,
`2026-08-05-ema-timing-v2`가 B등급 다음 세션 검토용으로 활성화되어 있습니다.

- 전체 보유: SOXL 99주, 평균단가 USD 123.32
- 전체 보유: MVLL 396주, 평균단가 USD 41.78
- 브로커 현금 및 신규매수 가용현금: USD 0
- 기준시각: 2026-07-31 15:48 KST
- 신규 관찰목록: DRAM, NBIS, BE, SOXL

이전 배당·코어 ETF 단계별 전환전략은 삭제되지 않았으며 state와 policy의 `archived_prior_strategy`에 보존됩니다. 현재 운영에는 사용되지 않습니다.

## 운영 파일

- `portfolio_state.json`: 사용자 확인 보유수량, 평균단가, 현금 및 상태 개정번호
- `alert_policy.json`: SOXL·MVLL 하드위험·EMA 분할규칙과 신규매수 관찰정책
- `alert_runtime_state.json`: 처리 세션, 이벤트 상태, 중복방지 및 감사기록만 저장
- `AUTOMATION_PROMPT_EN.md`: 반복 실행 Agent 지침
- `CURRENT_STRATEGY_2026-08-05.md`: 활성 EMA 검증·분할감축·기술손절·신규후보 관찰 기준
- `CURRENT_STRATEGY_2026-07-31.md`: 이전 전략 스냅샷(비운영 기록)
- `TRADINGAGENTS_INTEGRATION_2026-07-31.md`: 역할분리 연구층과 결정론적 하네스 설계 근거
- `market_snapshot.example.json`: 시장 스냅샷 예시
- `../manage-us-stock-strategy`: Skill 개발본

설치 Skill 경로는 `C:\Users\금동한\.codex\skills\manage-us-stock-strategy`입니다.

## 보유위험 규칙

위험선은 브로커에서 확인된 평균단가와 사용자가 정한 최대 허용손실의 크기로 계산합니다.

```text
정확한 위험선 = 평균단가 × (1 - 최대손실률)
```

- SOXL: `123.32 × 0.80 = 98.656`
- MVLL: `41.78 × 0.40 = 16.712`

완료된 미국 정규장 종가가 정확한 반올림 전 위험선 이하이면 `D` 위험검토 이벤트가 발생합니다. 이 값은 자동 손절가나 주문이 아닙니다. 비교는 반올림 전 값을 사용하고 표시에만 통화 형식을 적용합니다.

SOXL의 기본방향은 보유이고 MVLL의 기본방향은 감축입니다. SOXL은
`24/24/24주` 공유 슬롯과 27주 최종 잔여, MVLL은 `99/99/99/99주`
공유 슬롯을 사용합니다. 강세·약세 경로는 같은 슬롯을 소비하며, 앞 슬롯의
체결이 명시적으로 확인되기 전에는 다음 슬롯이 열리지 않습니다. 모든 후보는
`actionable=false`인 B등급 검토이며 주문이 아닙니다.

EMA 판단 전에는 10EMA·20EMA·ATR14 공식, 최근 완료봉 신호 플래그,
공식 거래일, 조기폐장, 기업행위, 독립 두 번째 종가를 매번 검증합니다. SOXL은
SOXX, MVLL은 MRVL의 동일 방향까지 확인합니다. 기술 검증 실패는 EMA 후보만
중단하며 원시종가 하드위험 검토를 숨기지 않습니다.

## 신규 관찰목록과 현금 게이트

DRAM, NBIS, BE, SOXL은 현금 USD 0인 동안 전부 `actionable=false`, `quantity=null`인 관찰항목입니다. 현금이 생기는 것만으로 매수후보가 활성화되지 않습니다. 다음 항목이 추가로 승인돼야 합니다.

1. 실제 매수할 정확한 종목
2. 레버리지 상품을 사용할 경우 정확한 티커와 공식 상품 검증
3. 진입규칙 또는 가격밴드
4. 포지션 크기 또는 거래당 위험예산
5. 최대손실 규칙

`레버리지 가능`이라는 선호는 Codex가 임의의 레버리지 티커를 선택할 권한이 아닙니다.

## 자동 알림

자동 점검은 공식 미국 거래일 달력으로 최신 완료 정규장을 검증한 후 실행합니다. 새 모드에서는 다음 순서가 고정됩니다.

1. 세션·상태·보유정보 검증
2. SOXL·MVLL 보유위험 계산
3. 10EMA·20EMA·ATR14 및 최근 완료봉 신호 재검산과 독립 종가 대조
4. SOXL/SOXX, MVLL/MRVL 확인 후 최상위 미완료 분할슬롯 평가
5. DRAM·NBIS·BE·SOXL 비실행 관찰목록 표시
6. D/B 이벤트 중복제거
7. runtime 메타데이터만 원자적으로 저장

보유종목의 종가·평균단가·동일세션 여부·기업행위에 문제가 있으면 F로 동결합니다. 관찰종목 하나의 데이터가 없으면 그 항목만 비활성화하고 보유위험 평가는 계속합니다.

보유상태 스냅샷이 정책의 4일 유효기간보다 오래되면 F로 동결하므로 주기적인 사용자 재확인 또는 검증된 읽기 전용 브로커 스냅샷이 필요합니다.

## 역할분리 연구와 결정론적 하네스

중대한 전략 변경이나 상충하는 뉴스가 있을 때는 TradingAgents에서 참고한 역할분리 구조를 사용합니다. 데이터 감사, 펀더멘털·밸류에이션, 기술, 뉴스·매크로, 강세·약세 반론, 독립 위험검토, 종합 역할을 분리하되 다수결로 매매를 결정하지 않습니다.

LLM의 구조화 제안도 신뢰하지 않고 `validate_research_packet.py`로 시점·근거 ID·보유수량·현금·레버리지 승인·정책 규칙을 먼저 검증합니다. 검증기는 `rejected`, `watch_only`, `eligible_for_alert_engine`만 반환하며, 마지막 상태도 주문 승인이 아닙니다. 실제 경보 등급은 별도의 `evaluate_alerts.py`가 결정하고 사용자가 최종 판단합니다.

일상적인 E 무신호 점검에는 다중 Agent 토론을 실행하지 않습니다. 새로운 D 위험이벤트나 실질적인 기업·섹터 사건처럼 정성적 문맥이 결정에 영향을 줄 때만 제한적으로 사용합니다.

정성적 전략 검토는 `research-lifecycle.md`의 반복 구조를 사용합니다. 최신 뉴스와 근거 조사 → 가장 강한 반대논리 → 상승·기본·하락 시나리오 → 거래 전 투자논리와 무효화 기준 기록 → 로컬 감사자료 공개 → T+5/T+20/T+60 및 촉매일 사후평가 순서입니다. `validate_research_cycle.py`가 누락된 반대논리·시나리오·무효화 기준과 사후적으로 바뀐 판단기록을 거부합니다. 외부 공개나 주문 실행은 별도 권한 없이는 수행하지 않습니다.

## 안전 원칙

1. 가격이 위험선이나 밴드에 닿아도 체결로 간주하지 않습니다.
2. 보유수량·현금·평균단가는 사용자 확인 또는 검증된 읽기 전용 브로커 자료로만 바꿉니다.
3. 미체결 매도대금, SGOV, 마진 또는 미래 입금은 가용현금으로 계산하지 않습니다.
4. 자동 실행은 `alert_runtime_state.json`만 변경할 수 있습니다.
5. 어떤 스크립트도 브로커 주문 기능을 갖지 않습니다.
6. 모든 이벤트는 다음 세션의 사람 검토용이며 주문은 실행·예약되지 않습니다.

## 자체 테스트

다음 명령은 구형 정책 하위호환, 하드위험 경계, EMA 신호 재계산,
공유 트랜치 상태, 독립종가 실패, 현금 게이트를 함께 검증합니다.

```powershell
python manage-us-stock-strategy/scripts/evaluate_alerts.py --self-test
python manage-us-stock-strategy/scripts/validate_research_packet.py --self-test
python manage-us-stock-strategy/scripts/validate_research_cycle.py --cycle <cycle.json> --packet <research_packet.json>
python manage-us-stock-strategy/scripts/resolve_leveraged_quote.py --help
python manage-us-stock-strategy/scripts/build_market_snapshot.py --self-test
python manage-us-stock-strategy/scripts/validate_technical_snapshot.py --self-test
python manage-us-stock-strategy/scripts/timing_engine.py
python manage-us-stock-strategy/scripts/option_analyzer.py --self-test
python -m unittest discover -s manage-us-stock-strategy/tests -v
```
