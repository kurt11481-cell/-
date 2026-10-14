---
id: review-stability-2026-10-13
title: 재검토 없이 끝나는 1차 검토 — 재검토에서 결과가 바뀐 원인과 규칙
date: 2026-10-13
status: 적용됨 r2 — r1 사용자 "적용 (권장)"(10/13 23:5x KST, V1~V4) · r2 사용자 지시 "재검토가 필요없도록 1차 검토에서 해결해야한다"·"재검토시 1차 검토의 오류가 발견되어 결과가 바뀜"(23:54~55 KST, V5 내장 재검토 추가, 이 문서에 V5 2회 적용). CLAUDE.md Working rules 95행 1줄(sha256 c4146cbb…). 커밋 755054d(사용자, 2026-10-14 08:56 KST, t1-safety 병합 뒤). 프로젝트 지침 5절 끝에 5-2 문단 반영(사용자, 2026-10-14 08:58 KST, project_info로 원문 일치 확인)
consumers: CLAUDE.md Working rules(Cowork·대화형 Claude Code 검토 세션) · 프로젝트 지침 5절(Chat) · 내장 재검토 subagent(3-1 지시문) · 사용자 재검토를 받은 세션(2절에 덧붙임, 3절 렌즈 개정)
weekly_user_touch: 0 (한 번만: CLAUDE.md 커밋 1줄 · 프로젝트 지침 붙여 넣기 1)
model: Opus 5.5 · high
---

## 1. 결론
- 사용자 지시(2026-10-13): 재검토 때 1차 검토의 오류·누락이 발견되어 결과가 바뀐다. 앞으로는 재검토가 필요 없도록 1차 검토에서 해결한다.
- 기록에서 찾은 재검토 정정 14건(2절)의 원인: 원문 미확인 6 · 범위 누락 4 · 자료 수준 2 · 제약 대조 2 · 처리 기준 2(6·10번은 두 원인). 14건 중 9건은 사용자가 요청한 재검토, 1건(7번)은 사용자가 붙인 자료에서 나왔다.
- 행 번호를 인용한 검토도 바뀌었다(10번: 인용한 55행 바로 아래 56행의 용어 정의를 읽지 않아 "사용자 결정"이 "코어 결함"으로 바뀜). 인용만으로는 부족하고, 결론이 기대는 용어의 정의와 같은 사실을 쓰는 다른 곳까지 열어야 한다.
- 공통점: 재검토는 원문을 다시 열고, 처음 보지 않은 층·제약·대안을 봤다. 1차 검토는 결론을 만드는 방향으로만 읽었다.
- 그래서 1차 검토 안에 재검토를 넣는다(3절 V5): 결론을 만든 추론을 모르는 subagent가 렌즈 L1~L6으로 초안의 오류·누락을 찾고, 본 세션이 원문으로 다시 확인해 고친 뒤 보고한다. 사용자가 받는 결과는 재검토를 이미 거친 것이다.
- 효과 실측(이 문서): V5 1회차가 17건(결론·문구를 바꾼 것 9), 2회차가 15건(4)을 찾았다(7절). 그 하나가 "지금 CLAUDE.md를 커밋하면 대기 중인 t1-safety 병합이 멈춘다"였다(devpipe.py 1951~1953행).
- 비용 실측: 1회차 subagent 227,030토큰 · 도구 40회 · 약 12분, 2회차(반영분만) 172,787토큰 · 26회 · 약 8분. 그래서 V5 subagent는 추천·결정 요청·미룸·변경 제안이 있는 검토에만 쓰고, 2회차는 1회차 반영분만 본다. 나머지 검토는 본 세션이 같은 렌즈로 자기 점검한다.
- 한계: 같은 모델의 subagent는 같은 맹점을 가질 수 있다(확인 필요). 그 뒤에도 사용자 재검토로 바뀐 항목은 2절에 "놓친 렌즈"와 함께 적고, 같은 렌즈가 2번이면 렌즈 개정을 제안한다.

