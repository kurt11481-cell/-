---
id: llm-pdfcmp-builder-prompt
title: "API 시범 3 — 외부자료 PDF 1차 분류를 Haiku Batch로 1회 비교 — llm-pdfcmp"
date: 2026-11-25
class: "general(새 시범 스크립트 1개와 그 시험만, 코어·정책·주문 경로와 무관). 개발 큐 general: Builder → Judge → READY_TO_MERGE면 Cowork 또는 사장 dev-merge"
source: "설계 docs/claude/api-pilots-2026-11-06.md 4절 시범 3·6절 순서 4(사장 2026-11-06 16:44:47 KST 카드 '시범 1부터 차례로'). 이번 등록 = 사장 결정 카드 'P1b 개발 큐 + P2 시범'(cmsg_0137MRzn9nuDvvQmVxm6WeX95rNSzrSLUx2SjPaLHndQPN, 2026-11-25 09:18:26 KST, 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH) — docs/claude/api-credit-expand-design-2026-11-25.md 8절. PDF 10개 고르기 = docs/claude/pdfcmp-pdf-selection-2026-11-25.md"
authority: "권한 표지 4종 줄 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장·연구 기록·카드 쓰기 없음 · 계좌·보유 자료를 읽지 않음 · API 키 값을 읽거나 출력하지 않음 · 켜기 파일을 바꾸지 않음 · 외부 주장 원장을 쓰지 않음"
---

## 목표
- 원장(docs/claude/external-claims-ledger.md)에서 이미 처리된 외부자료 PDF 10개를 Files API로 올리고, `claude-haiku-5-5` Batch + 문서 인용(citations)으로 "분류(후보|R0) · 라우트 · 대상 · 근거(인용)"를 받아, 원장 결과(정답표)와 **한 번** 비교한다.
- 합격: 분류 일치 ≥ 8/10 **그리고** 주제 겹침 ≥ 8/10 → `PASS`(외부자료 PDF 1차 분류를 API로 옮기는 안을 사장실이 따로 제안). 미달 → `FAIL`(지금 방식 유지, 질문 닫음). 쓸 수 있는 PDF가 8개 미만 → `HOLD`(판단 보류, API 호출 없음).
- 결과는 표시 전용 기록이다. 원장·통합점검·코어는 이 결과를 읽지 않는다.

## 바꿀 파일 (이 3개만, 모두 새 파일)
- manage-us-stock-strategy/scripts/llm_pilot_pdfcmp.py (LF, ASCII만 — 한글 상수는 `\uXXXX` 이스케이프)
- manage-us-stock-strategy/tests/test_llm_pilot_pdfcmp.py (LF)
- docs/claude/llm-pdfcmp-report.md (LF, 보고)
- llm_runner.py는 이미 pdfcmp 두 작업과 스크립트 이름을 갖고 있어(`llm_runner.py:53-54`) 고치지 않는다.

## 먼저 읽을 것 (고치지 않는다)
- `manage-us-stock-strategy/scripts/llm_pilot_common.py` 전체: `load_key`·`make_client`·`api_error_label`·`estimate_cost(batch=True)`·`append_usage`·`month_spend`·`atomic_write_text`·`write_failed`·`response_text`·`check_message`·`MODELS["pdfcmp"]`·`BUDGET_USD_MONTH["pdfcmp"]`(=5).
- `manage-us-stock-strategy/scripts/llm_pilot_news.py`: 제출·수거 두 단계 뼈대(540·1074·1114행), `batch.json` 멱등 처리(562·888행), Batch 결과 분류(960행), 마지막 줄 형식(213행), `--dry-run`.
- `manage-us-stock-strategy/scripts/llm_runner.py` 40~60행(작업 이름·인자 약속: `--phase submit|collect`, 실행기가 `--day`를 넘김).
- `manage-us-stock-strategy/tests/test_llm_pilot_news.py`의 `test_script_source_contract`(금지어 목록) — 새 스크립트도 같은 금지어를 쓰지 않는다(environ·zoneinfo·subprocess·import requests·urllib·fallbacks·advisor·socket·http.client·auto_core·kiwoom, 주석 포함).
- `docs/claude/pdfcmp-pdf-selection-2026-11-25.md`(정답표·파일 이름).
- `docs/claude/external-claims-ledger.md` 21~36행(1절 규칙: 라우트 정의). 모델에게 보낼 분류 지침은 이 행을 근거로 쓴다(행 번호를 상수 주석에 적는다).

