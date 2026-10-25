---
id: archive-candidates-2026-10-25
type: review
title: "끝난 작업 묶음의 archive 이동 후보 목록 + 동결 (D3)"
as_of: "2026-10-25 KST, 기준 커밋 bb11f04(worktree-d6-cleanup)의 추적 파일"
class: "읽기 전용 조사. 파일 이동·이름 변경·삭제 없음. 규칙·정책·상태·예약 작업 변경 없음"
authority: "order_authority=false · quantity_authority=none"
source_decision: "사장 D3 승인(2026-10-25 08:46Z, 이 묶음의 Builder 지시문 d6-builder-prompt.md) · 근거 operating-diagnosis-2026-10-25.md 2-C·5·10절"
consumers: "redesign-t4(docs/claude → archive/ 정리 착수 때 입력, roadmap.md T4 줄) · 사장실 회사PC 스레드(이동 실행 여부 판단)"
---

# 결론

1. **이동 후보 64개(약 0.87MB)**: 이미 병합·종결된 작업의 Judge 지시문·Judge 보고·Builder 중간 보고(r2~r5)·병합 스크립트(.ps1)·초안 1개. 64개 모두 코드·테스트·예약 지시문·사전 등록 문서·주간 보고·로드맵·홈에서 참조가 **0건**이다(아래 방법 2).
2. **후보에서 뺀 것**: `*-builder-prompt.md` 전부(61개, 00-home.md "고치면 안 되는 파일" 표 — 옮기면 개발 실행이 멈춤), 코드·테스트·예약 지시문·사전 등록·주간 보고가 참조하는 보고서, 진행 중이거나 오늘 병합된 묶음(아래 3절).
3. **이 문서는 목록만 만든다.** 실제 이동은 별도 작업(일반 변경, `git mv`로 바이트 그대로)이며, 이동 전 이 목록을 그 시점 저장소에 다시 대조한다.

# 1. 동결 (D3)

새 규칙·새 반복 문서·새 예약 작업은 지금부터 보류한다. 예외는 둘뿐이다: ① 안전 결함(주문·권한·상태·비밀·fail-closed를 깨는 문제)을 막는 변경, ② 사장 결정을 기록하는 문서. 이미 진행 중인 작업의 후속 문서(보고서·Judge 결과)는 새 반복 문서가 아니라 그 작업의 일부로 본다. 동결은 감량(이 목록의 이동, CLAUDE.md 정리)을 막지 않는다. 해제는 사장 결정으로만 한다.

# 2. 방법 (이 세션에서 직접 잰 값)

1. 대상: `docs/claude/` 바로 아래 추적 파일 467개(bb11f04, `git ls-files`). 하위 폴더(dev-runs·scheduled-prompts·library·order-instructions·playbooks·ceo-inbox·c1-keep-2026-10-20)는 대상 밖.
2. 참조: 추적 파일 전체(이진 제외)에서 파일 이름(또는 12자 이상 확장자 뺀 이름)이 나오는 곳을 셌다. `INDEX-auto.md`(make-index.py가 449개 파일을 모두 나열)와 `library/INDEX.md`는 색인이라 소비자에서 뺐다. **살아 있는 소비자**로 본 것: `docs/claude/*.md`가 아닌 모든 파일(코드·테스트·.txt 예약 지시문·.ps1·.json), `*preregistration*`, `ceo-weekly-report.md`, `roadmap.md`, `00-home.md`, `scheduled-prompts/` 아래 파일, CLAUDE.md, AGENTS.md.
3. 마지막 참조: 그 파일의 마지막 커밋 날짜(`git log`). 다른 문서의 링크는 "문서 링크 수"로만 적었다(모두 같은 묶음 또는 종결된 검토 문서).
4. 끝난 작업 판단: 병합 커밋 또는 기능 커밋이 bb11f04 이력에 있음(`git log --merges`, `git log --grep`).

# 3. 이동 후보 (64개)

