---
id: ext-1022b
title: 외부 글 3건(하이쿠 잡일 스킬 · harness2 · 클로드 코드 스킬 5개) 분석 → 도입 요소
date: 2026-10-22
class: 문서만(K0). 설치·구독·런타임·정책·예약 작업·권한 변경 0
sources: ① https://whimsical-weeder-523.notion.site/2-3fe7e3f0cdc58158b84af0e1eac32571 (PICKIT, 2026-10 기준, 내장 브라우저로 본문 조회) ② https://rebornlabs.kr/harness2 (REBORN LABS, 제3자 안내) + 원 저장소 https://github.com/google-research/harness2 ③ https://every-ai-guides.vercel.app/posts/claude-code-top-skills-5 (every._ai, 2026-09-28) — 조회 2026-10-22 08:15~08:40 KST
consumer: 플레이북 표준 docs/claude/playbooks/README.md(결정 시 개정) · pb-1022 평가(2026-11-07) · 관제판 ext-1022b
---

# 외부 글 3건 분석 → 도입 요소 (2026-10-22)

## 0. 결론
1. **설치할 것은 없다(3건 모두 NO_CHANGE).** 하이쿠 잡일 위임은 이미 2026-10-08에 도입했고(test-runner·summarizer, CLAUDE.md:80~83), 글이 권하는 "기본 Explore를 하이쿠로 덮어쓰기"는 그때 기각했다(haiku-5-5-review-2026-10-08.md 60행 — Builder가 Explore 결과로 수정 범위를 정해 위치 누락이 fail-open 위험). 새 근거 없음. 스킬 5개는 이미 있는 기능과 겹치거나 지금 쓸 데가 없다(3절). harness2는 설치하지 않는다(네트워크 무제한·샌드박스 꺼짐·Linux 전용·API 비용, 2절).
2. **뼈대에 넣을 요소는 작다 — 이미 하던 방식을 표준으로 굳히는 것(REUSE)**
   - H1 **변경 전 결정론 시험(이미 하던 방식의 표준화)**: 예약 작업의 스크립트·검사(checks.py)·출력 형식을 바꾸는 변경은, 교체 요청 전에 Cowork가 그 스크립트를 **입력 복사본(최근 실제 결과 파일 + 가짜 이상 사례)으로 scratch 폴더에서** 옛 판·새 판 실행해 비교한다. 우리는 이미 이렇게 해 왔다 — c1-host(실제 + 가짜 5종, README 51행), offsite-bak(실제 + 가짜 8종, "같은 입력에서 H ALERT는 v2.3 host.py와 같음", 60행), pb-r1(바이트 동일). 새로 정하는 것은 ① 기대하는 차이를 실행 **전에** notes.md(또는 변경 기록)에 먼저 적고 결과와 대조(만든 쪽이 결과를 보고 기준을 맞추지 않게 — 우리 쪽 보강. harness2에서 온 것은 옛·새 실행의 행동 차이 비교 "behavioral contrasts between executions") ①-2 출력 형식이 바뀌면 그 출력을 읽는 쪽 코드(플레이북 머리 outputs의 소비자)도 새 출력 견본으로 돌려 본다 ② 키움·웹·푸시·artifact·_pending·예약 실행(fire) 금지 ③ LLM이 쓰는 문장 부분은 시험 대상이 아니고 교체 뒤 첫 실행 확인으로 대신(선례 st-1014 첫 짝 실행 확인, README 39행) ④ 위험 축소·매도 알림을 되살리는 변경은 시험을 기다리지 않고 교체한 뒤 시험. 적용 범위: 플레이북(새 작업)과 기존 예약 작업 모두 — scheduled-prompts/README.md 변경 절차에 1줄로.
   - H2 **"제약 완화" 표시(작게)**: 변경 등급·권한 경로를 정하는 규칙은 이미 있다(CLAUDE.md Change classes 56~58행, playbooks/README.md 4절). 새로 넣을 것은 하나 — 기계로 판정: checks.py 검사 항목 수가 줄었거나 플레이북 머리 class 칸이 바뀌었으면 교체 요청 첫 줄에 "제약 완화"를 적는다(사장이 한눈에 보게). 그 밖의 완화(문장으로 된 막힘 규칙 완화)는 지금처럼 검토 안정성의 "기존 제약 완화 여부" 확인으로 본다. harness2가 가드레일까지 자동 편집 대상에 넣는 것과 반대 방향의 장치.
3. **측정 먼저**: 글 ①의 "한도 2배"는 API 토큰 가격(하이쿠 5.5가 오퍼스 5.5의 40분의 1 — 공식 가격표와 일치)으로 계산한 값이고, (프롬프트 10만 토큰 이하 기준, 넘으면 1/8) 구독 한도에 대한 배수는 글 스스로 "공개돼 있지 않다"고 적었다. 우리는 예약 작업별 사용량을 잴 방법이 없으므로(확인 필요) 모델 배정을 바꾸지 않는다. 자동 운영 코어 알림의 Opus는 사장이 2026-10-17 설정 화면에서 직접 되돌린 값이다(scheduled-prompts/README.md 46행). Projects가 열리면 Usage 탭(스레드·모델별 토큰)으로 재검토.

