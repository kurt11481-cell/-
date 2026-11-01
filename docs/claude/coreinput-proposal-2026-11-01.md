---
id: coreinput-proposal-2026-11-01
title: "자동 코어 입력 문서 보호 — duet-q4-coreinput 착수 제안"
date: 2026-11-01
status: "제안 — 사장 착수 결정 대기(무응답 = 현행 유지)"
class: "권한·한도(K3) — 매수 관문을 조이기만 함(완화 없음). 개발 큐 authority: Builder Opus → 자동 검사·전체 테스트 → Judge Opus → NEEDS_APPROVAL → 사장 병합 결정 + 사장 PowerShell -ApproveAuthority"
decisions_touched: "duet-1022 Q4 a(이 작업을 권한 대기열 첫 순서로 등록, duet-redesign-2026-10-22.md:123) · obs-1022b Q2 a(설계 방향, obsidian-ops-review-2026-10-22.md:68-70) — 둘 다 이 제안의 근거이며 충돌 없음. 관제판 duet-q4-coreinput의 '수동 경로' 표기와 경로만 다름(4절). dst-label A(active-decisions.md:103)와 권한 자리 순서가 겹침(4절)"
authority: "order_authority=false · quantity_authority 변경 없음 · 키움 없음 · 정책·상태·일지·원장 쓰기 없음"
source: "사장 요청 2026-11-01 17:00 KST(다른 스레드: '결함 해결을 위해 사장실에 별도 스레드로 요청해줘') → 코디네이터가 스레드 '자동 코어 입력 문서 보호' 개설"
consumers: "사장(착수·병합 결정) · 개발 큐 coreinput(지시문 coreinput-builder-prompt.md) · 관제판 duet-q4-coreinput · 00-home 경고 표(병합 뒤 갱신)"
---

# 자동 코어 입력 문서 보호 (2026-11-01)

## 0. 결론
- 07:45 자동 코어 판정(decide)은 docs/claude 문서 4종을 **커밋 검사 없이** 그대로 읽는다. 그중 3종은 고치기만 하면(또는 지우거나 사본을 만들면) 매수 관문이 풀린다.
- 권장(B): 이 문서들이 커밋 안 된 상태(수정·새 파일·삭제·링크 바꿔치기)면 **그날 매수 주문표만 막고 알림**을 띄운다. 매도 주문표는 막지 않는다(검증 안 된 재배치 후보만 빼고 계산). R-REC1 문서가 없어도 매수를 막는다(지금은 빈 글로 읽어 관문이 풀림).
- 지금 decision_mode = "compare"(workspace/policies/auto_core.json 11행)라 실제 입력 영향은 없다. **"켜" 전에** 막아야 한다.
- 고칠 파일 3개(auto_core_inputs.py · auto_core_decide.py · auto_core_tickets.py) + 새 테스트 1개. 정책·스키마·기존 테스트는 안 건드린다.

```
문서를 고침(Obsidian·세션 실수)
   ↓
지금: 07:45 판정이 고친 글을 그대로 읽음 → 매수 관문 풀림
   ↓
바꾼 뒤: 커밋 안 됐으면 → 매수만 멈춤 + 알림 1줄 (매도 주문표는 그대로 나옴)
   ↓
커밋되면(23:30 자동 커밋 등) → 다음 판정부터 평소대로
```

## 1. 구멍 (2026-11-01 17시대 KST, 코덱스저장소 c53940a 직접 확인)

| 입력 | 읽는 곳 | 고치면 | 지금 검사 |
|---|---|---|---|
| recovery-gate-R-REC1-2026-10-09.md | auto_core_decide.py:62·644-645 → auto_core_rules.py:69·733-734(ev3_dates) | `- 이벤트 YYYY-MM-DD(EV` 줄(지금 71행 10/08 1줄)을 지우면 사용자 지정 충격 EV3a가 사라져 R-REC1 관문 완화. 파일을 지우거나 이름을 바꿔도 같은 효과(644-645행: 파일이 없으면 빈 글) | 없음(sha256 기록만, decide:580) |
| m6-relative-comparison-7stock*.md (지금 2개) | auto_core_inputs.py:38·195-197(접두어 glob 전부) → auto_core_rules.py:986-993(m6_listed) | 본문에 종목 코드를 넣거나 같은 접두어 사본을 만들면 매수 요건 ④ 통과 | 없음 |
| watchlist-registry.json | auto_core_inputs.py:37·148-157, card_check 182-187 | ① 종목 줄을 더하면(예: AMD — 등록부에 관심 항목이 있고 M6 문서에도 있음) 매수 대상이 됨 ② cardStatus를 "수락…"으로 바꾸면 관심 카드가 수락된 것으로 보임(등록부 커밋 검사를 우회) ③ sector를 바꾸면 RG2 기준 ETF가 바뀜(auto_core_rules.py:981-983, decide:587-589·1037) | 없음 |
| redesign-t2-compare-explained.json | auto_core_compare.py:34·297-310 → decide:690·831 | 설명 항목을 넣으면 판정 대조 연속 일수가 늘어 "판정 대조 5일 — 완료 판정 필요"(decide:695-696)가 앞당겨짐 = "켜" 판단 자료. 주문표에는 영향 없음 | 없음 |

