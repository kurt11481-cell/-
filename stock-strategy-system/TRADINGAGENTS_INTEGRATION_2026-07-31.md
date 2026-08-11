# TradingAgents 통합 검토 — 2026-07-31

## 최종 결론

TradingAgents의 가장 유용한 부분은 여러 LLM에게 주문 권한을 주는 것이 아니라, 비정형 증거를 역할별로 분리하고 강세·약세 논리를 충돌시켜 누락을 줄이는 구조다. 기존 Skill에는 이 연구 구조만 흡수했고, 숫자·상태·위험·수량·허용 상품·중복 경보는 결정론적 코드가 통제하도록 분리했다.

```text
공시·뉴스·시장 문맥
→ 역할별 연구와 Bull/Bear 반론
→ 구조화된 research packet
→ 결정론적 packet 검증
→ 기존 alert evaluator
→ 사용자 검토
```

어느 단계도 브로커 주문을 만들거나 예약하지 않는다.

## 채택한 요소

- 데이터·펀더멘털·기술·뉴스 역할 분리
- Bull/Bear 반론과 독립 위험 통제자
- 증거 ID와 분석시점이 포함된 evidence ledger
- 구조화된 역할 출력과 명시적 미확인 항목
- 정책·상태·스냅샷 해시 및 결정 로그
- 동일 주장만 반복하는 토론의 라운드 제한

## 채택하지 않은 요소

- LLM 또는 다수결을 최종 매매 권한으로 사용
- 자유문장 출력의 자동 실행 대체
- 실시간 소셜 데이터를 과거시점 증거로 재사용
- 현금·보유·체결·손절수량을 LLM이 추정
- 변경 없는 일상 점검에서 매번 다중 Agent 실행

## 결정론적 하네스

`validate_research_packet.py`는 다음을 실패 폐쇄 방식으로 검사한다.

- 스키마, 티커 정체성, 전략 버전, 상태 개정번호
- 완료 세션, 공식 달력 검증, 생성·검색·효력 시점
- evidence source tier와 role/claim 연결
- 보유수량, 평균단가, 현금, 보유위험 입력
- 정책에 등록된 상품 유형과 신규매수 권한
- 정책 rule ID, 허용 action, 명시적 quantity authority
- 정책·상태·시장 스냅샷의 canonical hash
- 입력파일과 출력파일 경로 분리 및 원자적 저장

현재 모든 신규 후보는 `watchlist_approved=true`, `new_buy_instrument_approved=false`다. 후보로 연구하는 것과 매수를 승인하는 것을 분리한다. 최대손실 review rule도 `quantity_authority=none`이므로 매도 수량을 만들 수 없다.

## 현재 포트폴리오 적용

- SOXL: 기본 보유, 평균단가 기준 -20% 경계 `98.656`; 신규 추가매수는 비승인
- MVLL: 감축 방향, -60% 경계 `16.712`; 감축 수량·조건은 비승인
- 현금: USD 0
- DRAM·NBIS·BE·SOXL 신규매수: 전부 관찰 전용

따라서 현재 검증 결과는 MVLL 감축계획을 구체화해야 한다는 `B` 검토이며, `quantity=null`, `actionable=false`다.

## 참고와 제한

참고 구조는 TradingAgents 저장소의 2026-07 기준 main 검토본과 논문에서 가져왔다.

- https://github.com/TauricResearch/TradingAgents/tree/main
- https://github.com/TauricResearch/TradingAgents/commit/a33fd4c0f134485a43553a2c23a63cb14adbd88f
- https://arxiv.org/abs/2412.20138

TradingAgents 자체도 LLM·데이터·기간에 따른 비결정성을 명시한다. 이 통합은 해당 프레임워크를 자동매매 엔진으로 설치한 것이 아니며, 첨부 ZIP의 코드를 실행하거나 브로커와 연결하지 않았다. 정성적 연구는 여전히 틀릴 수 있으므로 결정론적 검증은 논문의 진위를 보장하지 않고, 구조·시점·정책 적합성만 보장한다.
