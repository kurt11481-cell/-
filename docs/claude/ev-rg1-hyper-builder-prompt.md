---
id: ev-rg1-hyper-builder-prompt
title: R-REC1 RG1 결함 수정 — 공식 테제 훼손은 카드 재수락 전까지 매수 막힘(사건 날·재기준·시간 소멸·닫힘과 무관) + 빅테크 훼손 출처 + 독립 계산기 RG1 동반 수정
date: 2026-10-17
class: 권한·한도 변경(K3 — 매수 관문 R-REC1 RG1의 의미. auto_core*.py·tests/test_auto_core*.py·card-evidence-registry.json·auto-core-*.schema.json = tools/dev_pipeline/authority-paths.txt 12·25·64·65행. 독립 계산기 고정값 = t2-rc-preregistration-2026-10-14.md 1절 C1·49행). 수동 경로: 이 Builder(worktree) → 별도 Judge 세션(docs/claude/ev-rg1-hyper-judge-prompt.md) → 사용자 승인 1줄 + 병합 스크립트 1번(Judge PASS 뒤 Cowork 작성)
decision: 사용자 "결정 ev-rg1-hyper: a"(2026-10-14 00:28 KST, event-strategy-2026-10-13.md 11-1 ①~④) · "결정 rrec-k3-timing: d"(2026-10-16 09:21 KST, pre-on-roadmap-review-2026-10-15.md 결정 기록 — hwm-fix 병합 뒤 계산기 RG1 동반 수정과 한 K3 묶음, 새 sha → Judge → 실행기 고정값 교체 승인, C1은 병합 뒤 0부터, "켜" 전) · 결정 D1 = c(2026-10-17 18:5x KST, 아래 "결정 항목")
evidence: event-strategy-2026-10-13.md 11-1·11-1a·11-2 · pre-on-roadmap-review-2026-10-15.md 3절·결정 기록 · hwm-fix-judge-report.md 발견 1 · recovery-gate-R-REC1-2026-10-09.md 37·43행 · 관제판 ev-rg1-hyper(version 7, next·doneWhen)
base: main(codex/master-recovery-expansion) HEAD a9ea3382639e17cc7bb0e5057b57c701eef3e6f1 — sha256(Windows 작업 트리 바이트): auto_core_rules.py 511c8a13ca3da46e5f4bb39a80e12ca3b72b6f23766e78948eed92a43aebe56a · auto_core_inputs.py 89666f990d975f2ed9d8004013b68a35aa40c31aa328cd5becba81a61446de9b · auto_core_decide.py 2eba6c58a67d025f6892e626b24f003ba3d26a5524a782eb5cbb2747c6731e33 · auto_core_tickets.py 846c3d862e5f13e35fea5d603a15fa4592451b71270a0dec1fe523398d3b7d9b · auto-core-card-registry.schema.json 663c6aaf9222774387e5b474136e6356a28e181da628296398a1f102fb800ca8 · docs/claude/t2rc-oracle.py sha256_lf 5607b09b47585a8b0799ae84b93cff434ebecdfc2b30f305607c8641b8f02a26(= 실행기 고정값. 메인 작업 트리는 LF라 원시 sha도 같지만 worktree는 CRLF로 체크아웃된다 — hwm-fix worktree 원시 af226e0a…, LF 5607b09b…) · docs/claude/t2rc-check-run.ps1 5d3502b90b3901823e0eded7d196d7c6710b63765bc7d003dc3e1ef313d2df7b(메인, LF) · test_auto_core_risk1r.py e2f16d19214830e5d66b153c92ae354314acf9270faf9c8417905cc972a56e70. 등록부는 HEAD 판(메인 작업 트리에는 커밋 안 된 10-17 카드 세션 변경이 있다 — _pending/wcg-1017.txt, 23:30 DocsCommit 대상)
model: Opus · xhigh · 새 worktree (claude --worktree ev-rg1-hyper)
authority: order_authority=false · quantity_authority·execution_quantity 불변 · R-REC1 사건(EV1~EV5)·C0·L0·DS1·RG2·RG3·RG4·EV3B 기록 공백·RG1 기록 범위(rrec-rg1 B)·rules.CONSTANTS 불변 · 정책·상태·장부·일지·예약 작업 불변 · 키움 호출 없음 · 판정은 더 엄격하게만(예외 1개: 결정된 해제 = 카드 재수락, 아래 R7)
weekly_user_touch: 0 (일회성: Builder 시작 1·Judge 시작 1·승인 1줄·병합 1번. 예외 때만: 공식 훼손 사실이 나오면 매수하려는 종목의 카드를 Cowork에서 다시 수락)
deadline: T2 "켜" 전(결정 d). 병합 전까지 센 C1 세션은 버려지므로 빠를수록 손실이 작다(10/17 C1 2/10, 관제판 redesign-t2)
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree(claude --worktree ev-rg1-hyper) · 이유: 매수 관문 R-REC1 RG1 의미 변경 + 독립 계산기 동반 수정(K3)

# 목표

승인된 RG1 정의는 "이벤트 뒤 2세션 경과 + 그 사이 테제를 깎는 공식 확인 없음 … **공식 확인이 나오면 카드 재작성 전 매수 금지**"다(recovery-gate-R-REC1-2026-10-09.md 37행). 코드는 훼손 사실을 **사건 날보다 뒤이고 판정일 이하**일 때만 센다(auto_core_rules.py 862~863행 `damage_after`, 계산기 t2rc-oracle.py 1048행). 그래서 ⓐ 훼손 날 자체가 사건이 되면(같은 날 −1σ 이하 → EV3b·EV1) 그 사실을 세지 않고, ⓑ 훼손 뒤 새 사건이 오면 기준이 다시 잡혀(834행 `events[-1]`) 잊고, ⓒ 사건 없이 나온 훼손은 아무 관문도 열지 않고(831~833행), ⓓ 시간 소멸 닫힘(907~909행)은 RG1이 '아니오'여도 사건을 닫고 닫힌 뒤 훼손은 무시된다. 승인된 정의와 코드가 다른 **결함**이다(event-strategy 11-1a 공백 2). 또 하이퍼스케일러 공식 IR은 출처로 받지 않는다(auto_core_inputs.py 207~215·246~248행, 계산기 819~826행).

**바꿀 의미(결정 a 수정판 ①~④, 11-1)**
- ① 창(60세션) 안의 공식 훼손 사실은 그 후보 카드가 그 뒤에 다시 수락될 때까지 RG1 = 아니오 — 사건 날·재기준·시간 소멸·닫힘과 무관. 해제 = 카드 재수락 또는 창 밖으로 밀려남.
- ② 시간 소멸 닫힘은 RG1이 '아니오'인 날 닫지 않는다.
- ③ 등록부 최상위 훼손 전용 도메인 목록 → 코어·계산기는 root_thesis_damage가 참인 사실에 한해 그 도메인을 받고, 그 사실은 RG1에만 쓴다(매수·매도 근거·C7·EV3b에 안 씀).
- ④ 훼손 사실이 없으면 결정·주문표·해시 불변(골든).
- 독립 계산기(t2rc-oracle.py) RG1을 같은 정의로 고치고, 실행기 고정값(t2rc-check-run.ps1 16행)을 새 sha로 바꾼다(결정 d).