- 각주: cardStatus는 보유 중인 관심(watch) 역할 종목의 매도 자격도 정한다(auto_core_inputs.py:182-187). 지금 보유 BE·LITE·SOXL은 보유(holding) 역할이라 해당 없음.
- 일부러 뺀 것: 등록부 card-evidence-registry.json은 이미 커밋 검사가 있다(auto_core_inputs.py:90-107·141·189-190 — 파일이 하나라 미커밋이면 **모든 종목의 매수·매도** 주문표가 막힘, auto_core_tickets.py:802·819). 카드 문서(등록부 card_doc, auto_core_inputs.py:172-178)는 커밋된 등록부의 절 해시로 고정돼 있어, 고치면 그 종목 주문표가 매수·매도 모두 안 나온다(완화 아님). 카드 수정이 매도까지 막는 현행 동작은 obs-1022b Q2 a의 "매도 비차단"과 다르지만 이번 범위 밖(6절).
- 코드 파일 안전선(auto_core_reconcile.py:1330-1341·1427-1436)은 scripts·schemas·assets와 옛 핀 목록만 본다 — docs/claude는 범위 밖. decide는 decision_mode가 apply일 때만 이 안전선을 쓴다(auto_core_decide.py:414·421).
- 재배치 후보(매도 regret 표에 열 2개를 더함, auto_core_tickets.py:328-331·735-739·1081-1084)도 매수 요건 ①③④⑤를 후보 조건으로 쓴다(auto_core_decide.py:1155-1156, 순위 1159 이하) → 위 문서를 고치면 매도 수량 계산 근거까지 바뀔 수 있다.
- 현재 상태: 4종 모두 git 추적 중이고 수정 없음(git status 빈 결과, 17시대).

## 2. 방법 비교 (NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD)
- **NO_CHANGE**(00-home 금지 규칙만): Obsidian 실수 편집·세션 실수를 막지 못하고, "켜" 뒤엔 실제 주문표에 반영된다. 기각.
- **REMOVE/SIMPLIFY**(문서 값을 코드 상수로): EV3a 날짜는 사장 지정으로 늘고, 관심 명단은 매주 자동 갱신(토 10:20) — 코드로 옮기면 매번 개발 큐가 필요. 기각.
- **REUSE — 권장 B**: 등록부에 이미 쓰는 커밋 검사(auto_core_inputs.registry_committed, 테스트 주입 경로까지 그대로)를 4종에도 쓴다. 미커밋이면 매수만 막고 알림.
- **REPLACE — A**(git 커밋본만 읽기): 미커밋 수정은 무시되고 코어는 평소대로 돈다. 대신 git show 읽기 코드가 새로 필요(4종 + 접두어 목록), 고친 사실이 조용히 묻혀 알림을 따로 만들어야 하고, 06:40 통합점검(작업 사본을 읽음)과 입력이 달라져 판정 대조 차이가 생긴다.
- **ADD**(문서 해시를 등록부에 고정): 관심 명단 주간 자동 갱신마다 등록부를 고쳐야 해 자동 운영 1순위와 부딪힌다. 기각.
- B를 고른 이유: 가장 작은 변경, 실패가 보임(fail-closed), "매수만 막고 매도는 막지 않음"(R-REC1 문서 57행, 헌법 §2-1 적용 예)과 같다.

B의 비용 — 미커밋 날은 매수 주문표가 없다. 실제로 생길 경우:
1. 관심 명단 주간 재채점: 토 10:20 쓰기 → 같은 날 23:30 자동 커밋(10/24·10/31 커밋 시각 23:30 확인, watchlist-weekly-rescore.txt:312 _pending), 다음 판정은 화 07:45 → 영향 없음.
2. 세션이 문서를 고치고 _pending을 안 쓴 경우 → 알림으로 드러나고, 커밋하면 다음 판정부터 풀린다(바라는 동작).
3. 판정 대조 설명: 보통 당일 23:30 커밋(10/23·10/26·10/28 확인) → 다음 판정 전 커밋됨.

