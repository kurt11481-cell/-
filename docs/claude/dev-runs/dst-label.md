# dev-run dst-label — BLOCKED

- 시각(UTC): 2026-11-03T02:05:12Z → 2026-11-03T02:30:21Z
- 기준 커밋(base): `4da584b864e66d9d36b21e71752d47954b624bb8` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority
- 상태: **BLOCKED** · 재시도: 1
- 테스트: 기준선 Ran 3513 · 실패 13 → 변경 후 Ran None · 새 실패 0 · skipped 3->None · 스키마 감사 PASS->None
- diff_hash: `None`
- Judge 파일 sha256: `None`
- 사유: 새 실패 2건은 허용 파일 밖(manage-us-stock-strategy/tests/test_score_spy_history.py)의 -05:00 미확인 전제 픽스처라 allowed_paths 안에서는 고칠 수 없음 — 범위 확장 판단 필요.
- 다음: `see docs/claude/dev-runs/dst-label.md`

## 바뀐 파일

- (없음)

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/dst-label/ 의 원본 기록입니다.)
