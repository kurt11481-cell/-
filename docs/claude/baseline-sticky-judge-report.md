---
id: baseline-sticky-judge-report
title: "baseline-sticky 독립 Judge 보고 (읽기 전용)"
date: 2026-11-02
source: "docs/claude/baseline-sticky-judge-prompt.md; 별도 Remote Control 세션(Opus, Builder와 다른 세션) 답을 프로젝트 스레드가 옮겨 적음, 2026-11-02 10:07 KST"
target: "worktree .claude/worktrees/baseline-sticky, 브랜치 worktree-baseline-sticky, 기준 커밋 8615efb"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

| # | 항목 | 판정 | 근거 |
|---|---|---|---|
| 1 | diff가 허용 파일 4개뿐 | PASS | 변경 3개(devpipe.py +11/-2, README.md +1/-1, test_dev_pipeline.py +68/-0)와 미추적 baseline-sticky-report.md 1개뿐(git status --untracked-files=all). BLOCKED.md 없음 |
| 2 | 멈춘 기준선만 후보에서 빠짐 | PASS | devpipe.py:1004-1008: added_failures가 목록이고 길이 ≥ BASELINE_ROSE_STOP이며 표식이 없을 때만 참. 키 없으면 isinstance 거짓, 1~9건은 길이 조건 거짓, 표식 있으면 거짓이라 셋 다 후보로 남음. 필터는 devpipe.py:1023 |
| 3 | 조상·python·method·정렬·문턱값 그대로 | PASS | devpipe.py:1020-1022·1025-1026은 조건이 더해졌을 뿐 그대로. devpipe.py:91 문턱값 10 변경 없음. data["base"]는 1021행 문자열 검사 뒤에 쓰임 |
| 4 | 판정·이름·표식·dev-merge 그대로 | PASS | diff가 baseline_rose_verdict(devpipe.py:627-641), evaluate_tests(644~), baseline_accept_path(999-1001)를 건드리지 않음. dev-merge.ps1도 diff에 없음 |
| 5 | 표식을 코드가 만들지 않음 | PASS | devpipe.py:1008은 .is_file() 읽기만. 표식을 쓰는 곳은 시험 도우미 test_dev_pipeline.py:1074-1078뿐 |
| 6 | 시험이 목록을 덮고 필터 분기를 거침, 기존 시험 변경 없음 | PASS | 지시문 5건 = test_dev_pipeline.py:1205·1219·1235·1241·1251, 보강 2건 = 1212·1227. prev_base를 first와 base로 구분해 단언하므로 필터가 없거나 틀리면 실패(코드 읽기로 판단, 변이 시험은 못 함). 시험 파일 삭제 0줄. 재실행 Ran 150, OK |
| 7 | 새 외부 호출·삭제 없음, 주문·정책 무관 | PASS | 더해진 호출은 .is_file()뿐. git·네트워크·unlink 추가 없음. 주문·키움·정책·상태 문자열 없음 |
| 8 | 줄바꿈 유지 | PASS | 고친 3개 파일 CRLF 100%(LF 단독 0줄), ls-files --eol은 i/lf w/crlf. 새 보고서는 LF |
| 9 | 보고서 (a)~(e), 수량·금액·표지 없음 | PASS | baseline-sticky-report.md:13-51에 (a)~(e), 57행 "표지 없음". (c) 150건 재실행과 일치. 구현 요구 5는 devpipe.py:1149-1150에서 확인. (e) 메인 _baseline/에 added_failures 캐시 0개, accept 표식 0개 직접 확인 |

## sha256 (Get-FileHash, Builder 보고값과 4개 모두 일치)
| 파일 | sha256 |
|---|---|
| tools/dev_pipeline/devpipe.py | ba9fa1a508c4cdbea71e517d378f2352284acb0d1bffaa421189ccac69050f0a |
| tools/dev_pipeline/README.md | 5601c19a4ead5d41b861c69b83dfa129e7c7f3297e1b3eae6ec5d5a60db74b1d |
| manage-us-stock-strategy/tests/test_dev_pipeline.py | e710adf8592f379080b1e32289b6ae471d2463bce3c4c6c130a2dc815c4507d7 |
| docs/claude/baseline-sticky-report.md | 4768988b8a1fa78276f528f34221922436ed437e65fa0914dc193fc3e31db068 |

## 주의 (판정 영향 없음)
- 지금은 어떤 캐시에도 added_failures 키가 없어, 이 규칙은 다음에 새로 재는 기준선부터 작동한다.
- Y 캐시가 생긴 뒤 accept-X를 두면 Y의 멈춤은 그대로이고 다음 기준 커밋부터 풀린다(바로 풀려면 accept-Y). 수정안 3항과 어긋나지 않는다.

VERDICT: PASS