## 3. 바꿀 동작 (지시문: coreinput-builder-prompt.md)

| 상황 | 매수 | 매도 | 기록·알림 |
|---|---|---|---|
| R-REC1 문서·관심 명단·M6 접두어 파일 중 하나라도 미커밋(수정·스테이징·추적 안 된 새 파일·심볼릭 링크) | 모든 매수 주문표 막힘(사유 `CORE_INPUT_UNCOMMITTED:<경로>`) | 막지 않음. 단 재배치 후보를 빼고 계산해 regret 열·수량·swap_pair 표시가 달라질 수 있음(후보가 없을 때의 기존 계산과 같음) | decision.json inputs.core_input_guard(경로·sha256), 처음 생긴 날 알림 1줄 |
| R-REC1 문서 없음 | 막힘(`CORE_INPUT_MISSING:<경로>`) | 위와 같음 | 같음 |
| git 확인 실패·검사 중 오류 | 막힘(fail-closed, 오류면 `CORE_INPUT_GUARD_ERROR:<오류>`) | 위와 같음 | 같음 |
| 판정 대조 설명 파일 미커밋 | 영향 없음 | 영향 없음 | 그날은 설명을 세지 않음(explained_errors에 EXPLAINED_FILE_UNCOMMITTED). 커밋되면 다음 판정에서 설명 포함 값으로 돌아옴 |
| 모두 커밋됨 | 지금과 같음 | 지금과 같음 | inputs.core_input_guard status OK |

- 검사 시점: 문서 3종을 한곳에서 읽고 바로 검사한다(R-REC1 읽기를 연구 기록 대기 앞으로 옮김 — 지금은 최대 08:30까지 기다린 뒤 읽어, 검사를 앞에 두면 그 사이 편집을 놓침, auto_core_decide.py:564·644).
- 재배치 후보를 빼는 이유: 매수가 막힌 날의 "팔고 내일 살 후보"는 검증 안 된 문서로 고른 것이라, 그것이 실제 매도 수량을 바꾸지 못하게 한다. 매도 주문표 자체는 나온다.
- compare·apply 두 모드에 똑같이 적용(등록부 검사와 같음).
- 하지 않음: 06:15 T1(대조) 실행에 넣지 않는다(T1이 멈추면 매도·대조까지 멈춤) · 정책 파일·스키마·기존 테스트·06:40 통합점검·replay 무변경 · M6 판정 방식(글자 포함) 무변경(7절).

## 4. 경로·승인
1. 사장 착수 결정: 이 스레드(사장실 회사PC 폴더에서 일하는 대화형 Claude Code 프로젝트 스레드)가 올린 결정 카드를 사장이 직접 누름 — CLAUDE.md 72-78행 조건(카드 id·제안 id·선택지·계정·KST 시각 기록). 이어서 결정 기록 + 지시문 최종본(source 줄에 카드 기록) 커밋 목록 + 큐 등록(이 스레드).
2. 개발 큐: Builder(Opus) → 범위·보호 경로·전체 테스트(기준선 대비 새 실패 0) → Judge(Opus, 읽기 전용) → **NEEDS_APPROVAL**(auto_core*.py는 권한 경로, tools/dev_pipeline/authority-paths.txt:12·25).
3. 사장 병합 결정 + 사장이 직접 연 PowerShell에서 `.\tools\dev-merge.ps1 coreinput -ApproveAuthority`(tools/dev_pipeline/README.md 11·70행).
- 경로 근거: CLAUDE.md 66-71행의 기본은 수동 경로(worktree Builder + 독립 Judge)이고 tools/dev_pipeline/README.md 4행도 "권한·한도 변경은 이 파이프라인을 쓰지 않는다"고 적는다. 반면 README 44·70행은 사용자 결정 기록이 있는 authority 작업의 큐 등록과 -ApproveAuthority 병합을 정해 두었고, 10/13 이후 권한 작업(t1-safety·pre-on-fix·enter-window3·decide-gap2·recon-cap·recon-krw·s7-hold-gap3 등)은 이 길로 했다. Judge는 별도 세션·읽기 전용이고 병합은 사장 몫이라 같은 안전을 준다. 관제판 duet-q4-coreinput의 "수동 경로" 표기(10/22)와 다르므로 착수 결정에 이 경로가 포함된다. README 4행과 44행의 문구 정리는 별도 안건 후보.
- 권한 자리(한 번에 1개, active-decisions.md:97): 지금 진행 0건(관제판 tasks 17시대 조회). 다음 후보 두 개와의 순서:
  - dst-label A(active-decisions.md:103): 11/03 아침 측정 뒤 개발 큐 authority, "11/03 실행은 막힐 수 있음" → 운영 영향이 있어 **dst-label이 우선**. coreinput이 11/03 아침 측정 전에 병합되지 않으면 coreinput은 결과(NEEDS_APPROVAL)를 둔 채 병합을 dst-label 병합 뒤로 미룬다.
  - cal-2027: 2027 휴장일 원문 대기(planned) — 영향 없음.
