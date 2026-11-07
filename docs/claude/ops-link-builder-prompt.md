---
id: ops-link-builder-prompt
title: "ops-link-1107 A — CLAUDE.md 111행·Judge G9·README 18행 연결표 (K3 수동 경로 Builder)"
date: 2026-11-07
class: "보호 경로(CLAUDE.md·tools/·test_dev_pipeline) 비권한 변경 — K3 수동 경로. 회사PC worktree Builder(Opus) → 별도 읽기 전용 Judge → 병합은 사장 PowerShell 한 줄"
source: "docs/claude/ops-linkage-guideline-2026-11-07.md 5절 (참고) A·6절 선택 2·기록 절 · 사장 직접 입력 2026-11-07 12:01:27 KST 'A, B, C 전부 다 넣어'(cmsg_0137MRzn9nuDvvQmVxm6WeX9YWQozN6PkxUjXViJm7R6YX — S4 착수 직접 입력 갈음)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음 · 권한·한도 변경 없음"
---

## 개정 기록
- 2차(2026-11-07 12:3x KST): 헌법 1.5.0 독립 재검토(검토자 2 발견 10·11)를 받아 CLAUDE.md 111행에 두 곳을 보탰다 — 급한 줄이기·사건 카드는 표 때문에 늦추지 않음, 'alert kind'를 '새 종류의 시장 징후 알림(헌법 §2-1 3항)'으로 좁힘, 기존 사용자 결정은 인용하고 다시 묻지 않음. 1차 목표 해시 fa55fb19…는 폐기. 같은 worktree의 CLAUDE.md 한 줄만 이 스레드가 바이트 치환으로 바꿨고(다른 세 파일·시험 그대로), Judge는 처음부터 다시 본다.

## 선행 조건 (하나라도 없으면 시작하지 않고 보고)
- 본 저장소 원본 `E:\사업\##금동한\코덱스저장소\docs\claude\ops-linkage-guideline-2026-11-07.md`의 '## 기록' 절에 "사장 결정 2026-11-07 12:01:27 KST" 줄이 있다(worktree 사본은 옛 커밋이라 없을 수 있다 — 원본에서 본다).
- 메인 체크아웃의 아래 4개 파일 sha256이 '바꾸기 전' 값과 같다.

## 작업 위치
새 worktree `ops-link`(경로 `.claude/worktrees/ops-link`, 브랜치 `worktree-ops-link`, 기준 = 시작 때 메인 HEAD). 모델 Opus. 기준 커밋 전체 해시를 보고서에 적는다.

## 바꿀 파일 (이 5개만)

| 파일 | 바꾸기 전 sha256 | 바꾼 뒤 sha256 | 줄 수 |
|---|---|---|---|
| CLAUDE.md | fcf6d25bc6e5888a133eedc7a4d039fe4821b5a86d02ae73e319d381100c27b2 | d2f22333b02712d64303ff6348941018b9dbae1536d17a4998e1048003ca4cfc (2차) | 138 → 138 |
| tools/dev_pipeline/judge-prompt.md | 877d34e27335bdc678e8ba2e707bca86bc913ec491cd7b216129c3c586632b6d | 768ee9aa82f6a67cabee9cb8074a3ad973c47a8ba607e81c5adaf78461b463c0 | 38 → 39 |
| tools/dev_pipeline/README.md | 5601c19a4ead5d41b861c69b83dfa129e7c7f3297e1b3eae6ec5d5a60db74b1d | 103a55cf2773787780884ce8eddfa54c412170211003553507b18969591cfa26 | 94 → 94 |
| manage-us-stock-strategy/tests/test_dev_pipeline.py | 5ec97a391eed25aa8e1bf956d17513cc7b259bc8278077ef8957eed4be994a47 | daa31643a922748d58dca6d2f3451e60faf53d6b825316c24941206a29b6ae8a | 1918 → 1924 |
| docs/claude/ops-link-report.md (새 파일) | — | — | 보고 |

