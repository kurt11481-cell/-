---
id: redesign-t2-builder-r2-2026-10-10
title: 재설계 T2 Builder 추가 지시 r2 — Judge FAIL 최소 수정 F-1~F-4 + "켜" 전 조건 묶음
date: 2026-10-10
from: docs/claude/redesign-t2-judge-report-2026-10-10.md (판정 FAIL, 3절 F-1~F-4 · 4절 조건 · 5절 다른 사실)
class: T2와 같음(권한·한도 변경). 범위·금지는 docs/claude/redesign-t2-builder-prompt-2026-10-10.md 4절 그대로(허용 경로 밖 변경 0)
authority: order_authority=false · execution_quantity=null · 주문표에만 quantity_authority="ORDER_TICKET_HUMAN_ENTRY"
consumers: T2 Builder(같은 worktree t2-core) · T2 Judge 2차(변경분) · 관제판 redesign-t2
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 기존 worktree `t2-core`에서 새 Claude Code 세션 · 이유: Judge FAIL의 최소 수정(같은 Builder 범위)**

## 사용자 조작 (Windows PowerShell, 한 번)
```
cd "E:\사업\##금동한\코덱스저장소\.claude\worktrees\t2-core"
claude --model opus --effort xhigh
```
첫 메시지로 이 한 줄만:
```
Read ../../../docs/claude/redesign-t2-builder-r2-2026-10-10.md and do sections 1-3 exactly.
```
끝나면 Cowork에 "T2 r2 완료"만 보낸다.

## 0. 왜

1차 Judge는 FAIL이다(주문 경로·체결 추정·기준값·등록부·황금 테스트·실자료 손계산은 모두 PASS). 실패는 둘이다. J6: 연구 기록이 없어도 지수 ETF(SOXL·TQQQ) 매수 주문표가 나온다. J10: 이른 HOLD/FAIL 날에 재발행 원장과 미분류 주문표가 끊긴다. R-REC1(G5) 결함도 둘이다: 그 세션의 EV4가 빠지고, 훼손 사실을 10기록일 창으로만 본다. Judge가 "켜" 전에 요구한 조건 1~5와 비교 모드 조건 1·3도 같은 파일·같은 범위라 이번에 함께 고친다(Builder·Judge를 한 번 더 돌리지 않으려는 것). 정책·상태·일지·.claude·CLAUDE.md·tools는 여전히 손대지 않는다.

## 1. 고칠 것