# 근거 (Cowork 2026-10-17 17~18시 KST 읽기 전용 확인 — Builder는 원문을 다시 연다)

1. **코어 rrec1**(auto_core_rules.py 754~920행): 사건 목록 809~830, EV3b = 훼손 사실 날 + 같은 날 SOXX ≤ −1σ60(807·819~820), 가장 최근 사건으로 기준(834~837), RG1 기록 범위(rrec-rg1 B, 839~853), `gates` 861~893(RG1 862~869), 닫힘 루프 895~909(모두 충족 904~906, 시간 소멸 907~909), 사건 = 평가 세션 910~911, 결과 914~920, `settle`(EV3B 공백 → unk) 801~805. 호출: auto_core_decide.py 1065~1074(종목별 + 포트폴리오 candidate=None), `damage = list(research["damage"])` 1005행 — **훼손 사실은 종목 구분 없이 모든 후보에 적용**된다(뿌리 테제).
2. **훼손 사실 적재**: auto_core_inputs.py `load_research` 263~301(창 = 기록 날 ≥ window_start, `damage` 294행, `facts` 292행), `check_record` 218~260(출처 = sec.gov 또는 그 사실 종목의 등록부 official_domains, 247~248행). decide의 창: 647~650행(평가 세션까지 60세션).
3. **카드 수락 날**: 등록부 HEAD 9종목(메인 작업 트리 10 — PLTR은 커밋 전) 모두 `accepted.date`가 있다(스키마 필수 — auto-core-card-registry.schema.json `accepted` required [text,date,source], additionalProperties false). 보유 MVLL·SOXL·NBIS "2026-10-04", 관심 MU·BE·DELL·AMD 10-02, PWR·LITE 10-03(HEAD 판). 등록부 updated_by(10-17 작업 트리) "관심 카드 7장 kill ④ 삭제로 절 해시 갱신 — accepted 날짜·원문은 유지" → **section_sha256 변경은 재수락 신호가 아니다. 해제 신호는 accepted.date만** 쓴다(11-1a의 확인 필요 "카드 재작성 신호" 해소). 등록부 스키마 최상위는 additionalProperties false → 새 키는 스키마 변경이 필요하다.
4. **실데이터에 훼손 사실 없음**: workspace/outputs/research-records/2026-10-13~2026-10-17 official_facts 0건(root_thesis_damage 0). 10-17 decision.json shock: event 2026-10-16 [EV2, EV4], rg RG1 no·RG2 no·RG3 no·RG4 ok, status no, by_symbol 8종목 같음. 10-17 t2rc-check.json verdict MATCH, requirements diffs [].
5. **주문표 요건 ⑤ 칸**(auto_core_tickets.py 268~277행): status unk → 확인 필요, open이면 RG 값, **그 밖(open False)은 "통과 (열린 이벤트 없음)"**. 그래서 사건이 닫혔거나 없을 때 status만 "no"로 바꾸면 매수가 열린다(fail-open 함정) → 칸 논리를 함께 고친다(D-1).
6. **open을 읽는 다른 곳**: auto_core_compare.py 270~292(포트폴리오 shock open·rg를 통합 점검과 대조), auto_core_decide.py 437~441(알림 상태 2:RREC 열림·닫힘), score_decision_journal.py 1328~1345(open 참인 날 묶음). → `open`의 뜻(사건이 열려 있음)은 바꾸지 않는다.
7. **하이퍼스케일러 IR 호스트**: docs/claude/event-calendar.json result_url — www.microsoft.com·abc.xyz·investor.atmeta.com·ir.aboutamazon.com(+ source_url news.microsoft.com). 하위 도메인 규칙은 기존 `_host_allowed`(207~215행)·계산기 822~825행과 같다 → 목록 microsoft.com·abc.xyz·atmeta.com·aboutamazon.com.
8. **재기준 주의**(11-1a): 새 사건은 C0·L0를 다시 잡아 더 낮은 종가 날이면 RG3·DS1이 쉬워진다(834~837행). 그래서 ③ 도메인으로만 받은 사실이 EV3b를 만들면 "더 엄격하게만"이 깨질 수 있다 → EV3b에 쓰지 않는다(R5).
9. **계산기**: docs/claude/t2rc-oracle.py `rrec1` 979~1099(EV3B 공백 1001~1011, 사건 1012~1035, 사건 없음 1036~1037, `rg12` 1045~1064·RG1 1048~1055, 루프 1066~1091·닫힘 1089, 닫힘 반환 1092~1093, 결과 1094~1099), `validate_facts` 805~844, `load_research_history` 1309~1325, 요건 ⑤ 호출 1820~1823, G2 `lines_open` 1851행, `sha256_lf` 108~111행. 계산기는 auto_core*를 import하지 않는다(사전 등록 3절 M1). 실행기 docs/claude/t2rc-check-run.ps1 16행 `$ExpectedOracleSha256` = LF 정규화 sha, 다르면 실행하지 않고 ORACLE_SHA_MISMATCH(8~14행 주석). 사전 등록 1절 C1 "계산기 결함 → 계산기 수정(새 sha, Judge 확인) 뒤 C1을 0부터", 49행 고정값(계산기 5607b09b… · 실행기 5d3502b9…). 요건 비교: 계산기 1493~1499·1990~1993행이 요건 ①~⑤ 상태 문자열을 코어 칸 `s`와 그대로 비교한다 → 상태 우선순위가 같아야 한다(R4).
10. **줄 끝**: 인덱스는 모두 LF. Windows 체크아웃(worktree)은 CRLF다 — t2rc-oracle.py·t2rc-check-run.ps1도 worktree에서는 CRLF(hwm-fix·pre-on-fix worktree 2249/2249·117/117행 CRLF). 메인 작업 트리의 두 파일만 LF다. 어느 쪽이든 **체크아웃된 줄 끝 그대로** 둔다(일괄 변환 금지). 계산기 고정값·비교·병합 확인은 `sha256_lf`(LF 정규화)로만 한다 — 실행기도 LF로 정규화해 비교하므로(16행·주석 12~13행) 줄 끝과 무관하다.
11. **기준선(Cowork, 장치 VM Linux Python 3.10, 메인 작업 트리)**: `test_auto_core*.py` Ran 423, 실패 2 = test_auto_core_risk1r `test_tickets_without_risk_1r_hash_as_before`(decide_compare·decide_apply 값이 OS마다 다름 — hwm-fix에서 확인) + test_auto_core_decide `RegistryTests`(symbol PLTR — 메인 작업 트리의 커밋 안 된 PLTR 항목이 CARD_SECTION_CHANGED·관심 명단 미수락. 범위 밖 자료 상태. worktree(HEAD)에는 PLTR 항목이 없다). 계산기 `selftest` PASS. **Windows worktree에서 다시 잰다.**

# 새 RG1 규칙 (코어와 계산기의 공통 정의 — 이 절이 기준이다)

