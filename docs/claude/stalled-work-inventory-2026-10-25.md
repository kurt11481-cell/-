---
id: stalled-work-inventory-2026-10-25
title: "멈춘 운영·개발 작업 한 장 목록과 재개 순서 (2026-10-25)"
date: "2026-10-25"
status: "읽기 전용 정리. 아무것도 실행·병합·삭제하지 않음. 관제판은 이 세션이 못 읽어 관제판 쪽 상태는 '확인 필요'"
class: "문서. 승인류·dev-queue·dev-run·dev-merge 실행 없음. 키움 도구 미호출. 비밀 파일 미열람"
authority: "order_authority=false · quantity_authority=none"
as_of: "2026-10-25 12:2x KST (git HEAD 5a289b8 = 10/25 08:08)"
consumers: "사장 · 사장실 코디네이터 · 다음 회사PC 스레드(재개 입구)"
---

# 결론
- **재개할 첫 작업은 cashflow-api-gap(cf-b2n, B2-N) 병합이다.** Builder 끝, 독립 Judge 2회 PASS(11:2x), 병합 스크립트까지 써 놓고 **병합만 안 됐다**(HEAD가 recon-dt 병합 5a289b8 그대로, cf-b2n 병합 커밋 없음).
- 멈춘 이유의 뿌리는 둘이다. ① cf-b2n 병합이 사장 한 줄 + 실행 대화를 기다림. ② 승인류를 칠 곳이 모호해짐: 옛 비서실(Cowork 프로젝트)이 09:24 보관됐는데, 11:32 사장 결정은 "승인은 Cowork에 직접 입력"이다. 사장실 지침 4절은 승인류를 막아 놓았다. 그래서 **승인과 병합을 실행할 Cowork 대화 하나가 살아 있어야 한다**(보관된 옛 비서실이 쓸 수 있는지 = 설계 문서 추가 결정 4, 확인 필요).
- 새로 만들 개발은 없다. 대부분 "순서 대기"이고 버려도 되는 것은 아래 D절에 따로 모았다.

# A. 재개 순서 (한 번에 한 단계)
| 순번 | 작업 | 사장이 할 일 | 근거 |
|---|---|---|---|
| 1 | **cf-b2n 병합**(권한·한도 K3) | Cowork 대화에서 병합 승인 한 줄을 오늘(KST) 안에 직접 입력 → Cowork가 `docs/claude/cf-b2n-merge-2026-10-25.ps1` 실행. 이미 입력한 승인(스크립트 머리말에 "Cowork 비서실 채팅, 2026-10-25"로 적힘)이 같은 날 1회 규칙에 아직 유효한지는 확인 필요 | cf-b2n-judge-report.md 머리(PASS 2회) · merge ps1 머리말 · git log |
| 2 | 10/27(화) 06:15 대조 결과 확인 | 없음(자동). 읽기만: I2 PASS, I3 사유가 현금 잔차 하나만 남는지. cf-b2n 병합이 끝났으면 I3도 PASS 기대 | recon-hold-2026-10-23.md 끝 "다음 확인" |
| 3 | 첫 실행 뒤 실측 3가지 | 없음. ust21132 요청 본문·06:15 시점 값·won_entr 표기. 틀리면 HOLD(안전)로 보임 | cf-b2n-judge-report.md 막지 않는 문제 3 |
| 4 | Projects K3 | **병합 전 하지 않음.** 승인 이전은 11:32 중단이므로 K3 자체의 남은 범위를 사장이 한 줄로 정해야 함(아래 B-3) | projects-new-board-design 0절·12절 |
기한: 대조 제외 기한 **10/30**(cashflow 방향 결정), **11/03** 실행부터 체결 조회 14일 한도 초과 → FILL_WINDOW_TOO_LONG(recon-hold 2차 재검토). 둘 다 1번이 해결.

# B. 멈춘 작업 목록

