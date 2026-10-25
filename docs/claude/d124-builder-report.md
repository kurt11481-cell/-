# d124 Builder 보고서 — D1·D2·D4 CLAUDE.md 문구 반영 (수동 경로)

- 작성: 2026-10-25, Claude Code Builder 세션 (워크트리 `d124-approval-venue`, 브랜치 `worktree-d124-approval-venue`, 기준 커밋 b6a83e2)
- 지시문: docs/claude/d124-builder-prompt.md (원 저장소 쪽 파일)
- 초안: docs/claude/d1-d2-d4-change-draft.md (변경 1~3, 경계, Q1 답 = 아니오)
- 사장 승인 근거(초안에 적힌 내용): "D4 b 승인, D2 승인, D1 a 승인" (2026-10-25 08:15Z), 변경 1 추가 줄 수락 (08:18Z), Q1 = 아니오 (08:17Z). 이 세션에서는 사장 메시지 "d124-builder-prompt.md 를 읽고 그대로 실행해"만 받았다.
- 커밋·푸시·병합: 하지 않음.

## 바뀐 파일
- `CLAUDE.md` 한 파일만 (+8 / -1). 이 보고서는 새 파일.
- sha256: 변경 전 `8c15ce670badacdcf99153d3e671d8f86bbd1440b0e42b3356155ea742a56b4d` → 변경 후 `a94fed66fb9f33fb47819acacd53ed9098628d84363ebde3c04392c9d495983e`
- 줄바꿈: CRLF 유지 (스크립트로 바이트 단위 치환, 모든 `\n`이 `\r\n`인지 확인). 일괄 변환 없음.

## 바뀐 줄 (변경 후 줄 번호)

| 변경 | 위치 | 줄 | 내용 |
|---|---|---|---|
| 변경 1 (D4 b) | Change classes, Authority/limit change 항목 끝 | 63~65 (추가) | 사장 본인이 대화형 Claude Code 프로젝트 스레드에 직접 입력한 메시지(from=human trust=principal)도 "current conversation"으로 인정. 중계 인용·버튼·카드·예약 턴은 승인 아님. 승인 1건 = 바로 앞 제안 1건, 같은 날, 1회. |
| 변경 1 추가 줄 (08:18Z 수락) | 같은 항목 | 66~67 (추가) | 사장 승인 뒤 대화형 Claude Code 프로젝트 스레드도 수동 경로 Builder(워크트리)와 별도 읽기 전용 Judge 세션을 시작할 수 있음. 병합은 사장 PowerShell 한 줄을 기다림. |
| 변경 2 (D2) | 같은 항목 | 68~69 (추가) | 스크립트가 필요한 승인의 공식 경로 = 사장이 자기 터미널에 치는 PowerShell 한 줄. 세션은 정확한 줄(`dev-merge.ps1 <id> -ApproveAuthority` 또는 `--confirmed-via USER_TERMINAL`)을 준다. |
| 변경 3 (D1) | Session hygiene, 관제판 줄 | 125 (수정, 변경 전 118) | 관제판 갱신 주체에 "사장과 대화 중인 사장실 회사PC 스레드(대화형 Claude Code)" 추가. 제외 목록 "Claude Code·Judge·예약 작업" → "Judge·예약 작업·하위 에이전트". |

## 확인
- **Hard safety 절 변경 없음.** 18~44행(`## Hard safety` ~ `## Kiwoom query rules` 직전) sha256이 HEAD와 작업본에서 같음: `7d60922e76a9fb08a2996bcfae8aff455807cd0c04249645ea78d0491fee8232`. diff 덩어리는 63행 이후와 125행뿐.
  - "Claude Code, Codex, scheduled LLM tasks and Judge sessions never run apply", "Claude Code, Codex and Judge sessions never apply or edit the journal"은 그대로 (Q1 = 아니오).
