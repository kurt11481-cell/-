# 확인 검토 — R2 발견을 고친 코드 변경만 (2026-11-10)

- 본 것: `r3_shadow.diff`, `r3_weekly.diff`, `r3_itest.diff`와 새 파일(fm3_shadow.py da12b055…, fm3_weekly.py eb83a1a4…, fm3_itest.py 97ea073a…). 해시가 알려 준 값과 같다. vixr.py·MENU.json은 그대로다(5be2fd0b…, d3268329…).
- 내 작업·로그: `/tmp/claude-0/-home-user/a406bf43-090f-5192-964f-c483e7203aaa/scratchpad/review3c/` (`ta_vixr_cut.py`, `tb_books.py`, `tc_world.py`, `logs/`). l3fix/에는 쓰지 않았다.
- vixr는 실제 결과와 대조하지 않았다. 자르기 대조(같은 예측을 두 가지 입력으로 계산해 견줌)만 했다.

## 판정: 통과

막는 결함은 찾지 못했다. 판정을 틀리게 하거나, 장부를 잃거나 망가뜨리거나, 결과 정보를 흘리는 변경은 없다. 아래 R3-1은 판정 구간이 둘인 도전자에만 해당하고 vixr(20일만)와는 무관하다. 나머지는 가벼움이다.

## 1. 막는 결함이 있는가 — 없다

가장 걱정한 것은 R2-4였다. 대조 불일치가 이제 도전자를 바로 끝내므로, 정직한 코드에서 거짓 경보가 나면 판정이 틀려진다.

- **[돌림] vixr 2년치 주간 대조**: 새 코드의 `_stage_one`(cut_test 포함)을 시작일 2024-11-01 ~ 2026-11-06, 20종 전부에 적용했다. **6,042행 중 다른 행 0**. 전날 값만 읽는 비미국 5종(미국 휴일인 시작일 포함)도 0이다(_N225 0/294, _KS11 0/294, _HSI 0/297, _GDAXI 0/306, _FTSE 0/306).
- 같은 시험에서 R2-3 더미 r2shift1은 XLE 84/84, _KS11 81/81이 걸렸다(고치기 전 0/84, 6/81).
- [읽기] 두 계산이 같은 실행에서 같은 파일을 읽으므로 자료 정정으로는 불일치가 날 수 없다. 시작일이 입력에 없는 경우는 일반 ValueError라 건너뛰기로만 간다(끝내지 않음).

## 2. 발견별로 닫혔는가

| 발견 | 닫힘 | 근거 |
|---|---|---|
| R2-2 | 닫힘 | [돌림 tc] history 더미의 결과 블록에 `"om` 없음, state는 문자열, 콘솔은 "share not shown". 보류·판정 사건의 row에만 om_mean이 남는다(판정일 숫자, 의도대로) |
| R2-3 | 닫힘 | 위 시험. `asset_context(..., cut_test=True)`를 주간 대조와 심사 'cut' 두 곳이 모두 쓴다(`fm3_shadow.py:379, 705`). 발급되는 값도 전날에서 자른 계산이다 |
| R2-4 | 닫힘 | [돌림 tc] 실제 stage가 낸 불일치(9행 중 9행)로 그 실행에서 20·60일 모두 end_cut_mismatch, status ended, REJECTED 2줄, 발급 파일 없음, 장부 OK. 같은 asof 재실행도 정상. 한 가지 남음: R3-1 |
| R2-5 | 닫힘(잠금 없음은 절차) | [돌림 tb] init에서 가드 통과. 디스크 장부가 남은 줄을 가진 경우 commit이 쓰기 전에 멈추고 LOG 줄 수 불변(1 → 1), 다음 명령이 남의 줄을 마저 씀. 찢어진 마지막 줄도 정상 |
| R2-6 | 적은 항목은 닫힘 | match·f-string·`str(V)` 거부 확인. 객체 주소 길은 일부 남음(R3-5, 머리글이 인정함) |
| R2-7 | 닫힘 | [돌림 tb] 통과·통과 → auto True, 실패·통과 → auto False 유지. 보류를 푸는 코드는 없어졌다(diff). 구간·길이가 빠진 보고는 거부 |
| R2-8 | 닫힘 | 계산 전에 INPUTS.sha256 삭제(`fm3_weekly.py:597-598`). 그쪽 t4 E 로그 0행 |
| R2-9 | 닫힘 | [돌림 tb] rejected 줄만 남은 outbox: 한 번만 덧붙음. 장부 파일이 깨졌거나 없을 때 rebuild 정상. 결과 파일은 commit 뒤 |
| R2-10(일부) | 고친 만큼 닫힘 | run 사건에 code·fm2_inputs_sha256 있음(tc). 23시 가드 재확인은 읽기만 |
| freeze none_kept | 문제없음 | 발급된 "예측 없음"은 그대로 남는다(selftest가 확인). report에서만 빠지고 결과 파일의 issued 칸에는 숫자가 있다 |

## 3. 발견