```
R2-1 (F-1, J6) 연구 기록이 OK가 아니면 모든 매수 차단
 - "연구 기록 OK" = 그날(KST) research-record.json이 있고, 스키마를 통과하고, written_at 검사(평가 세션 16:00 ET 이후 · decide 시각 이전)를
   통과함. 개별 항목이 검증에서 버려지는 것은 OK를 깨지 않는다.
 - OK가 아니면 모든 매수 후보(보유 추가·관심 신규·지수 ETF 포함)에 차단 사유 RESEARCH_RECORD_NOT_OK:<이유>를 붙인다. 매도 후보에는 붙이지 않는다.
 - 매수 요건 행 ①의 지수 ETF 칸도 연구 기록이 OK가 아니면 ok로 두지 않는다(no, 사유 같음) — 대조 B4로 분류되게.
 - 테스트: 연구 기록 없음 + SOXL에 새 + 가격 단서 2종류 → SOXL 매수 0·사유 확인 / 같은 조건의 매도 회로는 그대로 / 스키마 불통과 파일·written_at
   불통과도 같은 결과 / 항목 하나만 버려진 기록은 OK.

R2-2 (F-2, J10·K4) 재발행 원장·미분류 주문표가 실패 날을 건너 이어지게
 - decision.json에 f6_ran(bool)을 둔다. 다음 실행은 keys·open_tickets·아직 분류 안 된 tickets를 "f6_ran = true인 가장 최근 기록"에서 가져온다
   (그 사이 기록이 몇 개든).
 - F6 전에 끝나는 모든 기록(kill_switch, T1 없음·FAIL, 설정·프로필·달력 실패, DecideFailure, 예기치 않은 예외)도 그 출처 기록의 keys와 미분류 주문표를
   그대로 옮겨 적고 carried_from(출처 run_day)을 남긴다(사람이 볼 때도 끊겨 보이지 않게).
 - 미분류 주문표가 2개 이상의 실행일을 건너 남아 있으면 F6는 그 주문표들의 주문일 전부를 조회한다(ust21150, 주문일 = 각 발행 KST 날짜와 그다음 날).
 - 테스트: D apply 주문표 1건·닫힌 키 → D+1 T1 없음 HOLD → D+2에 D 주문표 분류·일지 기록, 닫힌 키 유지 / D+1이 예외 FAIL이어도 같음 / G0가 그 사이
   "빈 목록이라 통과"하지 않음.

R2-3 (F-3, G5) 그 세션의 EV4를 R-REC1에 넣는다
 - 계좌 EV4(총자산 ≤ V6 1차 선 25,626.55 또는 ≤ S7 hwm × 0.9)를 R-REC1 계산 전에 그 세션 값으로 구하고, 열렸으면 그 세션을 ev4_sessions에 넣은 뒤
   포트폴리오·종목별 충격을 계산한다. 리플레이도 같은 함수 한 곳을 쓴다(복제 금지).
 - 테스트: 직전 기록 없음 + 총자산 ≤ 1차 선 → shock open, 매수 요건 ⑤ ≠ ok, 매수 0.

R2-4 (F-4, G5) 훼손 사실을 R-REC1 창만큼 본다
 - RG1·EV3 ⓑ의 root_thesis_damage 사실은 최근 10기록일이 아니라 R-REC1 창(60세션)을 덮는 기간의 연구 기록 전부에서 모은다. C7용 10기록일은 그대로.
 - RG1(이벤트 뒤 훼손 공식 확인 없음): 이벤트 다음 세션 ~ 평가 세션의 모든 세션에 연구 기록(OK)이 있어야 판정한다. 하나라도 없으면 RG1 = unk
   (늘리는 매수 막힘). 결과에 rg1_coverage{from, to, missing_sessions[]}를 남긴다.
 - EV3 ⓑ: 창 안에서 기록이 있는 날만 보고, 첫 연구 기록 날짜를 ev3b_coverage_start로 남긴다. 그보다 앞 구간은 EV3 ⓐ(문서의 사용자 지정 날짜)가
   맡는다. 첫 기록 날짜 이후 기록이 빠진 날 중 SOXX 1일 수익률 ≤ −1σ60인 날(EV3 ⓑ가 열릴 수 있었던 날)이 창 안에 있으면 R-REC1 = unk로 두고
   늘리는 매수를 막는다(fail-closed). SOXX가 그보다 덜 빠진 날의 기록 누락은 EV3 ⓑ를 열 수 없으므로 판정에 영향이 없다(하루 누락이 60세션 동안
   모든 매수를 막지 않게).
 - 테스트: 이벤트 뒤 15기록일 전 훼손 사실 → RG1 no / 이벤트 뒤 기록 하루 빠짐 → RG1 unk·매수 0 / 첫 기록 이전 구간은 EV3 ⓐ만으로 판정 /
   SOXX −1σ60 이하인 날 기록 누락 → R-REC1 unk / SOXX가 덜 빠진 날 기록 누락 → 영향 없음.

R2-5 ("켜" 전 1) apply 모드 같은 날 재실행 멱등
 - 같은 평가 세션의 core_decision이 같은 decision_sha256으로 이미 일지에 있으면 쓰지 않고 status OK, 그날 decision.json은 덮지 않는다(같은 내용이면 그대로).
 - 다른 decision_sha256이면 쓰지 않고 status HOLD, 사유 CORE_DECISION_ALREADY_RECORDED_DIFFERENT, 기존 decision.json은 그대로 두고 새 결과는
   decision.rerun-<시각>.json으로만 남긴다. push 후보(받는 쪽 Cowork).
 - test_auto_core_decide.py의 기존 고정 테스트(같은 날 두 번 = FAIL)를 이 동작으로 바꾼다 — 약화가 아니라 지시 F8 "같은 날 두 번 = 같은 결과"에 맞추는 것임을
   보고에 적는다.

R2-6 ("켜" 전 2) 매도 주문표에 S7 계획 전제 표시
 - 매도 주문표 gap·after_sale에: S7 줄이기 계획의 앞 순서 종목과 오늘 그 종목 주문표 유무(예 "앞 순서 MVLL 상한 초과분 — 오늘 주문표 없음(매도 근거 없음)"),
   그리고 "이 주문표만 체결될 때 예상 E"를 한 줄로. 수량은 바꾸지 않는다(설계 7-1 그대로, 덜 파는 쪽으로만 틀림).

R2-7 ("켜" 전 3) OUTCOME_MISMATCH_WITH_RECONCILE 결과는 재발행 원장(keys)을 갱신하지 않는다(닫지도 다시 열지도 않음, 그 key는 다음 정상 분류까지 보류).

R2-8 ("켜" 전 4) 채점기 반환값이 0이 아니면 decision.journal.score_warning에 남긴다(예외와 같은 경고).

R2-9 ("켜" 전 5) 등록부 kind·side 묶음
 - 스키마와 로더 둘 다: drop_alert·close_at_or_below·log_only·earnings_notice는 side가 alert 또는 info여야 한다. 근거 kind(ema 계열·new_high_hold·
   pullback_rebound·good_news_drop 등)는 side + 또는 −. 어긋나면 그 종목 등록부 자격 없음(REGISTRY_KIND_SIDE_INVALID) → 주문표 0.
 - 테스트: 등록부에서 S8의 side를 "-"로 바꾼 사본 → 자격 없음.

R2-10 (비교 모드 1) 대조 판정 엄격화 — 부록 B 범위 안에서
 - decide 자신이 FAIL이거나 F1 전에 끝난 날은 연속 일수 0(지금은 "건너뜀"). 연속 일수를 유지하는 것은 "통합 점검 기록 사본이 없는 날"뿐.
 - N_DIFFERENCE: |ΔN| ≤ 0.03만 B2(종가 정의 차이), 그 위는 B7. R5_DIFFERENCE: 코어 종가 ÷ 고점과 문턱(0.70·0.75)의 차이 ≤ 1%p만 B2, 그 위는 B7.
 - EMA 계열의 3% 여유는 부록 B ②대로 두되, 여유가 1% 넘는 B2 항목 수와 목록을 compare.json에 b2_wide[]로 남긴다(Cowork가 R2 판정 때 본다).
 - 테스트: 각 경계.

R2-11 (비교 모드 3) decide의 S7 검토 출력 위치
 - decide가 돌리는 S7 검토(연구 기록 earnings·격자 제안 포함)는 workspace/outputs/auto-core/<날짜>/s7/ 아래에 쓴다(run_portfolio_exposure_review의
   --output-root). workspace/outputs/exposure-review/ 에는 쓰지 않는다 — 그 폴더의 "최신 파일"을 읽는 통합 점검·카드·상태 화면에 영향을 주지 않게.
 - 테스트: decide 한 번 뒤 exposure-review 폴더 파일 수 불변.

R2-12 작은 것
 - 단계 적용 뒤 0주는 LOT_ZERO로 표시(지금 CASH_ZERO/G2B_CAP로 섞임).
```

