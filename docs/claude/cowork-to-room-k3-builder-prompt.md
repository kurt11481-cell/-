---
id: cowork-to-room-k3-builder-prompt
title: "대조 확인·일지 기록을 사장실 회사PC 스레드로 + 증거 없으면 propose 거부 — cowork-to-room-k3 Builder"
date: 2026-11-20
class: "K3 수동 경로(Hard safety 확인 장소·대조 기록 경로, CLAUDE.md 보호 경로). 회사PC worktree Builder(Opus) → 별도 읽기 전용 Judge(지시문은 다른 세션이 씀) → 병합은 사장 결정 뒤 사장 PowerShell"
source: "docs/claude/cowork-to-room-k3-proposal-2026-11-20.md(수정안 id cowork-to-room-k3-proposal-2026-11-20, 2판). 승인 = 같은 수정안 '사장 결정' 절의 2026-11-20 13:06:03 KST 카드"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장·백업 쓰기 없음 · .claude 설정 변경 없음"
---

## 목표
수정안 0절 R1~R4를 수정안 2-1·2-2절대로 구현한다. 시작 전에 수정안 전문과 CLAUDE.md를 읽는다. 수정안과 이 지시문이 다르면 수정안이 맞다.

## 바꿀 파일 (이것만)
- CLAUDE.md (25~28행, 29~42행, 116행 — 수정안 2-1절. 다른 행은 손대지 않음)
- manage-us-stock-strategy/scripts/apply_user_confirmed_broker_snapshot.py
- manage-us-stock-strategy/scripts/reconcile_broker_state.py
- manage-us-stock-strategy/scripts/portfolio_review_journal.py
- manage-us-stock-strategy/scripts/validation_common.py (형식·4번째 칸 코드 검사 함수 옮김)
- manage-us-stock-strategy/schemas/portfolio-review-journal.schema.json (description만, enum 불변)
- manage-us-stock-strategy/assets/locales/reconcile-broker-state-ko-KR.json
- manage-us-stock-strategy/references/broker-snapshot-reconciliation.md, references/portfolio-exposure-review.md
- manage-us-stock-strategy/tests/test_auto_core.py (1056~1059행 기대 튜플만), tests/test_reconcile_broker_state.py (propose 도우미에 임시 --journal + 새 시험), tests/test_portfolio_review_journal.py·test_approval_human_check.py (새 시험), 새 시험 파일 tests/test_cowork_to_room_k3.py
그 밖의 파일을 고쳐야 하면 docs/claude/cowork-to-room-k3-BLOCKED.md에 이유를 쓰고 멈춘다.

## 구현 요구
1. `PROJECT_THREAD_USER_DECISION`을 대조 CONFIRMATION_METHODS에 더한다. 문자열 상수는 한 곳에서 정의해 대조·일지가 같이 쓴다.
2. validation_common.py에 (a) 4칸 형식 검사(지금 project_thread_message_valid와 같은 규칙) (b) 코드가 4번째 칸(`split('|', 3)[3]`)에 있는지 검사를 둔다. portfolio_review_journal.py의 project_thread_message_valid는 이 함수를 쓰도록 바꾸되 이름·동작은 유지(카드 항목은 코드 요구 추가 없음).
3. 대조 라이브러리(apply_confirmed, 키움 제안 분기 277~281행): 방법이 PROJECT_THREAD면 (a)·(b)를 라이브러리 안에서 검사. 기존 메시지 전체 코드 검사는 COWORK·USER_TERMINAL에 그대로.
4. reconcile_broker_state.py: 349행 user_message 필수를 PROJECT_THREAD에도, 362행 코드 대체는 PROJECT_THREAD에 쓰지 않음. 머리말·help 문구.
5. R3: propose에 `--journal`(기본 REPO_ROOT/stock-strategy-system/decision_journal.json). 키움 조회 전에 journal_view(load_journal())로 활성 판정 — MISSING = 활성 없음, CORRUPT·읽기 오류 = 거부, 활성 + 증거 없음 = `CASH_FLOW_EVIDENCE_REQUIRED_AFTER_ACTIVATION` 거부(종료 2, 출력 폴더·상태 불변). auto 경로는 바꾸지 않는다.
6. 일지: PROJECT_THREAD 허용 = 카드 2종 + line_review_completed·peak_review_card_completed. 새 두 종류는 (b) 필수(apply 556~558행과 체인 재검사 187~191행 둘 다). s5_activation은 계속 PROJECT_THREAD_ENTRY_TYPE_INVALID.
7. 문구: 로캘 5·6·51행 + R3 거부 문구, 참조 문서(수정안 2-2 표 마지막 두 행 — 159~161행 사실 정정 포함), 스키마 description.
8. CLAUDE.md: 수정안 2-1절의 뜻을 영어로. 대조는 사장 직접 입력만(카드 탭 제외), 스레드는 PROJECT_THREAD만, 4칸, 바로 앞 제안·같은 날·1회, 확인이 아닌 것 목록, R4 탈출구 한 줄. 줄바꿈은 CRLF 유지(일괄 변환 금지).

## 시험
수정안 4절 T1~T20을 새 파일(tests/test_cowork_to_room_k3.py)에. 시험은 임시 폴더의 상태·일지·원장만 쓴다(실제 stock-strategy-system 파일을 읽거나 쓰지 않음 — R3 시험도 임시 --journal). 작업 전·뒤 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"` 실패 수를 보고(auto_core.py 이름이 든 명령이 막히면 -p "test_auto_core*"를 따로). 새 실패 0.

## 보고 (docs/claude/cowork-to-room-k3-report.md)
바뀐 줄(파일:행), 시험 결과(기준선·이후 실패 수, 새 시험 이름과 T번호 대응), 기존 단언 변경 목록과 이유, 수정안 9절 확인 필요 3개 + USER_TERMINAL 대화형 프로세스 통과 여부를 그대로 옮김, 남은 위험. 끝에 커밋 해시와 브랜치 이름.

## 금지
주문·정정·취소, 키움 도구 호출, reconcile apply·propose·auto 실행, 일지 apply, auto_core.py 실행, .env·토큰·계좌번호 읽기, 실제 정책·상태·원장·일지·백업 쓰기, .claude 설정 수정, 기존 시험 약화(기대 튜플 1곳·도우미 --journal 외).