## 1. 글 ① 하이쿠 잡일 담당 스킬 (PICKIT)
| 주장 | 분류 | 대조 |
|---|---|---|
| 하이쿠 5.5 토큰 가격은 오퍼스 5.5의 1/40(입력 $0.10 vs $4, 출력 $0.50 vs $20), 프롬프트 10만 토큰 초과 시 $0.50/$2.50 | 사실 | 공식 가격표(platform.claude.com/docs/en/about-claude/pricing) 일치. 1/40은 10만 토큰 이하에서만, 넘으면 1/8 |
| 잡일이 절반을 넘으면 같은 요금제로 2배 이상 | 계산(가설) | 토큰 가격 기준 계산식은 맞음. 구독 한도 배수는 비공개(글 스스로 명시). 실제 효과는 잡일 비중에 달림 |
| haiku-helper(잡일)·Explore(탐색)를 ~/.claude/agents/에, 규칙 3줄을 ~/.claude/CLAUDE.md에 | 방법 | 우리는 저장소 .claude/agents/에 test-runner·summarizer(모델 haiku)로 이미 운영. 전역(~/.claude) 설치는 이 PC의 모든 Claude Code 작업(Builder·Judge 포함)에 퍼지므로 하지 않음 |
| 설명에 'use proactively'를 넣어 먼저 맡기게 | 방법 | 도입 안 함 — 전체 테스트는 이미 test-runner로 정해져 있고(CLAUDE.md:78), .claude/는 수동 경로(CLAUDE.md:108)라 얻는 것에 비해 비용이 큼 |
| 판단이 필요하면 하이쿠가 멈추고 메인에 넘김 | 방법 | 우리 기준과 같음(summarizer.md:14 "Do not judge, score, recommend trades or decide pass/fail", CLAUDE.md:83 출력은 위치 안내일 뿐) |
| 기본 Explore를 하이쿠로 | 방법 | 2026-10-08 기각 유지(새 근거 없음) |

## 2. 글 ② harness2 (REBORN LABS 안내 + Google Research 저장소)
| 주장 | 분류 | 대조 |
|---|---|---|
| 구글이 푼 프레임워크 | 사실(단서 포함) | 저장소 google-research/harness2, Apache-2.0. README "This is not an officially supported Google product" |
| 모델은 고정, 하네스(프롬프트·가드레일·기억·도구 안내·서브에이전트·스킬·스크립트·플러그인)만 개선 | 사실 | README 8개 요소 |
| 제안(Propose)→시험(Probe)→결합(Compose), 근거 있는 교훈을 남겨 다음 개선에 | 사실(설계) | README "propose edits, probe their effects on the same task, and compose a refined harness" |
| WorkBuddy-Bench +11.5 · JobBench +4.5 · LAB +11.8%p | 사실(저장소 보고) | GLM-5·Gemini 3.5 Flash 기준, 벤치마크용. 우리 일에 같은 효과는 미검증 |
| 위험 | 사실 | README "Executor network access is unrestricted, and Codex runs with its sandbox disabled", 모델 비용, Linux 전용 |
| 안내 페이지의 설치법 | **주의** | `npx --yes reborn-harness2`는 원 저장소가 아닌 제3자 패키지, 클로드가 막으면 `!`·`--yes`로 우회하라는 안내, 유료 스킬팩 판매 — 따르지 않음 |
- 설치하지 않는 이유: 실행기 네트워크 무제한·Codex 샌드박스 꺼짐(README), Linux 전용, 모델 API 비용, 공식 지원 제품 아님. 키움 MCP가 있는 사장 PC에 맞지 않는다. README는 제안·시험·결합 전체를 정답 채점 없이("without ground-truth feedback") 실행 간 행동 차이로 한다고 밝힌다. 우리 쪽에서 쓸 것은 그 옛·새 비교 방식(H1)뿐.

## 3. 글 ③ 클로드 코드 스킬 5개 (every._ai)
| 스킬 | 판정 | 이유 |
|---|---|---|
| agent-browser (vercel-labs) | 안 함 | 내장 브라우저·Claude in Chrome이 이미 있음. 별도 CLI 전역 설치 필요 |
| find-skills (vercel-labs) | 안 함 | 스킬 찾기 기능이 이미 있음. 제3자 스킬 자동 설치는 설치 전 검토 규칙(external-skills-review-2026-10-02.md 8행)과 충돌 |
| GSD Core (open-gsd) | 안 함 | 논의→계획→실행→검증 흐름은 개발 파이프라인(Builder→검사→Judge→병합)과 겹침. 옛 저장소는 보관 처리(글). 설치 명령이 `@latest`라 판 고정이 안 됨(공급망) |
| Taste (design-taste-frontend) | 안 함 | frontend-design 스킬 + 사장 디자인 기준(KRDS 등)으로 충분 |
| MCP Builder (anthropics/skills) | 지금은 안 함 | Anthropic 공식. 새 MCP를 만들 일이 생기면 그때 검토 |
- 공통: `npx skills add … -y`는 프로젝트 .claude/에 설치 — 보호 경로(수동 경로) + 공급망 위험.

