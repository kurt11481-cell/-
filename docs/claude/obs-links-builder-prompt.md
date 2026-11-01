---
id: obs-links-builder-prompt
title: "docs/claude 자동 목록(INDEX-auto.md)의 파일 칸을 Obsidian이 선으로 잇는 링크로 — obs-links"
date: 2026-11-01
class: "general(일반 변경 — docs/claude/make-index.py 출력 형식만). 개발 큐: Builder Sonnet → 스크립트 판정 → Judge → READY_TO_MERGE면 병합(dc-dev Q1 a)"
source: "사장 결정 카드 'B 설정 + 연결 만들기'(사장실 회사PC 스레드 'Obsidian 트리·그래프 뷰 정리', 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9VeRLPokEe3DUQWwRVS72hC, 2026-11-01 13:05 KST, 계정=사장). 기록 docs/claude/obsidian-tidy-2026-11-01.md"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
weekly_user_touch: "0"
---

## 목표
Obsidian으로 docs/claude를 열면 문서 597개 사이 링크가 9개뿐이라 그래프가 흩어진 점뿐이다. 문서 본문은 고치지 않고(CRLF·해시 보호), 자동 목록 `INDEX-auto.md`의 파일 칸을 마크다운 링크로 바꿔 모든 문서가 목록에 이어지게 한다. Obsidian 그래프는 마크다운 링크 `[이름](이름.md)`도 선으로 그린다.

## 바꿀 내용 (`docs/claude/make-index.py` 만)
1. `docs_index()`의 문서 표 첫 칸을 `name` 대신 `[name](name)`으로 쓴다(예: `| [00-home.md](00-home.md) | ...`). 파일 이름 글자는 그대로 남아 기존 키워드 검색이 계속 된다. 이름에 공백·괄호·`|`·`<`·`>`·`]`가 있으면 `[name](<name>)` 꼴로 쓰고, `|`는 기존 `cell()`처럼 `/`로 바꾼 표시 글자만 쓴다(지금 docs/claude 맨 위 md 이름은 모두 ASCII·공백 없음 — 2026-11-01 확인).
2. `## 하위 폴더` 표: 그 폴더 바로 아래에 `README.md` 또는 `INDEX.md`가 있으면 폴더 칸을 `[폴더/](폴더/README.md)`(README 우선, 없으면 INDEX.md)로 쓴다. 없으면 지금처럼 `폴더/`.
3. 머리말 아래 안내 줄에 한 줄 더한다: `- Obsidian 그래프: 이 목록의 링크로 모든 문서가 이어진다(문서끼리 직접 잇는 선은 아님).`
4. `## 기타 파일` 표, `outputs_index()`·`INDEX-outputs-auto.md` 형식, 정렬, 날짜·id·상태·요약 칸, 머리말(id·type·status·summary), 결정론(같은 입력 = 같은 출력), 쓰는 파일 2개는 그대로 둔다. 새 출력 파일·새 명령 인자 없음.
5. 이 작업에서 `make-index.py`를 실행해 INDEX-auto.md를 다시 만들지 않는다(실행 허용 밖, 병합 뒤 따로 갱신).

## 테스트
새 파일 `manage-us-stock-strategy/tests/test_make_index_links.py`만 만든다. `importlib.util.spec_from_file_location`으로 `docs/claude/make-index.py`를 불러오고(실행 부분은 `__main__` 가드라 실행 안 됨), 모듈의 `DOCS`를 `tempfile.TemporaryDirectory()` 경로로 바꿔 `docs_index()` 문자열만 검사한다(실제 docs/claude에 쓰지 않음, `write()` 호출 금지). 사례:
a. `a-2026-11-01.md`(머리말 있음)·`b.md`(머리말 없음) → 표에 `| [a-2026-11-01.md](a-2026-11-01.md) |`와 `| [b.md](b.md) |`, b의 비고 `머리말 없음` 유지.
b. 공백 든 이름 `c d.md` → `[c d.md](<c d.md>)`.
c. 하위 폴더 `lib/`에 `README.md` → `[lib/](lib/README.md)`, `x/`에 `INDEX.md`만 → `[x/](x/INDEX.md)`, `y/`에 둘 다 없음 → `| y/ |`.
d. `.obsidian` 같은 점 폴더는 지금처럼 표에 없음. `INDEX-auto.md`·`INDEX-outputs-auto.md`는 문서 표에 없음.
e. 같은 입력 두 번 → 같은 문자열. 머리말 첫 6줄(`---`, `id: index-auto-docs`, `type: index`, `status: generated`, summary, `---`) 그대로.
- 실행: 환경 변수 `PYTHONDONTWRITEBYTECODE=1`을 켠 채 `python -B -m unittest discover -s manage-us-stock-strategy/tests -p "test_make_index_links*.py"` **만**. 전체 스위트·기준선 비교는 파이프라인이 한다. `.claude/` 아래 파일을 불러오는 테스트·명령은 실행하지 않는다. 허용 목록 밖 셸 작업(`python docs/claude/make-index.py`, `python -c`, `cd`, `&&`, 해시 계산)은 하지 않는다.

## 지켜야 할 것 (어기면 Judge FAIL)
1. 허용 파일 3개만 바꾼다. docs/claude의 다른 문서·INDEX-auto.md·INDEX-outputs-auto.md·.obsidian은 손대지 않는다. make-index.py 줄바꿈(LF) 유지.
2. 쓰는 파일은 지금처럼 INDEX-auto.md·INDEX-outputs-auto.md 2개뿐. 저장소 다른 곳을 읽는 범위 확대 없음(하위 폴더는 바로 아래 README.md·INDEX.md 존재만 확인).
3. 주문·키움·정책·상태·일지·원장·예약 작업과 무관. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음.
4. 판단이 안 되면 멈추고 보고에 적는다.

## 보고 docs/claude/obs-links-report.md
바뀐 줄(파일:행), 링크 규칙(일반·꺾쇠·하위 폴더), 대상 테스트 결과 마지막 3줄, 남은 위험. 반드시 포함: (a) 병합 뒤 INDEX-auto.md를 한 번 다시 만들어야 그래프에 보인다(지금 INDEX-auto.md는 373개로 실제 맨 위 md 523개보다 낡음 — 갱신 주체 확인 필요) (b) Obsidian이 꺾쇠 링크를 선으로 그리는지는 화면 확인 필요. 이 보고서 문장에는 주문·권한 표지 문자열을 적지 말고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목
1. diff가 make-index.py·새 테스트·보고서뿐이고 make-index.py가 여전히 두 파일만 쓴다.
2. 문서 표 파일 칸이 `[name](name)`(특수 글자면 `[name](<name>)`)이고 파일 이름 글자가 그대로 남는다. 다른 칸·정렬·머리말·INDEX-outputs-auto 형식 무변경.
3. 하위 폴더 링크는 README.md 우선, 없으면 INDEX.md, 둘 다 없으면 기존 표시.
4. 테스트가 임시 폴더만 쓰고 실제 docs/claude에 쓰지 않음. 새 실패 0(파이프라인 checks).
5. 보고 (a)(b) 포함, 표지 없음.

```dev-run
{"task_id": "obs-links", "class": "general", "builder_model": "sonnet", "builder_effort": "high", "max_turns": 60, "builder_timeout_min": 40, "allowed_paths": ["docs/claude/make-index.py", "manage-us-stock-strategy/tests/test_make_index_links.py", "docs/claude/obs-links-report.md"], "target_tests": ["test_make_index_links*.py"], "commit_message": "feat(docs-index): link each doc and subfolder in INDEX-auto.md so Obsidian graph connects them"}
```
