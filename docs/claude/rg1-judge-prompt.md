# Judge 지시문: 10-13 RREC:RG1 CORE_BUG 해소 판정 (t2-gate REMOVE-v2 조건 3)

너는 독립 Judge다. 파일을 고치지 않는다(Read·Grep·Glob만). 커밋·푸시·병합 안 함. 비밀(.env*, 토큰, 계좌번호)·키움 도구 금지. 보고는 한국어.

## 질문
docs/claude/redesign-t2-compare-explained.json의 2026-10-13 `RREC:RG1`(verdict CORE_BUG)이 t2-gate REMOVE-v2 조건 3("고친 커밋이 병합되고 그 SHA가 적혀야 해소")에 따라 **해소**됐는가?
비서실 주장(docs/claude/roadmap-fix-decisions-2026-10-26.md 1-3절): 73e18b4(t2-equity-cash, 총자산 현금 → EV4 원인 제거) + da5d85e(cmp-fix3, 연구 기록 공백으로 생긴 RG1 unk를 사전 등록 B4로 분류).
2차 Judge(저장소 루트 t2-gate-judge-2.txt, 문구 d)는 "10-13 RREC:RG1은 조건 3에 걸려 판정을 막는다"고 했다.

## 읽을 원문
- docs/claude/redesign-t2-compare-explained.json — 2026-10-13 RREC:RG1 항목 note 전체
- docs/claude/roadmap-fix-decisions-2026-10-26.md 1-1·1-2·1-3절
- t2-gate-judge-2.txt (문구 d와 조건 3 관련 부분)
- 두 수정의 기록: docs/claude/t2-equity-cash-*.md(빌더 보고·Judge 보고), docs/claude/dev-runs/cmp-fix3.md, docs/claude/cmp-fix3-builder-prompt.md. 그리고 현행 코드 manage-us-stock-strategy/scripts/auto_core_decide.py(총자산 현금)·auto_core_compare.py(rg1_coverage) — Bash가 없으니 git show는 쓰지 않는다
- docs/claude/t2-rc-preregistration-2026-10-14.md (B4·CORE_BUG·24행 초기화 규칙)
- 필요하면 workspace/outputs/auto-core/2026-10-1*/compare.json 의 RREC:RG1

## 확인 항목 (각각 PASS/FAIL + 원문 행)
1. RG1 차이의 원인이 둘(총자산 현금 EV4, 연구 기록 공백 unk)로 맞게 나뉘는가.
2. 원인 1은 73e18b4로 코어에서 고쳐졌는가(코드 근거).
3. 원인 2는 코어 결함인가, 아니면 입력(연구 기록) 공백이라 da5d85e의 B4 분류가 "해소"로 인정되는가. 분류 변경이 차이를 숨기는 완화라면 FAIL.
4. 이후 비교일(10-17 이후 compare.json)에 같은 RG1 차이가 다시 나오면 해소 아님.

## 출력
마지막 줄 한 줄: `VERDICT: RESOLVED` 또는 `VERDICT: NOT_RESOLVED — <이유 한 줄, 필요한 수정>`.
