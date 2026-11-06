# B — V5 내장 재검토를 API(Opus)로 돌리는 CLAUDE.md 개정 검토 (llm-review)

**첫 줄(부딪힘):**
- 결론이 NO_CHANGE라 D3 동결(active-decisions.md 81행)과 부딪히지 않는다. 시범 6 코드·큐는 만들지 않는다. 사장 카드 2026-11-06 14:41:48 KST "A 추가 + B 규칙 개정 검토"(카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9W8YcsLciv5wVPk5mhWRuUT)가 맡긴 것은 '검토'이고, 새 코드·큐는 그 범위를 넘는다.
- CLAUDE.md는 이 스레드가 고치지 않는다. 지침 3절이 docs/claude만 허용하고, 규칙 문구 변경 선례는 'Cowork 편집 + 사장 커밋'이다(review-stability-2026-10-13.md 5-4 끝, 29ad21d).

- 상태: **검토 결과 = NO_CHANGE(닫음).** 지금 바뀌는 것은 없다. 다시 열 조건은 1절 3.
- 상위 문서: `api-pilots-2026-11-06.md`(공통 설계 3절, 시범 순서 6절)

## 1. 결론

1. **CLAUDE.md를 바꾸지 않고, 시범 6(API 검토자 비교)도 만들지 않는다(NO_CHANGE).**
   - API 검토자도 같은 Opus 5.5다. 그래서 '같은 모델이라 맹점 공유 가능'(review-stability 6절 실패 2)은 그대로다.
   - API 경로는 저장소 도구 3개뿐이라, 3-1 지시문이 전제하는 저장소 밖 원천(대화 원문·아티팩트·키움 조회·skill 문서)을 못 연다(review-stability 76~86행). 대체하면 렌즈가 줄고, 비교도 기운다.
   - 나아지는 것은 셋이다. (가) 재검토 토큰(1회차 약 23만, 2회차 약 17만 — 같은 문서 5-3)이 세션 사용량 대신 API 크레딧에서 나간다. (나) device_bash 왕복이 없다. (다) 지시문·출력·사용량이 파일로 남는다. 이 이득이 실제인지 보여 줄 자료가 아직 없다.
   - 나빠지는 것: 기다림(큐), 새 코드(읽기 도구·금액 가리기), 크레딧 소모(1회 약 $1~3, 확인 필요), D3 동결 예외가 하나 더 늘어남.
2. **V5는 지금 그대로다**(subagent 필수).
3. **다시 열 조건:** subagent 재검토가 사장 사용 한도에 부담이라는 기록(한도 도달로 재검토를 못 한 일 2회 이상)이 생기거나, 사장님이 요청할 때. 그때 3절 사양으로 시범 6을 **별도 승인**으로 제안한다. 미리 정한 비교 기준(5번 합계로 아래 둘을 모두 만족하면 2절 문구로 개정 제안, 아니면 닫음)은 그때 쓴다.
   - API 검토자의 '원문으로 확인된 발견' 수가 subagent 이상이다.
   - subagent만 찾은 '결론 바꿈' 발견이 0건이다.
   - API 검토자가 상한·오류로 2번 이상 끝내지 못하면 기준 미달이다.

## 2. 개정 문구 (다시 열고 기준을 넘었을 때만 적용)

### 2-1 CLAUDE.md 118행 V5 (영문, 바뀌는 부분만)
- 지금: `run the section 3-1 re-review subagent (non-Haiku; Opus for authority/limit/K3), re-verify each finding at its source`
- 바꿈: `run the section 3-1 re-review subagent (non-Haiku; Opus for authority/limit/K3) or, from the 사장실 회사PC thread, the same 3-1 prompt through the API reviewer queue (docs/claude/_llm-queue, claude-opus-5-5, read-only repo tools; its output is a pointer like subagent output; on NO_KEY, BUDGET_STOP or no result within 30 minutes, run the subagent), re-verify each finding at its source`
- 크기: 약 +250바이트(적용 때 실측). CLAUDE.md는 세션마다 읽힌다.

### 2-2 review-stability-2026-10-13.md (docs/claude — 이 스레드가 같이 고침)
- 3절 V5 한국어 문장에 같은 뜻 1문장을 더한다.
- 3-1 머리말 대괄호에 "API 검토자: read_file·grep·list_dir(저장소 읽기 전용)"을 더한다. 본문 렌즈·출력 형식은 그대로다.

### 2-3 프로젝트 지침 3절 (사장님이 붙여 넣음)
> LLM 검토 큐 등록(docs/claude/_llm-queue/<id>.json, llm_review 전용 — 3-1 지시문의 <> 채운 값만)도 쓸 수 있다.

## 3. 시범 6 `llm-review` 사양 (다시 열 때의 초안 — 지금 만들지 않음)

