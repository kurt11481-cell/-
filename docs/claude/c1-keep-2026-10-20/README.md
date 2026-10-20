---
id: c1-keep-2026-10-20
title: C1 초기화 재현 확인 — 새 계산기(6a74f813)로 10-16·10-17 재검사
date: 2026-10-20
class: 검토 기록(문서만). 코드·정책·상태·예약 작업·사전 등록 변경 없음
consumers: T2 "켜" 판정(t2-rc-preregistration-2026-10-14.md 1절 C1) · 결정 c1-keep(K3 제안) 독립 Judge · 관제판 redesign-t2
---

# C1 초기화 재현 확인

## 방법
- 현행 계산기 docs/claude/t2rc-oracle.py(sha256 LF 6a74f813…)를 사용자 PC 저장소 밖 임시 복사본($HOME/t2rc-hist)에서 `check --day <날> --repo <복사본>`로 실행(--ignore-input-sha 쓰지 않음).
- 그날 decision.json inputs가 가리키는 바뀌는 입력을 sha가 같은 판으로 복원:
  - card-evidence-registry.json dcb788c2… = .claude/worktrees/c1-host-status 사본
  - watchlist-registry.json 75826e4f… = git 8883507
  - recovery-gate-R-REC1 문서 332a416e…(10-16) = git a2bc25c, c056d542…(10-17) = git e3db01c
  - portfolio_state.json bdc2720a…(10-16) = .claude/worktrees/evo-s1 사본, ddcb987a…(10-17) = .claude/worktrees/ev-rg1-hyper 사본(state는 git 미추적 — 이번엔 worktree 사본이 남아 있어 복원 가능)
  - 카드 문서(section_sha256 일치): integrated-stock-cards-v1 = git b387150, watch-card-PWR·LITE = git a2bc25c
  - decision.json 파일 시각은 원본과 같게(08:40 마감 검사).
- 결과: 이 폴더 t2rc-recheck-2026-10-16.json · t2rc-recheck-2026-10-17.json.

## 결과
| 세션(실행일) | 원래(계산기 5607b09b) | 재검사(6a74f813) | 입력 sha 불일치 | 차이 |
|---|---|---|---|---|
| 10-16 | MATCH, counts_for_c1 true, 회로 DELL·MU 매수 | MATCH, counts_for_c1 true, 회로 DELL·MU 매수 | 없음 | ev4_history 필드 없어짐(EV4 삭제, 예상된 차이)뿐. c1·tickets·ticket_leaks·requirements·exposure(부동소수 1e-16 제외) 같음 |
| 10-17 | MATCH, counts_for_c1 true, 회로 없음 | MATCH, counts_for_c1 true, 회로 없음 | 없음 | 위와 같음 |

## 한계(확인 필요)
- 재검사 상대는 그날 옛 코어가 쓴 decision.json이다. 새 코어(병합 0d55b9a·5d5cf79 뒤)를 그날 입력으로 다시 돌린 결과는 만들지 않았다. 새 계산기가 새 규칙으로 옛 코어 출력의 모든 비교 항목을 그대로 재현했으므로 그날 판정 결과가 두 변경의 영향을 받지 않았다는 근거는 되지만, 새 코어 동일성 자체는 Judge 범위.
- 첫 시도에서 카드 문서를 빠뜨리거나 현행판(10-19 재수락)을 쓰면 요건 ③ 차이가 났다(복원 오류, 계산기 결함 아님). 복원 절차가 수작업이라 규칙으로 쓰려면 입력 보관 장치가 필요하다.

## 결정 기록
- 2026-10-20 14:51 KST 사용자 원문: "결정 c1-keep: a" (Cowork 대화). 뜻: 10-16·10-17 두 세션을 한 번만 C1에 되살린다(C1 1/10 → 3/10). 상시 규칙화(b)는 하지 않는다.
- 등급: K3(T2 "켜" 판정 기준 — 사전 등록 0절은 느슨하게 바꾸지 못함, 24·50행 초기화의 일회 예외). 순서: 독립 Judge(docs/claude/c1-keep-judge-prompt.md) PASS → 사용자 적용 승인 "결정 c1-keep 적용: 승인" → Cowork가 사전 등록 변경 기록 1줄 + 관제판 redesign-t2·t2-rc next 갱신. 코드·계산기·실행기·결과 파일(t2rc-check.json)·정책·상태·예약 작업은 바꾸지 않는다.
- 기본 처분: Judge FAIL·NOT_VERIFIED 또는 승인 없음 → NO_CHANGE(C1은 10-20부터 센 값 유지). 노출·예산·권한을 올리는 효과 없음(C1은 비교 모드 판정 증거 셈일 뿐, "켜"는 여전히 C2·R2·R-A·사용자 "켜"가 모두 필요).
- 주간 사용자 손: 일상 0, 일회 2(Judge 세션 1번, 적용 승인 1줄).

