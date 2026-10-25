# dev-run t2rc-eq-none — BLOCKED

- 시각(UTC): 2026-10-25T12:05:12Z → 2026-10-25T12:15:37Z
- 기준 커밋(base): `42510be5502c5674b108b5d113483c88e87585d7` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **BLOCKED** · 재시도: 0
- 테스트: 기준선 Ran 3353 · 실패 31 → 변경 후 Ran None · 새 실패 0 · skipped 3->None · 스키마 감사 PASS->None
- diff_hash: `None`
- Judge 파일 sha256: `None`
- 사유: oracle 해시 고정 비교가 있어 docs/claude/t2rc-oracle.py를 바꾸면 InvestmentV2-T2rcCheck가 ORACLE_SHA_MISMATCH로 중단된다. 지시문 "하지 않는 것" 3항에 따라 파일을 바꾸지 않고 멈춘다.
- 다음: `see docs/claude/dev-runs/t2rc-eq-none.md`

## 바뀐 파일

- (없음)

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/t2rc-eq-none/ 의 원본 기록입니다.)
