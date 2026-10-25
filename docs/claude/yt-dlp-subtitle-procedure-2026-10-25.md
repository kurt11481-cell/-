---
id: yt-dlp-subtitle-procedure-2026-10-25
type: procedure
status: current
as_of: 2026-10-25
summary: "공개 YouTube 영상 자막만 받는 yt-dlp 시험 절차와 결과 기록. 격리 폴더·고정 버전·쿠키 미사용."
consumers: "사장실 코디네이터 · 회사PC 스레드"
authority: "order_authority=false · quantity_authority=none · 기록용. 가격·재무 증거가 아니고 커뮤니티·AI 자료와 같은 가설 등급"
source_decision: "사장 2026-10-25 KST(스레드 직접 입력) 'yt-dlp 자막 시험 승인', 이어 이 문서 1개 쓰기와 active-decisions.md 한 줄 추가 허용"
---

# yt-dlp 자막 시험 절차 (2026-10-25)

## 범위 (사장 승인된 것만)
- 코덱스저장소 밖 전용 폴더 `%USERPROFILE%\yt-dlp-test`에 파이썬 venv, `yt-dlp==2026.8.19` 하나만 설치.
- 공개 YouTube 영상 1개에서 자막만 받는다. 쿠키·로그인·`--cookies-from-browser` 사용 금지.
- 하지 않음: 코덱스저장소·.env·토큰·계좌 파일 접근, 키움 도구, 주문, 다른 패키지, 전역 설치, PATH·설정 변경.

## 절차 (PowerShell)
```powershell
$d="$env:USERPROFILE\yt-dlp-test"; New-Item -ItemType Directory -Force $d | Out-Null; cd $d
python -m venv venv
.\venv\Scripts\python.exe -m pip install yt-dlp==2026.8.19
.\venv\Scripts\python.exe -I -m yt_dlp --skip-download --write-subs --write-auto-subs --sub-langs "en" --sub-format vtt -o "out\%(id)s.%(ext)s" "<공개 영상 URL>"
```

## 결과
| 항목 | 내용 |
|---|---|
| Python | 3.13.15 |
| yt-dlp | 2026.08.19 (정확히 고정 버전 설치됨) |
| 1차 영상 jNQXAC9IWjw | 실패: `ERROR: [youtube] jNQXAC9IWjw: This video is unavailable` |
| 2차 영상 dQw4w9WgXcQ | 성공: `out\dQw4w9WgXcQ.en.vtt` 4,263바이트, 영어 자막 1개 |
| 경고(오류 아님) | deno JS challenge solver 원격 구성요소 생략으로 서명·n challenge 일부 포맷 누락 경고, impersonation 대상 없음 경고. 자막 받기에는 영향 없음 |
| 자막 형식 | `WEBVTT` 헤더 3줄 뒤 `시간 --> 시간` + 텍스트 블록 (가사 본문은 저작권이라 기록하지 않음) |

2026-10-25 재점검: venv에서 `yt_dlp --version` = 2026.08.19, 자막 파일 그대로 있음.

## 한계 (확인 필요)
- 영상 1개(성공 1, 실패 1)만 시험했다. 다른 영상·언어·자동 자막 전용 영상에서의 성공률은 모른다.
- 자막은 커뮤니티·AI 등급의 가설 자료다. 투자 판단의 증거는 가격·계좌 = 키움, 재무 = SEC·공식 자료.
- YouTube 쪽 변경으로 같은 명령이 나중에 실패할 수 있다(위 1차 실패 사유는 영상 쪽 문제인지 도구 문제인지 확인 못 함).

## 지우는 법
```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\yt-dlp-test"
```