## Judge 결과와 처분
- 2026-10-20 15:45 KST 독립 Judge(docs/claude/c1-keep-judge-report.md, 마지막 줄 VERDICT: FAIL). 항목 1·3·4·5·6 PASS, 항목 2 FAIL(10-16).
- 차단 결함 B1: 현행 코어(decide 안 S7 포함)가 10-16 입력으로 그날 결과를 재현하지 못한다 — hwm-fix 210e951(10-17 병합)의 HWM 재평가(30,255.36 → 31,711.76)로 10-15에 L2가 열려 요건 ②가 6종목 ok → no, DELL·MU blocked 사유 2개 추가. C1 비교 칸(회로 집합 DELL·MU 매수)은 그대로지만 사전에 정한 항목 2 기준(허용 차이 EV4만) 밖. 10-17은 70/70 같음.
- 처분: 기본 처분대로 NO_CHANGE. C1은 10-20부터 센 1/10 유지. 사전 등록·관제판 C1 문구 변경 없음.
- Cowork 방법 정정(Judge N1): 이 README의 1차 재검사는 현재 저장소의 페이지 전체(그날 뒤 페이지 포함)와 10-17 m6 판을 읽었다 — 그날 판 복원이 아니었다. 판정 칸 결과는 Judge의 그날 판 복원과 같았지만 방법은 틀렸다. 또 1차 재검사는 새 코어를 돌리지 않았고(한계 절), Judge가 그 빈칸에서 B1을 찾았다.
- 남은 선택(새 사용자 결정 필요, 기본 = 현행 유지): 10-17만 복원(1/10 → 2/10, Judge 권고 (a)), 또는 항목 2 기준 완화(Judge (b), 권하지 않음).

## c1-keep2 결정 기록
- 2026-10-20 15:46 KST 사용자 원문: "결정 c1-keep2: 10-17" (Cowork 대화). 뜻: 2026-10-17(평가 세션 10-16) 한 날만 C1에 다시 센다(C1 1/10 → 2/10). 10-16은 계속 세지 않는다.
- 근거: c1-keep Judge 보고서 항목 1·2(10-17 70/70)·3·4 — 10-17은 현행 계산기·현행 코어 모두 그날 결과를 재현(차이는 EV4 표지뿐). Judge 의견 (a) 권고.
- 등급·순서: K3(사전 등록 0절 일회 예외, 범위 축소). 확인 Judge(docs/claude/c1-keep2-judge-prompt.md) PASS → 사용자 "결정 c1-keep2 적용: 승인" → Cowork가 사전 등록 변경 기록 1줄(50·51행 함께 인용, Judge N2) + 관제판 redesign-t2·t2-rc next "C1 2/10". 코드·계산기·실행기·t2rc-check.json·정책·상태 불변.
- 기본 처분: FAIL·NOT_VERIFIED·승인 없음 → NO_CHANGE(C1 1/10).
- 2026-10-20 16:14 KST 확인 Judge PASS(docs/claude/c1-keep2-judge-report.md, 차단 결함 없음, 현행 코어 HEAD 4fe10b3·계산기 6a74f813 기준). 남은 순서: 사용자 "결정 c1-keep2 적용: 승인" → 사전 등록 변경 기록 1줄(Judge 보고서 184~185행 초안) + 관제판 C1 2/10. 승인 전 코어·S7·계산기·실행기 코드가 바뀌면 재현을 다시 한다(Judge 의견).
- 2026-10-20 16:15 KST 사용자 적용 승인 "결정 c1-keep2 적용: 승인" → 사전 등록 변경 기록 끝에 1줄 추가(16:2x, Cowork). C1 = 2/10(10-17·10-20). 코드·계산기·실행기·t2rc-check.json·정책·상태 변경 없음.