"이동 안 하면 생기는 비용"은 모든 후보에 공통으로: ① INDEX-auto.md·Obsidian 볼트·`grep`/LLM 검색 결과에 섞여 현행 근거처럼 읽힐 위험, ② 세션이 문서를 찾을 때 읽는 양(토큰) 증가, ③ T4 정리 때 다시 전수 조사해야 하는 일. 표의 "추가 비용"은 그 묶음에만 해당하는 것.

| 묶음(종결 근거) | 파일 (마지막 커밋 · 바이트 · 문서 링크 수) | 추가 비용 |
|---|---|---|
| S4 신호 연구(merge 10-01) | s4-builder-report-2026-10-01.md (10-01 · 7,941 · 2) · s4-2-builder-report-2026-10-01.md (10-01 · 7,200 · 2) · s4-3-builder-report-2026-10-01.md (10-01 · 8,396 · 2) | 손실 한도 검토 문서와 이름이 겹쳐 검색 혼동 |
| S6 = S5 손실한도 정책안 Judge(커밋 10-01 "S6 pass") | s6-judge-prompt-2026-10-01.md (10-01 · 19,239 · 3) | — |
| S7 1단계와 하위 작업(merge 10-02) | s7-builder-report-2026-10-01.md (10-10 · 134,376 · 14) · s7-1-judge-prompt-2026-10-01.md (10-02 · 10,378 · 2) · s7-calendar-binding-builder-report-2026-10-02.md (10-02 · 22,695 · 2) · s7-calendar-binding-judge-prompt-2026-10-02.md (10-02 · 10,035 · 2) · s7-cli-page-shape-builder-report-2026-10-02.md (10-02 · 3,501 · 1) · s7-split-adjustment-builder-report-2026-10-02.md (10-02 · 9,781 · 1) · s7-u3-cash-flow-evidence-builder-report-2026-10-02.md (10-02 · 7,499 · 3) | s7-builder-report는 docs/claude 최대급(134KB). "S7"은 지금도 코어 노출 규칙 이름이라 옛 S7 수동 루틴 서술이 현행처럼 검색됨 |
| I0 대조 루프(merge 09-30) | i0-builder-report-2026-09-30.md (09-30 · 41,958 · 2) | 대조 규칙(현행은 redesign 3-5)과 혼동 |
| p-earn(merge 10-03) | p-earn-builder-report-2026-10-03.md (10-03 · 23,640 · 2) · p-earn-judge-prompt-2026-10-03.md (10-03 · 6,895 · 0) · p-earn-judge2-prompt-2026-10-03.md (10-09 · 10,354 · 1) | — |
| S1b plan B'(merge 10-04) | s1b-plan-b-builder-report-2026-10-04.md (10-04 · 9,798 · 2) | — |
| gov-r6 I4 R6/R7(merge 10-05) | i4-r6-builder-report-2026-10-05.md (10-05 · 34,300 · 2) | 은퇴한 키움 승인 고정(CLAUDE.md "Kiwoom acceptance pin: retired")을 현행처럼 읽을 위험 |
| e-filing-feed K2(기능 커밋 10-05 "feat(sec-shadow)") | e-filing-feed-k2-builder-report-2026-10-05.md (10-05 · 7,710 · 2) | — |
| 키움 토큰 재사용·재고정(기능 커밋 10-06, 고정은 T1이 은퇴) | kiwoom-token-reuse-builder-report-2026-10-06.md (10-06 · 38,209 · 6) · kiwoom-token-reuse-judge-prompt-2026-10-06.md (10-09 · 7,961 · 0) · kiwoom-repin-judge-prompt-2026-10-07.md (10-07 · 9,817 · 2) · kiwoom-repin-judge-report-2026-10-07.md (10-07 · 9,753 · 1) | 인증·토큰 문서가 현행 규칙(CLAUDE.md Kiwoom query rules)과 섞여 검색됨 |
| I0-b·r-i0b-k2(merge 10-07) | i0b-policy-builder-report-2026-10-06.md (10-07 · 34,651 · 5) · i0b-policy-judge-prompt-2026-10-06.md (10-07 · 10,917 · 1) · r-i0b-k2-builder-report-2026-10-07.md (10-07 · 14,179 · 1) | — |
| redesign T1(merged 510961a) | redesign-t1-builder-r2-2026-10-10.md (10-10 · 5,926 · 2) · redesign-t1-builder-r3-2026-10-10.md (10-10 · 4,018 · 2) · redesign-t1-judge-prompt-2026-10-10.md (10-10 · 7,200 · 1) · redesign-t1-judge-report-2026-10-10.md (10-10 · 15,905 · 4) · redesign-t1-judge2-prompt-2026-10-10.md (10-10 · 2,625 · 1) · redesign-t1-judge2-report-2026-10-10.md (10-10 · 11,166 · 1) | — |
| redesign T2(merge 10-12) | redesign-t2-builder-r2-2026-10-10.md (10-10 · 10,170 · 2) · redesign-t2-builder-r3-2026-10-11.md (10-11 · 5,754 · 2) · redesign-t2-builder-r4-2026-10-11.md (10-11 · 4,753 · 2) · redesign-t2-builder-r5-2026-10-12.md (10-12 · 4,627 · 2) · redesign-t2-judge-prompt-2026-10-10.md (10-10 · 8,168 · 1) · redesign-t2-judge-report-2026-10-10.md (10-10 · 29,639 · 8) · redesign-t2-judge2-prompt-2026-10-11.md (10-11 · 6,346 · 2) · redesign-t2-merge-2026-10-12.ps1 (10-12 · 10,602 · 1) | — |
| redesign T3·T3b(커밋 10-10 "T3 done, T3b merged") | redesign-t3-builder-r2-2026-10-10.md (10-10 · 5,825 · 3) · redesign-t3-judge-prompt-2026-10-10.md (10-10 · 10,718 · 2) · redesign-t3-judge-report-2026-10-10.md (10-10 · 21,510 · 5) · redesign-t3-judge2-prompt-2026-10-10.md (10-10 · 4,495 · 2) · redesign-t3-judge2-report-2026-10-10.md (10-10 · 12,480 · 3) · redesign-t3b-builder-report-2026-10-10.md (10-10 · 25,287 · 3) · redesign-t3b-judge-prompt-2026-10-10.md (10-10 · 7,715 · 1) | — |
| redesign T3c(merge 10-12) | redesign-t3c-judge-prompt-2026-10-12.md (10-12 · 8,733 · 1) · redesign-t3c-merge-2026-10-12.ps1 (10-12 · 7,213 · 0) | — |
| t2-equity-cash(merge 10-13) | t2-equity-cash-judge-prompt.md (10-13 · 3,254 · 1) · t2-equity-cash-merge-2026-10-13.ps1 (10-13 · 5,103 · 1) | — |
| rrec-rg1(merge 10-13) | rrec-rg1-judge-prompt.md (10-13 · 3,207 · 2) · rrec-rg1-merge-2026-10-13.ps1 (10-13 · 5,347 · 1) | — |
| T2 첫 실행 병합 보조(10-13, runner-fix·ust21100-fix2 merged) | merge-cmpfix2-ust21100-2026-10-13.ps1 (10-13 · 3,254 · 1) · merge-ust21100-fix2-2026-10-13.ps1 (10-13 · 3,265 · 2) · runner-fix-merge-retry-2026-10-13.ps1 (10-13 · 4,538 · 1) | 앞의 둘은 안에서 `dev-merge.ps1 … -ApproveAuthority`를 부른다(hnd-check-report.md:101). 다시 돌릴 대상이 아닌데 눈에 띄는 곳에 남아 있음 |
| hwm-fix(merge 10-17) | hwm-fix-judge-prompt.md (10-17 · 15,491 · 3) · hwm-fix-merge-2026-10-17.ps1 (10-17 · 6,715 · 1) | — |
| ev-rg1-hyper(merge 10-18) | ev-rg1-hyper-judge-prompt.md (10-18 · 14,708 · 4) · ev-rg1-hyper-merge-2026-10-18.ps1 (10-18 · 10,662 · 2) | — |
| rrec-ev4-remove(merge 10-19) | rrec-ev4-remove-judge-prompt.md (10-19 · 10,631 · 4) · rrec-ev4-remove-merge-2026-10-19.ps1 (10-19 · 12,023 · 2) | — |
| close-confirm-e(merge 10-21) | close-confirm-e-judge-prompt.md (10-21 · 20,063 · 3) · close-confirm-e-merge-2026-10-21.ps1 (10-21 · 10,729 · 2) | — |
| 관제판 검토 지시문 초안 v1(v1.1로 대체) | dev-board-review-prompt-v1-draft-2026-10-03.txt (10-09 · 10,683 · 1) | v1.1(scheduled-prompts/README.md가 참조)과 이름이 비슷해 잘못 고를 위험 |

