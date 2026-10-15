# dev-run t2rc-corefix — BLOCKED

- 시각(UTC): 2026-10-15T02:05:10Z → 2026-10-15T02:36:02Z
- 기준 커밋(base): `8502a0fa93a664d0f748b18720fcd9d566483e62` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority
- 상태: **BLOCKED** · 재시도: 0
- 테스트: 기준선 Ran 3047 · 실패 28 → 변경 후 Ran None · 새 실패 0 · skipped 3->None · 스키마 감사 PASS->None
- diff_hash: `None`
- Judge 파일 sha256: `None`
- 사유: 골든 test_auto_core_risk1r GOLDEN["sell"] 해시가 바뀜(a3a23720… → 07c78134…) — 원인은 항목 4의 ⑤ ok 거르기(SOXX 470으로 MU R-REC1 열림 → 재배치 후보 없음 → 매도 후회표 MU 열 사라짐). 지시문대로 골든은 고치지 않음.
- 다음: `see docs/claude/dev-runs/t2rc-corefix.md`

## 바뀐 파일

- (없음)

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/t2rc-corefix/ 의 원본 기록입니다.)