## 구현 요구
1. **PDF 표 상수** `PDFS`: 10행, 각 행 = (`pid` "P01"~"P10", 파일 이름, sha256, 정답 분류 `CAND`|`R0`, 주제 낱말 튜플). 파일 이름·sha256은 아래 표 그대로(파일 이름은 이스케이프로). 주제 낱말은 대소문자 무시·공백 무시로 비교한다.

| pid | 정답 | sha256 | 주제 낱말(하나라도 '대상'에 있으면 겹침) | 파일 이름 |
|---|---|---|---|---|
| P01 | CAND | 300bca2e1b23896e8dba18e2178ead47654307ca8d3071429afd0183c93a4402 | MU · 마이크론 · 메모리 | 마이크론 $MU ___30년 말까지 피지컬AI가 메모리와 스토리지 수요의 중요한 동인이 될 수 있다._ - 주식 - 에펨코리아.pdf |
| P02 | CAND | 8fdeb7c97f07236b2c804d0663fa41bad8cdfee0861c8bce07fe3c53d65553e3 | MU · 마이크론 · 메모리 | 28년 메모리 Q 사이클에 대한 일반적인 인식이 - 주식 - 에펨코리아.pdf |
| P03 | CAND | 960abfa0ba0d8924d06d38cad6a618595ec6002a96ece77c518c96043ab0a2a0 | SNDK · 샌디스크 · 낸드 · NAND | _레포트_ 샌디스크 SNDK __ 퓨어 낸드 플레이어 - 주식 - 에펨코리아.pdf |
| P04 | CAND | 30a3002b62fb72bc7ef7576ac7beafacb467ed65004308081f0b142cced3c3ec | 연준 · Fed · 인플레이션 · 금리 | 단독_ 연준, 인플레이션 전망 위해 AI·관세·에너지 주시 - 주식 - 에펨코리아.pdf |
| P05 | CAND | a67c86fd8a640fc799f2bac0cebaa968dd660aab4327dd0f0417389d395bfe02 | AMD · INTC · 인텔 · CPU | 연휴기간에는 글 안쓸려고 했는데 심심해서 쓰는거 절대루 아니거등_ 흥! - 주식 - 에펨코리아.pdf |
| P06 | R0 | 83a04de9ed3f51266601be05b2550baaec3f9cfaa3848ef1fe83ce28957a1bd1 | 추세추종 · 매매 · 손절 · 돌파 | 추세추종 트레이딩 _ 그래서 매수와 매도는 언제 해요_ - 주식 - 에펨코리아.pdf |
| P07 | R0 | f47cd947c308a93d1e19ee02e06fef2fdfdf76cc11d7b571f94bde7077480210 | PER · 밸류에이션 · S&P | bbs_1790030156281.pdf |
| P08 | R0 | 35141529a39e283a51b323bdbb7f233ef5c3211bf37a1c057a12a0102215d28b | PER · 마진 · 밸류에이션 | bbs_1791326873246.pdf |
| P09 | R0 | 4a01351c52de27259bc71599abfbe470364d446e04856b8745dfd7a45cf678f5 | 중간선거 · 모건스탠리 · 선거 | 10월, 랄부 떨리는 조정 오려나_ 플러스 모건스탠리 중간선거 시나리오 - 주식 - 에펨코리아.pdf |
| P10 | R0 | ddcb2546dec63baee64aa578103e37e7e12435551bf164cabf6593e7b4ec9973 | 전력 · 발전 · 데이터센터 · BYOP | AI 인프라투자에서 전력 테마주들의 위치를 재정의해야 한다는 얘길 해주고 싶어 적는 글 절대루 아니거등_ - 주식 - 에펨코리아.pdf |

