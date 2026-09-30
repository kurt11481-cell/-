# 인계: 손실한도·전략 전면 재검토 (2026-10-01)

새 작업(Cowork)에서 이 문서를 먼저 읽고 시작한다. 권장 설정: **Sonnet · high**(결과 검증·분석). 정책 변경 제안(S5)이나 Judge 단계로 넘어가면 **Opus · xhigh**. 출력은 한국어, 결론 먼저, 한 번에 한 단계, 확인 못 한 수치·사실은 "확인 필요".

## 1. 사용자 요청 (원문 요지)

트레이딩 전략, 정책 기본 방향, 손실한도를 전면 재검토하는 프로세스 수립. 개별종목 레버리지(MVLL)는 한국 규정상 사실상 매수 불가(매도만), 지수 레버리지(SOXL·TQQQ)는 매매 가능. 너무 보수적이지 않은, 레버리지·스윙을 활용한 창의적 전략을 원함. "시장 급락은 매수 찬스이자 자산 증식의 최대 기회"라는 관점. 정책 파일은 검토 중 수정하지 않는다.

## 2. 사용자가 정한 것

- 손실 예산(S1 결정 1): 기준 자산 $28,028.57(9/30 장중 키움 mark, 사용자 확인) 대비 1차 선 −10%($25,226), 최대 선 −20%($22,423).
- 레버리지 상한(S1 결정 2): 1.9배. 단 장기 데이터상 2020-03-16(SOXL −38.6%)이면 하루 만에 최대 선 초과 → 하루 기준 경계는 SOXL 약 1.55배.
- S4 후보 등록·검증 → 게이트 통과 없음, 신호 채택 없음(NO_CHANGE). 결과 병합 커밋 `63c9f20`.
- S4-2(여유 비례 + 변동성 조정, CPV) 사전 등록 검증 착수 요청.
- NBIL은 과거 소량 보유 후 정리 완료(오타 아님). 키움 조회 데이터가 맞음.

## 3. 현재 상태 (2026-10-01)

- 저장소 브랜치 `codex/master-recovery-expansion`, HEAD `6a59328`(S0~S4 문서 커밋). 미커밋: S1 메모 수정, S3b·S4-2 지시문·이 인계 문서.
- S4-2 Builder: worktree `s4-2-cpv`(브랜치 `worktree-s4-2-cpv`). 1단계 기준선(테스트 미통과 314, S4와 동일)과 2단계 계획 승인 완료. Cowork가 명확화 1~12 승인 + 결과 전 추가 A·B·C 지시(지시문 문서 진행 기록 참고). 사용자가 붙여 넣은 뒤 3단계(사전 등록)부터 진행 중일 것.
- 정책·상태 파일 해시(변경 없음): alert_policy.json `184008bd…`, portfolio_state.json `28fd77c5…`.

## 4. 새 세션 첫 작업

1. 사용자가 "Builder 완료, worktree s4-2-cpv, 새 실패 수 N"을 주면 Cowork가 직접 확인한다(붙여넣기 요청 금지).
   - git: `R=$HOME/mnt/코덱스저장소; W=$R/.claude/worktrees/s4-2-cpv; git --no-optional-locks -c core.autocrlf=true --git-dir=$R/.git/worktrees/s4-2-cpv --work-tree=$W status --short` → 새 파일만인지.
   - 해시: 프로토콜 원본·LF sha256이 sidecar·결과 JSON과 같은지, 러너 해시.
   - 재실행: `PYTHONDONTWRITEBYTECODE=1 python3 window_study_soxl_cpv_2026-10-01.py --self-test`, `--run --output-dir $HOME/<임시>`(지원 시) → 결과 JSON·windows CSV가 저장본과 같은지(줄바꿈 정규화).
   - 게이트 H1~H6와 판정, U(2010년 이전 합성) 결과를 먼저 본다(m=2는 2010년 이후를 보고 골랐으므로 U가 유일한 깨끗한 검증).
2. 사용자에게 결론 먼저 보고하고 다음 결정 하나를 묻는다(아래 5절).
3. 병합은 사용자가 Windows 터미널에서: `git merge --no-ff -m "merge: S4-2 CPV window study (worktree-s4-2-cpv <커밋>)" worktree-s4-2-cpv` (Builder 커밋 승인 뒤).

## 5. 남은 결정 (한 번에 하나씩)

