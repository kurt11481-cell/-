---
id: obs-links2-report
type: report
status: builder-done-tests-not-run
summary: INDEX-auto.md 파일 칸을 마크다운 링크로 바꾸는 make-index.py 변경 보고 (대상 테스트는 실행이 거부되어 못 돌림)
---

# obs-links2 Builder 보고 (2026-11-01)

## 바뀐 곳
- `docs/claude/make-index.py`
  - `md_link(label, target)` 새 함수: target에 공백 또는 `(`·`)`가 있으면 `[label](<target>)`, 아니면 `[label](target)`.
  - `docs_index()`: 문서 표 첫 칸을 `md_link(name, name)`으로 씀(파일 이름 글자는 그대로). 하위 폴더는 바로 아래 `README.md`, 없으면 `INDEX.md`가 있을 때만 `[폴더/](폴더/README.md)` 꼴, 둘 다 없으면 기존 `폴더/`. 머리말 아래 안내 줄 한 줄 추가(`- Obsidian 그래프: ...`).
  - 그대로: 기타 파일 표, `outputs_index()`, 정렬, 날짜·id·상태·요약·비고 칸, 머리말, 쓰는 파일 2개. 줄바꿈은 파일 원래대로(CRLF 170줄 전체, 섞임 없음 — 지시문은 LF라 했으나 실제 파일이 CRLF여서 원래대로 지킴).
- `manage-us-stock-strategy/tests/test_make_index_links2.py` 새 파일: 임시 폴더만 사용, `write()` 호출 없음. 사례 a~e(일반 링크·머리말 없음 비고, 공백·괄호 꺾쇠, 하위 폴더 README/INDEX/없음, 점 폴더·INDEX 파일 제외, 결정론·머리말 첫 6줄). 하위 폴더 이름에 공백이 있는 경우 한 사례 추가(같은 `md_link` 분기).

## 링크 규칙
- 일반: `[name](name)`
- 꺾쇠: 공백·괄호가 있으면 `[name](<name>)`
- 하위 폴더: `README.md` 우선 → `INDEX.md` → 없으면 링크 없이 `폴더/`
- `|`·`<`·`>`·`[`·`]` 등 그 밖의 특수 글자는 지시문대로 처리하지 않음.

## 대상 테스트 결과
실행하지 못함. `python -B -m unittest discover ... -p "test_make_index_links2*.py"` 호출이 승인 화면이 없는 세션에서 자동 거부됨(`2>&1 | tail` 붙인 복합 명령 형태였음). 재시도하지 않음. 파이프라인 checks가 이 테스트를 돌려 확인해야 함(통과 여부 확인 필요).

## 남은 위험
- (a) 병합 뒤 INDEX-auto.md를 한 번 다시 만들어야 그래프에 보인다. 지금 INDEX-auto.md는 373개로 실제 맨 위 md 523개보다 낡음 — 갱신 주체 확인 필요.
- (b) Obsidian이 꺾쇠 링크를 선으로 그리는지는 화면 확인 필요.
- 테스트가 한 번도 실행되지 않았으므로 단언 오류 가능성이 있음(코드는 읽어서 검토만 함).
- 주문·권한 표지: 표지 없음.
