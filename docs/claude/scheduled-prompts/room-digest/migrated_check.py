#!/usr/bin/env python3
"""사장실 이관 예약 지시문 대조 v2 (지침 v2.19 4절 ⑧, schedule-to-room-1124).
사용: python3 -I migrated_check.py <room-migrated.json> <triggers.json> [<now UTC ISO>|-] [<body_path>=<받은 파일> ...]
 triggers.json = 배열. 항목: id, name, updated_at, enabled, cron_expression, model, prompt_hashes
   (prompt_hashes = 그 예약 지시문에 들어 있는 64자리 16진수 문자열 전부 — 지시문 전체를 옮겨 쓰지 않는다)
 room-migrated.json tasks[]: name, trigger_id, cron, model, body_path, body_sha256(CR 제거 뒤 UTF-8 바이트),
   changes[].at = 승인된 update_trigger/create_trigger 응답의 updated_at 값(ISO, 시간대 포함)
판정: 이관 예약은 창 없이 매번 — 목록에 없음·꺼짐·일정/모델 다름·로더에 본문 해시 없음·본문 해시 다름·
   updated_at이 changes[].at 어느 것과도 ±30분 안에 안 맞음 → RED. 이관 밖 예약은 36시간 안 변경을 INFO.
출력: 'RED …'/'INFO …' 줄, 마지막 'RESULT OK|RED|EMPTY|ERROR …'. 종료 0(OK·EMPTY) 1(RED) 3(ERROR). 읽기만."""
import sys, json, hashlib, re
from datetime import datetime, timedelta, timezone
KST = timezone(timedelta(hours=9))
HEX = re.compile(r"^[0-9a-f]{64}$")

def h(b): return hashlib.sha256(b).hexdigest()
def ts(s):
    m = re.fullmatch(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?(Z|[+-]\d\d:\d\d)", str(s).strip())
    if not m:
        raise ValueError("bad time")
    frac = (m.group(2) or "0")[:6].ljust(6, "0")
    tz = "+00:00" if m.group(3) == "Z" else m.group(3)
    return datetime.fromisoformat(f"{m.group(1)}.{frac}{tz}")
def k(d): return d.astimezone(KST).strftime("%m/%d %H:%M KST")

def main(a):
    if len(a) < 2:
        print("RESULT ERROR usage"); return 3
    try:
        man = json.load(open(a[0], encoding="utf-8"))
        trg = json.load(open(a[1], encoding="utf-8"))
        now = datetime.now(timezone.utc) if len(a) < 3 or a[2] == "-" else ts(a[2])
    except Exception as e:
        print(f"RESULT ERROR input {type(e).__name__}"); return 3
    if not isinstance(trg, list) or not isinstance(man, dict) or not isinstance(man.get("tasks", []), list):
        print("RESULT ERROR shape"); return 3
    bodies = dict(kv.partition("=")[::2] for kv in a[3:])
    tasks = man.get("tasks", [])
    by_id = {t.get("id"): t for t in trg if isinstance(t, dict)}
    red, info = [], []
    for t in tasks:
        n, tid = t["name"], t["trigger_id"]
        tr = by_id.get(tid)
        if tr is None:
            red.append(f"{n}: 예약 목록에 없음(지워졌거나 목록을 다 못 읽음, {tid})"); continue
        if tr.get("enabled") is False:
            red.append(f"{n}: 예약이 꺼져 있음")
        if t.get("cron") is not None and tr.get("cron_expression") != t["cron"]:
            red.append(f"{n}: 일정 다름(지금 {tr.get('cron_expression')} / 기록 {t['cron']})")
        if t.get("model") is not None and (tr.get("model") or "") != t["model"]:
            red.append(f"{n}: 모델 다름(지금 {tr.get('model') or '세션 모델'} / 기록 {t['model'] or '세션 모델'})")
        hs = [x for x in tr.get("prompt_hashes", []) if isinstance(x, str) and HEX.match(x)]
        if t["body_sha256"] not in hs:
            red.append(f"{n}: 로더에 기록된 본문 해시({t['body_sha256'][:8]}…)가 없음")
        f = bodies.get(t["body_path"])
        if not f:
            red.append(f"{n}: 본문 파일 못 받음({t['body_path']})")
        else:
            try:
                b = open(f, "rb").read().replace(b"\r", b"")
                if h(b) != t["body_sha256"]:
                    red.append(f"{n}: 본문 해시 다름(지금 {h(b)[:8]}… / 기록 {t['body_sha256'][:8]}…)")
            except OSError:
                red.append(f"{n}: 본문 파일 못 읽음({t['body_path']})")
        try:
            ut = ts(tr.get("updated_at"))
            ok = any(abs(ts(c["at"]) - ut) <= timedelta(minutes=30) for c in t.get("changes", []))
        except (ValueError, KeyError, TypeError):
            red.append(f"{n}: 변경 시각을 읽지 못함"); ok = True
        if not ok:
            red.append(f"{n}: 승인 기록 없는 예약 변경({k(ut)})")
    ids = {t["trigger_id"] for t in tasks}
    for tr in by_id.values():
        if tr.get("id") in ids: continue
        try:
            ut = ts(tr.get("updated_at"))
        except ValueError:
            continue
        if timedelta(0) <= now - ut <= timedelta(hours=36):
            info.append(f"바뀐 예약(이관 밖): {tr.get('name')} {k(ut)}")
    for r in red: print("RED " + r)
    for i in info: print("INFO " + i)
    if not tasks:
        print("RESULT EMPTY"); return 0
    print("RESULT RED" if red else "RESULT OK")
    return 1 if red else 0

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:
        print(f"RESULT ERROR crash {type(e).__name__}"); sys.exit(3)
