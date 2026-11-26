# llm-srcfix Builder 보고 (2026-11-26)

지시문: docs/claude/llm-srcfix-builder-prompt.md · 규칙: tools/dev_pipeline/builder-rules.md
권한 표지 4종 줄 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장·연구 기록·카드·켜기 파일 쓰기 없음 · 키 값 읽기 없음 · 웹 접속 없음 · 스크립트 실제 실행 없음(`--dry-run` 포함).

## (a) 바꾼 줄

### manage-us-stock-strategy/scripts/llm_pilot_srccheck.py
| 행(후) | 전 | 후 |
|---|---|---|
| 117 | `WEB_FETCH_TYPE = "web_fetch_20260209"` | `WEB_FETCH_TYPE = "web_fetch_20250910"` |
| 171~172 (추가) | — | 주석 1줄 `# DEF 14A: EDGAR "period of report" is the shareholder meeting date.` + `CLAIM_SEC_MEETING = "주주총회일 %s"`('주주총회일 %s') |
| 362~363 | `extras.append(CLAIM_SEC_REPORT % f["report_date"])` | `date_claim = CLAIM_SEC_MEETING if f.get("form") == "DEF 14A" else CLAIM_SEC_REPORT` / `extras.append(date_claim % f["report_date"])` |

그 밖(모델·예산·하루 건수·허용 호스트·차단 낱말·max_tokens·도구 정의의 나머지 칸·결과 URL 글자 대조·NO_CITATION 낮춤)은 그대로다. code_execution 도구는 넣지 않았다. 스크립트는 ASCII만 유지(기존 소스 계약 시험 통과).

### manage-us-stock-strategy/tests/test_llm_pilot_srccheck.py
- 590행: 도구 정의 단언의 `"web_fetch_20260209"` → `"web_fetch_20250910"` (글자만).
- 파일 끝(클래스 마지막)에 새 시험 2개 추가, 기존 시험 함수·가짜 자료 블록은 바꾸지 않음:
  - `test_web_fetch_version_without_dynamic_filtering`(1009행): 스크립트 소스에 `web_fetch_20260209` 글자가 없음, `WEB_FETCH_TYPE` 값, `web_fetch_tool()`의 칸 전체(name·max_uses 1·allowed_domains·max_content_tokens 20000·citations 켬)가 그대로임.
  - `test_def14a_claim_names_meeting_date`(1017행): `claim_text`에 target dict를 직접 넘김. DEF 14A는 '…DEF 14A 서류이고, 주주총회일 <report_date>이다'이고 '보고 기준일'이 없음, 8-K는 기존 기대 문장(`CLAIM_8K`, '보고 기준일')과 같고 '주주총회일'이 없음, report_date가 없는 DEF 14A는 날짜 구절 없이 끝남.

두 기존 파일은 CRLF 그대로(바뀐 줄 포함, 줄 끝이 LF만인 줄 0개).

## (b) 시험 결과

명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot_srccheck*.py"` (전체 시험은 돌리지 않음)

```
----------------------------------------------------------------------
Ran 46 tests in 0.720s

OK
```

`git diff --stat`(보고서 쓰기 전, 새 보고 파일은 추적 전이라 빠짐):

```
 .../scripts/llm_pilot_srccheck.py                  |  7 ++++--
 .../tests/test_llm_pilot_srccheck.py               | 29 +++++++++++++++++++++-
 2 files changed, 33 insertions(+), 3 deletions(-)
```

## (c) 병합 뒤

- 켜기 파일 `docs/claude/llm-pilots-schedule.json`은 그대로 둔다(srccheck 두 줄 이미 켜짐, dac6d40). 다음 08:10 KST srccheck-submit 제출부터 새 도구 판이 쓰인다.
- 첫 실행(2026-11-26) 4건은 seen 기록 때문에 다시 제출되지 않는다. 20건 셈에서 빼는 것은 사장실 채점 기록 docs/claude/llm-srccheck-score.md에 적혀 있다.

## (d) 확인 필요

- `web_fetch_20250910`에서 Batch 안 응답의 text 블록에 인용(citations)이 실제로 붙는지 — 다음 실행 `checks.json`의 `rows[].block_types`(code_execution_tool_result가 사라지는지)와 `reason`(NO_CITATION이 줄어드는지)으로 확인.
- 건당 입력 토큰 변화 — 본문 상한 20,000 토큰이고 첫 실행은 코드 실행 왕복이 끼어 건당 14k~43k였다. 다음 실행 usage로 확인.
- 이 worktree에는 `workspace/outputs/llm/srccheck/2026-11-26/checks.json`이 없어(작업 산출은 추적 밖) 지시문 '먼저 읽을 것'의 모양 확인은 하지 못했다. 판단은 스크립트 691~782행(인용 읽기·결과 블록 판정·NO_CITATION 낮춤)과 지시문 source 칸의 설명에 기댔고, 그 판정 코드는 바꾸지 않았다.

## 연결표

지시문 연결표와 같다(산출·소비자·알림 끊김 변화 없음, 도구 판과 DEF 14A 주장 문구만 바뀜).