- **R0 정의**
  - 창 W = 평가 세션 t의 SOXX 세션에서 lo = max(0, t − 60 + 1) ~ t(코어 `window_start`, 계산기 `lo` — 지금 그대로). W[0] = 그 첫 세션 날짜.
  - 훼손 사실 F = 지금처럼 유효 연구 기록의 root_thesis_damage 참인 사실 + ③의 훼손 전용 도메인 사실(B·G절).
  - 해제 날 rel(f) = max(f.event_session, f.announced_at을 KST(UTC+9 고정 오프셋)로 바꾼 날짜). 읽기 규칙(양쪽 같게): announced_at은 끝의 "Z"를 "+00:00"으로 바꾼 뒤 ISO 시각, 오프셋 필수(auto_core_inputs.py `_moment` 197~204행과 같음). 못 읽으면 rel(f) = 없음. accepted.date는 YYYY-MM-DD 엄격 읽기, 못 읽으면 카드 날 없음.
  - 카드 날 a: 후보 = 등록부 `symbols[후보].accepted.date`. 코어 포트폴리오 판정(candidate=None) = 지금 보유 종목들의 accepted.date 중 가장 이른 날(보유 종목 중 등록부 항목이나 날짜가 없는 것이 하나라도 있으면 없음). 계산기에는 포트폴리오 판정이 없다.
  - 해제됨(f, a, d) ⟺ a 있음 그리고 rel(f) 있음 그리고 rel(f) ≤ a ≤ d. **소급 해제 금지**: 재수락은 그 날짜(a) 이후 세션부터만 효력이 있다 — 재수락 전 날의 RG1을 다시 계산해 그날 닫힘(모두 충족·시간 소멸)이 생기면, 지금 RG2가 no이거나 DS1이 진행 중이어도 결과가 ok(닫힘)가 되어 결정 ①·②보다 느슨해진다. a는 KST 날짜, d는 미국 세션 날짜라 KST 아침 재수락은 한 세션 늦게 풀릴 수 있다(더 엄격).
  - 미해제 집합 U(d) = { f ∈ F : W[0] ≤ f.event_session ≤ d 그리고 해제됨(f, a, d)이 아님 }. 루프의 i일은 d = day_i, R3는 d = t.
  - 결정 문구 "accepted.date ≥ 훼손 event_session"을 **더 엄격하게만** 고친 것이다: 장 마감 뒤 발표는 event_session이 미국 날짜, KST로는 다음 날이라, 발표 전에 같은 날짜로 수락된 카드가 보지도 않은 사실을 해제하는 경우를 막는다(KST 날짜 ≥ event_session이 항상 참이라 더 느슨해지는 경우는 없다).
- **R1 RG1(i)**(열린 사건 e, e < i ≤ t, 그리고 e = t인 경우): F가 None(연구 기록 추적 안 함)이면 unk(그대로). U(day_i)가 비어 있지 않으면 **아니오**. 그 밖은 지금 그대로(i − e ≥ 2 그리고 기록 범위). 사건 날짜와 비교하지 않는다 → ⓐ 사건 날·ⓑ 재기준 전 훼손도 센다.
- **R2 닫힘**: RG1~RG4 모두 충족 닫힘은 그대로. **시간 소멸 닫힘(DS1 없이 20세션 + RG2)은 그날 RG1이 '아니오'면 닫지 않는다**(코어 907행, 계산기 1089행). RG1 unk는 지금처럼 시간 소멸을 막지 않는다.
- **R3 닫힘 뒤·사건 없음**: 사건이 닫혔을 때와 창 안에 사건이 없을 때(아래 "D2 처리"), F가 None이 아니고 U(t)가 비어 있지 않으면 → status "no", `open`은 False 그대로(사건이 열린 것이 아니다), rg["RG1"] = "no"(다른 관문 값은 있으면 그대로, 없으면 넣지 않는다), reasons에 `RG1_THESIS_DAMAGE:<fact_id 쉼표, 정렬>` 1개. closed_at·events는 그대로.
- **R4 상태 우선순위**(코어·계산기 같게): 자료 없음 → unk(코어 BENCHMARK_DATA_MISSING·BENCHMARK_SIGMA_UNAVAILABLE·EVENT_LOW_UNAVAILABLE, 계산기 SOXX_MISSING·CANDIDATE_MISSING·C0_L0_MISSING — 그대로) → EV3B 기록 공백 → unk(코어 `settle`, 계산기 1001~1011 — 그대로) → R3 → 지금 결과 식. 요건 ⑤ 칸의 `s`와 계산기 reqs[4]가 모든 경우에 같은 문자열이어야 한다.
- **R5 바꾸지 않는 것**: 사건 목록·EV 종류·C0·L0·DS1·RG2~RG4·EV3B 공백·RG1 기록 범위. EV3b는 지금처럼 기존 출처(sec.gov·그 종목 official_domains) 훼손 사실만 만든다 — ③ 도메인으로만 받은 사실은 EV3b를 만들지 않는다(근거 8).
- **R6 해제 경로**: 카드 재수락(rel(f) ≤ a ≤ 판정하는 날) 또는 창 밖(f.event_session < W[0]). 시간 소멸·새 사건·닫힘·통합 점검 문구로는 해제되지 않는다.
- **R7 엄격성**: 해제된 사실이 없는 입력에서 새 결과는 지금 결과보다 느슨하지 않다(지금 막힘 no·unk면 새것도 막힘, 지금 ok면 새것은 ok 또는 no). 느슨해지는 유일한 경로는 결정된 해제(재수락, 그 날짜 이후 세션만)다 — 지금 코드는 "사건 뒤 훼손"을 수락과 무관하게 그 사건이 닫힐 때까지 센다. 재수락이 있어도 재수락 전 날의 판정은 해제 없는 판정과 같아야 한다. 그 밖의 느슨해짐이 보이면 멈추고 보고한다.
- **R8 출력 키**: 미해제 사실이 있을 때**만** rrec1 결과에 `rg1_damage`(U(t)의 fact_id 정렬 목록)를 싣는다(사건 열림·닫힘·없음 모두). 없으면 결과 dict는 base와 글자까지 같다.

# 결정 항목

## D1 — 계산기 G2 `lines_open` (답: **c 항 삭제** — 사용자 선택 "c 항 삭제 (Recommended)", 2026-10-17 18:5x KST Cowork 대화)
- 문제: 계산기 G2(t2rc-oracle.py 1851행)는 L2 이상 선이 같은 하락 구간에서 한 번 걸리면 일지 검토 뒤에도 계속 참이다. 코어 멈춤은 열린 사건 중 멈춤 표지(pause_add·pause_new_buy)가 있는 것만 REVIEW_LINE_OPEN으로 싣는다(portfolio_exposure.py 1378~1386행). 승인 규칙은 코어 쪽이다 — R4 "L2 and below pause recommendations until a journal review"(references/portfolio-exposure-review.md 27행), `line_review_completed` "for L2 and below it releases the pause"(같은 파일 321행). 계산기 주석(1850행)도 "until a journal review".
- 영향: L2 검토가 기록되면(10-19 수락 세션 예정, l2-full-review-2026-10-17.md) 다른 관문이 모두 열리는 날 코어는 매수 주문표를 내고 계산기는 그 주문표의 G2를 false로 본다 → 주문표 항목 불일치(should_exist·G2) → MISMATCH → C1 0부터 + 그 방향 첫 주문표 "확인 대기 — 입력 금지"(사전 등록 C3). 회로 집합(C1 match 1464행)은 G2와 무관하다. R-REC1이 막는 동안은 실효 없음(hwm-fix-judge-report 발견 1).
- c: 1851행의 `lines_open` 항을 지운다. 같은 G2 식의 `not s7["pauses"]["new_buy_recommendations"].get("paused")`(1854행)가 열린 멈춤 선(REVIEW_LINE_OPEN)을 이미 막는다(REMOVE — 가장 단순).
- a: 1851행을 `lines_open = any(event.get("pause_add_recommendations") or event.get("pause_new_buy_recommendations") for event in s7["review_lines"].get("open_events") or [])`로 바꾸고 주석에 R4·321행을 적는다(c와 결과가 같고, S7 안 open_events와 pauses의 일관성을 한 번 더 본다).
- b: 그대로(1851행 불변) — 기본값.

