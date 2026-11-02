---
id: ic-rules-bundle-proposal-2026-11-02
type: proposal
status: 승인 대기 (사장 직접 입력)
as_of: 2026-11-02 KST
summary: "통합 점검 규칙 파일 v3.12.10 → v3.12.11, 지시문 v3.12.10-L+R2 → v3.12.11-L+R2. 기다리던 4건(close-confirm a · ic-rerun-core a · 원장 트리거 2개 · fact_id 판 바꿈)을 한 판으로. 제약 완화(코어 + 강 근거 경로 확대) 포함."
consumers: "예약 작업 '보유·관심 종목 통합 점검 (장마감 후)' trig_01YWzNq847nJfNgDUnnukBqP · 07:45 자동 운영 코어(연구 기록) · 08:40 독립 대조 · 관제판 ic-rules-bundle·close-confirm·ic-rerun-core·rule-factid-version·rule-rev-ledger-trig"
source_decision: "사장 'ic-rules-bundle 진행'(2026-11-02 19:44 KST) · stalled-1101 · close-confirm a · ic-rerun-core (a) · rule-1028 a-1 · t2rc-factid-1101 B"
---

# 통합 점검 규칙 개정 묶음 v3.12.11 — 제안

**제약 완화(코어 입력: + 강 근거 경로 추가·판 올림 인정).** 부딪히는 결정: ledger-apply A '하지 않음(통합 점검 지시문 변경)' — rule-1028 a-1이 이 용도에 한해 풂(active-decisions 113행) · t2rc-factid-1101 B 문구 "criterion_a·방향·kind가 바뀌면"을 **코어 셈 여부가 바뀔 때만**으로 좁힘(3절 ④, 독립 검토 7번).

## 1. 무엇이 바뀌나 (4건)

| # | 결정 | 바뀌는 곳 | 성격 |
|---|---|---|---|
| ① | close-confirm a (10/20) | 규칙 51행 끝 문장 → 결정 문서 2절 a 문장 그대로 | 문구(실행 없는 약속 삭제) |
| ② | ic-rerun-core (a) (10/23) | 규칙 174행: 같은 날 재실행 때 08:50 코어 결과(core 칸)를 쓰기용 사본에만 붙여 보존. 로더 build에 `run.pop('core')` 안전장치 | 표시 전용 |
| ③ | rule-1028 a-1 (10/28 사장 카드) | 규칙 125행 NBIS N11(+)·N12(−) · 126행 MU U9(+)·U10(−) · 119행 종류 이름 · 116행 관심 카드 보유 목록 · 332행 "⑤에 넣지 않음" 명시 | **코어 입력** (+ 쪽은 매수 근거가 될 수 있음) |
| ④ | t2rc-factid-1101 B (11/01) | 로더 ㉰: 지난 기록(코어 창과 같은 앞선 9개)의 같은 fact_id와 **코어 셈 여부**가 다르면 `-v2`(-v3…) 새 id + 읽기 전용 PRIOR python 1개 | **코어 입력** (판 올림이 새 근거로 셈) |

- 알림 조건·매수 요건·쓰기 범위·금지 목록은 그대로다. 새 ID는 기존 알림 ①(보유 매도 강 근거)·④(매수 요건 ③)로만 이어진다.
- 원문: 새 규칙 파일 `docs/claude/integrated-check-prompt-v3.12.11-2026-11-02.txt`, 새 지시문 `docs/claude/scheduled-prompts/pending-ic-rules/integrated-check-daily.txt`, 줄 단위 비교 `pending-ic-rules/rules.diff`(30줄)·`loader.diff`(40줄).

## 2. 해시

| | 지금 | 바꿀 것 |
|---|---|---|
| 규칙 파일 | v3.12.10 · 106,962 B · 54fc685ecad1bb466c2daaabfc43ed82bc49d3a19ce94bf0df8ff306ff644978 | v3.12.11 · 111,196 B · 32ec42b2a29ffba64fc21b9901b2da328abbacd78b50e8e622a21ada57be7b85 |
| 예약 지시문 | v3.12.10-L+R2 · 23,301 B · 1101af455c43a54951363c621ee55cfca4687b8eab3a7b629205a7d651a3bb8c | v3.12.11-L+R2 · 25,816 B · 74b1a367728ef691c1ea35edf1635810d8a672a3777b93d4eaf1475bef00c9da |

- 지금 예약 본문(get_trigger 2026-11-02 KST, updated_at 2026-10-22T05:35:50Z)의 머리·규칙 경로·해시·writer가 저장소 지시문과 같다(눈 대조. 바이트 대조는 교체 때 응답으로 한다).

## 3. 그대로인 것
일정(CRON_TZ=Asia/Seoul 40 6 * * 2-6) · 모델(claude-sonnet-5-5) · 폴더 2개(코덱스저장소·chatgpt_종목분석결과) · 권한 모드 auto · 푸시 켬 · 이름. 자동 코어·독립 계산기·정책·상태 파일 코드 변경 0.

