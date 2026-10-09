---
id: fx1009-fx1-record
title: FX-1009 fx-1 문서 일괄 정리 — 실행 기록
date: 2026-10-09
class: K0 (설계 G3 문구는 K1)
plan: docs/claude/fx1009-fix-plan-2026-10-09.md 5-1절 · 부록 A-1
status: 완료(사용자 커밋 대기)
authority: order_authority=false · quantity_authority=none · execution_quantity=null
---

# FX-1009 fx-1 실행 기록 (2026-10-09 14:47~15:0x KST, Cowork)

## 결과 (5-1의 1~10)

| 항목 | 내용 | 결과 |
|---|---|---|
| 1 | CLAUDE.md: R-REC1 줄 끝 Replay 문구 · Decision journal 줄 · Session hygiene 공유 문서 줄 · 동결 줄 | 3줄 추가, 동결 줄은 이미 있어 확인만. CRLF 유지 |
| 2 | AGENTS.md (Q6 b): 키움 프로필·옵션 층·위원회·R-REC1 문단 4개를 CLAUDE.md 링크 1줄로 | 완료. ChatGPT 문서 참조·context-mode 절은 그대로 |
| 3 | 설계 문서 `order-instruction-design-2026-10-06.md` | 3절 G3 칸(Q5 문구 + Q2 a′) · 7-2절 끝 지원표 · 9절 확인 ③ 문구 · 10절 일지 제안 1줄 · 12절 Q1 결정 1줄 |
| 4 | 정정 1줄씩 | prep-decisions(128줄 아래, D1) · policy-proposal("S5 확정안 r2" 절 첫머리, D3) · s7-builder-report 5.6절(A4). 각 파일 줄바꿈 형식 유지 |
| 5 | 예약 지시문 원문 보관 | `docs/claude/scheduled-prompts/` 에 반복 7개 + 이벤트 표본 1개 + README(이름·trigger id·sha256·대조). 저장 후 해시 일치 확인 |
| 6 | `library/INDEX.md` · `analysis-linkage-map` | INDEX: as_of 10/9, 보유 현행 카드 유효기한 "다음 M6 카드에서 갱신", 통합 점검 규칙 행, 구판 목록, 이름 접두어 3줄. 연결 지도 통합 점검 표기 갱신 |
| 7 | 관제판 | s-kiwoom → done · p-s7-routine ③ 문구 · p-u2는 이미 "fx-3으로 앞당김" 반영돼 변경 없음 · oi-k3 priority 1 · fx-1 done · 로그 1줄 |
| 8 | 메모리 | 10/9 결정 세션에서 완료(tuja-v2.md 현재 17,712바이트). 다시 하지 않음 |
| 9 | 지식 파일 머리말(D6) | NO_CHANGE (계획대로 보류) |
| 10 | 커밋 묶음 | 아래 명령 1블록 |

## 이탈 사항 (계획서와 다르게 한 곳 — 확인 필요)

1. **통합 점검은 이미 v3.12.2다.** 계획서 5-1의 6번·5-2절은 "현행 v3.12.1"을 전제하지만, 예약 작업 목록 조회(10/9 14:5x KST)의 지시문 해시가 `integrated-check-prompt-v3.12.2-L-loader-2026-10-09.txt`(sha256 d1bba04e…6f1c)와 같다. 10/9 14:35 KST에 교체됐다(`integrated-check-v3.12-change-2026-10-09.md` 8절). 그래서 INDEX·연결 지도는 v3.12.2로 적었다. **fx-2는 시작 전에 계획서 5-2를 이 사실에 맞춰 다시 읽어야 한다**(규칙 파일 v3.12.2는 이미 있고 통합 점검 규칙 파일은 fx-1이 고치지 않았다).
2. **Q2는 a′로 적었다.** 5-1의 3번 문구는 Q2 = a(C 단독은 단계를 정하지 않음) 기준인데, 결정 기록은 a′(C 단독 근거 = 단계 상한 ⅓)다. 결정 기록을 따랐다.
3. **지원표의 "확인됨" 범위가 좁다.** 프리마켓 접수 → 정규장 유지는 MVLL 1건만 실측이라 SOXL·NBIS·SOXX·PWR·LITE는 "확인 필요"로 적었다. 9절 확인 ③이 지원표를 보게 됐으므로, 다음 지시서(PWR 1차)부터 이 상품들은 사용자가 키움 화면에서 접수 가능 여부를 확인한 뒤 표를 고쳐야 "확인됨"이 된다.
4. **이벤트 예약 5개 중 표본 1개만 보관**(10/14 CPI). 나머지 4개는 원문 비교를 하지 않았다.
5. **관제판 fx-1은 done으로 표시했지만 커밋은 아직이다.** 커밋 뒤 commit 칸을 채운다.

## 파일 해시 (수정 전 → 후, 전체 바이트 sha256)

| 파일 | 수정 전 | 수정 후 |
|---|---|---|
| CLAUDE.md | e8f1c8a9…c6d4 | 45ad776e…4e5e |
| AGENTS.md | f720a8a4…fce311 | 5ad801ab…2875a3 |
| order-instruction-design-2026-10-06.md | d4f18f50…c8bf40 | 27137b9f…9219 |
| library/INDEX.md | 21c44bf5…fe0b | 7645e69e…2177 |
| analysis-linkage-map-2026-10-05.md | 93e1f658…de299 | ad106cbe…5bd3 |
| loss-limit-review-s5-prep-decisions-2026-10-01.md | d8c8eead…06cf | afc58db4…d0fe4ce |
| loss-limit-review-s5-policy-proposal-2026-10-01.md | 6ace18ab…6021 | 1384001c…9b5 |
| s7-builder-report-2026-10-01.md | cad72daa…dd5ac | 863c6746…2c2 |
| scheduled-prompts/README.md | (새 파일) | e9d7437d…e5 |

각 파일은 수정 직전 해시를 다시 확인한 뒤 저장했다(7절 2번). 다른 세션과의 충돌은 없었다.

## 건드리지 않은 것

정책·상태 파일, 키움 주문 도구, `integrated-check-prompt-*` 규칙 파일, 지식 파일, 예약 작업(조회만 했고 바꾸지 않음), 확인 코드 apply.

## 커밋 (사용자가 직접 실행)

PowerShell에서 한 줄씩:

```
cd "E:\사업\##금동한\코덱스저장소"
git add CLAUDE.md AGENTS.md docs/claude
git status --short
git commit -m "docs: FX-1009 fx-1 document cleanup (rules, order-instruction design, INDEX, scheduled prompt copies, judgment docs)"
```

- `git add docs/claude`는 docs/claude 아래 수정 13개 안팎 + 미추적 판단 문서(카드·M6 카드·상품 승인·근거 원칙·order-instructions/·검토 문서·이 계획·이 기록)를 모두 올린다. `git status --short`로 올라간 목록을 먼저 본다.
- 제외(이번 커밋 대상 아님): `Claude outputs/` · `visualizations/` · `workspace/outputs/` · `stock-strategy-system/backtests/r_rec1_gate_replay_2026-10-09.*`(코드 산출물, 별도 판단). 상태·일지 파일은 .gitignore 대상이다.