## D2 처리 — 창 안에 사건이 없을 때의 미해제 훼손: 막는다 (질문하지 않음)
- 결정 a의 고칠 결함 목록(11-1a 공백 2)에 ⓒ "사건 없이(−1σ 미만) 나온 훼손은 아무 관문도 열지 않는다"가 들어 있고, 11-1 ①은 "사건 날·재기준·시간 소멸·닫힘과 무관", 승인 정의는 "공식 확인이 나오면 카드 재작성 전 매수 금지"(37행)다. 그래서 결정 범위 안의 구현으로 본다.
- 막지 않으면 R5(③ 사실은 EV3b를 만들지 않음)와 겹쳐, 창 안에 다른 사건이 없을 때 하이퍼스케일러 설비투자 하향은 아무것도 막지 못한다(③을 넣는 이유가 사라진다). 또 60세션 안에 무관한 닫힌 사건(예: EV4)이 있느냐에 따라 같은 훼손의 결과가 갈린다.
- 사용자가 다르게 정하면 Cowork가 이 절을 고친다(그때는 R3를 닫힌 사건에만).

# 바꿀 것

## A. auto_core_rules.py
1. 순수 함수 하나(예: `uncleared_damage(thesis_damage, window_start_day, through_day, card_accepted_on)` → U(through_day)의 사실 목록, fact_id 정렬 — R0의 a ≤ d 조건 포함)를 두고 rrec1이 쓴다. KST 변환은 고정 오프셋(UTC+9)으로 한다(계산기 1231행 `KST`와 같게).
2. `rrec1`에 키워드 인자 `card_accepted_on: str | None = None`만 더한다(기본값 None = 해제 불가 → 기존 호출의 동작은 R1~R3 그대로).
3. RG1(R1): 862~869행의 `damage_after`를 U(day_i) 기준으로 바꾼다. 기록 범위·2세션 조건은 그대로.
4. 시간 소멸(R2): 907행 조건에 `current["RG1"] is not False`를 더한다.
5. R3: 914~916행(닫힘 반환)과 831~833행(사건 없음 반환) 앞에서 U(t)를 보고 R3대로 바꾼다. `settle`은 그대로 마지막에 적용(R4).
5-1. R8: U(t)가 비어 있지 않을 때만 결과에 `rg1_damage`를 싣는다(열림·닫힘·없음 모두).
6. EV3b(R5): 807행 `damage_days`는 ③ 표지(B-3)가 없는 사실만으로 만든다.
7. docstring의 thesis_damage 설명을 새 규칙으로 고친다(영문, ASCII). rules.CONSTANTS에 새 상수를 넣지 않는다(60·2·20은 기존 상수).

## B. auto_core_inputs.py
1. `load_registry`: 문서 최상위 `thesis_damage_domains`(없으면 빈 목록)를 소문자로 결과에 싣는다(예: 키 `damage_domains`). 등록부 상태가 OK가 아니면 빈 목록.
2. `check_record`: 지금 순서대로 검사하되, 출처 호스트가 sec.gov·그 종목 official_domains에 없고 **root_thesis_damage가 참이고** 호스트가 `damage_domains`에 맞으면(https·`_host_allowed`와 같은 규칙) SOURCE_HOST_NOT_OFFICIAL로 버리지 않고 남은 검사(source_kind·event_session·announced_at·summary)를 계속한다. 통과하면 `facts`가 아니라 별도 목록(예: `damage_only`)에 넣는다. root_thesis_damage가 거짓이면 지금처럼 버린다.
3. `load_research`: ③ 사실은 창 안 기록일 때 `damage`에만 넣고 표지 키(예: `"damage_source": "THESIS_DAMAGE_DOMAIN"`)를 단다. `facts`(C7·근거 판정)에는 절대 넣지 않는다. 기존 사실 dict에는 키를 더하지 않는다.
4. ③ 사실이 없으면 반환 값은 base와 같다(키·값·순서). `today`(check_record 결과)에 새 키를 더하면 decide가 결정 파일에 싣는 부분(decide 655~658행 status·reasons·dropped)이 바뀌지 않는지 확인한다.

## C. auto_core_decide.py
1. rrec1 호출(1065~1074행)에 `card_accepted_on`을 넘긴다: 후보 = `checks[symbol]["entry"]["accepted"]["date"]`(항목 없음 → None), 포트폴리오 = R0의 보유 종목 가장 이른 날. 리플레이(auto_core_replay.py)는 damage []라 영향 없음 — 확인만.
1-1. `shock.by_symbol` 항목(1083~1084행: status·open·rg)에 종목 결과의 `rg1_damage`가 **있을 때만** 같은 키로 싣는다. 포트폴리오 shock은 rrec1 결과를 그대로 펼치므로(1083행) 따로 할 일 없음. 알림(C-2)은 이 두 곳만 읽는다(`alert_candidates`는 decision만 받는다, 801~802행).
2. 알림(398~475행 `alert_candidates`): 포트폴리오나 어느 후보의 U(t)가 비어 있지 않을 때**만** 상태 `2:RG1DMG` = "<fact_id 쉼표>|<막힌 종목 쉼표>"를 alert_states에 둔다(반복 억제용 — 값이 바뀔 때만 알림). 값이 처음 생기거나 바뀐 날에는 **예외 알림**(push 참, 모드와 무관)으로 줄 "R-REC1 RG1 \uacf5\uc2dd \ud14c\uc81c \ud6fc\uc190 N\uac74 \u2014 \uce74\ub4dc \uc7ac\uc218\ub77d \uc804 \ub9e4\uc218 \ub9c9\ud798 M\uc885\ubaa9(\ub300\uc2dc\ubcf4\ub4dc \ub9e4\uc218 \uc694\uac74 \u2464)"(뜻: 공식 테제 훼손 N건 — 카드 재수락 전 매수 막힘 M종목(대시보드 매수 요건 ⑤))을 기존 예외 줄들 **뒤에** 붙인다. 이유: 상태 줄은 `"push": mode == "apply"`(462행, mode = decision_mode 507행)라 비교 모드에서 울리지 않고 알림 ⑦은 push 줄만 보낸다(auto-core-alert.txt 47·122행 "비교 모드에서는 예외만 나온다" — 예외로 두면 이 문구도 그대로 맞다). 줄에 **종목 코드·fact_id를 넣지 않는다**: 기록 모드에서 알림 지시문은 확인 대기 주문표의 종목 코드가 글자로 든 push 줄을 지운다(auto-core-alert.txt 56~60행) — 지워지면 상태는 남아 다음 날 다시 울리지 않는다. 종목·사실은 요건 ⑤ 칸과 `rg1_damage`로 본다. 자료는 C-1-1의 `rg1_damage`에서 읽는다. 미해제가 없으면 alert_states·alerts는 base와 같다. 재수락이 사람 손이라 조용히 막히지 않게 하는 것이 목적이다(pre-on-roadmap 1절 ⑥과 같은 이유). 알림 지시문은 바꾸지 않는다.
3. 결정 파일에 새 최상위 키를 더하지 않는다.

