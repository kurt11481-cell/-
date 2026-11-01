---
id: stalled-1101
type: decision-record
status: current
as_of: 2026-11-01 17:30 KST
summary: "비서 10/31 '멈춤 의심' 11건을 관제판과 대조해 닫기 2·살리기 1묶음·조건 고치기 7로 정리. 사장 결정 카드 '정리안 전부 적용'(17:21 KST)."
consumers: "개발 관제판(tasks·log) · 비서 제안(다음 실행부터 ㉳ 목록) · 사장실 코디네이터"
authority: "order_authority=false · quantity_authority=none · 관제판 기록만, 코드·정책·예약·권한 불변"
source_decision: "사장 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9TGJLnby4Ji6YjjRZawNLUh, 선택 '정리안 전부 적용', 2026-11-01 17:21 KST, 사장실 회사PC 스레드 '멈춤 의심 작업 11건 정리'"
---

## 결정 기록
- 2026-11-01 17:21 KST 사장 결정 카드 "멈춤 의심 11건을 정리안대로 관제판에서 고칠까요?" → **정리안 전부 적용**.
- 반영: 2026-11-01 17:30 KST 관제판 ArtifactData batch 16건(tasks 14 · log 2026-11-01-stalled-1101 · meta/board).

- 출처: workspace/outputs/secretary/2026-10-31.md 17~29행(비서 v1.2 ㉳), 관제판 tasks(2026-11-01 17시대 KST 읽기, 246건), 저장소 codex/master-recovery-expansion
- 왜 계속 뜨나: 비서 지시문 secretary-daily.txt 21행 ㉳ 규칙 = (가) waiting이고 resume.type이 event·manual인데 날짜가 없으면 마지막 갱신 7일 넘으면 표시, (나) paused인데 after에 끝난 작업이 남아 있으면 표시. 그래서 오래 기다리는 게 맞는 작업도 매일 뜬다. 비서에서 빠지려면 type을 after로 바꾸거나, 점검 날짜(resume.date)를 넣거나, paused로 둬야 한다.
- 결정 충돌 확인(active-decisions.md): duet-1022(37행)·redesign-t5 무응답 = 현행 유지(180행)·t2rc-factid-1101(110행)·노출 E B(107행). 아래 안은 이 결정들을 바꾸지 않는다. 관제판 기록만 고치고 코드·정책·예약 작업·권한·주문은 건드리지 않는다.

## 1. 닫기 (2건)

| 작업 | 닫는 이유(확인한 곳) | 다시 열 조건 |
|---|---|---|
| fx6-legacy-cash-min 옛 현금 계산·옛 인증 해시 | 작업의 끝 기준이 "사례가 없으면 NO_CHANGE로 닫기". 15일간 사례 기록 없음. auto_core*.py는 그 검증기를 부르지 않음(grep 0건), 키움 인증 고정은 T1에서 폐지(CLAUDE.md 83행), 코어 현금은 주문 가능액 fc_ord_alowa(CLAUDE.md 22행) | 수동 분석에서 settled 한도 때문에 판단이 어긋난 사례 |
| swap-soxl-pwr SOXL→PWR 단계 교체(A안, 10/8) | 끝 기준이 "목표 수량 도달 또는 사용자 중단"이라 사장 중단 결정이 필요. 그 뒤 PWR 매수는 자동 코어 주문표 회로가 판정하고(active-decisions 110행), SOXL 노출은 10/31 노출 결정 B(107행, 1.9 아래로 + 반등 때 줄이기 알림)가 맡는다. 작업의 재개 조건 "E < 1.9 때 PWR 재판정"도 B가 가는 곳과 같아 따로 둘 이유가 없다 | 사장이 수동 교체 계획을 다시 원할 때 |

## 2. 살리기 (1묶음, 이 목록의 2건 + 같은 고리 2건)

