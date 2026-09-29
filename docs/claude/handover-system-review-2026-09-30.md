# 인계: 시스템 개발·운용 방향 재검토 (2026-09-30)

새 작업(Cowork)에서 이 문서를 먼저 읽고 시작한다. 권장 설정: **Opus · xhigh**. 출력은 한국어, 결론 먼저, 확인 못 한 수치·사실은 "확인 필요".

## 1. 사용자 요청 (원문 요지)
전반적인 시스템 개발·운용 방향을 창의적·혁신적으로 재검토하는 **프로세스를 설계**하고 **1차 진단**까지 수행.
1. ChatGPT·Codex로 진행한 개발·운용이 비효율적이거나 기능적으로 부족한지, 방향 설정이 잘못돼 엉뚱한 방향으로 진행돼 왔는지
2. 놓친 아이디어
3. 미국주식 현황판 활용 아이디어: https://claude.ai/artifact/K5HqLvCGfQD9AQNbSHVE3Q (Artifact 도구 `read`로 읽기. 웹 fetch 금지)
4. 여러 기업 earnings archive 활용 아이디어: `E:\사업\##금동한\chatgpt_종목분석결과` (현재 하위 폴더는 `JAY_Earnings_Archive_2026-09-25` 하나이며, 이미 연결돼 있음)

## 2. 사용자가 정한 것
- 범위: **재검토 프로세스 설계 + 1차 진단**(현황 증거 수집 + 1~4번 초안). 전체 로드맵 확정은 다음 단계.
- 목표(모두 선택): **투자 판단 품질 · 운영 부담 축소 · 단순화 · 자동화 확대**. 목표끼리 충돌하면(예: 자동화 확대 vs 단순화) 명시하고 우선순위를 사용자에게 묻는다.
- K3 작업(Kiwoom acceptance 6~9단계)은 이 재검토 **뒤로 보류**. 재검토 결과에 따라 K3 방식 자체가 바뀔 수 있음(예: 고정 파일 범위 축소).

## 3. 현재 상태 (2026-09-30 기준, 사실)
- 저장소 `E:\사업\##금동한\코덱스저장소`, 브랜치 `codex/master-recovery-expansion`, HEAD `a453755`(push 안 함). 첫 커밋 2026-08-11, 커밋 약 100개.
- 규모: docs 51개(v2.1~v2.6.13 버전별 migration·validation·high-risk review 문서), scripts 160개, tests 74개 파일(약 1,900건), schemas 159개, policies 30개. `run_manual_portfolio_analysis.py` 2,437줄, `portfolio_decision_dashboard.py` 2,734줄. 미추적 `workspace/outputs` 약 509MB.
- 직전 작업: Kiwoom acceptance 고정 해시 진단과 K2 정리 → `docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md`(진행 기록 포함), `docs/claude/test-run-latest.md`.
- 예약 자동화: Codex automations(`C:\Users\금동한\.codex\automations`의 Pre-Open, Post-Close)이 **별도 런타임 clone** `E:\사업\##금동한\runtime\stock-strategy-scheduled`의 고정 HEAD `41f7b3f…`에서 실행(이 폴더는 연결 안 됨).
- 지침 원본: `E:\사업\##금동한\chatgpt md_주식\`(constitution, 분석 protocol, Codex 라우팅·핸드오프 지침, 2026-09-28 CA K3 작업물).

## 4. 1번 항목 진단에 쓸 관찰 (결론 아님, 근거로만 사용)
- 해시 고정 거버넌스 비용: Kiwoom acceptance가 Hot Path 파일(`run_manual_portfolio_analysis.py`)까지 고정 → Hot Path를 고칠 때마다 K3. 새 acceptance를 만드는 도구도 1회용 하드코딩이라 교착 상태였음.
- 재현성: 원시 해시 증거 파일 중 다수(workspace·stock-strategy-system 추적 파일 343개 중 201개)가 git blob과 바이트가 달라 새 clone·worktree·CI에서 재현되지 않음. 테스트 일부가 미추적 `workspace/outputs`와 저장소 밖 폴더에 의존.
- 운영 증거: 테스트는 통과해도 Windows 전용 실패(PowerShell 5건, pypdf)가 남아 있음. 대시보드·수동 분석 한 커밋에 +1,000줄 단위 변경.
- 프로젝트 지침 7절(NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD, SIMPLE+VERIFIED, Hot Path 짧게)을 평가 기준으로 쓴다.

## 5. 작업 규칙
- 읽기 전용 진단. 코드·정책·포트폴리오 수정 금지, 키움 주문 도구 금지, 커밋은 사용자 승인 후.
- VM에서 git은 `--no-optional-locks -c core.autocrlf=true`. 줄바꿈 일괄 변환 금지.
- 긴 로그·전체 파일은 붙이지 말고 경로·요약만. 여러 파일 조사는 서브에이전트로 분리.
- 결과물은 `docs/claude/`에 저장(프로젝트 문서에는 knowledge 3개만).