## D. auto_core_tickets.py
1. 요건 ⑤ 칸(268~277행): unk 가지 다음, open 가지 앞에 `status == "no"이고 open이 참이 아님` 가지를 둔다 → {"s": "no", "t": "\ub9c9\ud798 RG1 \uacf5\uc2dd \ud14c\uc81c \ud6fc\uc190(\uce74\ub4dc \uc7ac\uc218\ub77d \uc804)"}(뜻: 막힘 RG1 공식 테제 훼손(카드 재수락 전)). 기존 세 가지의 출력은 글자 하나 바뀌지 않는다(지금은 open False + status no가 생기지 않는다).

## E. manage-us-stock-strategy/schemas/auto-core-card-registry.schema.json
1. 최상위 properties에 선택 키 `thesis_damage_domains`: array, uniqueItems, items = 소문자 호스트 문자열(scheme·경로·대문자 없음, 점 1개 이상). required에는 넣지 않는다. description에 한 문장: 이 호스트는 root_thesis_damage 사실에만, RG1에만 쓰이고(근거·C7·EV3b 아님) 권한 변경(K3)으로만 바뀐다.

## F. docs/claude/card-evidence-registry.json (worktree의 HEAD 판)
1. `"symbols"` 바로 앞에 `"thesis_damage_domains": ["microsoft.com", "abc.xyz", "atmeta.com", "aboutamazon.com"],` 한 줄만 넣는다(들여쓰기·CRLF는 주변 줄과 같게). updated_at·updated_by·symbols는 건드리지 않는다(Cowork 카드 세션과의 병합 충돌을 줄이기 위해 — 출처는 커밋 메시지와 보고서에 남긴다).

## G. docs/claude/t2rc-oracle.py (계산기 — auto_core*를 import하지 않는 원칙 유지)
1. `rrec1`(979~1099행): 인자 `accepted_on`을 더하고(호출 1822행에서 `(e.get("accepted") or {}).get("date")`), R0~R7을 코어와 같은 정의로 쓴다 — RG1 1048~1055행, 시간 소멸 1089행, 사건 없음 1036~1037행·닫힘 반환 1092~1093행에 R3, EV3b 1023~1025행은 ③ 표지 없는 사실만. 반환 dict의 기존 키는 그대로 두고 R3일 때만 rg·reason을 싣는다.
1-1. **훼손 사실 집합을 코어와 같게**(rrec1에 넘기는 기록·훼손 사실에만 — 오늘 사실·C7이 읽는 `history`(1444·1454~1457행)와 C1·C2의 다른 판정은 그대로): ① 코어는 기록을 스키마로 먼저 검사해(auto_core_inputs.py 224~227행) announced_at이 없거나 오프셋이 없는 사실이 하나라도 있으면 **기록 전체**를 무효로 본다(연구 기록 스키마 required·format date-time, validation_common.py 44~48행 `parse_datetime`) — 그 기록은 기록 범위(coverage)에도 훼손 사실에도 들어가지 않는다. 계산기도 rrec1에 넘기는 records에서 그런 기록을 뺀다(그 밖의 스키마 차이는 이미 있던 것 — 범위 밖, 보고서에 적음). ② 사실 단위: 결정 시각 이하 announced_at, event_session ≤ 그 기록의 evaluation_session, summary_ko 200자 이하(코어 check_record 249~254행)를 통과한 훼손 사실만 쓴다(지금 validate_facts 816~843행에는 이 검사가 없다). ③ 같은 fact_id는 세션을 가로질러 기록 날 순 첫 판만 쓴다(코어 load_research 280~294행 setdefault와 같게) — 같은 평가 세션 기록이 여럿이면(1324행 `out[ev] = facts`가 덮어씀) 훼손 사실은 합친 뒤 이 규칙을 적용한다. 새 규칙은 훼손을 최대 60세션 붙잡으므로 이 차이가 MISMATCH·C1 재시작으로 커진다.
2. `validate_facts`(805~844행): B-2와 같은 규칙으로 ③ 사실을 받아 표지를 단다(도메인 목록은 `reg.get("thesis_damage_domains")`). 표지 달린 사실은 rrec1의 RG1 말고는 **어디에서도 쓰지 않는다** — validate_facts 결과를 쓰는 곳을 모두 찾아(오늘 사실·C7·new 표시·근거 r_max·facts 출력 등) 표지 사실을 빼고, 그 위치를 보고서에 표로 적는다.
3. 결정 D1 = c: 1851행 `lines_open` 정의와 1853행의 `and not lines_open` 항만 지우고(1850행 주석은 다음 문장으로 바꿈) 주석에 "R4: pauses.new_buy carries REVIEW_LINE_OPEN for open pause lines (portfolio-exposure-review.md 27, 321)"을 단다. G2의 다른 항은 그대로. 테스트 S16: 일지 검토가 끝난 L2 사건(open_events 없음, lines의 triggered_in_current_drawdown 참, pauses.new_buy 안 멈춤)인 합성 S7 dict에서 계산기 G2가 다른 항만으로 정해지고, 열린 L2(pauses.new_buy REVIEW_LINE_OPEN)에서는 false — selftest에 넣는다.
4. `selftest`: 기존 골든(G-1·G-S1·G-2·앵커)은 그대로 통과. 아래 테스트 S1~S9와 같은 합성 경우를 계산기 쪽에도 넣어 같은 기대값(status·RG1)을 단언한다.
5. 맨 위 docstring 출처 목록에 이 결정(event-strategy-2026-10-13.md 11-1, 이 지시문)을 한 줄 더한다. `ORACLE_VERSION`은 그대로. 그 밖(Judge2 권장 R1~R5, pre-on-roadmap 6절 낮은 위험 등)은 바꾸지 않는다.

## H. docs/claude/t2rc-check-run.ps1
1. 16행 `$ExpectedOracleSha256`만 새 계산기의 LF 정규화 sha256(`sha256_lf`, 108~111행과 같은 계산)으로 바꾼다. 다른 줄과 줄 끝은 체크아웃된 그대로. 이 한 줄이 "실행기 고정값 교체"다 — 효력은 사용자 승인 + 병합 때(아래 "병합" 절).

## I. manage-us-stock-strategy/references/auto-core-decision.md
1. R-REC1 문단(83~92행)의 RG1 문장을 R0~R3·R5로, 등록부 계약 문단(96행 부근)에 `thesis_damage_domains` 한 문장을 더한다(영문). 그 밖은 그대로.

# 바꾸지 않는 것

