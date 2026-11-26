---
id: llm-srcfix-builder-prompt
title: "API 시범 4 고침 — 출처 확인의 웹 가져오기 도구를 동적 필터링 없는 판(web_fetch_20250910)으로, DEF 14A 주장 문구 바로잡기 — llm-srcfix"
date: 2026-11-26
class: "general(시범 스크립트 상수 2곳과 그 시험, 코어·정책·주문 경로와 무관). 개발 큐 general: Builder → Judge → READY_TO_MERGE면 Cowork 또는 사장 dev-merge"
source: "앞 작업 llm-srccheck(지시문 docs/claude/llm-srccheck-builder-prompt.md, 병합 f90cf00, 켜기 dac6d40 — 사장 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9A7AqUsEfz8FL8Z8Rf18Ci1 2026-11-25 18:40:14 KST). 첫 실행 2026-11-26 결과 workspace/outputs/llm/srccheck/2026-11-26/checks.json: 4건 모두 가져오기 성공·결과 URL 일치·stop end_turn·모델 판정 '맞음'인데, 응답 블록에 code_execution_tool_result가 섞여(동적 필터링) text 인용이 0개 → 4건 모두 NO_CITATION으로 '확인 불가'. 설계 docs/claude/api-pilots-2026-11-06.md 7절 3이 첫 제출로 확인하라던 항목의 답"
authority: "권한 표지 4종 줄 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장·연구 기록·카드 쓰기 없음 · API 키 값을 읽거나 출력하지 않음 · 켜기 파일을 바꾸지 않음"
---

## 목표
- `llm_pilot_srccheck.py`의 웹 가져오기 도구 판을 `web_fetch_20260209`(동적 필터링이 자동으로 켜져 코드 실행 안에서 가져옴 → 인용이 text에 붙지 않음)에서 `web_fetch_20250910`(동적 필터링 없음, 가져온 문서가 그대로 문맥에 들어와 인용이 붙음)으로 바꾼다.
- SEC 주장 문구: `report_date`를 늘 '보고 기준일'로 부르면 DEF 14A에서 틀린다(EDGAR 'period of report'가 위임장 설명서에서는 주주총회일이다 — 2026-11-26 사장실 스레드 원문 대조, MU DEF 14A: 2027-01-14는 총회일, 주주 기준일은 2026-11-18). `form`이 `DEF 14A`면 '주주총회일 %s'로, 그 밖에는 지금처럼 '보고 기준일 %s'로 쓴다.
- 나머지 사양(한 URL만·max_uses 1·allowed_domains·max_content_tokens 20,000·citations 켬·결과 URL 글자 대조·인용 없으면 '확인 불가')은 그대로 둔다. 판정 기준을 느슨하게 하지 않는다.

## 바꿀 파일 (이 3개만)
- manage-us-stock-strategy/scripts/llm_pilot_srccheck.py — 117행 `WEB_FETCH_TYPE` 값 1줄, 170행 근처에 DEF 14A용 주장 상수 `CLAIM_SEC_MEETING` 1개 추가(`\uc8fc\uc8fc\ucd1d\ud68c\uc77c %s`), 359~360행 근처에서 form이 `DEF 14A`일 때 그 상수를 쓰는 분기. 그 밖은 바꾸지 않는다.
- manage-us-stock-strategy/tests/test_llm_pilot_srccheck.py — 590행 근처 도구 정의 단언의 `"web_fetch_20260209"` 글자만 새 값으로. 추가 단언은 모두 파일 끝의 **새 시험 함수**에만 넣는다(기존 시험 함수·기본 가짜 자료 150~160행은 590행 글자 말고 건드리지 않는다).
- docs/claude/llm-srcfix-report.md (새 파일, LF, 보고)

## 먼저 읽을 것 (고치지 않는다)
- `llm_pilot_srccheck.py` 110~125행·165~175행(주장 상수)·350~365행(주장 문장)·535~555행(도구 정의)·691~782행(인용 읽기·결과 블록 판정·NO_CITATION 낮춤).
- `workspace/outputs/llm/srccheck/2026-11-26/checks.json`의 `rows[].block_types`·`reason`·`stop_reason`(모양만, 값은 보고에 옮기지 않는다).

