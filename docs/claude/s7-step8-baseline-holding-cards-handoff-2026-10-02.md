# S7 5.4-8 보유 종목 기준 카드 — 새 작업 인계 (2026-10-02)

- 목적: S7 적용 시작 뒤 보유 3종목(MVLL·SOXL·NBIS)의 기준 카드를 1회 쓴다(S7 보고 5.4-8, R5 기준 고점의 출발점 기록).
- 권장 설정: Sonnet · high (보유 카드 = 포트폴리오 분석). 새 작업에서 시작한다.
- 새 작업 첫 메시지 예: `S7 5.4-8 기준 카드 진행. docs/claude/s7-step8-baseline-holding-cards-handoff-2026-10-02.md 읽고 시작`
- 권한: 주문·수량 권한 없음. 카드는 판단 근거 기록이며 매매 지시가 아니다. 위험 한도는 검토만 연다(`trade-evidence-principle-2026-10-01.md`).

## 1. 지금 상태 (2026-10-02 13:45 KST)

| 항목 | 값 | 출처 |
|---|---|---|
| 적용 시작 기록 | 확인 기록 1번 s5_activation, 적용일 2026-10-01, HWM 29127.99, 기준 상태 revision 16 | `stock-strategy-system/decision_journal.json` |
| 상태 파일 | revision 17(10/02 대조, 보유·평단·현금 일치) | 대조 원장 |
| 노출 점검(평가 세션 10/01) | 검토선 EVALUATED, L1까지 10.0%. N 2.29, V 2.91(수익률 126개, 짧은 이력), 실질 2.91 → HARD_CEILING, 신규 매수 권고 멈춤 | 아래 점검 파일 |
| 줄이기 권고(표시 전용, 긴급) | ① MVLL 비중 50.0% → 20%(종목 상한 0.4배 초과) ③ SOXL | 같음 |
| R5 기준 고점(10/01 종가) | MVLL 36.79 → 점검선 25.753 / SOXL 153.75 → 107.625 / NBIS 232.46 → 162.722 | 같음 |
| 1단계 운용 | 새 노출·검토선은 표시 전용. 옛 원가 한도(HR-*-MAXLOSS)와 슬롯 알림은 2단계 전까지 그대로 켜져 있다 | S7 보고 |
| 알려진 보류 | 평가 세션 10/02부터 "거래내역 증거 없음" 보류(revision 17에 증거 없음). 다음 대조(증거 10/02~대조일)에서 해소 | S7 보고 7번 |

입력 파일:

- 노출 점검(적용 시작 뒤, 세션 10/01): `workspace/outputs/exposure-review/2026-10-01/portfolio-exposure-review.20261002T044548628715Z.json`
- 수동 분석(13:24 KST): `workspace/outputs/manual-portfolio-analysis/manual-20261002T042421103871Z-2a49b44cb4f7/manual-portfolio-analysis.json` — `broker_diff_status` MATCH, preflight FAIL(9/30부터 같은 알려진 문제, `preflight-fail-diagnosis-2026-09-30.md`) → 증거 등급 UNVERIFIED, 확신도 낮음 상한.
- 지금 카드 묶음(사용자 수락, v2): `docs/claude/integrated-stock-cards-v1-2026-10-02.md`. 그 안의 "S5(미적용)" 문구와 "S7 때 R5로 대체" 문구가 이번에 바뀌는 곳이다.

## 2. 할 일

1. fact pack을 만든다(노출 점검 블록 포함):
   `python manage-us-stock-strategy/scripts/build_holding_fact_pack.py --analysis <수동 분석 파일> --output-dir workspace/outputs/holding-cards/2026-10-01-s7 --exposure-review <노출 점검 파일>`
2. 보유 3종목 카드를 v2 형식으로 다시 쓴다. 바뀌는 것만 고친다:
   - 규칙 결과: S7 1단계 적용(표시 전용) 사실, R5 기준 고점·점검선, 종목 상한 0.4배와 줄이기 권고 순서, 옛 원가 한도는 2단계 전까지 유지.
   - 트리거 표: R5(고점 −30% → 카드 다시 쓰기, 추가 매수 권고 멈춤) 줄 추가. 나머지 트리거는 수락본 유지.
   - MVLL은 10/15 KST 기한의 MVLL·SOXL·현금 상대 비교 카드(E2)와 연결만 적는다(이번에 상대 비교를 쓰지 않는다).
3. `validate_holding_card.py`로 검사하고 `render_holding_cards.py`로 표시한다.
4. 사용자 수락을 받은 뒤 S7 보고 5.4-8에 결과를 적는다. 다음은 5.4-9 매 세션 루틴(30분봉 → 이력 `--update` → 거래내역 원문 저장 → 증거 → 대조 → 노출 점검).

## 3. 주의

- 거래내역 원문 저장은 대조 제안·수동 분석보다 먼저 한다. 그 둘이 키움 토큰을 새로 받아 kiwoomcli 토큰이 무효가 된다(8005). 필요하면 `kiwoomcli auth login` → 2번(토큰만 다시 발급).
- kiwoomcli 종료 코드 0은 성공 뜻이 아니다. 정규화 결과로 판단한다.
- 대조 apply와 확인 기록 apply는 사용자가 이 대화에서 "확인 <코드>"를 보냈을 때만 한다.
