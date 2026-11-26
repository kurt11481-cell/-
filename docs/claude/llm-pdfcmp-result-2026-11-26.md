---
id: llm-pdfcmp-result-2026-11-26
title: "API 시범 3 PDF 1차 분류 1회 비교 — 결과 FAIL, 질문 닫음"
date: 2026-11-26
source: "workspace/outputs/llm/pdfcmp/compare.md·compare.json(2026-11-26 15:10 KST 수거), 실행기 기록 workspace/outputs/llm/runner/2026-11-26.json, 설계 docs/claude/api-pilots-2026-11-06.md 154~164행"
---

## 결론
- 판정 **FAIL**: 분류 일치 7/10(기준 8), 주제 겹침 8/10(기준 8), 인용 확인 5/10.
- 설계 158행대로 **지금 방식(Claude 세션이 외부자료 PDF를 .md 캐시로 읽고 분류)을 유지하고 이 질문을 닫는다.** 다시 열 조건: 사장 요청, 또는 더 큰 모델로 비교하자는 별도 제안.

## 내용
- R0 정답 5개는 모두 R0로 맞혔다. 틀린 3개는 모두 '후보'인 글을 R0로 낮춘 것이다(P01 마이크론 피지컬 AI, P02 메모리 사이클, P04 연준). 후보를 놓치는 쪽으로 보수적이다.
- 주제 겹침 실패 2개: P02(대상을 'DRAM 비트 공급'으로 적어 주제 낱말 MU·마이크론·메모리와 안 겹침), P08(대상에 PER·마진 낱말 없음).
- 비용(정가 환산, Batch): 10건 합 약 $0.009, 입력 약 136k토큰. 모델 claude-haiku-5-5.
- 확인된 것(설계 7절 3): Batch 안에서 Files API file_id와 문서 인용이 동작한다. 27쪽·16.6MB PDF(P09)도 받았다.

## 뒷정리
- 스크립트는 compare.json이 있으면 아무것도 안 해(DONE_ALREADY) 더 돌아도 비용이 없다. 켜기 파일의 pdfcmp 두 줄 끄기는 사장 카드로 따로 묻는다.