## B-1. 운영
| 작업 | 상태·시각 | 왜 멈춤 | 재개에 필요한 것 | 근거 |
|---|---|---|---|---|
| 자동 코어 대조 HOLD | 10/22·23·24 daily/decide HOLD, 상태 파일 옛 값(MVLL 159·NBIS 13·SOXL 179) | 체결 날짜 해석 결함(→ recon-dt로 병합됨) + 출금 $82.93 증거 없음(→ cf-b2n 대기) | A-1 병합 → A-2 확인 | ceo-weekly-report 2026-10-25 절 · recon-hold |
| recon-dt 후속 확인 | 병합 완료(5a289b8, 10/25 08:08). 확인만 남음 | 순서 대기(10/27 06:15 실행) | 없음(자동) | recon-hold 끝 |
| 사장 결정 D1 "원인 조사 지시할까요?" | 기한 10/31, 무응답 시 현행 유지 | 사장 결정 대기. 단 **원인은 이미 recon-dt·cf-b2n으로 밝혀져 중복** | 사장이 답하거나 기본값(현행 유지)으로 둠 | ceo-weekly-report 4절 |
| 독립 대조(t2rc-check) | 10/22~24 결과 없음(S7 equity None에서 oracle 1734행 TypeError) | HOLD 부작용. 대조기가 판정 대신 죽는 결함 별도 | 별도 일반 변경(미착수) | recon-hold 미해결 2 |
| 매도 주문표에 G1 사유가 붙는 문제 | 미해결(하위 에이전트 보고, 원문 확인 필요) | "매도는 막지 않는다" 원칙과 어긋나는지 검토 미착수 | 검토 문서 1개 | recon-hold |
| redesign-t2 비교 모드 → "켜" | 비교 모드. C1 연속 일치 0/10부터(HOLD로 계속 끊김), C2 미충족 | 순서 대기(대조 정상화 뒤 일수 다시 셈) + 사장 "켜"는 승인류 | A-1 뒤 정상 일수 쌓기 | roadmap 1절 · 비서 제안 10/24 |
| c-hwm-review | "막힘, recon-dt 해소 대기" | 순서 대기 | recon-dt 해소 확인 | secretary/2026-10-24.md |
| 10/24 비서 제안이 가리킨 정지 의심 3건: e-new(외부자료 PDF, 10/05 이후 갱신 없음) · fx6-legacy-cash-min(10/16) · redesign-t2 | 조건 미충족으로 대기 | 조건 대기 | 조건이 생길 때만 | secretary/2026-10-24.md |
| 예약 작업 점검 R1/R2(관제판 17건) | 지시문 버전 ≠ 관제판 표기(sch-secretary·autocore-alert·monpre·check) 등 | 관제판 기록 갱신 지연 | Cowork가 관제판 갱신(dev-dashboard-protocol) | ceo-weekly-report S-OPS-4 |
| PC 상태 WARN task_logon_type | 10/24 | 원인·영향 확인 필요 | 확인 필요 | ceo-weekly-report S-OPS-5 |
| 키움 환전·출금 TR 조사 | 끝 — 거래 기록 TR 없음, 잔액 추론만 가능 | (결론 났음) | cf-b2n이 그 결론의 구현 | recon-hold TR 조사 절 |

## B-2. 개발
| 작업 | 상태·시각 | 왜 멈춤 | 재개에 필요한 것 | 근거 |
|---|---|---|---|---|
| **cf-b2n(cashflow-api-gap, B2-N)** | Builder 4회·Judge 2회 PASS, worktree `.claude/worktrees/cf-b2n` **미커밋**(수정 6 + 새 파일 2), 병합 ps1 11:31 작성 | 사장 병합 실행 대기(승인 입력은 Cowork) | A-1 | dev-runs/cf-b2n/status.txt · judge 보고 · ps1 |
| 개발 진행 수 "5/3" | 주간 보고가 상한(3) 초과로 셈 | 어떤 5개인지 이 세션이 못 확인 | 관제판 열람(확인 필요). 후보: cf-b2n · Projects K3 · graphify-refresh · duet-r3a · obs-sys/비서 v1.2 | ceo-weekly-report 2절 |
| duet-r3a(일지 확인 코드 제거) | 비서 제안 10/24 2번 | 선행 duet-sec은 끝(10/22 교체). 요청에 "제약 완화" 표시 → 비서는 소개만 | 사장 판단. 권한 성격이면 K3 칸 순서 | secretary/2026-10-24.md · roadmap 3절 |
| obs-sys 비서 v1.2·관제판 한 화면 개편(board-merge 묶음) | 기한 10/29 | 선행 duet-sec 완료 추정(확인 필요) | Cowork에 "obs-sys 진행" | secretary/2026-10-24.md |
| 권한 칸 대기열: cal-2027 · duet-q4-coreinput(자동 코어 입력 문서 보호, 00-home.md가 "구멍"이라 적음) · duet-q4-recon | 2026-10-22 순번 이후 갱신 확인 필요 | **권한 칸은 한 번에 1건**(CLAUDE.md:99) — cf-b2n이 쓰는 중 | cf-b2n 병합으로 칸이 비면 다음 착수(순서는 관제판 원본, 확인 필요) | roadmap 3절 · 00-home.md |
| 일반 변경 후보: oracle 크래시 수정 · 시험 데이터/주석 정리(cf-b2n Judge 권고 1) · 새 시험 파일 LF | 미착수 | 권한 칸과 무관, 일반 변경 | 개발 큐에 Cowork가 등록(상한 3 안에서) | recon-hold · cf-b2n Judge |