## 2. 정정 기록 (재검토에서 바뀐 항목 — 덧붙이기만)
원인: U 원문 미확인 · D 자료 수준 · S 범위 누락 · C 제약 대조 · P 처리 기준 · I 입력 변경 · N 사용자 새 정보. 발견: 사용자(요청) · 사용자 자료(사용자가 붙인 결과) · 위원회 · 다음 단계(이어진 작업 중) · 내장(V5)

| # | 날짜·검토 | 처음 | 재검토 뒤 | 원인(놓친 렌즈) | 발견 | 원문 |
|---|---|---|---|---|---|---|
| 1 | 10/12 관제판 정렬 #3 | SAVE 종목 목록에 PWR·LITE 없음 | 오판. 근거로 쓴 s-library verify 메모가 낡았음 | U(L1) | 사용자 | board-redesign-alignment-2026-10-12.md 33·48행 |
| 2 | 10/12 관제판 정렬 #5 | 기한 지난 2건을 다음 세션으로 | 그 자리에서 기본 처분으로 닫음 | P(L4) | 사용자 | 같은 문서 50행 |
| 3 | 10/12 FTD 핸드북 검토 #2 | "주문표 근거 종류가 이미 기록됨" | 결정 일지 payload엔 없음(코드 확인) | U(L1) | 사용자 | external-traders-handbook-ftd-pullback-review-2026-10-12.md 148행 |
| 4 | 같은 검토 #8·#9 | (빠짐) | 1차 누락 2건(REMOVE/SIMPLIFY 단계, 수익 보호) | S(L6) | 사용자 | 같은 문서 153·154행 |
| 5 | 10/9 G6 장중 감시 | "장중 값과 종가가 비슷"(02:4x KST 한 시점 현재가) | 정규장 30분봉: MVLL 장중 −13.44% vs 종가 −7.30% → 낙폭 표시 줄 추가 | D(L2) | 다음 단계 | integrated-check-v3.12-change-2026-10-09.md 87·88행 |
| 6 | 10/13 매수 막힘 | "켜" 뒤 첫 코어 기록에서 S7 풀림, 첫 매수 10/21(추정). RG1은 (a) 불가, (b) 시간 경과만 | 켜도 영구 HOLD(증거 시작일 코드). RG1은 결함 → 주중 해소 경로. 1차가 "확인 필요"로 남긴 공백이 바로 결함이었음 | U·S(L1·L4) | 사용자 | buy-unblock-review-2026-10-13.md 17행 · 대화 "통합점검 매수요건 해소" |
| 7 | 10/9 MVLL 10/8 종가 | "정규장 마감 뒤 조회라 확정 가능성 높음" | 그 근거가 틀림(일봉 종가가 조회 시점마다 바뀜) | D(L2) | 사용자 자료 | 대화 "MVLL Investor Day B+ 마무리" |
| 8 | 10/5 결정 영수증 | S7b 채점기를 병합 전으로 봄 | 10/5 병합돼 있었음 | U(L1) | 위원회 | decision-receipt-m6v2-spec-2026-10-05.md 59행 |
| 9 | 10/9 fx-4 | "FX-1009 동결 때문에 안 된다" | 틀림(fx-4는 계획 단계) | U(L1) | 위원회 | fx1009-fx4-record.md 62행 |
| 10 | 10/13 B7 총자산 | "사용자 결정 2", (가) 결제된 예수금만 / (나) 새 공식, 추천 (나) | 추천은 유지. 분류는 사용자 결정 → CORE_BUG, 공식은 새 공식 → T1 정의 fc_ord_alowa 그대로 | U·S(L1·L3) | 사용자 | redesign-t2-compare-b7-2026-10-13.md 14·32·38~41행 vs 50~55행 |
| 11 | 10/9 설계·운영 결함 검토 | 후보 13건 + 추가 A1~A5 | 사용자 "후보 밖도 봤나" → A6~A12, 그중 A7 서머타임(심각도 높음, 11/2 기한) | S(L3): 읽은 범위에 예약 지시문 원문·테스트 기준선·서머타임 코드 없음 | 사용자 | system-design-ops-review-2026-10-09.md 8·235행 · fx1009-fix-plan-2026-10-09.md 29~35행 |
| 12 | 10/9 fx-4 Builder 지시문 | 승인본 5절 | 매수 자금 상한을 min → 주문 가능액으로 넓힐 수 있었음(위원회 "낮추기·유지만" 위반) → 수정 3건 | C(L5) | 사용자("2번 검토", Judge 지적 뒤) | fx1009-fx4-record.md 114행 |
| 13 | 10/12 관제판 정렬 #4 | "일지 30건" 셈 → 사용자 확인 | 원래 뜻을 지키는 셈이라 기본 처분으로 정함 | P(L4) | 사용자 | board-redesign-alignment-2026-10-12.md 34·49행 |
| 14 | 10/13 매수 막힘 사용자 손 | "결정 1회 · 병합 1회" | K3 수동 경로라 Builder·Judge가 더 필요(같은 문서 48행). 39행은 아직 옛 숫자 | C(L5·L3) | 다음 단계 | buy-unblock-review-2026-10-13.md 39·48행 |
| 15 | 10/13 이벤트 결합 event-ctx | 코어 decide가 일정표를 읽어 주문표·일지에 표시·기록 | 결정 계산 무변경, 채점기 사후 분류 + 예약 점검 표시(event-ctx2) | S(L6) | event-strategy-2026-10-13.md 11-2절 · CLAUDE.md:40 |
| 16 | 같은 설계 | 체결 = buy_session 16:00 ET, 매도도 "떠안음" | core_close_at(조기 폐장 13:00), 매도 = "피함" | U(L1) | 같은 문서 11-2절 · 세션 일정 조회 10/13 23:5x |
| 17 | 10/13 이벤트 점검 예약 v1 | 기록 절 "## 공식 결과" | 통합 점검 2-1이 읽는 "## 공식 사실"·"## 다음 작업이 확인할 항목"으로 정정(v1.1) | S(L3) | integrated-check-prompt-v3.12.2-2026-10-09.txt:60 |
| 18 | 10/13 ev-rg1-hyper | 권장 b(이유 FX-1009 동결), a = 출처만 넓힘 | 권장 a 수정판(RG1 결함 — 사건 날·재기준·시간 소멸 뒤 훼손 미반영), 무응답 기본 b | U(L5)·S(L1) | 같은 문서 11-1절 · auto_core_rules.py:838-843·872-877 · CLAUDE.md:91 |
| 19 | 같은 건 | 사람 경로 = "EV3a 지정 검토" 푸시 | 기준 재설정으로 관문이 풀릴 수 있어 철회 → SOXL S3 판정 | S(L5) | auto_core_rules.py:808-811·832-833 |