## 4. H1 시험 (클라우드 사본, 키움·웹·푸시·대시보드·관제판·예약 실행 없음)
기대 차이를 먼저 적고 대조했다(`pending-ic-rules/h1-notes.md`).
- T1 규칙 확인: 새 지시문+새 규칙 MATCH(LF·CRLF), 엇갈린 짝 MISMATCH, 파일 없음 UNREADABLE — PASS
- T2 build: 가짜 core 칸을 넣은 10/31 run 사본 → 새 판은 core를 뺌, 그 밖 차이는 writer 한 칸 — PASS. finalize는 바이트 같음.
- T3 PRIOR: 깨진 기록은 건너뛰고, 오늘 뒤 기록은 읽지 않으며, 앞선 파일 폴더 9개만 읽음. PWR 두 판이 나옴 — PASS
- T4 코어 의미(코어 함수 원문 실행): 10/31형 올림(false→true)은 옛 규칙에선 + 근거 0개, 새 규칙에선 1개로 독립 계산기와 같아짐. 내림은 차이 없음. − 쪽에서 셈 종류로 바뀌면 − 근거가 1개 생김 — 기대대로
- T5 `-v2` id: build 정규식과 저장소 스키마(schemas 38행)를 통과
- LLM이 쓰는 문장(51·125·126·174행, ㉰ 비교)은 교체 뒤 첫 실행으로 확인한다(H1 ③).

## 5. 독립 검토 (Opus, 읽기 전용, 1회)
판정 **PASS(수정 후)**, 11건. 수정 권고 6건은 모두 반영하고 다시 시험했다.
1. N11과 N12가 함께 성립하지 못하게 했다. $20M/MW는 문턱이 아니라 참고값으로 적었다.
2. N12의 kind 지정은 결정에 없던 내용이라 지웠다(kind는 ㉰ 목록에서 사실 그대로 고른다).
3. 174행은 버전 충돌로 다시 시도할 때도 core를 다시 붙인다. get 파일 위치도 적었다.
4. `-vN`은 코어 셈 여부가 바뀔 때만 붙인다. kind만 바뀌는 경우에는 같은 사실이 하루 더 근거로 세지는 문제가 있어서다.
5. PRIOR 창을 9개로 줄여 코어와 맞췄다.
6. 머리말과 이 문서 첫 줄에 '제약 완화'를 적었다.

참고로 확인한 것: 해시·writer가 일치한다. 독립 계산기 t2rc-oracle.py는 오늘 사실을 그날 기록(1550행)과 이전 facts_seen(1546행)으로 센다. 코어와 같은 규칙이어서, 판정을 FAIL로 바꿀 조건에 해당하지 않는다.

## 6. 위험과 기본 처분
- 지금은 비교 모드라 주문표 입력이 없어 실제 위험이 낮다. ③의 +(N11·U9)와 ④는 매수 회로가 열리는 경로를 넓힌다. 다만 노출(E)·현금·R-REC1·실적 금지 구간 관문은 그대로 막는다.
- 미승인이나 무응답이면 v3.12.10을 그대로 둔다(NO_CHANGE). 관제판 4건은 waiting으로 남는다.
- ④만 빼는 길: ④는 지시문만 바꾸므로, 규칙 파일 해시를 다시 만들지 않고 ㉰·PRIOR·writer만 되돌린 지시문으로 바꿔 넣을 수 있다.

## 7. 승인과 적용
1. 사장이 이 스레드에 직접 입력한다: `예약 작업 변경 승인: 보유·관심 종목 통합 점검` (카드 아님, sc-1022 S4)
2. 스레드가 update_trigger로 지시문만 바꾼다(이름·일정은 그대로). 결과가 needs_device_approval이면 사장이 PC 데스크톱 앱에서 승인해 재서명한다.
3. 응답 본문의 바이트 해시를 74b1a367…와 대조한다. scheduled-prompts/integrated-check-daily.txt를 새 판으로 바꾸고 README 표·변경 기록·active-decisions 1줄·관제판 5건을 갱신한다.
4. 첫 적용 실행(다음 화~토 06:40)에서 확인할 것: 1단계 MATCH, writer v3.12.11, 연구 기록 RR OK, 대시보드 기록 정상, PRIOR 줄. 같은 날 재실행이 있으면 core가 남는지도 본다. 07:45 코어 research OK, 08:40 독립 대조 MATCH.

## 8. 되돌리는 법
pending-iv-c1c2/integrated-check-daily.txt(1101af45…, v3.12.10-L+R2)로 지시문을 다시 바꾼다. 같은 승인 절차와 재서명을 거친다. 규칙 파일 v3.12.10은 저장소에 그대로 남는다. 연구 기록에 이미 쓴 `-v2` id는 그대로 둬도 스키마에 맞는다.

## 9. 결론을 바꿀 조건
첫 실행에서 PRIOR나 core 붙이기 단계가 실패하거나, LLM이 N11·N12·U9·U10을 기준 밖 사실에 쓰면 그 부분만 되돌리는 안을 다시 올린다. 08:40 대조에서 fact_id 판 때문에 새로운 MISMATCH가 나와도 같다.

검토 완결: 원문 확인 14/14 · 내장 재검토 1회(반영 6건) · 미해결 0 · 자료 시점 2026-11-02 KST(저장소 52bbe81 작업 트리) · 바뀔 조건 9절