병합 스크립트(.ps1)는 이미 실행된 기록이고 고정된 base SHA·sha256을 담는다(hnd-check-report.md:101). 옮길 때는 `git mv`로 바이트를 그대로 두고, 내용은 고치지 않는다.

# 4. 후보에서 뺀 것과 이유

| 무엇 | 이유 |
|---|---|
| `*-builder-prompt.md` 61개 | 00-home.md:21 "고치면 안 되는 파일"(개발 실행이 멈춤). 실제로 코드가 읽는 예도 있다: rrec-rg1-builder-prompt.md ← docs/claude/t2rc-oracle.py. 끝난 작업분만 옮기려면 표 개정이 먼저 필요(사장 결정) |
| 같은 묶음의 Judge 보고·Builder 보고 중 살아 있는 소비자가 있는 것 | 예: hwm-fix-report.md·rrec-ev4-remove-report.md(테스트가 참조), redesign-t1-builder-report(CLAUDE.md:73·test_auto_core.py), redesign-t2/t3-builder-report(tools/dev_pipeline/authority-paths.txt), redesign-t3b-judge-report(devpipe.py), i1-builder-report(test_holding_card.py), *-judge-report 다수(ceo-weekly-report.md·t2-rc-preregistration·예약 지시문 .txt) |
| t2rc·c1-keep·r5-align 묶음 | T2 "켜" 평가(t2-rc-preregistration-2026-10-14.md)가 아직 진행 중이고 그 문서가 이 보고들을 참조 |
| recon-dt·cf-b2n·hnd-check·d124 | 오늘(10-25) 병합. 관제판·주간 보고 반영 전이라 아직 현행 근거 |
| ceo-room-merge-2026-10-22.md | 개발 묶음이 아니라 조직 결정 기록(single-channel-redesign이 참조) |
| integrated-check-prompt-v*.txt 23개 | scheduled-prompts/README.md 변경 기록과 해시가 판본을 참조. 지시문 교체 이력이라 별도 판단(확인 필요) |
| 하위 폴더(dev-runs/ 등) | dev-runs/는 파이프라인이 쓰는 곳. 이 조사 대상 밖 |