- 표본: docs/claude에서 "정정·오판·1차 누락·처음 판단"을 찾은 문서와 지난 대화 검색 결과, 그리고 이 문서의 V5 1회차(10·13·14번 추가). 전수 조사 아님.
- 14번 문서의 39행(사용자 손)·5행(status "사용자 결정 대기", 48행 결정·52행 병합 뒤 낡음) 정정은 이 작업 범위 밖 — 미해결(기본 처분, 알림만).
- 개정 조건: 2026-10-14 이후 V5를 거친 검토가 사용자 재검토로 바뀌면 여기에 덧붙이고, 같은 렌즈가 2번이면 3절 렌즈 개정을 제안한다(제안할 때만 묻고, 답이 없으면 NO_CHANGE).

## 3. 1차 검토 완결 조건 (V1~V5)
적용 세션: Cowork와 대화형 Claude Code. 개발 파이프라인·수동 경로의 Builder와 Judge(마지막 줄 `VERDICT:` 계약, 헤드리스 Judge는 Read·Grep·Glob만), 예약 작업(고정 지시문), 모든 subagent(Haiku·리서치·내장 재검토 포함)는 각자의 출력 계약을 따른다(V1~V5·끝 줄 모두 미적용). subagent 출력은 위치 안내다.

- **V1 원문 확인.** 결론에 쓰는 주장마다 이번 세션에 연 원문 위치(파일:행, 조회 시각, 커밋, 이번 세션에 연 대화의 사용자 말·도구 응답)를 단다. 결론이 기대는 용어·칸의 정의 행까지 연다(사례 10). 메모·관제판 note/verify·요약·이전 답(어시스턴트 주장)·기억·subagent 출력은 어디를 볼지 알려 줄 뿐 근거가 아니다. 읽기 전용으로 확인할 수 있으면 확인하고, 숫자는 코드로 다시 계산한다. 끝까지 닿을 수 없는 것만 "확인 필요"로 보이게 두고, 그 공백에 기대는 판단은 fail-closed(매매: 매수 쪽 막힘·매도는 막지 않음, 규칙·개발: NO_CHANGE).
- **V2 자료 수준.** 결론이 자료의 해상도·시점·확정 여부에 달렸으면 닿을 수 있는 가장 정확한 자료(한 시점 값보다 봉, 잠정보다 확정)를 쓰고 기준 시각과 확정 여부를 적는다.
- **V3 범위.** 개발·규칙 검토는 NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD를 한 줄씩 본다. 막힘·보류는 "규칙대로 적용됐나"와 "결함인가"를 둘 다 본다(Goal: 막힌 자동화 = 결함). 범위 안이고 정책·상태·예약 작업·권한·주문·코드 변경이 없는 항목은 미루지 않는다(코드는 변경 등급 경로로).
- **V4 바뀔 조건.** 결론마다 "이 결론을 바꿀 증거" 1줄.
- **V5 내장 재검토.** 추천·결정 요청·미룸·변경 제안이 있는 검토는 보고 전에 3-1 지시문으로 새 subagent를 돌린다(Haiku 금지, 권한·한도·K3 결론이면 Opus). subagent는 과제·초안 결론·근거 위치만 받는다. 본 세션은 발견마다 원문을 직접 다시 열어 맞으면 초안을 고친다(subagent 출력은 위치 안내). 본 세션이 원문으로 확인해 결론을 고친 것이 1건 이상이면, 고친 부분만 새 subagent로 1번 더 본다. 최대 2회. 남은 것은 "미해결"로 보고에 적고 기본 처분(NO_CHANGE, 알림만)을 따른다. 변경을 제안할 때만 사용자에게 묻는다.
- **그 밖의 검토**(추천·결정 요청·미룸·변경 제안이 없는 결과 보고)는 본 세션이 L1~L6으로 자기 점검한다.
- **끝 줄.** `검토 완결: 원문 확인 n/m · 내장 재검토 r회(반영 k건) · 미해결 j · 자료 시점 <KST> · 바뀔 조건 <위치>`