| 번호 | 심각도 | 무엇 · 실패 시나리오 | 최소 처방 |
|---|---|---|---|
| R3-1 | 중요(판정 구간이 둘인 도전자 전. vixr 무관) | `fm3_weekly.py:475` — 대조 불일치로 끝난 도전자가 다른 구간이 이미 pass_to_judge였으면 status가 **candidate**가 된다. [돌림 tb b9] h_status {20: pass_to_judge, 60: end_cut_mismatch} → 'candidate'. 시나리오: 20일이 104주에 통과 → 60일을 재는 중 불일치 → 그 주 report는 "was ended"라고 하지만 장부는 candidate이고, 그 뒤 매주 awaiting_judge에 경고 없이 뜬다. 미래 자료를 쓴 것으로 드러난 코드의 통과가 카드로 갈 수 있다 | 475행 조건에 `and 'end_cut_mismatch' not in hs`를 더한다(ended로 감, '덜 하는 쪽'). 고치지 않으면 "판정 구간이 둘인 메뉴 항목은 다음 판 전에 등록하지 않는다"를 규칙에 적는다. 지금 메뉴는 vixr [20]뿐이다 |
| R3-2 | 가벼움 | `fm3_weekly.py:85, 189, 191` — flush가 commit **안에서**(장부 저장 뒤) 멈추면 "wrote nothing into … REGISTRY.json"이 거짓이다. [돌림 tb b4] 가드와 덧붙이기 사이에 남의 줄이 끼면 디스크 장부는 이 명령의 상태(last_run_asof '2026-11-13', 남은 줄 1개)이고 모든 명령이 멈춘다. rebuild가 그 줄을 버리며 화면에 찍고 LOG대로 되돌린다(확인). 창은 밀리초이고 머리글이 이 경우를 인정한다 | commit에서 부른 flush가 멈출 때는 "장부는 저장됐다. rebuild를 돌려라"로 문구를 바꾼다 |
| R3-3 | 가벼움 | `fm3_weekly.py:308-311` — 옛 장부의 outbox 모양이 깨져 있으면 rebuild가 KeyError·AttributeError·TypeError로 죽는다(open도 같다). [돌림 tb b5] 세 경우 모두. 손으로 고쳤거나 상했지만 JSON으로는 읽히는 장부에서만 난다 | 311행을 `except (SystemExit, Exception)`으로 바꿔 '버림'으로 처리한다 |
| R3-4 | 가벼움 | `fm3_weekly.py:166` — REJECTED.md가 지워지면 머리글만 조용히 다시 만든다. [돌림 tb b7] 9줄 → 8줄, 잃은 줄은 돌아오지 않고 알림도 없다. 전에는 파일이 없는 채로 드러났다. 기록은 LOG에 남아 있다 | 다시 만들 때 한 줄 출력한다. 다음 판에서 LOG의 judged·status 사건과 대조한다 |
| R3-5 | 가벼움 | R2-6의 '객체 주소' 길은 이름 str·repr만 막혔다. [돌림] `'%r' % (V,)`, `np.str_(V)`, `np.array([V], dtype='U99')`, `b'to' + b'day'`가 정적 검사를 통과한다. 머리글이 우회 가능하다고 적었고, 프로세스 간 결정성 시험과 Judge 읽기가 받친다 | Judge 점검표 4번에 이 넷을 적는다. 코드 변경 불필요 |
| R3-6 | 가벼움 | `fm3_weekly.py:348` — interval-check가 true/false를 1.0/0.0으로 받는다. [돌림 tb b10] `{"65": true, …}`가 통과로 기록됨 | bool을 거부한다 |

코드 결함은 아니지만 규칙문에 적어야 할 설계상 결과(R2-7을 고친 결과):

- 보류된 판정은 `close`로만 끝난다. close는 도전자 전체를 닫는다(`fm3_weekly.py:479-489`). 판정 구간이 둘이면 한 구간의 보류를 정리할 때 다른 구간도 끝난다.
- 보류된 숫자가 pass_to_judge로 읽혀도 awaiting_judge에는 뜨지 않는다. report의 "PERSON DECISION NEEDED" 줄로만 보인다.
- close의 탈락 기록 줄에는 보류된 숫자가 없다('채점 없음', 0주). 숫자는 LOG의 held 사건에 있다.
- 점검이 한 번 실패하면 그 구간은 이 장부에서 영영 자동 판정이 없다.
- 멈춘 실행이 쓴 발급 파일은 장부에 없는 파일로 남는다(그쪽 t4 C 로그: 디스크에 `2008-03-21_001.npz`, 장부 0개). 같은 asof를 다시 돌리면 덮어쓰고, 다음 주로 넘어가면 남는다. Judge의 해시 대조 때 설명이 필요하다.

## 4. 돌린 것

- `ta_vixr_cut.py`(142초): 위 숫자. 로그는 `/tmp/claude-0/-home-user/a406bf43-090f-5192-964f-c483e7203aaa/scratchpad/review3c/logs/ta_vixr_cut.log`.
- `tb_books.py`: 장부 탐침 b1~b10. 로그는 같은 폴더의 `tb_books.log`.
- `tc_world.py`(5초): 합성 세계에서 itest의 미래 자료 더미(PEEK_SRC)를 심사를 건너뛰어 등록 → 실제 불일치로 종료. 로그는 `tc_world.log`.
- 정적 검사 탐침 7건.
- 그쪽 로그(`r3check/logs/`의 t3·t4·t5, 심사 보고 4건)를 읽었고 적어 준 결과와 맞다. selftest와 itest는 다시 돌리지 않았다.

확인하지 못한 것: 23시 가드 재확인과 12회 건너뜀 종료는 읽기만 했다. 불일치 + 보류가 겹친 경우는 itest의 모의 경로와 내 실제 경로를 따로 확인했고, 둘을 한 번에 돌리지는 않았다. R3-1을 고치면 그 한 줄은 내가 보지 않은 변경이 된다(itest 재실행으로 충분하다).