# 5. 확인 필요

- 저장소 밖 소비자: claude.ai 예약 작업 원본 지시문, 관제판 DB, Obsidian 링크는 이 조사가 읽지 못했다. 이동 전 scheduled-prompts/README.md 표의 현행 지시문 사본으로 다시 grep한다.
- 메인 체크아웃의 커밋 안 된 파일(hnd-check-report.md:101에 따르면 recon-dt·cf-b2n 병합 스크립트 등)은 bb11f04 기준이 아니라 이 목록에 없다.
- 이동 위치(`docs/claude/archive/` 등)와 INDEX-auto.md 재생성 방식은 T4 설계에서 정한다. 옮기면 다른 문서의 링크(위 "문서 링크 수")는 낡은 경로가 된다 — 끝난 문서 사이 링크라 실행에는 영향이 없다.

# 6. 바뀔 조건

- 이동 시점에 어떤 후보가 코드·예약 지시문·사전 등록·주간 보고에서 새로 참조되면 그 파일은 후보에서 뺀다.
- 00-home.md 표가 "끝난 작업의 builder-prompt는 이동 가능"으로 바뀌면 builder-prompt 중 끝난 묶음분을 후보에 더한다.

검토 완결: 원문 확인 64/64(후보 전부 참조 재계산) · 내장 재검토 0회(목록 작성, 결정 요청 없음 — 사장 D3 승인 범위) · 미해결 3(5절) · 자료 시점 2026-10-25 KST, bb11f04 · 바뀔 조건 6절.
