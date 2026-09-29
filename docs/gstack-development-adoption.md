# 투자_V2 개발 검토 절차 도입

도입일: 2026-09-22  
적용 방식: **프로젝트 안에서 명시적으로 요청한 개발 검토에 적용**

gstack의 설계 검토·변경 검토·오류 조사 방법을 투자_V2 지침에 맞게
적용했다. 기존 AGENTS.md가 필요한 참조 문서를 연결한다.
Bun이나 gstack 실행 도구를 설치할 필요 없이 사용할 수 있다.

## 사용 방법

이 프로젝트의 작업에서 목적과 대상을 말하면 해당 절차를 사용한다.
특별한 명령어나 매 단계의 재승인은 필요하지 않다.

| 요청 | 적용 절차 | 결과 |
|---|---|---|
| “이 투자_V2 개발 계획의 범위와 검증 방법을 검토해 줘.” | [설계 검토](../manage-us-stock-strategy/references/development-plan-review.md) | 필요한 수정·검증·복구 계획 |
| “이번 작업에서 변경한 파일만 읽기 전용으로 검토해 줘.” | [변경 검토](../manage-us-stock-strategy/references/development-change-review.md) | 근거가 있는 결함과 검증 한계 |
| “이 오류 로그의 원인을 분석해 줘.” | [오류 조사](../manage-us-stock-strategy/references/development-incident-analysis.md) | 원인·근거·확인할 사항 |
| “원인을 확인하고 승인된 범위에서 수정·검증해 줘.” | 오류 조사 후 기존 Builder 절차 | 최소 수정과 실제 검증 결과 |

종목 분석이나 일반적인 작은 수정에 새로운 검토 단계를 일괄 추가하지 않는다.
읽기 전용 검토는 직접 수정하지 않으며, 이미 수정까지 요청한 작업은
기존 권한 범위에서 Builder가 계속 수행한다.

## 적용 범위와 한계

- 세 가지 참조 문서와 프로젝트 내 연결만 도입한다.
- 기존 투자 판단·검증기·정책·계좌·자동화의 소유권을 유지한다.
- 기존 미커밋 변경과 이번 후보를 구분한다.
- 읽기 전용 검토의 산출물과 임시 파일은 보호 대상 저장소 밖에 둔다.
- gstack의 review 자동 수정, ship·autoplan·업데이트·외부 AI 호출을 실행하지 않는다.
- gstack의 careful·freeze를 Codex의 실제 권한 제한으로 간주하지 않는다.

이 도입은 **프로젝트 개발 절차의 적용**이다. 사용자 전역 gstack 설치,
새 slash 명령 등록, 운영 Skill 배포, 투자 정책 승인 또는 운영 승격을
의미하지 않는다. 전역 설치본만 사용하는 다른 프로젝트에는 적용되지 않는다.

## 유지관리와 복구

출처·버전·차용 범위·MIT 고지는
[gstack-NOTICE.md](../manage-us-stock-strategy/references/gstack-NOTICE.md)에 보존한다.
업데이트는 필요한 부분의 변경을 검토해 수동 반영한다.

사용을 해제하려면 AGENTS.md의 “Development review procedures” 절에 있는
명시적 연결만 제거한다. 관련 없는 AGENTS.md 내용이나 기존 작업을
되돌리지 않는다. 참조 문서는 이후 사용처가 없는지 확인한 뒤 제거할 수 있다.
SKILL.md와 승인 정책을 자동으로 다시 쓰는 복구 작업은 필요하지 않다.

## 검증 기록

이번 도입의 검증 결과와 변경 범위는
[도입 완료 기록](../workspace/outputs/gstack-development-adoption-20260922/implementation-report-ko.md)에 기록한다.
행동 점검과 실제 두 개발 작업에서의 장기 사용 효과를 구분하며,
문서 정합성이나 설치 검증을 투자 성과의 증거로 표시하지 않는다.