## 지켜야 할 것
1. 허용 파일 3개 밖은 손대지 않는다. 두 기존 파일에서는 위에 적은 줄만 바꾼다. **시험 파일 95~118행 블록(`make_record`, 권한 표지 이름이 든 표식 줄 포함)은 바꾸기·지우기·옮기기·복사 모두 금지** — 추가 줄과 삭제 줄 둘 다 권한 분류가 된다(`tools/dev_pipeline/devpipe.py:898-914`). 새 시험은 기존 도우미(`make_record`·`sec_event`)를 호출만 하고, 새 시험·보고서에 권한 표지 이름 글자를 쓰지 않는다.
2. 위 두 곳 밖의 상수(모델·예산·하루 5건·허용 호스트·차단 낱말·max_tokens)는 바꾸지 않는다. code_execution 도구를 넣지 않는다.
3. 키 값을 읽지 않는다. 비밀 파일을 열지 않는다. 웹에 접속하지 않는다. 스크립트를 실제 저장소에 대고 돌리지 않는다(`--dry-run` 포함). pip 설치 없음.
4. 주문·키움·일지·원장·예약·정책·상태와 무관. git은 status·diff·log만. commit·push·병합 없음. `python -c` 쓰지 않음.
5. 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 시험
- 590행 근처 단언을 새 값으로 바꾼다.
- (추가) 소스 계약: 스크립트 안에 `web_fetch_20260209` 글자가 없음을 단언.
- (추가) DEF 14A 시험은 `claim_text`에 target dict를 직접 넘긴다. DEF 14A 사건의 주장 문장에 '주주총회일 <report_date>'가 들어가고 '보고 기준일'이 없음, 8-K 사건은 지금처럼 '보고 기준일'.
- Builder 시험 명령(이 글자 그대로): `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot_srccheck*.py"`. 전체 시험은 돌리지 않는다.

## 보고 docs/claude/llm-srcfix-report.md
- (a) 바꾼 줄(파일:행, 전·후)·추가 시험 이름 · (b) 시험 결과 마지막 3줄 · `git diff --stat`
- (c) 병합 뒤: 켜기 파일은 그대로(이미 켜짐), 다음 08:10 제출부터 새 판이 쓰인다. 첫 실행 4건은 seen 때문에 다시 제출되지 않는다(20건 셈에서는 빼기로 사장실 채점 기록 docs/claude/llm-srccheck-score.md에 적음).
- (d) 확인 필요: `web_fetch_20250910`에서 Batch 안 인용이 실제로 붙는지(다음 실행의 block_types·reason으로 확인), 건당 입력 토큰이 어떻게 달라지는지(본문 상한 20,000, 첫 실행은 코드 실행 왕복이 낀 14k~43k) 다음 실행 usage로 확인.
- 수량·금액·키 값·URL을 적지 않는다. 표지 문자열 대신 '권한 표지 4종 줄 변경 없음'.

## 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| `workspace/outputs/llm/srccheck/<날짜>/checks.json`·`checks.md` · 누적 `srccheck/checks.jsonl`(기존 산출, 새 산출 없음 — 도구 판만 바뀜) | Windows 작업 InvestmentV2-LLMPilots → `manage-us-stock-strategy/scripts/llm_runner.py:51-52` srccheck-submit 08:10 · srccheck-collect 10:10 KST(켜기 파일 `docs/claude/llm-pilots-schedule.json` srccheck 두 줄 켜짐, dac6d40) | 사람 단계 — 사장실 회사PC 스레드가 `checks.md`의 URL·주장으로 원문을 WebFetch 대조해 20건 일치율을 센다(`docs/claude/api-pilots-2026-11-06.md:178-179`) | 일치 ≥ 80%면 '통합점검 공식 사실 재확인 표시' 안 제안(별도 승인), 60일 안 20건 미달이면 NO_CHANGE(`docs/claude/api-pilots-2026-11-06.md:178`) | 끊김 — 실행기 하루 기록 `workspace/outputs/llm/runner/<날짜>.json`을 읽는 예약이 없다(`docs/claude/llm-srccheck-builder-prompt.md` 연결표와 같음). 메울 변경: 사장실 결과 모음 예약이 실행기 하루 기록을 읽게 하기 · 승인 경로: 지침 4절 `예약 작업 변경 승인: <이름>`(이 작업 밖). 그 전까지 사장실 스레드가 10:30 KST 뒤 `checks.md`를 직접 읽는다 | 연결(산출) · 알림 끊김(기존과 같음) |

## Judge 확인 항목
1. diff가 허용 파일 3개뿐이고, 스크립트는 `WEB_FETCH_TYPE` 1줄과 DEF 14A 주장 상수·분기만, 시험은 도구 단언 글자와 추가 시험만 바뀌었다. 권한 표지 이름이 든 추가 줄이 없다.
2. 새 값이 `web_fetch_20250910`이고 나머지 도구 칸(name·max_uses 1·allowed_domains·max_content_tokens·citations)이 그대로다. code_execution 도구가 없다.
3. 결과 URL 글자 대조·NO_CITATION 낮춤 등 판정 코드가 바뀌지 않았다.
4. 새 실패 0. 보고서 (a)~(d) 있음, 표지 문자열·URL 없음.

```dev-run
{"task_id": "llm-srcfix", "class": "general", "builder_model": "opus", "builder_effort": "high", "max_turns": 50, "builder_timeout_min": 30, "allowed_paths": ["manage-us-stock-strategy/scripts/llm_pilot_srccheck.py", "manage-us-stock-strategy/tests/test_llm_pilot_srccheck.py", "docs/claude/llm-srcfix-report.md"], "target_tests": ["test_llm_pilot_srccheck*.py"], "commit_message": "fix(llm-pilot): srccheck uses web_fetch_20250910 so fetched-document citations reach the answer, and labels DEF 14A report_date as the meeting date (llm-srcfix)"}
```

조언 기록: Fable 형식 점검 1번(medium) 5건 — 결론 바뀜 0 · 정정 5 · 미반영 0.