해시는 작업 폴더 파일 바이트 그대로 잰다(`python -c "import hashlib,sys;[print(hashlib.sha256(open(p,'rb').read()).hexdigest(),p) for p in sys.argv[1:]]" <파일들>`). Git Bash의 sed|sha256sum은 CR을 떼어 다른 값이 나온다.

## 바꿀 내용 (바이트 단위 — 네 파일 모두 줄 끝 CRLF 유지)

1. CLAUDE.md 111행(지금 `- Every analysis/inquiry/discovery output must be linked: …`로 시작하는 한 줄) 전체를 아래 한 줄로 바꾼다(ASCII).
~~~text
- Every analysis/inquiry/discovery output, new feature and scheduled-task change must be linked through to company action (user standing rules 2026-10-05 and 2026-11-07, ops-link-1107): write results where other tasks read them, name at least one consumer, and attach to the design or proposal the linkage table of docs/claude/analysis-linkage-map-2026-10-05.md section 1 item 8, with cells 2, 3 and 5 cited by file:line or trigger id. A cell that cannot be cited is a break, shown with the change and approval that close it; 'intentionally none' needs a user decision that chose it beside alternatives (cite an existing one rather than asking again). Urgent reduce or incident cards are not delayed for it: post the card first and attach the table the same day. Design/proposal sessions only (Cowork, project threads, interactive Claude Code); scheduled-task runs, Builder, Judge and subagents keep their own contracts. Adds no authority or trading rule; a new kind of market-signal alert still needs its own approval (constitution section 2-1 item 3).
~~~
2. tools/dev_pipeline/judge-prompt.md 24행(`- G8 …`) 바로 뒤에 아래 한 줄을 넣는다(25행이 된다).
~~~text
- G9 연결표(docs/claude/analysis-linkage-map-2026-10-05.md 1절 8번): task-prompt.md에 `## 연결표` 절이 있으면 ②(만드는 주체·시각)·③(읽는 점검)·⑤(끊기면 누가 아나) 칸이 원문 위치(파일:줄 또는 예약 trig id)나 '끊김(…)'으로 적혔나, 파일:줄이면 그 줄을 Read해(diff 안이면 diff 기준) 칸 내용과 맞나(trig id는 `trig_`로 시작하는지만). 절이 없는데 이 diff가 새 산출(새 출력 파일·알림·화면 칸·예약·점검 결과 — 테스트·보고 파일 제외)을 만들면 FAIL, 새 산출이 없으면 "해당 없음". 지시문 머리말 date가 2026-11-07 이하인 지시문(전환 전)도 "해당 없음".
~~~
3. tools/dev_pipeline/README.md 18행(`- 본문: 목표, 바꿀 내용, 테스트, 보고 위치, 그리고 …`) 전체를 아래 한 줄로 바꾼다.
~~~text
- 본문: 목표, 바꿀 내용, 테스트, 보고 위치, `## 연결표`(새 산출이 있을 때 — docs/claude/analysis-linkage-map-2026-10-05.md 1절 8번 6칸, Judge가 G9로 본다), 그리고 `## Judge 확인 항목`(Judge가 G8로 하나씩 본다).
~~~
4. manage-us-stock-strategy/tests/test_dev_pipeline.py: `def test_docs_lines_n2_and_id_length` 메서드 끝 빈 줄 다음, `    def test_docs_commit_runner_keeps_commit_docs_safety(self):` 바로 앞(지금 1691행)에 아래 6줄(마지막 줄은 빈 줄)을 넣는다.
~~~text
    def test_docs_ops_link_linkage_table(self):
        judge = (PIPELINE / "judge-prompt.md").read_text(encoding="utf-8")
        self.assertIn("- G9 연결표(docs/claude/analysis-linkage-map-2026-10-05.md 1절 8번)", judge)
        readme = (PIPELINE / "README.md").read_text(encoding="utf-8")
        self.assertIn("`## 연결표`(새 산출이 있을 때", readme)

~~~