- 개발 큐는 test-state-fixture 실행 중(16:50 KST 시작) → 그 뒤 차례.

## 5. 병합 뒤 (이 스레드)
- 00-home.md 고칠 곳: 19·20·25행("본문에 코드를 넣으면 관문이 풀림" → "커밋 전에는 매수가 멈춤(알림). 커밋되면 반영되니 여전히 고치지 말 것"), 18행 카드 목록(LITE·BE 보유 카드는 holding-cards-BE-LITE-2026-10-27.md, 확인 필요), watchlist-registry.json·redesign-t2-compare-explained.json 행 추가.
- 관제판 duet-q4-coreinput → done, active-decisions 1줄, 다음 권한 순번 duet-q4-recon.
- 병합 다음 **새 세션 판정**(화~토 07:45, 미국 휴장 다음 날 제외)의 decision.json에서 inputs.core_input_guard.status = OK 확인. 새 세션이 없는 날은 이 키가 없다(auto_core_decide.py:527-531·807 _no_new_session).

## 6. 남는 위험 (고치지 않음)
- 커밋된 편집은 막지 못한다(_pending에 이름을 올리면 23:30 자동 커밋). 이 수정은 "모르게 바뀐 것"을 막는다. 커밋된 변경은 git 기록과 decision.json inputs.core_input_guard의 파일별 sha256으로 남는다.
- git 고급 명령(`git update-index --assume-unchanged`/`--skip-worktree`)을 걸면 변경이 git status에 안 보인다(일부러 해야 하는 일).
- 문서를 읽은 직후와 검사 사이 아주 짧은 틈(밀리초 단위).
- 카드 문서를 고치면 그 종목 매도 주문표까지 안 나오는 현행 동작(1절).
- 06:40 통합점검(LLM)도 같은 문서를 읽지만 표시·대조용이라 주문표에는 영향 없음.

## 7. 따로 발견·범위 밖
- M6 판정이 "글자 포함"이다(auto_core_rules.py:991 `symbol in text`, 규칙 파일 integrated-check-prompt-v3.12.10 134행 "grep -c"). S·NOW 같은 짧은 코드는 M6 문서에 없어도 통과한다(SOXL·UNKNOWN 안의 글자). 지금 관심 명단(MU·DELL·PWR)과 보유 종목은 단어 기준으로도 문서에 있어 영향 없음. 짧은 코드가 명단에 들어오기 전에 규칙 파일·코어를 함께 "단어 일치"로 바꾸는 별도 안건 후보.
- workspace/policies/auto_core.json이 10/28 18:19 KST부터 커밋 안 된 상태다(SPY 추가 = d10 사장 실행, active-decisions.md 100행; 줄바꿈까지 바뀌어 파일 전체 diff). 정책 파일은 사장이 직접 바꾸는 파일이라 이번 보호 대상이 아니다. 커밋 여부는 사장 판단(확인 필요).
- docs/claude 밖에서 커밋 검사 없이 판정에 닿는 입력(범위 밖): stock-strategy-system/alert_policy.json(노출 정책 — 정책·보호 경로) · research-record.json(F3 계약, 항목별 결정론 검사) · regular-session-closes/corporate-actions.json(git 무시 대상) · 직전 decision.json의 keys(재발행 제한). docs/claude 쪽 decide 입력은 위 4종 + 등록부 + 카드 문서뿐이다(auto_core_*.py에서 docs/claude·DOCS_DIR grep, 본 세션).
- 06:15 T1은 관심 명단으로 수집 종목을 정한다(auto_core.py:55·106) — 수집만이라 그대로.
- 채점(score_decision_journal.py:901-902, event_calendar.py:39)의 docs/claude 입력도 검사 없이 읽지만 사후 채점이라 주문표와 무관.

## 8. 바뀔 조건
- 미커밋 때문에 매수가 막히는 날이 한 달에 2회를 넘으면 → A(커밋본 읽기)로 바꾸는 것을 다시 검토.
- 다른 docs/claude 파일이 판정 입력으로 추가되면 → 같은 목록에 넣는다(새 테스트가 입력 목록을 고정).
- "켜" 전에 병합되지 않으면 → "켜" 제안 때 이 구멍을 위험으로 함께 적는다.
- 11/03 dst-label 측정이 미뤄지면 → coreinput 병합을 먼저 해도 된다(권한 자리 1개 조건 유지).