## 4. 한계를 넘는 점 (솔직한 평가)
- 이번 3건에서 뼈대를 크게 바꿀 새 요소는 나오지 않았다. 하이쿠 위임·변경 전 시험은 이미 하고 있고, 스킬 5개는 겹친다.
- 남는 가치는 "이미 잘하던 것을 빠짐없이 하게" 만드는 것: 예약 지시문은 10/9~10/21에 약 30번 교체됐고(새로 만든 3건 제외, 수기 분류 — 확인 필요), 그중 시험 기록이 남은 것은 일부다(README 33·51·60행, pb-r1). H1은 그 시험을 모든 스크립트·검사 변경의 기본 절차로 만든다.
- 사람 손: 일상 0(시험은 Cowork가 변경을 준비할 때). 비용: 스크립트만 돌리므로 토큰은 거의 없음(시험 결과를 읽는 Cowork 대화분만).
## 5. 바뀔 조건
- 예약 작업별 사용량을 볼 수 있게 되면(Projects Usage 탭 등) → 모델 배정 재검토.
- 사장이 요금제 한도에 자주 걸린다고 알려 주면 → 하이쿠 위임 범위 재검토(판단 일 제외 유지).
- H1을 적용한 변경 5건에서 시험이 결함을 한 번도 못 잡고 교체를 늦추기만 하면 → H1 축소.

## 6. 결정 요청 (`결정 ext-1022b: a|b`, 기한 2026-10-29, 무응답 = 현행 유지)
- **a) H1(변경 전 결정론 시험 — 기대 차이 먼저 기록)을 플레이북 표준과 예약 지시문 변경 절차에 1줄씩, H2("제약 완화" 표시) 추가(권장)** · b) 현행 유지

## 7. 내장 재검토 기록
- 1회차 8건 — 결론을 바꾼 것 4건: ① H1은 새 요소가 아니라 이미 하던 시험(README 51·60행 등)의 표준화(REUSE)로 ② 적용 범위를 기존 예약 작업까지(변경 절차 1줄) ③ 시험 방법을 결정론 부분·입력 복사본·scratch·기대 차이 선기록·외부 호출 금지로 확정, 비용 정정 ④ H2를 "제약 완화" 표시 하나로 축소(나머지는 기존 규칙과 중복). 문구 4건: harness2 설치 안 하는 이유 정정 · use proactively 이유 정정 · 근거 표기(summarizer.md:14, 1/40 조건, 8행, @latest) · 교체 횟수 약 30·정정 23건 근거 문장 삭제.
- 2회차(바뀐 부분만) 7건, 모두 문구·보완: harness2 인용("without ground-truth feedback", 전 단계) · ① 출처 구분(기대 차이 선기록은 우리 보강) · ①-2 출력 소비자 코드 시험 추가 · ③ 선례 st-1014(README 39행) · H2 근거 Change classes·기계 판정(검사 항목 수·class 칸) · 출처 목록 정리 · 검토 완결 줄.

검토 완결: 원문 확인 14/14(외부 5 · 내부 9) · 내장 재검토 2회(반영 15건, 결론 변경 4건) · 미해결 1(예약 지시문 교체 횟수 약 30은 수기 분류 — 확인 필요) · 자료 시점 2026-10-22 08:15~09:00 KST · 바뀔 조건 5절

## 8. 결정 기록
- 답: 결정 ext-1022b: a (2026-10-22 08:31 KST, Cowork, 사장 원문 그대로)
- 반영: playbooks/README.md 7절(H1·H2) 추가 · scheduled-prompts/README.md 머리에 변경 전 시험 1줄(기존 작업에도 적용).

## 출처
- ① https://whimsical-weeder-523.notion.site/2-3fe7e3f0cdc58158b84af0e1eac32571 · 가격표 https://platform.claude.com/docs/en/about-claude/pricing
- ② https://rebornlabs.kr/harness2 · https://github.com/google-research/harness2
- ③ https://every-ai-guides.vercel.app/posts/claude-code-top-skills-5
- 내부: CLAUDE.md:56~58·78~83·108, .claude/agents/summarizer.md(14행)·test-runner.md, haiku-5-5-review-2026-10-08.md 1·60행, scheduled-prompts/README.md 33·39·46·51·60·62행·변경 기록, external-skills-review-2026-10-02.md 8행, playbooks/README.md