2. **폴더**: `--pdf-dir` 인자, 기본값 상수 `DEFAULT_PDF_DIR = "E:\\\uc0ac\uc5c5\\##\uae08\ub3d9\ud55c\\chatgpt_\uc885\ubaa9\ubd84\uc11d\uacb0\uacfc\\\uc678\ubd80\uc790\ub8cc"`(원장 17행). 이 폴더는 **읽기만** 한다. 파일이 없거나 sha256이 다르면 그 PDF는 뺀다(`skipped` 목록에 pid와 이유 MISSING|SHA_MISMATCH|TOO_LARGE). 32,000,000바이트 넘는 파일은 TOO_LARGE. 쓸 수 있는 PDF가 8개 미만이면 `HOLD`로 끝내고 API를 부르지 않는다. **제출 단계 HOLD는 `compare.json`·`batch.json`을 쓰지 않는다**(다음 날 다시 확인, failed.md 1줄만). `compare.json`은 수거 단계에서만 쓴다.
3. **한 번만**: 결과 폴더는 `workspace/outputs/llm/pdfcmp/`(날짜 폴더 아님). `compare.json`이 있으면 두 단계 모두 아무것도 안 하고 `DONE_ALREADY`. `batch.json`이 있고 `compare.json`이 없으면 제출은 `PENDING`(다시 제출하지 않음).
4. **제출**(`--phase submit`): 키 확인(`load_key`, 없으면 NO_KEY) → 이달 `month_spend(root, "pdfcmp", "<KST YYYY-MM>")`(ValueError 등 예외면 BUDGET_STOP, `llm_pilot_news.py:584-588`과 같음) + 이번 추정(입력 PDF당 상한 60,000토큰 가정, 출력 4,096토큰, Batch 0.5배)이 `BUDGET_USD_MONTH["pdfcmp"]`를 넘으면 BUDGET_STOP → 각 PDF `client.files.upload`(이름은 `<pid>.pdf` ASCII, 형식 application/pdf — 원래 파일 이름은 API로 보내지 않는다) → `client.messages.batches.create`. 요청 1개 = PDF 1개, `custom_id` = pid, `model` = `MODELS["pdfcmp"]`, `max_tokens` 4096(생각 토큰 포함 여유), content = [`{"type":"document","source":{"type":"file","file_id":…},"citations":{"enabled":true}}`, 분류 지침 text]. 서버 대체 모델·advisor·베타 헤더 쓰지 않음. 올린 file_id·pid·sha256·batch_id를 `batch.json`에 원자적으로 쓴다(올리기 중 실패하면 이미 올린 파일을 지우고 failed.md).
5. **분류 지침 text**(상수, 고정): 원장 1절 규칙(21~36행)의 라우트 뜻을 한국어로 요약해 넣고, 답을 다음 4줄로만 받는다: `분류: 후보|R0` · `라우트: R1|R2|R3|R4|P|R0` · `대상: <종목 기호나 주제 낱말, 쉼표로>` · `근거: <글 속 문장 그대로 한 줄>`. 금액·수량을 묻지 않는다.
6. **수거**(`--phase collect`): `batch.json` 읽기 → `batches.retrieve`가 ended가 아니면 `WAITING`(아무것도 안 씀) → 결과마다 `check_message`(None이면 정상) → `response_text`로 text 블록만 읽어 4줄을 정규식으로 파싱(형식 틀리면 `PARSE_FAIL`로 그 PDF는 불일치로 셈) → 인용: 응답 citations 중 하나라도 `cited_text`가 있고 그 문장이 '근거' 줄과 공백 정규화 뒤 6자 이상 겹치면 `quote_ok`, 아니면 `quote_missing`(분류 판정에는 쓰지 않고 따로 셈) → **분모와 실패 처리**: used = 제출한 PDF 수 − MODEL_MISMATCH로 버린 수. REFUSAL·MAX_TOKENS·BAD_STOP·PARSE_FAIL과 Batch 결과 errored·expired·canceled·결과 없음은 그 PDF를 분류·주제 모두 불일치로 세고 이유를 표에 적는다 → 정답표와 비교: 분류 일치(후보=CAND), 주제 겹침(주제 낱말 중 하나가 '대상'에 있음) → `usage.jsonl`에 message가 있는 결과마다 1줄(`append_usage`, USAGE_KEYS 10개를 모두 채움: `ts_kst` = KST ISO 문자열, `pilot` = "pdfcmp", `model`, 토큰 4개, `batch` = True, `cost_usd_est` = `estimate_cost(model, usage, batch=True)` 숫자, `status`. message가 없는 결과는 줄을 쓰지 않는다 — usage.jsonl은 공용이라 한 줄이라도 모양이 틀리면 다른 시범의 `month_spend`가 멈춘다, `llm_pilot_common.py:331-349`) → `compare.json`·`compare.md` 원자적으로 쓰기 → 올린 파일 모두 `client.files.delete`(지우지 못한 file_id는 `compare.json`의 `files_not_deleted`에 적는다. 순서: compare 쓰기 → delete → compare 다시 쓰기).
7. **판정**: used = 비교한 PDF 수. used < 8 → HOLD. 분류 일치 ≥ 8 그리고 주제 겹침 ≥ 8 → PASS, 아니면 FAIL. `compare.md` 첫 줄 = `판정: PASS|FAIL|HOLD — 분류 n/used · 주제 m/used · 인용 확인 q/used`. 그 아래 PDF별 표(pid · 정답 · 모델 분류 · 라우트 · 대상 · 일치 · 인용) — 파일 이름은 pid로만 적고 근거 문장은 60자에서 자른다.
8. **마지막 줄**(stdout, ASCII): `llm-pdfcmp <day> <STATUS>`(실행기 정규식 `llm_runner.py:69-70`). STATUS와 종료 코드: SUBMITTED·PENDING·WAITING·PASS·FAIL·HOLD·DONE_ALREADY·NO_BATCH(수거인데 batch.json 없음, 아무것도 안 씀)·DRY_RUN = 0, UNEXPECTED = 1, NO_KEY = 4, BUDGET_STOP = 5, API_ERROR = 7(`llm_pilot_news.py:82-104`의 같은 이름 값과 같게). 실패는 `write_failed(<root>/workspace/outputs/llm/pdfcmp/<day>, STATUS, 이유)`로 `workspace/outputs/llm/pdfcmp/<day>/failed.md` 1줄(`llm_pilot_common.py:369-370`).
9. `--dry-run`: 키·호출·쓰기 없이 PDF 확인 결과(used·skipped)만 출력.
10. 키 값은 어디에도 쓰지 않는다. 오류는 `api_error_label`만 기록.