재검토 렌즈(L1~L6, 2절 사례에서 뽑음):

| 렌즈 | 보는 것 | 사례 |
|---|---|---|
| L1 주장-원문 대조 | 초안의 주장이 원문과 맞나, 용어 정의 행까지 봤나, 숫자를 다시 계산하면 같은가 | 1·3·6·8·9·10 |
| L2 자료 수준 | 한 시점 값·잠정 값·낮은 해상도를 썼나 | 5·7 |
| L3 인접 층 | 같은 사실을 적거나 쓰는 다른 곳(예약 지시문 원문·저장소 사본·대시보드·테스트·코드·메모리·문서)도 맞나 | 10·11·14 |
| L4 막힘·보류·미룸 | 막힘이 결함인가, 미룬 항목·"확인 필요"를 지금 읽기 전용으로 풀 수 있나 | 2·6·13 |
| L5 제약 대조 | 제안이 기존 제약(권한·한도·위원회 낮추기 전용·fail-closed·매도 비차단·승인 범위·변경 경로·커밋 순서)을 완화하거나 어기나 | 12·14 |
| L6 빠진 대안 | NO_CHANGE·REMOVE/SIMPLIFY·현금·다른 경로를 봤나 | 4 |

### 3-1 내장 재검토 subagent 지시문 (그대로 쓰고 <> 만 채움)
```
[내장 재검토 — 읽기 전용. 파일·정책·상태·관제판·예약 작업 수정 금지. 키움 주문 도구 금지. 키움 조회는 꼭 필요할 때만, "profile": "실전계좌", "mode": "real", 8005·인증 오류면 재인증하지 말고 실패로 적기. 비밀(.env·토큰·계좌번호) 읽기 금지. git은 --no-optional-locks -c core.autocrlf=true 읽기만. 사용자 저장소: Cowork는 mcp__remote-devices__device_bash 로 "$HOME/mnt/코덱스저장소"(Read·Bash 도구는 다른 컴퓨터), 대화형 Claude Code는 저장소 루트에서 Read·Grep·Glob·Bash 읽기 전용]
과제(사용자 요청 원문): <…>
초안 결론(번호마다 근거 원문 위치): <1. … (파일:행 / 조회 시각)>
<2회차면: 1회차에서 고친 부분만: …>
할 일: 이 초안의 오류와 누락을 찾는다. 작성자의 추론은 받지 않았다. 원문을 직접 연다.
렌즈: L1 주장-원문 대조(용어 정의 행까지, 숫자는 다시 계산) · L2 자료 해상도·확정 여부 · L3 같은 사실을 적거나 쓰는 다른 곳(예약 지시문 원문·저장소 사본·대시보드·테스트·코드·메모리·문서) · L4 막힘·보류·미룸·확인 필요 — 결함인가, 지금 읽기 전용으로 풀 수 있나 · L5 제안이 기존 제약(권한·한도·위원회 낮추기 전용·fail-closed·매도 비차단·승인 범위·변경 경로·커밋 순서)을 완화하거나 어기나 · L6 빠진 대안(NO_CHANGE·REMOVE/SIMPLIFY·현금·다른 경로)
출력(한국어): 표 하나 — # | 렌즈 | 문제 | 원문 위치(파일:행) | 결론 영향(바꿈/안 바꿈) | 고칠 문구(짧게). 없으면 "새 발견 0". 원문 위치 없는 발견은 쓰지 않는다. 표 뒤에 확인한 범위 1줄. 검토 완결 끝 줄은 쓰지 않는다.
```