## 2. 지켜야 할 것

- 1차 Judge의 PASS 항목(J1~J5, J7~J9, J11~J16, K2·K8)을 깨지 않는다. 바뀐 줄은 위 R2-1~12에 필요한 곳만.
- 기존 테스트 약화 0(R2-5의 고정 테스트 변경은 이유를 보고에). 테스트 수 감소 0. 대상 테스트 OK, 전체 스위트 실패 줄 = 기준선 28줄과 같은 id(새 실패 0).
- 스크립트 ASCII(한국어 문구는 \uXXXX), 줄바꿈 원본 유지, 스키마 감사 PASS, 키움 실제 호출 0.

## 3. 보고

docs/claude/redesign-t2-builder-report-2026-10-10.md 끝에 "# r2" 절을 더한다:
- r2-0 요약(BLOCKED 여부, 바뀐 파일, 테스트 수 변화, 전체 스위트 결과).
- r2-1 R2-1~12 각각: 바꾼 곳(파일:함수) · 고정한 테스트 이름.
- r2-2 Judge 5절 "다른 사실" 1~6을 보고 본문에서 바로잡은 곳(원문은 지우지 말고 "정정(r2):" 줄을 덧붙인다).
- r2-3 새로 고른 것(이 지시가 정하지 않은 것)과 이유 — Judge 2차 확인 요청.