## B-3. 사장실 이사(Projects) 관련
| 작업 | 상태 | 왜 멈춤 | 재개에 필요한 것 | 근거 |
|---|---|---|---|---|
| Projects 새 판 K3(승인 이전 ①②) | **11:32 사장 결정으로 중단**, 승인은 Cowork 직접 입력 유지. K3 지시문·큐 없음 | ①-c 시험 실패(⓪) | 사장 한 줄: K3 전체를 **종결**할지, 남은 것(Mods 설치 금지 문구·지침 v2·09:25 지시문 "비서실에" 문구)만 **일반 변경으로 축소**할지 | design 0절·12절 · 1c-test |
| 지침 v1.2 4절 "K3 병합 전 승인류 금지" | K3가 병합되지 않으므로 **영구 적용 상태** | 위 결정의 부작용 | 위와 같이 정리하면 지침 4절 문구도 "Cowork에서 입력"으로 고침(사장 승인 필요) | projects-instructions-v1.md · 지침 4절 |
| 승인 없이 Cowork 안 열고 승인하는 방법 | 검토 끝: 권장 NO_CHANGE(사장 터미널 USER_TERMINAL 경로가 이미 있음) | 11:32 "현행 유지"로 사실상 해결 | 종결 처리만 | approval-without-cowork-review |
| graphify-refresh | 지시문 초안 `graphify-refresh-builder-prompt.md`, 큐 미등록. **GRAPH_REPORT.md는 지금 있음**(수정 시각 10/25 11:52 KST) → 누군가 이미 재생성한 듯, 누가·어떤 명령인지 확인 필요 | 실행 경로 결정 대기였음 | 보고서 `graphify-refresh-report.md`는 없음. 해시 대조(CLAUDE.md·settings 불변)만 하면 종결 | graphify-refresh-builder-prompt.md · 파일 수정 시각 |
| graphify 정기 갱신 예약 작업 | "K3 병합 뒤" 대기 | K3가 중단됐으므로 조건이 영영 안 채워짐 | 사장이 조건을 "K3 병합 뒤" 대신 "Cowork에서 예약 승인 한 줄"로 바꿀지 | design 9절 6번 |
| Mods | 설치 금지만(Q2 b) | 반영할 곳이 지침 v2 | 위 K3 축소 결정과 함께 | design 1절 |

# C. 문서 보관 상태 (git)
- 미커밋 수정 2개: `ceo-weekly-report.md`(10/25 절 덧붙임, _pending에 있음) · `recon-hold-2026-10-23.md`(병합 기록, _pending에 있음). 23:30 InvestmentV2-DocsCommit이 커밋.
- **_pending에 안 올라간 새 문서 3개**: `dc-dev-2026-10-22.md`, `dcdev-claudemd-builder-prompt.md`, `cf-b2n-merge-2026-10-25.ps1`. CLAUDE.md가 dc-dev 문서를 인용하므로 자동 커밋에서 빠지면 저장소에 근거가 없다. 이 문서와 함께 _pending에 올릴지는 사장 한 줄(아래).
- `_dev-queue` 비어 있음. `_pending` 14건 대기(전부 문서).

