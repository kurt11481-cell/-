# dev-run recon-cap — BLOCKED

- 시각(UTC): 2026-10-27T01:20:09Z → 2026-10-27T01:34:46Z
- 기준 커밋(base): `672f52cee253d3fcdf46ae27b231fec65503d401` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority
- 상태: **BLOCKED** · 재시도: 0
- 테스트: 기준선 Ran 3394 · 실패 31 → 변경 후 Ran None · 새 실패 0 · skipped 3->None · 스키마 감사 PASS->None
- diff_hash: `None`
- Judge 파일 sha256: `None`
- 사유: 지시문 충돌: basis에 outflow_cap_usd를 더하면 기존 테스트 test_withdrawal_matched_by_the_ledger_passes_as_unverified_outflow(142행 dict 전체 비교)가 깨지는데, 지시문은 기존 함수 1개 외 수정 금지·새 실패 0을 요구함
- 다음: `see docs/claude/dev-runs/recon-cap.md`

## 바뀐 파일

- (없음)

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/recon-cap/ 의 원본 기록입니다.)