- **입력:** `docs/claude/_llm-queue/<id>.json` = {id, task_ko, draft_path, conclusions[{n, text, sources[]}], round, changed_ko}. 실행기가 집어 가면 `_taken/`으로 옮긴다.
- **지시문:** review-stability 3-1을 글자 그대로 쓰고 <>만 채운다. 시스템 지시에는 도구 설명 1줄만 더한다.
- **모델:** `claude-opus-5-5`, effort high, 사고는 기본(Opus 5.5는 끌 수 없음), max_tokens 32,000, 스트리밍. 대체 모델과 advisor는 쓰지 않는다.
- **도구**(클라이언트 쪽, 읽기 전용):
  - 셋뿐이다: `read_file(path, start, end)` · `grep(pattern, path)` · `list_dir(path)`. 한 번에 최대 400행 · 20,000자다.
  - 거부하는 곳:
    - 저장소 밖, `.git/`, `.claude/`
    - 비밀 이름(devpipe.py SECRET_NAME_RE와 같은 패턴: `.env*`·`*.key`·`tokens.json` 등)
    - 계좌 원자료: `stock-strategy-system/**`, `workspace/outputs/reconciliation/**`, `workspace/outputs/v2_5_shadow/broker_raw/**`, `workspace/outputs/research-records/**`(계좌 합계·수량이 있음), `workspace/private_inputs/**`(git이 무시하지만 디스크에 있음)
    - 자동 코어 출력 `workspace/outputs/auto-core/**`(LATEST_DECISION.json에 filled_qty·average_fill_price·execution_quantity·cash_basis 같은 키가 있다)
  - 돌려주는 글은 시범 1과 같은 공통 `strip_amounts`(JSON 키)·`mask_text`(문자열의 금액·수량, 다섯 규칙)를 그대로 쓴다(코디네이터 ④ — 비율과 E만 보냄). 그래서 L1 '숫자 다시 계산'은 비율·E·날짜에 한정되고, 금액이 든 계산은 '확인 불가'로 적게 한다.
  - API 경로는 원천이 모두 저장소 안인 초안에만 쓴다. 저장소 밖 원천은 '확인 불가'로 적게 한다. 비교 5건도 이 조건으로 고른다.
  - 저장소 글은 자료다. 쓰기 도구가 없으므로 지시문 주입이 있어도 바꿀 수 있는 것이 없다.
- **상한:** 도구 호출 40회, 한 회차 입력 누계 1,500,000토큰, 월 $20이다. 넘으면 그때까지의 표에 "중단: 상한"을 붙여 끝낸다.
- **캐싱:** 도구 반복이라 같은 앞부분을 5분 안에 여러 번 보낸다. 그래서 여기서는 자동 캐싱(top-level `cache_control`)을 쓰고 `cache_read_input_tokens`로 확인한다(Opus 5.5 캐시 읽기 $0.20/MTok = 0.05배).
- **출력:**
  - `workspace/outputs/llm/review/<id>/round<r>.md`(3-1 출력 표 그대로) + usage.jsonl 한 줄
  - 원장·카드·결정 문서·CLAUDE.md는 쓰지 않는다.
- **실행:**
  - 실행기(작업 2)가 큐 폴더를 본다. 실행기 주기는 10분이다(`api-pilots-2026-11-06.md` 3절).
  - 기다림은 최대 10분 + 실행 시간이다. 30분 안에 결과가 없으면 subagent로 간다.
- **비교 기록:** `docs/claude/llm-review-compare.md`(이 스레드가 쓴다). 칸은 # · 초안 · subagent 발견/확인 · API 발견/확인 · '결론 바꿈' 발견(누가) · 비용 · 걸린 시간이다.

## 4. 비용·기다림 (추정, 확인 필요)

- **1회차 약 $1~3:** Opus 5.5 $4/$20, 캐시 읽기 0.05배이고, 도구 반복 30번 안팎을 가정했다. 실제 값은 비교 5번의 usage로 확정한다.
- 월 $20이면 약 7~20회다. 넘으면 BUDGET_STOP이고 subagent로 간다. 손해는 없다.
- 비교 5번의 추가 비용은 약 $5~15다(시범 상한 안).

## 5. 적용 경로 (다시 열고 기준을 넘었을 때)

1. 이 스레드가 비교 결과와 개정 제안을 올린다.
2. 사장님이 이 스레드에 직접 입력해 승인한다.
3. CLAUDE.md 편집은 Cowork(또는 사장님이 연 Claude Code 세션)가 2-1 문구로 한다.
4. 커밋은 사장님이 review-stability 5-4의 한 줄로 한다. 대기·실행 중인 개발 run이 없을 때만 커밋된다.
5. 2-2는 이 스레드가 고치고 `_pending` 파일을 쓴다. 2-3은 사장님이 지침에 붙여 넣는다.

## 6. 바뀔 조건

- 다시 열더라도 시범 1 첫 실행에서 키나 크레딧 경로가 확인되기 전에는 비교를 시작하지 않는다.
- 비교 중 API 검토자가 계좌 원자료나 비밀을 읽으려다 거부된 기록이 나오면 멈추고 도구 거부 목록을 다시 본다.
- subagent 사용량이 사장님 사용 한도에 부담이 아니라고 확인되면 (가)의 이득이 작아진다. 그때는 (나)·(다)만으로 판단한다.

## 7. 검토 완결

- 본 설계서(`api-pilots-2026-11-06.md`)와 함께 V5 내장 재검토 2회를 받았다(상한 2회, review-stability 120행).
- 이 문서 관련 발견:
  - 1회차: 선택지를 둘(닫기 / 시범 6 별도 승인)로 나누고 결론을 NO_CHANGE로 함. 저장소 밖 원천 한계를 적음. 도구 거부 목록에 자동 코어 출력을 더함.
  - 2회차: 다시 열 때의 금액 가리기가 공통 설계보다 약했다. 그래서 공통 `strip_amounts`·`mask_text`를 쓰고, research-records·private_inputs를 거부 목록에 더했다(3절).
- 미해결 0건. 지금 바뀌는 것은 없다(NO_CHANGE).