## 9. 내장 재검토 기록
- 1회차(2026-11-01 17:3x~17:5x KST, Opus 하위 에이전트, 16건): 결론 변경 4건 — ① 재배치 후보를 빼면 매도 regret 열·수량이 달라질 수 있음(auto_core_tickets.py:328-331 본 세션 확인) → "매도는 그대로"를 "매도 주문표는 막지 않음, 재배치 후보만 빼고 계산"으로 고치고 테스트 b에서 매도 비교 삭제(i에서만 확인) ② R-REC1 문서는 연구 기록 대기(최대 08:30) 뒤에 읽혀 검사 뒤 편집을 놓침(decide:564·644 본 세션 확인) → 읽기를 앞으로 옮기고 바로 검사 ③ 카드 문서·등록부를 일부러 뺀 이유가 없어 Judge FAIL 위험(auto_core_inputs.py:172-178 본 세션 확인) → 1절·지시문에 명시 ④ 권한 자리 순서에 dst-label 누락(active-decisions.md:103 본 세션 확인) → 4절에 순서. 문구 12건: 파일별 sha256 기록, 검사 전체 오류도 매수만 막음, 심볼릭 링크 바꿔치기 차단(registry_committed가 resolve로 대상 파일을 봄, auto_core_inputs.py:93 본 세션 확인)·남는 위험 2건, 관심 명단 줄 추가 경로, 등록부 비교 문장(모든 종목 매수·매도, tickets:802·819 본 세션 확인), 경로 근거(CLAUDE.md 66-71·README 4행과 다름, 선례 10/13부터 — git log 본 세션 확인), 큐 넣기 전 source 줄·제안서 커밋, 테스트 안내(h 직전 기록 방식·i tk.plan·j 대체 주입·None 대입 위치), 연속 일수 문구, 줄 번호 3건, 00-home 갱신 범위·새 세션 날 확인, 범위 밖 입력 목록.
- 결론이 바뀐 4건은 모두 원문 행을 본 세션에서 직접 열어 반영했고, 새로 만든 결론은 없어 2회차는 돌리지 않았다. 재검토 지적 가운데 본 세션에서 다시 열지 않은 것: 관심 명단에 AMD를 더하면 매수 관문이 실제로 열리는지(등록부 해시 일치·card_stock_core 포함 — 재검토 보고) → 1절 예시로만 쓰고 결론에는 쓰지 않음.

## 10. 결정 요청 coreinput (오늘 같은 날, 버튼 1번)
- **a) 착수 — B 방식(미커밋이면 매수만 막고 알림), 개발 큐 authority (권장)**
- b) 착수 — A 방식(커밋본만 읽기, 지시문 다시 씀)
- c) 보류 — 현행 유지(00-home 금지 규칙만)
- 무응답 = c(NO_CHANGE, 대기 유지). 착수해도 병합은 사장 결정 1번 + PowerShell 한 줄이 따로 필요.
- **결정 기록: a) 착수 — B 방식** · 2026-11-01 17:53 KST · 사장 결정 카드(이 스레드, cmsg_0137MRzn9nuDvvQmVxm6WeX9FN5zdRrmv1MZgP5gkYnJhR) · 계정=사장. 같은 날 지시문 source 줄을 이 기록으로 바꾸고 개발 큐 authority(id coreinput)에 올림. 병합은 아직 승인 아님.
- **병합 결정 기록: 문구 고친 뒤 병합** · 2026-11-01 19:23 KST · 사장 결정 카드(이 스레드, cmsg_0137MRzn9nuDvvQmVxm6WeX9Xd2TCniqTrddfHGWP2Jjq6) · 계정=사장. coreinput(18:55 KST NEEDS_APPROVAL, Judge 2회차 PASS)은 병합하지 않고, 알림의 '매도 그대로' 문구를 '매수 주문표 막힘·재배치 후보 빠짐(매도는 후보 없는 날처럼 계산)'으로 고친 새 실행 coreinput2(지시문 coreinput2-builder-prompt.md, 참고 diff coreinput2-reference.diff.md)를 같은 날 올림. coreinput2 결과 뒤 다시 병합 결정.

검토 완결: 원문 확인 1·3·4·7절 근거 행 전부 본 세션 확인(AMD 예시 1건만 재검토 보고 기반) · 내장 재검토 1회(반영 16건) · 미해결 0 · 자료 시점 2026-11-01 17시대 KST(저장소 c53940a, 관제판 tasks 조회) · 바뀔 조건 8절
