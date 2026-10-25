# Builder 지시문: D6·D3·D11·D12 (수동 경로)

사장 승인: 이 스레드에 직접 입력 "D5, D8, D6, D3, D11, D12 승인" (2026-10-25 08:46Z), 지시문 내용 확인 "확인" (08:54Z).
D5·D8(프로젝트 지침)은 이 묶음이 아니다. 근거: docs/claude/operating-diagnosis-2026-10-25.md 7-2, 9-2, 9-3, 10절.
작업 위치: 이 워크트리(기준 bb11f04). 커밋·푸시·병합은 하지 않는다. 줄바꿈 CRLF 유지, 일괄 변환 금지.

## A. CLAUDE.md — 아래 7곳만 바꾼다 (줄 번호 말고 문구로 찾는다)
1. 삭제: Session hygiene의 "At task start, state the recommended model/effort in one line: ..." 문장만.
   같은 항목의 "Ask the user to restart only when authority/limit or Judge work runs on a non-Opus model", "Never suggest switching model mid-session", "Effort may change mid-session ..." 문장은 남긴다(항목 머리말이 지워져 문장이 어색해지면 "- Model and effort:" 정도의 머리말만 붙인다).
2. 삭제: "- When the topic changes, tell the user to run /clear; ..." 항목 전체.
3. 삭제: "- Talk to the user in Korean, one step at a time, giving the exact command to type." 항목 전체.
4. 문구: Goal 절 "Read-only work Cowork can do itself is done, not handed to the user." -> "Read-only work the session can do itself is done, not handed to the user."
5. 문구(Hard safety 절 안, 단어 치환만): "A Cowork session that changes or accepts a card updates" -> "An interactive session that changes or accepts a card updates". 같은 절의 다른 글자는 한 글자도 바꾸지 않는다.
6. 문구: Touch budget 항목에서 "(2026-10-09 Q2, superseded 2026-10-10 by Goal): routine user touches target 0 except order entry. Every proposal states its weekly user-touch cost and may not add a routine touch." 부분을 지우고 "At most 3 active development tasks and 1 authority/limit change in progress at a time." 한 문장만 "Concurrency cap:" 머리말로 남긴다.
7. 문구: Doc-only commits 항목의 "when a Cowork session leaves docs/claude/ changes" -> "when an interactive session leaves docs/claude/ changes".
이 7곳 밖은 바꾸지 않는다. 의심스러우면 하지 말고 보고서에 "확인 필요"로 적는다.
Hard safety 절(## Hard safety ~ ## Kiwoom query rules 직전, CR 제거 후 18~44행 범위)의 sha256을 변경 전(기대값 7d60922e76a9fb08a2996bcfae8aff455807cd0c04249645ea78d0491fee8232)과 변경 후 둘 다 보고서에 적는다. 달라지는 것은 5번 때문이어야 하고, 5번 외 차이가 있으면 안 된다.

## B. 새 문서 (모두 docs/claude/ 아래 새 파일)
- D3: archive-candidates-2026-10-25.md — 끝난 작업 묶음의 archive 이동 후보 목록(읽기 전용 조사, 이동·삭제 금지). 후보마다 근거(마지막 참조, 소비자 없음)와 "이동 안 하면 생기는 비용". 동결 한 문단: 새 규칙·새 반복 문서·새 예약 작업은 안전 결함과 사장 결정 기록을 빼고 보류.
- D11: new-pc-recovery-procedure.md — 새 PC 복구 절차 1장. 확인된 사실만(OffsiteBackup 구성, backup/LATEST.json 위치, 제외 항목, 인증은 세션이 재발급하지 않음). 모르는 단계는 "확인 필요".
  restore-hash-check-2026-10-25.ps1 — 최신 zip을 임시 폴더에 풀어 원본과 sha256만 대조하는 읽기 전용 스크립트(ASCII, Windows PowerShell 5.1, 원본 쓰기 금지, 화면 출력만).
- D12: tax-pretax-note-2026-10-25.md — 한 문단: 주문표와 현행 점수는 세전이고 세후 결과는 승인된 세금 가정이 있을 때만 낸다(manage-us-stock-strategy/references/portfolio-policy.md 99-100행, capital-redeployment.md 33-34행 인용). 세율·공제 수치는 "확인 필요". 새 규칙을 만들지 않는다.

## C. 하지 않는 것
커밋·병합, 5번 외 Hard safety 변경, D5·D8, 새 규칙 추가, 권한(주문·한도·예산) 관련 표현 변경.

## D. 보고
docs/claude/d6-builder-report.md : 바뀐 곳 7개의 전후 문구, 해시(전/후), 새 파일 목록, 하지 않은 것과 이유.
끝나면 사장에게 한국어로 결론 먼저, 바뀐 곳 수와 Judge 시작 방법을 알린다.