| 작업 | 문제 | 안 |
|---|---|---|
| close-confirm · ic-rerun-core (+ rule-factid-version · rule-rev-ledger-trig) | 넷 다 "다음 통합 점검 규칙 파일 개정 때"를 기다리는데, 규칙 파일은 10/22 v3.12.10 뒤 개정이 없고 개정을 시작할 작업이 관제판에 없다. 서로 기다리기만 하는 고리 | 새 작업 ic-rules-bundle(planned) 1개를 만들고 넷의 재개를 type after=[ic-rules-bundle]로 바꾼다. 각 작업의 "바로 진행" 조건 문구(ic-rerun-core: 같은 날 재실행 주 1회 이상·실제 덮어쓰기 / rule-factid-version: 같은 MISMATCH 재발)는 그대로 남긴다. 실제 개정은 지금 규칙대로 H1 시험·독립 검토·사장 직접 입력 '예약 작업 변경 승인'. 착수는 사장이 "ic-rules-bundle 진행"이라고 할 때(기본 = 대기) |

## 3. 조건만 고치기 (7건, 상태는 그대로 두고 비서 목록에서만 빠짐)

| 작업 | 지금 | 고칠 것 |
|---|---|---|
| e-new 외부자료 새 PDF | waiting·event, 10/05 뒤 갱신 없음. 실제 새 PDF는 묶음 작업(ext-1027 등)으로 처리됨 | 닫지 않는다. verify의 미확인 목록과 상시 입구("외부자료 새 PDF 처리해줘")를 남기고, resume.date 2026-11-30(원장 EXT-20261009-03·-12 최종 확인일) 점검으로 바꾼다 |
| duet-r3a | paused, after=[duet-sec](이미 done) → (나)로 계속 뜸 | after를 비운다. 사장 10/30 "Duet 아직 사용 불가, 나중에" 보류 그대로. 뒤에 묶인 duet-idx·duet-k1 영향 없음 |
| duet-trial | waiting·manual "Duet 열리면 사장이 알려 줌" | paused로(같은 10/30 사장 말 근거). 재개는 사장이 알려 줄 때 |
| devpipe-merge-lock | waiting·event "T2 '켜' 전 회차 뒤 또는 한가할 때" | 아직 안 고쳐짐(dev-merge.ps1에 _lock 검사 없음, dev-run.ps1 67행만). type after=[t2-rc]로. 운영 규칙 "_lock 있으면 dev-merge 금지" 유지 |
| redesign-t5 (권한) | waiting·event "1단계 10거래일 또는 주문표 5건 오류 0" | 지금은 비교 모드이고 주문표 1건뿐(roadmap.md 20·27행). type after=[t2-rc]로 하고 원래 조건 문구는 남긴다("켜" 뒤에 셈 — 판단, 원문에 순서 규정은 없음). 무응답 = 현행 유지(1단계) 그대로 |
| f-ifixai-audit | waiting·event "T5 결정 전" | paused로, 문구 "redesign-t5 질문 조건이 차면 그 질문 전에 착수" |
| f-openshell (권한) | waiting·event "T5 결정 전" | 위와 같음. "I4 정적 경계 테스트는 별도 승인 시 언제든" 문구는 유지 |

## 4. 바꾸지 않는 것
코드·정책·상태 파일·예약 작업·권한·주문. 비서 지시문의 ㉳ 규칙도 그대로(고치려면 예약 작업 변경 승인 경로).

## 5. 결론을 바꿀 조건
- fx6: 운영 경로가 검증기를 부르는 것이 나오면 닫지 않는다.
- swap-soxl-pwr: 사장이 수동 교체 계획을 계속 쓰고 있다면 닫지 않는다.
- redesign-t5: T5 셈이 비교 모드 주문표로도 시작된다고 정하면 after를 빼고 날짜 점검으로 바꾼다.

## 6. 재검토 기록
1회(독립 하위 에이전트, Sonnet). 반영 4건: e-new 닫기 → 조건 고치기(근거로 든 ext-1012-setup·ext-1022b는 PDF 묶음 작업이 아니었음, verify 미확인 목록 보존) / after만 넣으면 11/08에 다시 뜸 → type을 after로 / ic-rerun-core·rule-factid-version의 즉시 진행 조건 보존 / f-openshell I4 문구 보존. 미해결 0.