## 4. 그래도 사용자가 재검토를 요청하면
1. 처음부터 다시 하지 않는다. 이전 기록(문서·대화)을 먼저 읽는다.
2. 이전 기록의 원문 위치·기준 시각·커밋을 지금과 비교한다. 바뀐 입력은 다시 보고, 나머지는 이전 기록의 주장을 L1~L6으로 원문과 대조한다(처음부터 다시 분석하지 않는다).
3. 결론은 넷 중 하나일 때만 바꾼다: I 입력 변경 · U/D 원문으로 보인 사실 오류(어느 주장이 왜 틀렸는지 행 번호로) · S/C 1차 누락 · N 사용자 새 정보. 아니면 "유지 — 새 근거 없음".
4. 재검토 요청 자체나 사용자의 불만은 결론을 바꾸는 근거가 아니다. 사용자가 원하는 결과(예: "이번 주 안에 해소")가 있으면 결론을 맞추지 않고, L4 결함 점검으로 그 결과에 닿는 경로를 찾는다(사례 6).
5. 보고는 표 하나: 처음 판단 | 재검토 | 이유(I/U/D/S/C/N 또는 유지) | 원문.
6. 바뀐 항목은 2절 표에 "놓친 렌즈"와 함께 1줄 덧붙인다.

## 5. 적용할 곳과 문구
### 5-1 CLAUDE.md Working rules — Default disposition 줄 다음 1줄(영문 그대로)
```
- Review stability (user 2026-10-13, docs/claude/review-stability-2026-10-13.md; Cowork and interactive Claude Code only: pipeline/manual-route Builder and Judge, scheduled tasks and all subagents keep their own output contracts, and subagent output is a pointer): a first review must leave nothing for a re-review to find. Before a review or analysis concludes: (V1) every claim cites a source opened in this session (file:line, query time, commit, or the user's words/tool output in a chat turn opened in this session), including the definition lines of terms it relies on; notes, board text, summaries, earlier answers, memory and subagent output only point to sources; check what is checkable read-only and recompute numbers; what stays unreachable is shown as "확인 필요" and anything resting on it fails closed (trading: blocks buys, never sells; rules/dev: NO_CHANGE); (V2) use the most precise reachable data (bars over a one-time quote, final over provisional) with as-of; (V3) dev/rule reviews walk NO_CHANGE→REMOVE/SIMPLIFY→REUSE→REPLACE→ADD; check every block both as rule application and as a defect; resolve in-scope items that need no policy, state, scheduled-task, authority, order or code change (code goes through the change classes); (V4) name the evidence that would change each conclusion; (V5) if it recommends, asks for a decision, defers or proposes a change, run the section 3-1 re-review subagent (non-Haiku; Opus for authority/limit/K3), re-verify each finding at its source and fix the draft; if a conclusion changed, run one more round on the changes only; leftovers are 미해결 under default disposition (notify only); other reviews do the L1-L6 check in-session. End with "검토 완결: 원문 확인 n/m · 내장 재검토 r회(반영 k건) · 미해결 j · 자료 시점 … · 바뀔 조건 …". On a user re-review, read the earlier record first, re-check changed inputs and run L1-L6 on the earlier record against its sources (no fresh analysis from scratch); change a conclusion only for changed input, a factual error shown from the source, a first-pass omission or new user information (else "유지 — 새 근거 없음"); report 처음 판단 | 재검토 | 이유 | 원문 and log the missed lens in section 2.
```
### 5-2 프로젝트 지침(Chat) 5절 Evidence 끝 — 사용자가 붙여 넣음 (Chat은 본 대화가 자기 재검토)
```
검토 안정성(2026-10-13): 1차 검토에서 재검토가 찾을 것을 미리 찾는다. 결론에 쓰는 주장은 이번 대화에서 직접 연 원문 위치(파일·행·조회 시각)를 달고, 결론이 기대는 용어의 정의까지 확인한다. 메모·요약·이전 대화의 주장·기억은 위치 안내일 뿐 근거가 아니다. 확인할 수 있으면 확인하고 숫자는 다시 계산한다. 끝까지 닿을 수 없는 것만 확인 필요로 보이게 두고, 그에 기대는 판단은 보수적으로(매수 쪽 막힘, 매도는 막지 않음). 가장 정확한 자료와 기준 시각을 쓰고, 결론마다 바꿀 증거 1줄. 보내기 전에 초안을 재검토하는 눈으로 한 번 더 보고 고친다: 주장-원문 대조, 자료 해상도, 같은 사실을 적은 다른 곳, 막힘·보류가 결함인지, 기존 제약을 완화하지 않는지, 빠진 대안(NO_CHANGE·현금 포함). 사용자가 재검토를 요청하면 이전 답을 먼저 보고, 바뀐 입력은 다시 보고 나머지는 이전 답의 주장을 원문과 대조한다. 입력 변경·원문으로 보인 오류·1차 누락·새 정보일 때만 결론을 바꿔 처음|재검토|이유 표로 보인다. 아니면 "유지 — 새 근거 없음".
```
### 5-3 바꾸지 않는 것
- AGENTS.md(Codex 전용), 메모리, Judge·개발 파이프라인 지시문(tools/** 보호 경로, Judge는 이미 별도 세션에서 실제 diff·테스트를 본다), 위원회 규칙. 위원회도 전제 사실을 잡은 적이 있지만(8·9번) 사람이 부를 때·정책 변경 때만 돌므로, 상시 사실·누락 점검은 V5가 맡는다.
- 비용: CLAUDE.md 95행 1줄 2272바이트(CRLF 포함, 파일 14,385 → 16657바이트). 세션마다 읽힌다. V5 subagent 실측 1회차 약 23만 토큰·12분, 2회차 약 17만 토큰·8분(이 문서, 규칙 검토 기준. 다른 검토 크기는 확인 필요). 사용자 재검토 왕복을 없애는 대가다.

### 5-4 CLAUDE.md 커밋 순서 (사용자 한 줄)
- 개발 파이프라인 dev-merge는 run 기준 커밋 뒤에 docs/claude 밖 커밋이 있으면 멈춘다(STOP_BASE_MOVED non_docs_commits, tools/dev_pipeline/devpipe.py 1951~1953행). 2026-10-14 00시 기준 t1-safety가 NEEDS_APPROVAL로 병합 대기(workspace/outputs/dev-runs/LATEST.json, base 3edc19f).
- 그래서 CLAUDE.md 커밋은 대기·실행 중인 run이 없을 때 한다: LATEST가 병합 안 된 READY_TO_MERGE·NEEDS_APPROVAL이 아니고(병합 뒤에도 status는 그대로, merged_at이 생김 — devpipe.py do_merge), docs/claude/_dev-queue가 비었고, 최근 _queue 로그 2개(파일 이름은 KST 날짜 — 2026-10-14.log에 15:30:06Z 줄이 있음)를 이어서 본 마지막 "DEV-RUN start" 뒤에 "DEV-RUN end"가 있을 때(자정을 넘긴 실행도 잡도록 2개)(LATEST는 run 끝에만 쓰이고 큐 파일은 시작 때 _taken으로 옮겨짐).
- 아래 한 줄이 그 조건을 스스로 확인하고, 안전할 때만 커밋한다(Windows에서 실행해 보지는 못함 — 오류가 나면 그대로 알려 주면 됨):
```
$r="E:\사업\##금동한\코덱스저장소"; $l=Get-Content "$r\workspace\outputs\dev-runs\LATEST.json" -Raw | ConvertFrom-Json; $q=Get-ChildItem "$r\workspace\outputs\dev-runs\_queue\*.log" | Sort-Object Name | Select-Object -Last 2; $s=(Select-String -Path $q.FullName -Pattern 'DEV-RUN (start|end)' | Select-Object -Last 1).Line; if ((($l.status -in 'READY_TO_MERGE','NEEDS_APPROVAL') -and -not $l.merged_at) -or (Get-ChildItem "$r\docs\claude\_dev-queue" -File -ErrorAction SilentlyContinue) -or ($s -match 'DEV-RUN start')) { "WAIT: a dev run is pending or running - commit later" } else { git -C $r commit -m "docs: CLAUDE.md review stability rule (review-stability-2026-10-13)" -- CLAUDE.md }
```
- 적용 시점: 작업 폴더의 CLAUDE.md는 편집 뒤 새로 시작하는 Cowork·대화형 Claude Code 세션부터 적용된다(이미 열린 세션은 시작 때 사본). 커밋하지 않은 상태는 병합을 막지 않는다(병합은 staged 변경과 사이 커밋만 본다, 1918·1951행).
- 변경 경로: 규칙 문구만 바꾸는 변경(런타임 변경 없음) — Cowork 편집 + 사용자 커밋. 선례 29ad21d(10/12, CLAUDE.md만 10줄 추가, redesign-t2-claude-md-proposal-2026-10-12.md).

## 6. 루프 점검 (loop-design-check, V5 루프)
- 판정: 진행. 유형 = 목표에서 멈추는 루프(servo).
- 끝 조건(판정 가능): 본 세션이 원문으로 확인해 고친 결론 0건. 2회차는 1회차 반영분만. 횟수 상한 2회, 남은 것은 미해결 + 기본 처분(알림만).
- 경계: subagent는 읽기 전용. 점검 조건·렌즈를 스스로 줄이거나 바꾸지 못한다(개정은 2절 조건 → 사용자 제안만). 정책·상태·권한·주문과 무관.
- 대조 원천: 원문 파일·조회 결과. subagent의 발견도 본 세션이 원문으로 다시 확인한다.
- 실패 1~5: 1 통과(건수로 판정) · 2 부분 — 같은 모델이라 맹점 공유 가능(확인 필요), 2절 기록으로 잰다 · 3 통과(렌즈 삭제 금지) · 4 통과(사용자 결정 거리는 결정 요청으로 올림) · 5 주의 — CLAUDE.md가 길어짐, 렌즈·지시문 세부는 이 문서에만 둔다.
- 레드 라인: 위반 없음. 승인은 사람, 권한 없음, 규칙 자기 수정 없음.

## 7. 이 문서의 내장 재검토 기록
- 1회차(2026-10-14 00시, general-purpose subagent, 227,030토큰): 17건. 결론 영향 "바꿈" 9건.
- 본 세션이 원문으로 다시 확인한 것: #1(board 34·49행) · #2(B7 13·32·38~40 vs 50~55행) · #5(buy-unblock 39·48행) · #6(judge-prompt.md 26~31행 VERDICT 마지막 줄) · #7(i0b 문서 273행 index.lock) · #8(devpipe.py 1945~1955·1918행, LATEST.json t1-safety NEEDS_APPROVAL). 나머지(#3·#4·#9~#17)는 이 문서 문구에 관한 것이라 이 문서로 확인.
- 반영: 2절 10·13·14번 추가·정정, 7번 문구, 발견 칸, V1(정의 행·대화 원문·fail-closed), V3(정책·상태·예약 작업), V5(대상 좁힘·2회차 범위·기본 처분·Opus), 적용 세션, 3-1(git·키움·device_bash·끝 줄 없음), 5-1 재작성, 5-3 위원회 문구, 5-4 커밋 순서, 소비처에서 fx-6 뺌, _pending 메시지.
- 반영 안 함: 없음(#17 단계 구분 안은 V5 대상 좁힘으로 반영).
- 2회차(2026-10-14 00시, 반영분만, 172,787토큰): 15건, "바꿈" 4건(3-1 Claude Code 저장소 접근 · 5-4 실행 중 run 놓침 · 재검토 규칙 "바뀐 입력만"과 U/S 모순 · V1 영문 "chat turn" 범위). 안 바꿈 11건(제외 목록 모든 subagent · V3 개발·규칙 한정 · 코드 변경 경로 · 변경 경로 근거 · 5-2 매도 · 규칙·개발 fail-closed=NO_CHANGE · 적용 시점 · 바이트 · 10번 행 번호 · 사용자 9건 · 14번 미해결 표기).
- 본 세션 원문 재확인: _queue/2026-10-13.log(DEV-RUN start 12:05:08Z → end 12:53:20Z) · B7 13·14·41행 · git show 29ad21d(CLAUDE.md만) · do_merge의 write_latest(status 유지, merged_at 추가). 나머지는 이 문서·CLAUDE.md 95행 문구로 확인. 15건 모두 반영.
- 상한 2회 도달 → 3회차 없음. 미해결 1: 14번 문서 39·5행(범위 밖, 기본 처분·알림만).
- 2026-10-14 00:30 KST 자기 점검(L3): 5-4 로그 파일 이름이 UTC가 아니라 KST 날짜였음 → 문구 정정, 한 줄 명령을 로그 2개로 고침(자정 넘긴 실행을 놓치지 않게).
