# dev-run enter-window2 — BLOCKED

- 시각(UTC): 2026-10-20T11:25:07Z → 2026-10-20T11:44:56Z
- 기준 커밋(base): `8f6bdcf6f7314214476dc36c9802956c6dab9f33` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority
- 상태: **BLOCKED** · 재시도: 0
- 테스트: 기준선 Ran 3230 · 실패 30 → 변경 후 Ran None · 새 실패 0 · skipped 3->None · 스키마 감사 PASS->None
- diff_hash: `None`
- Judge 파일 sha256: `None`
- 사유: risk1r GOLDEN 8 keys: 5 change (default, sell, pwr, decide_compare, decide_apply) because the golden hashes whole tickets including enterWindow; prompt says golden change = BLOCKED and test_auto_core_risk1r.py is outside allowed_paths.
- 다음: `see docs/claude/dev-runs/enter-window2.md`

## 바뀐 파일

- (없음)

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/enter-window2/ 의 원본 기록입니다.)