- 손실 예산과 레버리지 맞추기: Cowork 추천은 CPV(바닥 −20%, SOXL 비중 = min(63.3%, 2×여유)×변동성 조정). 대안은 1.0배 + 변동성 조절(손실선은 검토용). S4-2 결과로 판단.
- 손실선 행동(결정 3): 앞서 추천한 "1차 A + 최대 D"는 1.9배 고정 위에서는 손실을 확정해 **정정됨**. CPV를 쓰면 행동이 규칙에 포함된다.
- 기준점 재설정·재진입(결정 4), 루트 테제 집중 상한·현금 예비분(결정 5), 종목별 배분 방식(결정 6).
- S2 MVLL 매도 전용 계획(매수 불가, 되살 수 없음)과 현재 2.29배 → 새 상한으로 줄이는 순서.
- 그 뒤 S5 정책 제안(적용 안 함) → S6 Independent Judge(Opus xhigh, 별도 Claude Code 세션) → S7 사용자 승인·적용.

## 6. 핵심 근거 요약

- S0: 현행 손실한도 합계 $11,490(41%) 중 MVLL $7,104. 원가 기준 한도는 수익 종목에 느슨.
- S3·S4: "급락 탈출 → 회복 재진입" 신호는 가짜 신호·반등 놓침으로 수익 급감(S4 C2 CAGR 7.5% vs 기준 34.6%). 변동성 비중조절(C1)이 가장 나았으나 이웃 안정성·표본 부족으로 탈락.
- 1년 안에 −20% 도달 확률(1.9배 보유): 2011~2026 49%, 2021~2026 64%. 1.9배 + A·D 손실선은 2021~2025 시작일 1년 중앙값 −19.3%(손실 확정).
- S3b: 2020~2026은 2010년대보다 변동성·큰 등락일·하루 되돌림(휩쏘)·밤사이 갭 비중이 크고, 급락 후 반등이 빠르다(절반 회복 중앙값 86 → 16거래일). 신호·추세 필터·딱딱한 손절에 불리, 변동성 비중 조절에 상대적으로 유리.

## 7. 작업 규칙과 교훈

- Cowork의 git은 `--no-optional-locks -c core.autocrlf=true` 읽기 전용만. 커밋·병합은 사용자가 Windows 터미널에서, 병합은 `-m`으로 메시지를 넣어 편집기 대기를 피한다.
- 2026-09-30 병합 사고: 첫 병합이 리눅스 형식 색인 기록(uid 1013)을 남긴 비대화형 환경에서 시작돼 빈 MERGE_HEAD로 멈춤(이 대화에서 실행한 것은 아님, 실행 주체 확인 필요). 해결: `git update-index --refresh` → `git merge --abort` → `git merge --no-ff -m ...`.
- 이미 기기에 쓴 문서를 고칠 때는 기기에서 직접 수정한다(클라우드 산출물 재커밋 때 첫 스냅샷이 반영된 오류가 있었음).
- worktree 테스트 기준선 314건(고정 해시·한글 경로·pypdf 등)은 작업과 무관. 전후 수·ID 동일 여부만 본다.
- 가격·계좌 근거는 키움이 우선이고, 과거 검증용 외부 가격(Yahoo·Nasdaq)은 참고용(D/C 등급).

## 8. 문서 목록 (docs/claude)

- `loss-limit-review-s0-dollar-comparison-2026-09-30.md` — 후보 한도 금액 환산
- `loss-limit-review-s1-decisions-2026-09-30.md` — 결정 1·2, S4 입력, Cowork 추천(CPV)
- `loss-limit-review-s3-crash-recovery-signals-2026-09-30.md` — 급락·회복 신호 아이디어·간이 재현
- `loss-limit-review-s3b-market-regime-2026-10-01.md` — 최근 시장 국면 검토
- `s4-signal-walk-forward-builder-prompt-2026-10-01.md`, `s4-builder-report-2026-10-01.md` — S4 지시문·결과(병합됨)
- `s4-2-cpv-builder-prompt-2026-10-01.md` — S4-2 지시문·진행 기록
- 결과 파일: `stock-strategy-system/backtests/SOXL_SIGNAL_WALK_FORWARD_*`, (S4-2 완료 후) `SOXL_CPV_WINDOW_*`

## 9. 새 세션 시작 문구 (붙여넣기용)

"docs/claude/handover-loss-limit-review-2026-10-01.md를 읽고 이어가. S4-2 Builder 완료, worktree s4-2-cpv, 새 실패 수 N" (Builder가 아직 끝나지 않았으면 앞 문장만)