# D. 끝났거나 버려진 일 (건드리지 않음, 표시만)
- **끝**: recon-dt(5a289b8) · decide-gap/gap2 · hide-task-window · enter-window1~3 · dcdev-claudemd · evo-s1~3 · hwm-fix · rrec-* · t2rc-* · 그 밖 `worktree-*` 브랜치 전부. `git branch --no-merged HEAD`에 남은 것은 아래 8월 옛 브랜치뿐이라 worktree 브랜치는 모두 본 브랜치에 병합됐다(cf-b2n은 미커밋이라 목록에 안 보임).
- 사장이 예로 든 `auto-core-t1`(10/10) · `c1-host-status`(10/12) · `c6-fix`(10/14)도 위에 해당 → **병합 끝난 작업 사본**이다. worktree 디렉터리는 85개. 정리(삭제)는 사장 승인 뒤 별도(이번에 하지 않음). 사본 안의 **미커밋 변경 유무는 이 환경에서 확인 못 함**(확인 필요 — 지우기 전 필수).
- **버려진 옛 브랜치**(8월, 본 브랜치에 없음): `main`(GitHub 옛 판, 8/15) · `backup/*` 7개 · `claude/e-judge-verdict-*`, `claude/git-log-branch-check-*` · `codex/v2.6.*` 3개 · `feature/v2.6.4-*`. 읽지 않는다는 사장실 규칙대로 두되 정리 대상으로 표시.
- **종결 후보**: Projects 1-c 시험(마감) · Cowork 없이 승인하는 방법 검토 · r-wd-1022(출금 선언 확인 → cf-b2n으로 대체, 사장 판단 필요) · 키움 환전·출금 TR 조사.

# E. 사장이 정할 것 (각 1줄, 오늘 순서대로)
1. **cf-b2n 병합 승인**을 Cowork 대화에 직접 입력할까요? (권장 예. 일요일이라 병합 금지 시간대 밖)
2. Projects K3를 **종결/축소**할까요? (권장: 승인 이전은 이미 중단했으므로 남은 문구 몇 줄만 일반 변경으로 축소, 지침 4절은 "Cowork에서 입력"으로 고침)
3. D1(원인 조사 지시)은 **현행 유지**로 닫을까요? (권장 예, 원인이 이미 밝혀짐)
4. _pending에 빠진 문서 3개를 올릴까요? (권장 예)
5. 병합 끝난 작업 사본 정리는 cf-b2n 뒤에 따로 묻겠습니다(미커밋 변경 확인이 먼저).

# F. 사장 결정 기록
- 2026-10-25 12:24 KST(03:24Z) 사장 원문 "전부 예"(cmsg_0137MRzn9nuDvvQmVxm6WeX9Fbg91mAPqeax26JfuraCAV, 코디네이터가 전달한 서버 복사본). 바로 앞 제안 = E절 1~5. 적용: 2번 Projects K3 종결, 남은 문구는 일반 변경(지침 4절은 코디네이터가 v1.6으로 수정) · 3번 D1 현행 유지로 닫음 · 4번 빠진 문서 3개 _pending 등록 · 5번 작업 사본 정리는 cf-b2n 뒤 별도 질문.
- **1번 cf-b2n 병합 승인은 이 "전부 예"로 대신하지 않는다.** 병합은 사장이 Cowork 대화에 병합 승인 문구를 직접 입력해야 함(승인류는 이 프로젝트에서 실행하지 않음). 승인 문구는 recon-dt 때 형식 "결정 recon-dt 병합: 승인"에 맞춘 "결정 cf-b2n 병합: 승인"이 후보이나 정확한 id는 확인 필요(병합 ps1 머리말은 "cashflow-proof"로 적음).

# 바뀔 조건
- cf-b2n Judge 이후 본 저장소 HEAD가 움직였거나 병합이 이미 실행된 흔적이 나오면 A-1은 "끝"이 된다(이 문서는 git HEAD와 dev-runs/cf-b2n만 근거로 함).
- 관제판에서 다른 진행 상태·권한 칸 순번이 확인되면 B-2의 해당 줄을 고친다.

검토 완결: 원문 확인 — CLAUDE.md · 00-home.md · handoff · recon-hold 전체 · cf-b2n Judge 보고 전체 · roadmap · 설계 문서 0·1·7·9·11·12절 · 1c-test·k3-rereview4·approval-review·graphify-refresh 머리 · ceo-weekly-report 10/25 절 · secretary/2026-10-24.md 머리 · git status/log/branch 출력 · dev-runs/cf-b2n/status.txt · 미확인(확인 필요): 관제판 내용 · worktree 사본의 미커밋 변경 · 10/25 승인 입력의 유효성 · 진행 개발 5/3의 정체 · graphify 재생성 주체 · 자료 시점 2026-10-25 12:2x KST.