## 시험 (test_llm_pilot_pdfcmp.py, 가짜 클라이언트·가짜 키·임시 폴더만)
- 임시 폴더에 가짜 PDF 바이트를 두고 `PDFS`를 `mock.patch.object`로 가짜 sha256 표로 바꿔 쓴다(실제 외부자료 폴더를 읽지 않는다).
- 표: 10개 다 있음 → 제출 요청 10개·custom_id P01~P10·document 블록에 citations 켬·모델 고정 / 3개 없음 → HOLD, 업로드·Batch 호출 0 / sha 다름 → SHA_MISMATCH로 빠짐 / `batch.json` 있음 → PENDING / `compare.json` 있음 → 두 단계 DONE_ALREADY / 예산 넘음 → BUDGET_STOP·호출 0 / 키 없음 → NO_KEY.
- 수거: 가짜 결과로 PASS(8·8), FAIL(분류 7), PARSE_FAIL 셈, 모델 다른 결과 버림, 인용 셈, 파일 delete 호출, usage.jsonl 줄 수, 마지막 줄 형식.
- 가짜 키 문자열이 stdout·모든 출력 파일에 없음을 단언.
- 소스 계약: 금지어 없음, 파일이 ASCII.
- 정답표 계약: `PDFS`의 pid·정답·sha256 10행이 이 지시문 표와 같고, 파일 이름 10개를 풀었을 때 이 지시문 표의 이름과 같음(시험 파일도 `\uXXXX`로 적는다).
- usage 줄이 USAGE_KEYS 10개를 모두 갖고 `month_spend`가 그 파일을 예외 없이 읽음. 제출 HOLD 뒤 compare.json·batch.json이 없음. 수거 NO_BATCH. 올린 이름이 `P01.pdf` 꼴.
- Builder 시험 명령(이 글자 그대로): `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot_pdfcmp*.py"`. 전체 시험은 돌리지 않는다(파이프라인이 한다).

