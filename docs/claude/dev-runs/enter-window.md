# dev-run enter-window — BLOCKED

- 시각(UTC): 2026-10-20T10:40:12Z → 2026-10-20T10:49:05Z
- 기준 커밋(base): `422eadf8e59cd4955cc7f4bf2c0c0cc513daa750` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority
- 상태: **BLOCKED** · 재시도: 0
- 테스트: 기준선 Ran 3230 · 실패 30 → 변경 후 Ran None · 새 실패 0 · skipped 3->None · 스키마 감사 PASS->None
- diff_hash: `None`
- Judge 파일 sha256: `None`
- 사유: 범위 초과: 바꿀 문구 둘(:700 새 세션 안내, carried 안내)의 기존 기대값이 allowed_paths 밖인 tests/test_auto_core_preon_fix.py에 있어, 지시대로 고치면 그 파일 테스트 3건이 새로 실패한다.
- 다음: `see docs/claude/dev-runs/enter-window.md`

## 바뀐 파일

- (없음)

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/enter-window/ 의 원본 기록입니다.)
