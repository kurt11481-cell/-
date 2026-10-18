# pending-ev-rg1 — ev-rg1-hyper 병합 뒤 함께 바꿀 것 (Cowork 초안, 2026-10-18)

효력: 사용자 승인 1줄(`결정 ev-rg1-hyper 병합: 승인`) + 병합 스크립트 출력 `EVRG1_DONE` 뒤, 같은 Cowork 세션에서만. 그 전에는 아무것도 바뀌지 않는다(현행 로더 v3.12.6-L+R2·규칙 파일 v3.12.6·개장 전 v1.1·계산기 5607b09b… 유지).

## 1. 예약 지시문 교체 (재서명)
| 파일(이 폴더) | sha256(LF 파일) | 교체 대상 | 바뀐 곳 |
|---|---|---|---|
| integrated-check-prompt-v3.12.7-2026-10-18.txt | d2bde3c2066b74506b528d4b9f10d8199bd0a7a34fcfa1294ad0ab5c3e9c4203 | docs/claude/로 복사(로더가 읽는 경로) | 1행 머리말 + 102행 4곳: EV3ⓑ(하이퍼스케일러 IR 사실은 ⓑ 아님) · RG1(미해제 공식 훼손 = 카드 재수락 전 막힘, 소급 해제 없음, 포트폴리오 = 보유 카드 가장 이른 수락일) · 닫힘(RG1 아니오면 시간 소멸 안 닫힘) · ⑤(닫힘·사건 없음에서도 미해제 훼손이면 막힘) |
| integrated-check-daily.txt | f948ca6e56b0f29a608eb25fede6a27c8352c0998bf63ad8988ecd874df8bc24 | 예약 trig_01YWzNq847nJfNgDUnnukBqP(통합 점검 06:40) | 1행 머리말 · 4·12행 규칙 파일 경로 · 18행 해시 129f78af… → d2bde3c2… · 37행 ㉰ 하이퍼스케일러 IR 1문장 · 75행 writer v3.12.7-L+R2 |
| event-pre-open-calendar.txt | 2e4057bcf9b987f3777e1db611af8a16869a078849e940d45afba5a0d9dd7e6d | 예약 trig_015WVdwRscJ2tQqjPputAxsU(개장 전 09:20 ET) | 15행 괄호 문구만(병합 뒤 사실로) |

교체 순서: ① 예약 목록 조회로 두 예약의 현재 본문 sha = README 표(915e1966… · 8620a46e…)인지 확인 ② 규칙 파일 복사 ③ update_trigger 2번(응답 "prompt re-signed" 확인, 응답 본문 sha = 위 표) ④ scheduled-prompts/README.md 표·변경 기록 ⑤ 이 폴더 파일을 scheduled-prompts/ 원본 자리로 옮김(이전 판은 git 이력). 로더 길이가 늘어 교체가 거절되면 ㉰ 문장을 줄여 다시(뜻 그대로) — 사용자에게 알림.

## 2. 문서 (병합 뒤)
- ④ recovery-gate-R-REC1-2026-10-09.md — 37행 표 아래와 43행 아래에 메모 각 1줄(정의 변경 아님, 적용 기록):
  - "- 적용 메모(2026-10-18 ev-rg1-hyper, K3 Judge PASS): RG1의 '공식 확인이 나오면 카드 재작성 전 매수 금지'는 60세션 창 안 공식 훼손 사실을 그 종목 카드 재수락(등록부 accepted.date ≥ 발표 KST 날짜, 소급 없음)까지 세는 것으로 구현했다 — 사건 날·재기준·닫힘과 무관. 하이퍼스케일러 공식 IR(등록부 thesis_damage_domains)은 RG1에만 쓴다."
  - "- 적용 메모(같은 날): 시간 소멸 닫힘은 그날 RG1이 아니오면 일어나지 않는다."
- ⑤ docs/claude/card-evidence-registry.json `rule` 끝에 1문장: "공식 테제 훼손 사실을 검토하고 다시 수락할 때만 accepted.date·text·source를 새로 쓴다(이 날짜가 R-REC1 RG1 해제 신호다). 훼손과 무관한 카드 수정은 날짜를 유지한다."
- ⑥ CLAUDE.md 90행(보호 경로 — 사용자 승인·사용자 커밋): "RG1 thesis (no official damage within 2 sessions)" → "RG1 thesis (2 sessions after the event and no uncleared official root-thesis damage in the 60-session window; a damage fact clears only when the candidate's card is accepted again, registry accepted.date, ev-rg1-hyper 2026-10-18)".
- 사전 등록 docs/claude/t2-rc-preregistration-2026-10-14.md 끝 "변경 기록"에 1줄: "2026-10-18 ev-rg1-hyper(사용자 승인 원문 …, 독립 Judge 1차 FAIL → 재판정 PASS docs/claude/ev-rg1-hyper-judge2-report.md): 고정값 계산기 9f0e2238…1aae · 실행기 fcd8977b…80a7(LF 기준; 원시 3735492e…) · 로더 v3.12.7-L+R2 f948ca6e… · 규칙 파일 v3.12.7 d2bde3c2…(49행 고정값 갱신, 알림 v2.2 eb2b9710… 그대로). 계산기 RG1을 코어와 같은 정의로 고친 계획 변경이라 C1은 병합 뒤 첫 decide 세션부터 0/10. 병합 전 C2 일치는 세지 않는다(관문이 바뀜 — 더 엄격). D0(10-16)와 C4·C5 예약 날짜는 그대로."