## 지켜야 할 것
1. 허용 파일 3개 밖은 손대지 않는다. `llm_pilot_common.py`·`llm_runner.py`·`llm-pilots-schedule.json`·원장·고르기 기록을 고치지 않는다. 기존 시험을 고치지 않는다.
2. 키 값을 읽지 않는다. 비밀(.env*·토큰·계좌번호) 파일을 열지 않는다.
3. 어떤 시범도 켜지 않는다. Windows 작업을 등록·실행·변경하지 않는다. 저장소 루트·실제 외부자료 폴더에 대고 스크립트를 돌리지 않는다(`--dry-run` 포함). pip로 무엇도 설치하지 않는다.
4. 주문·키움·일지·원장·예약·정책·상태와 무관하다. auto_core.py 실행 금지. git은 status·diff·log만. commit·push·병합 없음. `python -c` 쓰지 않음.
5. 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/llm-pdfcmp-report.md
- (a) 만든 함수(파일:행)와 상수 · (b) 시험 이름과 단언 요약 · (c) 시험 결과 마지막 3줄 · `git diff --stat`
- (d) 병합 뒤 사장실이 할 일: 켜기 카드 1번(`pdfcmp-submit`·`pdfcmp-collect` 둘을 한 번에 켜고, PASS/FAIL/HOLD가 나오면 끄기 카드) — 실행은 실행기 13:10 제출·15:10/17:10 수거.
- (e) 확인 필요로 남은 것: Haiku 5.5 생각 토큰이 max_tokens 4096 안에 드는지, Batch 안에서 Files API file_id·문서 인용이 되는지(api-pilots 7절 3), Haiku 5.5가 27쪽·16.6MB PDF(P09)를 받는지, Batch·Files 사용분이 크레딧에서 빠지는지(7절 1).
- 수량·금액·키 값을 적지 않는다. 주문·권한 표지 문자열도 적지 않고 '권한 표지 4종 줄 변경 없음'이라고만 쓴다.

## 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| `workspace/outputs/llm/pdfcmp/compare.json`·`compare.md`(이 작업이 새로 만듦) · `usage.jsonl` 줄 | Windows 작업 InvestmentV2-LLMPilots → `manage-us-stock-strategy/scripts/llm_runner.py:53-54` pdfcmp-submit 13:10 · pdfcmp-collect 15:10/17:10 KST(켜기 파일 `docs/claude/llm-pilots-schedule.json` pdfcmp 두 줄이 켜졌을 때만) | 사람 단계 — 사장실 회사PC 스레드가 `compare.md` 첫 줄을 읽어 판정(설계 원문 `docs/claude/api-pilots-2026-11-06.md:154-164` '소비자 = 이 스레드의 1회 비교 기록') | PASS면 '외부자료 PDF 1차 분류를 API로 옮기는 안' 제안(별도 승인), FAIL이면 질문 닫음(`docs/claude/api-pilots-2026-11-06.md:158` 합격 줄) | 끊김 — 실행기 하루 기록 `workspace/outputs/llm/runner/<날짜>.json` status를 읽는 예약이 없다(`docs/claude/llm-newsca-builder-prompt.md` 연결표와 같은 끊김). 메울 변경: 사장실 결과 모음 예약이 실행기 하루 기록을 읽게 하기 · 승인 경로: 지침 4절 `예약 작업 변경 승인: <이름>`(이 작업 밖). 그 전까지는 켠 날 이 프로젝트가 17:30 KST 뒤 `compare.md`를 직접 읽는다 | 연결(산출) · 알림 끊김(기존과 같음) |

## Judge 확인 항목
1. diff가 허용 파일 3개뿐이다(새 파일 3개). `llm_runner.py`·`llm_pilot_common.py`·켜기 파일·원장·고르기 기록 변경 없음.
2. 정답표 10행의 sha256·정답 분류가 이 지시문 표와 글자 그대로 같다.
3. `compare.json`이 있으면 API 호출이 없다(한 번만). `batch.json`이 있으면 다시 제출하지 않는다. 8개 미만이면 호출 0.
4. 외부자료 폴더는 읽기만 한다(쓰기·이동·삭제 코드 없음). 쓰기는 `workspace/outputs/llm/` 아래뿐이다.
5. 모델 고정(`MODELS["pdfcmp"]`, check_message), 대체 모델·advisor·베타 없음, 월 상한 확인이 업로드 전에 있음, 수거 뒤 올린 파일 delete.
6. 키 값 미출력 시험·금지어 없음·ASCII 소스. 새 실패 0. 보고서 (a)~(e) 있음, 표지 문자열 없음.

```dev-run
{"task_id": "llm-pdfcmp", "class": "general", "builder_model": "opus", "builder_effort": "high", "max_turns": 100, "builder_timeout_min": 60, "allowed_paths": ["manage-us-stock-strategy/scripts/llm_pilot_pdfcmp.py", "manage-us-stock-strategy/tests/test_llm_pilot_pdfcmp.py", "docs/claude/llm-pdfcmp-report.md"], "target_tests": ["test_llm_pilot_pdfcmp*.py"], "commit_message": "feat(llm-pilot): one-time Haiku batch comparison of ten processed external PDFs against the ledger classification, display only (llm-pdfcmp)"}
```