R5의 관문들, rules.CONSTANTS, RG1 기록 범위, auto_core_compare.py, auto_core_replay.py, score_decision_journal.py, portfolio_exposure.py, 알림·통합 점검·개장 전 예약 지시문과 규칙 파일(docs/claude/scheduled-prompts/**, integrated-check-prompt-*.txt — Judge 뒤 Cowork가 사용자 승인으로 함께 교체, 아래 "병합" 절), 사전 등록 문서, 정책·상태·장부·일지, watchlist-registry.json, 등록부의 symbols.

# 테스트

새 파일(authority-paths.txt 25행 패턴 `tests/test_auto_core*.py`에 맞는 이름) `manage-us-stock-strategy/tests/test_auto_core_rg1_damage.py`. test_auto_core_rules.py·test_auto_core_rrec_bootstrap.py의 `helpers.sessions`·`helpers.bars`·`helpers.zigzag`·`rules.build_series` 방식을 따른다.

- S1 ⓐ 같은 날: 훼손 사실 날에 SOXX가 −2σ(EV1) → 그날이 사건, RG1 no(base: 2세션 뒤 ok). 재수락(rel ≤ a ≤ 평가 세션) → 재수락 날 이후 세션의 RG1은 기록 범위 규칙대로.
- S2 ⓑ 재기준: 사건 A 뒤 훼손, 그 뒤 새 사건 B(EV1) → RG1 no(base: B 뒤 잊음).
- S3 ⓓ 시간 소멸: 사건 → 훼손 → DS1 없이 20세션 이상·RG2 ok → 닫히지 않고 open, RG1 no, status no(base: 닫힘, ok).
- S4 닫힌 뒤 훼손: 사건이 RG1~RG4 충족으로 닫힌 뒤 훼손 → status no, open False, rg RG1 no, reasons `RG1_THESIS_DAMAGE:<id>`(base: ok).
- S5 ⓒ 사건 없음: 상승일 훼손, 창 안 사건 0 → status no·open False·rg {"RG1": "no"}·reasons `RG1_THESIS_DAMAGE:<id>`·`rg1_damage`(base: ok).
- S6 해제 경계(평가 세션 ≥ 그 KST 날짜에서): 장 마감 뒤 발표(announced_at 16:05 −04:00) — a = event_session(미국 날짜) → 막힘, a = 그 KST 날짜 → 해제. 평가 세션 < a면 막힘(a ≤ d). rrec1 단위 입력으로: announced_at 없음·오프셋 없음 → a가 있어도 막힘, "Z" 끝 → +00:00으로 읽음.
- S6b 소급 해제 금지(R0 a ≤ d): 사건 0일 → 훼손 3일 → 5~8일 RG2~RG4 충족 → 9일부터 EMA50 아래(DS1) → 15일 재수락 → 평가 세션 결과는 열림·no(재수락 전 날의 닫힘 없음). base도 열림·no. 재수락 날을 rel(f) 이상 5일 미만으로 두면 그때는 닫힘이 맞다.
- S7 창 경계: event_session = W[0] → 막힘, W[0] 하루 전 → 무시.
- S8 포트폴리오(candidate=None): 보유 종목 수락일 중 가장 이른 날 기준. 보유 종목 하나라도 항목 없음 → 해제 불가.
- S9 ③ 입력: MSFT 사실(https://www.microsoft.com/…, root_thesis_damage true) → load_research damage에만(표지), facts·근거·C7·facts_seen에 없음. 같은 사실 root_thesis_damage false → SOURCE_HOST_NOT_OFFICIAL로 버림(지금처럼). ③ 사실이 −1σ 날이어도 사건 목록은 base와 같다(EV3b 없음), RG1 no. 등록부에 키가 없으면 base와 같다(버림).
- S10 스키마: 키 있는 등록부 통과, 대문자·scheme·경로가 든 호스트는 실패. 실제 등록부(worktree) 통과(validate_schema_contracts.py).
- S11 요건 ⑤ 칸: open False + status no → s "no"·새 문구. 기존 세 가지 출력은 base와 글자까지 같다.
- S12 알림: 미해제 있을 때만 `2:RG1DMG` 상태, 처음·값이 바뀐 날만 예외 줄(push 참 — 비교 모드 포함, 기존 예외 줄 뒤, 종목 코드·fact_id 없음), 값이 같으면 다음 날 반복 안 함, 재수락으로 막힌 종목이 줄면 한 번 더. 미해제 없으면 alert_states·alerts가 base와 같다.
- S13 엄격성(R7): 고정 시드 합성 입력 여러 개(훼손 위치·사건·DS1·RG2 조합, card_accepted_on None, 그리고 재수락 날이 있는 경우)에서 base rrec1 대비 느슨해지는 경우 0 — 재수락이 있는 입력은 "재수락 날 이후만 다를 수 있다"를 단언(재수락 전 날까지 자른 입력에서는 해제 없는 결과와 같다). base 결과는 같은 테스트 안에서 계산하지 말고 base 커밋으로 잰 값을 상수로 고정하거나, R7을 상태 순서(ok > no/unk)로 단언한다.
- S14 골든 불변(④): 훼손 사실이 없는 기존 테스트 전부와 test_auto_core_risk1r GOLDEN이 **고치지 않고** 통과한다. 미해제가 없으면 rrec1 결과·shock·by_symbol에 `rg1_damage` 키가 없다.
- S15 계산기 사실 검사(G-1-1): 오프셋 없는 announced_at이 든 기록은 코어·계산기 모두 rrec1에서 기록 전체가 빠진다(기록 범위 포함). 결정 시각 뒤 announced_at·event_session > 기록 세션·summary 201자인 훼손 사실은 양쪽 모두 쓰지 않는다. 같은 평가 세션 기록 2개·같은 fact_id 다른 판은 양쪽 모두 기록 날 순 첫 판. C7이 읽는 history는 그대로.
- 가능하면 대등 테스트 `test_auto_core_rg1_oracle_parity.py`: 계산기 파일을 importlib로 읽기 전용 로드해 S1~S8과 같은 합성 입력에서 코어 rrec1과 계산기 rrec1의 status·RG1이 같은지 단언한다. 계산기 입력 구조를 만들기 어려우면 만들지 않고, 대신 G-4의 selftest 경우와 이 파일의 기대값이 같음을 보고서 표로 보인다.

기존 테스트는 고치지 않는다. 예외 하나(미리 허용): 훼손 사실이 **카드 수락일보다 앞서** 새 규칙으로 해제되어 단언이 깨지는 테스트는 그 테스트의 카드 수락일 **입력만** 훼손 앞 날짜로 바꾸고 영문 주석 1줄("ev-rg1-hyper: the card must be accepted before the damage fact so it stays uncleared")을 단다. 예상 대상: test_auto_core_decide.py `DamageWindowTests.test_old_damage_fact_keeps_rg1_no`(642~677행 — 훼손 event_session은 DAYS[event+2] ≈ 2026-09 중순, 픽스처 accepted.date는 tests/fixtures/auto_core_t2/helpers.py 84행 "2026-10-01"). 픽스처 helpers.py의 기본값은 바꾸지 않는다. 단언을 바꿔야 하는 테스트나 다른 종류의 입력 변경이 필요하면 **멈추고** 보고서 4절에 파일:행·이유를 적는다(Cowork가 추가 범위를 정한다 — rrec-rg1·hwm-fix 선례).

실행(Claude Code는 "auto_core.py"가 든 명령을 거부한다):
- 변경 전 worktree에서 기준선: `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"`, `python docs/claude/t2rc-oracle.py selftest --repo <메인 체크아웃>`.
- 변경 뒤 같은 명령 + `-p "test_score_*.py"`·`-p "test_decision_journal_cards.py"`. 전체 스위트는 `test-runner` 서브에이전트(Haiku)로 돌려 실패만 보고 — 기준선 대비 새 실패 0, Ran 감소 없음.
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` 통과.

# 실데이터 확인 (읽기 전용, 보고서에 결과만)

입력은 메인 체크아웃(E:\사업\##금동한\코덱스저장소)의 workspace/outputs·docs/claude에서 읽고, 출력은 저장소 밖 임시 폴더(예: $env:TEMP\ev-rg1-check)에만 쓴다. auto_core.py·키움 실행 금지.
1. 연구 기록 2026-10-13~(최신)의 root_thesis_damage 사실 수(Cowork 확인 0)와 ③ 도메인 사실 수.
2. 코어 rrec1 재계산(파일을 쓰지 않는 python 한 번, worktree 코드): 평가 세션 2026-10-16, 포트폴리오와 8종목 — 10-17 decision.json `shock`·`by_symbol`과 같아야 한다(event 2026-10-16 [EV2, EV4], RG1 no·RG2 no·RG3 no·RG4 ok, status no). ev4_sessions는 그 decision의 기록에서 가져온다. 다르면 이유를 적는다.
3. 계산기 비교: worktree 계산기와 base 계산기(메인 체크아웃)로 각각 `check --day 2026-10-16`·`--day 2026-10-17` `--repo <메인 체크아웃>` `--out <임시 폴더>`. 두 출력 JSON이 `oracle_sha256` 말고 같아야 한다(입력 sha 차이로 NOT_CHECKED면 양쪽 모두 `--ignore-input-sha`로 한 번 더).
4. 가정 실험(합성 훼손 1건, 실제 봉): MSFT 사실(https://www.microsoft.com/en-us/investor/…, root_thesis_damage true, event_session 2026-10-14, announced_at 2026-10-14T16:05:00-04:00)을 넣은 입력으로 코어·계산기 rrec1(SOXL)을 함수 수준에서 돌린다 → 평가 세션 2026-10-16은 사건 당일이라 RG1은 2세션 규칙으로 어차피 no다. 해제는 RG1 값이 아니라 코어 결과의 `rg1_damage`(카드 10-04면 [그 id], 수락일 10-15 사본이면 키 없음)와 계산기의 U(t) 함수 값으로 확인한다(그 밖 관문 값 그대로). 파일은 임시 폴더에만.

# 지켜야 할 것 (어기면 Judge FAIL)

1. 바뀐 파일: auto_core_rules.py, auto_core_inputs.py, auto_core_decide.py, auto_core_tickets.py, auto-core-card-registry.schema.json, docs/claude/card-evidence-registry.json(한 줄), docs/claude/t2rc-oracle.py, docs/claude/t2rc-check-run.ps1(16행), references/auto-core-decision.md, 새 테스트 1~2개, (미리 허용한 입력만) test_auto_core_decide.py, 보고서. 그 밖이 필요하면 멈추고 보고.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 든 줄을 만들거나 바꾸거나 지우지 않는다. 주문 경로 문자열 없음. 키움·auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행 금지.
3. 스크립트는 ASCII만(한국어는 `\u` 이스케이프). 정책·상태·장부·일지·workspace/policies·stock-strategy-system·workspace/outputs 쓰기 금지, docs/claude는 위 목록과 보고서만. 줄 끝은 체크아웃된 그대로(근거 10).
4. R7을 어기는 느슨해짐, 훼손 사실이 없는 입력에서의 출력 변화(결정·주문표·알림·해시), 계산기의 auto_core import는 FAIL.
5. **커밋하지 않는다.** 예약 작업·관제판·사전 등록 문서를 고치지 않는다.

# 보고 `docs/claude/ev-rg1-hyper-report.md` (worktree 안에 새로)

0 worktree HEAD(base와 다르면 그 사이 커밋이 docs/claude만인지) · 1 파일별 바뀐 줄(diff 요약) · 2 새 규칙 한 문단(R0~R8, D1 답·D2 처리 반영) · 3 테스트 목록과 결과(기준선·변경 뒤 Ran 수, 새 실패 0, 계산기 selftest, 기존 테스트 입력 수정 목록 파일:행) · 4 멈춤·범위 문제(없으면 "없음") · 5 실데이터 결과(1~4) · 6 계산기 표지 사실 소비처 표(G-2) · 7 sha256: 바뀐 파일 전부(작업 트리 바이트) + 새 계산기 sha256_lf + 실행기 16행 값 일치 확인 · 8 남은 위험: (a) 같은 KST 날짜 안에서 발표보다 먼저 한 재수락은 날짜 단위라 해제로 본다 (b) 잘못된 훼손 사실도 카드 재수락 전까지 매수를 막는다(예외 손 1번/종목) (c) 통합 점검 규칙 파일·로더가 교체되기 전에는 포트폴리오 RG1이 통합 점검 판정과 달라 비교 B7 "RREC:RG1"이 날 수 있다 (d) 관심 카드 수락은 코어가 관심 명단 cardStatus로, 해제는 등록부 accepted.date로 본다 — 두 기록이 어긋나면(Cowork 규칙상 같이 갱신) 해제가 늦거나 빠를 수 있다 (e) 도메인 목록 변경은 K3 (f) D1 결과에 따른 G2 차이 (g) 표시만 달라지는 곳(fail-open 아님): 채점기는 R3 막힘을 shock.open False라 rrec1_key NONE(score_decision_journal.py 1413~1415행) → DISPLAY_ONLY로 분류(873·1710행), 대시보드 runCore.shock에는 status가 없어(auto_core_decide.py 1206행) 막힘인데 '닫힘'으로 보인다 — 요건 ⑤ 칸과 알림 2:RG1DMG에는 막힘으로 보인다 (h) KST 아침 재수락은 한 세션 늦게 풀린다(R0 a ≤ d).

# 병합·고정값 교체·C1 재시작 (Judge PASS 뒤 — Builder는 하지 않는다)

1. **Cowork**(Judge PASS 확인 뒤):
   - 병합 스크립트 docs/claude/ev-rg1-hyper-merge-<날짜>.ps1 작성(hwm-fix-merge-2026-10-17.ps1 방식): 자동 코어·decide·T2rcCheck·DocsCommit·DevQueue 실행 중이면 멈춤 · Judge 마지막 줄 `VERDICT: PASS` · base 뒤 메인 이동은 docs/claude 커밋만 · 메인에서 t2rc-oracle.py·t2rc-check-run.ps1이 base 뒤 바뀌지 않았고 병합 대상 경로에 커밋 안 된 변경이 없음(등록부는 23:30 DocsCommit 뒤) · worktree 경로 목록 = Judge가 잰 목록, sha256 = Judge가 잰 값 → worktree 커밋 → `merge --no-ff`(충돌이면 abort·멈춤) → 메인에서: 실행기 16행 = 계산기 sha256_lf, `t2rc-oracle.py selftest` PASS, `test_auto_core*.py`·스키마 검사, 등록부 load_registry OK·키 있음.
   - 함께 교체할 예약 지시문 초안(pending-ev-rg1/): ① 통합 점검 로더 ㉰(integrated-check-daily.txt 37행)에 "뿌리 테제 훼손(root_thesis_damage true)에 한해 하이퍼스케일러 공식 IR(microsoft.com·abc.xyz·atmeta.com·aboutamazon.com, symbol = 그 회사 코드)도 출처로 쓴다 — 개장 전 기록의 '⚠ 뿌리 테제 하향(공식)' 줄을 확인 대상으로" 1줄 ② 규칙 파일 v3.12.6 → v3.12.7: 102행 RG1·닫힘 문구를 R0~R3·R5(카드 수락일 기준, 소급 해제 없음, 시간 소멸은 RG1 아니오면 안 닫힘, ③ 사실은 EV3ⓑ 아님, 포트폴리오 카드 날 = 보유 종목 가장 이른 수락일)로 — 로더의 규칙 파일 해시 고정값도 함께 ③ 개장 전 점검 v1.1 15행 괄호 "(회복 관문 R-REC1 RG1은 이 회사 출처를 받지 않는다 — 관제판 ev-rg1-hyper)"를 병합 뒤 사실로 고침. 각 파일 sha256을 적는다.
   - 같은 정의를 적은 문서 초안: ④ recovery-gate-R-REC1-2026-10-09.md 37행 아래 메모 1줄(해제 = 카드 재수락, 사건·닫힘과 무관)·43행 시간 소멸 닫힘 메모(RG1 아니오면 안 닫힘) ⑤ 등록부 `rule` 1문장 "공식 훼손 사실을 검토하고 다시 수락할 때만 accepted.date·text·source를 새로 쓴다. 훼손과 무관한 카드 수정은 날짜를 유지한다"(해제 신호가 accepted.date뿐이라 — 병합 뒤에 고친다. F에서 고치면 메인 4~5행 변경과 붙어 충돌) ⑥ CLAUDE.md 90행 R-REC1 요약의 "RG1 thesis (no official damage within 2 sessions)" 구절 교체안(보호 경로 — 사용자 승인·사용자 커밋).
   - 사용자에게 승인 1줄 요청(예: `결정 ev-rg1-hyper 병합: 승인`) — 범위: 코드 병합, 계산기 새 sha·실행기 고정값 교체, C1 재시작, **병합 전 C2 일치 불산입**(사전 등록보다 엄격), 등록부 키, 예약 지시문 ①~③ 교체(재서명), 문서 ④~⑥.
2. **사용자**: 승인 1줄 → 병합 스크립트 한 번(시각: 화~토 06:00~09:00 KST·23:20~23:45 KST 밖).
3. **Cowork**(병합 출력 `..._DONE` 확인 뒤, 같은 세션): 예약 지시문 ①~③ 교체(재서명, scheduled-prompts/README.md 변경 기록) · ④~⑥ 반영(CLAUDE.md는 사용자 커밋) · 사전 등록 문서 끝 "변경 기록"에 1줄 덧붙임 — "계산기 <새 sha> · 실행기 <새 sha> · 로더 <새 sha> · 규칙 파일 v3.12.7 <새 sha>(49행 고정값 갱신, ev-rg1-hyper, Judge PASS <보고서 sha>, 사용자 승인 원문) · C1은 병합 뒤 첫 decide 세션부터 0/10 · 병합 전 C2 일치는 세지 않음(관문이 바뀜 — 더 엄격) · D0(10-16)와 C4·C5 예약 날짜는 그대로" · 관제판(ev-rg1-hyper 완료, redesign-t2·t2-rc C1 0/10) · _pending 커밋 목록.
4. **첫 확인**: 병합 뒤 첫 08:40 t2rc-check.json의 oracle_sha256 = 새 sha·verdict MATCH(ORACLE_SHA_MISMATCH면 고정값 교체 실패 — 그날 ⑫ 알림이 온다).

# 작성 기록 (Cowork, 2026-10-17)

- 원문 확인: 결정 문서 3개(event-strategy 11-1·11-1a·11-2, pre-on-roadmap 3절·결정 기록, hwm-fix-judge-report 발견 1)·관제판 ev-rg1-hyper(v7)·t2-rc·redesign-t2 · authority-paths.txt · recovery-gate 37·43행 · auto_core_rules.py rrec1 · auto_core_inputs.py 113~301 · auto_core_decide.py 640~660·730~770·975~1095·398~475 · auto_core_tickets.py 262~278 · auto_core_compare.py 130~160·265~292 · score_decision_journal.py 1328~1345 · t2rc-oracle.py 1~70·720~845·979~1099·1305~1345·1486~1530·1780~1860 · t2rc-check-run.ps1 · t2-rc-preregistration 전문 · 등록부·등록부 스키마·연구 기록 스키마 · 연구 기록 5개 · 10-17 decision.json·t2rc-check.json · integrated-check-daily.txt 37·52~72행 · 규칙 파일 v3.12.6 102행 · event-pre-open-calendar.txt 15행 · event-calendar.json URL · references/portfolio-exposure-review.md 27·321행 · 기존 테스트(rules 455~470, rrec_bootstrap 80~95, decide 100~135·640~677, fixtures helpers 84행).
- 결정 문구를 더 엄격하게만 고친 곳: 해제 날 = max(event_session, 발표 KST 날짜)(R0), ③ 사실은 EV3b에 안 씀(R5), 사건 없음/닫힘 뒤 막힘이 요건 ⑤ 칸에서 풀리지 않게 칸 논리 수정(D), 재수락이 필요한 막힘의 알림(C-2).
- 내장 재검토 2회차(고친 부분만, 10건, 모두 원문 재확인 뒤 반영): 기록 전체 무효(스키마)와 사실 단위 검사 구분·합집합은 rrec1 입력에만·fact_id 세션 간 첫 판(G-1-1), 알림은 예외 줄로·종목 코드 없이(기록 모드 필터 56~60행, 비교 모드 문구 122행 유지 — 알림 지시문 무변경), 가정 실험은 `rg1_damage`로 확인, Judge 10 호출부 1822행, S6·S6b 날짜 조건, 줄 번호 4곳, KST 고정 오프셋 이유.
- 내장 재검토 1회(Opus, 읽기 전용, 13건) — 본 세션이 원문으로 다시 확인하고 모두 반영: 소급 해제 금지(R0 a ≤ d — 처음 초안은 재수락 전 날의 닫힘을 만들어 결정 ①②보다 느슨했음), 알림은 비교 모드에서도 push(auto_core_decide.py 462·507행), 알림 자료 키 `rg1_damage`(R8·C-1-1), 계산기 훼손 사실 검사·합집합(G-1-1), D2는 결정 범위로 처리(질문 안 함), worktree 줄 끝 CRLF(hwm-fix worktree 확인)·sha256_lf로만 비교, D1 선택지 c(삭제) 추가·a 식을 멈춤 표지 기준으로·영향 문구 정정(회로 집합 아님), 사전 등록 고정값 로더·규칙 파일 포함·C2 불산입 승인 범위, 같은 정의를 적은 문서(references/auto-core-decision.md는 I로, 회복 관문 문서·CLAUDE.md는 병합 절), 채점기·대시보드 표시 차이(보고 8(g)), D1 답 기한, 등록부 HEAD 9종목.
- 결정 문구보다 느슨해지는 곳: 없음. 결정 a의 해제(재수락)는 지금 코드보다 느슨해질 수 있는 유일한 경로다(R7) — 11-1a의 "매수를 더 막는 쪽으로만"은 이 경로를 빼면 맞다.