- 권한(주문·한도·예산·주문 단계·승인 상품·대사 불변식·킬 스위치) 확대 표현 없음. 바뀐 것은 "누가·어디서 승인을 받는가"와 관제판 갱신 주체뿐.
- 승인 인정 조건은 초안대로만: 사장 본인 직접 입력, 바로 앞 제안 1건, 같은 날, 1회.
- 병합은 계속 사장 PowerShell 한 줄. Manual route의 "Claude Code sessions never run dev-run/dev-merge/dev-queue"(작업본 122행)는 초안의 "같이 정리할 충돌"대로 그대로 둠.

## Builder 해석 (Judge 확인 대상)
1. 지시문의 "변경 1(추가 문장 2개)"은 초안 변경 1의 두 추가분(본문 블록 + 08:18Z 추가 줄)으로 읽었다. 본문 블록은 문장 3개다.
2. 위치: 초안이 "항목 끝"이라고 해서 항목 마지막 문장 "(never from an older record or memory)." 뒤에 변경 1 → 변경 1 추가 줄 → 변경 2 순서로 넣었다. 그래서 "current conversation" 확장은 항목 안의 두 언급(Cowork Builder 시작, -ApproveAuthority) 모두에 걸린다.
3. 변경 3: 초안의 현행 인용은 "…"로 줄여져 있어서, 줄인 부분("(완료·시작·새 재개 조건)", "docs/claude/" 경로, "관제판의", "변화가 없으면 갱신하지 않는다.")은 남기고 주체와 제외 목록만 바꿨다. 초안 수정문을 글자 그대로 쓰면 이 부분이 빠진다.
4. 기존 줄 폭(약 120자, 들여쓰기 2칸 연속 줄)에 맞춰 줄을 나눴다. 단어는 초안과 같다.

## 남은 것 (미해결, 이번 범위 밖)
- 변경 3의 "확인 필요"(초안): 대화형 Claude Code 스레드가 관제판 HTML(Artifact)을 실제로 갱신할 수 있는지는 확인하지 않았다. 안 되면 초안대로 docs/claude 결정 문서 기록으로 대체.
- Session hygiene의 Manual route 줄(작업본 121행 "Cowork may start both on the PC via Desktop Commander after the user's approval (dc-dev Q2 a)")은 Cowork만 적혀 있다. 변경 1 추가 줄과 충돌하지는 않지만(그 줄은 Cowork 허용, 새 줄은 Claude Code 스레드 허용) 같은 내용을 맞추는 것은 초안 절차 3(D5·D8 묶음)으로 미룬다.
- 변경 1 추가 줄은 병합 전에는 효력이 없다(초안). 이번 Builder도 사장이 연 세션이다.

## 추가 수정 (2026-10-25, 사장 지시: 63행 앞에 "In this item, " 붙이기, 다른 줄은 그대로)
- 63행: "The current conversation may also be …" → "In this item, the current conversation may also be …". 다른 줄은 바꾸지 않음. CRLF 유지(바이트 단위 치환, `\n` 개수 = `\r\n` 개수).
- CLAUDE.md sha256: `a94fed66fb9f33fb47819acacd53ed9098628d84363ebde3c04392c9d495983e` → `1feb18f5ee10bb5d4e16a5e3a76f6aca4c58cde80e7d0a1fe7d2da62790c8159`
- Hard safety 절(18~44행) 다시 계산: `sed -n '18,44p' CLAUDE.md | sha256sum` = `7d60922e76a9fb08a2996bcfae8aff455807cd0c04249645ea78d0491fee8232`, HEAD(`git show HEAD:CLAUDE.md | sed -n '18,44p' | sha256sum`)와 같음. 변경 없음.
- `git diff -U0` 덩어리: 63~69행 추가, 125행 수정. 이 두 곳 말고는 없음.

## 테스트
- 문서(CLAUDE.md)만 바뀌어서 단위 테스트 대상 없음. 실행하지 않음.

## 연결
- 소비자: 독립 Judge 세션(읽기 전용, Opus) → 사장 병합 결정. 병합 뒤 지침 v1.6 2절·4절 정리(D5·D8)가 이 결과를 읽는다.