방법: python으로 `open(p,'rb')` → `split(b'\n')` → 해당 줄만 바꾸거나 넣고, 새 줄 끝에도 `b'\r'`을 붙여 `b'\n'.join`으로 쓴다. 텍스트 모드·편집기·일괄 줄바꿈 변환 금지. 끝나면 네 파일 sha256이 위 '바꾼 뒤' 값과 정확히 같아야 한다. 하나라도 다르면 더 고치지 말고 worktree 루트에 BLOCKED.md(첫 줄 = 이유, 다음 줄 = 잰 해시)를 쓰고 멈춘다.

CLAUDE.md Hard safety 절(18~53행, `python -c "import hashlib;L=open('CLAUDE.md','rb').read().split(b'\n');print(hashlib.sha256(b'\n'.join(L[17:53])+b'\n').hexdigest())"` = 56db42e87ed8f99d385d1243264ce53035cb4bd73c9e6a8d95a0ddd88ff53057)이 바꾸기 전후 같은지 재서 적는다.

## 시험
- 이 한 줄만 글자 그대로: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`
- 전체 스위트는 돌리지 않는다.

## 지켜야 할 것
- 위 5개 밖 tracked 파일은 바꾸지 않는다(authority-paths.txt·devpipe.py·dev-run/dev-merge/dev-queue/commit-docs·.claude 설정·정책·상태·docs/claude 다른 문서 포함).
- git은 status·diff·log·rev-parse와 worktree 만들기만. commit·push·merge·reset 금지.
- 주문·키움·일지·원장·예약과 무관하다. auto_core.py·kiwoomcli 실행 금지. 비밀(.env*·토큰·계좌번호)을 읽지 않는다.
- 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/ops-link-report.md (worktree 안)
- (a) 기준 커밋 전체 해시 · worktree 경로 · 브랜치
- (b) 네 파일 바꾸기 전·뒤 sha256(전체 64자)과 줄 수, CRLF 확인(`\r\n` 수 = `\n` 수)
- (c) CLAUDE.md Hard safety 18~53행 해시 전후
- (d) `git diff --stat`과 `git diff -U0`의 바뀐 줄 번호
- (e) 시험 결과 마지막 3줄
- (f) `git status --short`

수량·금액·주문 표지 문자열은 적지 않는다("표지 없음").

## 끝나면
사장에게 한국어 3줄: 바뀐 곳, 네 해시 일치 여부와 시험 결과, Judge 지시문 위치(docs/claude/ops-link-judge-prompt.md).

## 연결표 (analysis-linkage-map 1절 8번 — 이 변경 자체)

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| CLAUDE.md 111행 새 문장 | 병합 뒤 설계·제안 세션이 시작 때 읽음(CLAUDE.md 자동 로드) | CLAUDE.md 111행 → docs/claude/analysis-linkage-map-2026-10-05.md 1절 8번(29~37행) | 설계 문서에 연결표 첨부, 끊김은 메울 승인과 같은 제안에 | 내장 재검토 L3(review-stability-2026-10-13.md 72행) · 4주 측정(ops-linkage-guideline 7절, 관제판 작업) | 연결(병합 뒤) |
| judge-prompt.md G9 | 개발 큐 dev-run의 헤드리스 Judge — 기준 커밋의 judge-prompt.md를 받음(tools/dev_pipeline/devpipe.py 1768행 base_blob) | judge-prompt.md 25행 G9 | 연결표 없이 새 산출을 만드는 개발 작업은 Judge FAIL → 지시문 보완 뒤 다시 | dev-run 결과 workspace/outputs/dev-runs/LATEST.json · docs/claude/dev-runs/<id>.md(Judge FAIL 항목) | 연결(병합 뒤 기준 커밋부터) |
| README.md 18행 | 지시문을 쓰는 세션(Cowork·사장실 스레드) | tools/dev_pipeline/README.md 18행 | 지시문에 '## 연결표' 절을 넣음 | Judge G9 FAIL(위 줄) | 연결(병합 뒤) |
