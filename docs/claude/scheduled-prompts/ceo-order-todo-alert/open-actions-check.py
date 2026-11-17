#!/usr/bin/env python3
"""Read-only check of the CEO's open order actions (alert-strengthen-1117).

usage: python3 -I open-actions-check.py <repo_root> <today_kst YYYY-MM-DD>
reads : docs/claude/ceo-open-actions.json (ledger, written only by interactive sessions)
        workspace/outputs/auto-core/<run day>/s7/<session>/portfolio-exposure-review.*.json (newest session)
prints: one JSON object {items:[{id,state,line,push,weight,session}], status}
No writes, no network, no broker calls. Missing or stale data -> state "unknown" (the reminder is still sent).
"""
import glob, json, os, re, sys

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def newest_s7(root):
    best = None
    for p in glob.glob(os.path.join(root, "workspace", "outputs", "auto-core", "*", "s7", "*",
                                    "portfolio-exposure-review.*.json")):
        sess = os.path.basename(os.path.dirname(p))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", sess):
            continue
        key = (sess, os.path.basename(p))
        if best is None or key > best[0]:
            best = (key, p)
    return (best[1], best[0][0]) if best else (None, None)

def main():
    root, today = sys.argv[1], sys.argv[2]
    out = {"schema": "ceo-open-actions-check-1.0", "today_kst": today, "status": "OK", "items": []}
    try:
        led = load(os.path.join(root, "docs", "claude", "ceo-open-actions.json"))
    except (OSError, ValueError) as e:
        out["status"] = "LEDGER_UNREADABLE"
        out["error"] = type(e).__name__
        print(json.dumps(out, ensure_ascii=False))
        return
    s7p, sess = newest_s7(root)
    pos = {}
    if s7p:
        try:
            for x in load(s7p).get("positions", []):
                if isinstance(x, dict) and x.get("symbol"):
                    pos[x["symbol"]] = x.get("weight")
        except (OSError, ValueError):
            s7p = None
    for it in led.get("items", []):
        if it.get("status") != "open":
            continue
        sym, side, done = it.get("symbol"), it.get("side"), it.get("done") or {}
        r = {"id": it.get("id"), "state": "unknown", "weight": None, "session": sess}
        w = pos.get(sym) if s7p else None
        if s7p and sym not in pos and side == "sell":
            w = 0.0                      # no longer held -> fully sold
        if isinstance(w, (int, float)):
            r["weight"] = round(w, 4)
            kind, v = done.get("kind"), done.get("value")
            if kind == "weight_le" and isinstance(v, (int, float)):
                r["state"] = "done" if w <= v else "open"
            elif kind == "weight_gt" and isinstance(v, (int, float)):
                r["state"] = "done" if w > v else "open"
        wtxt = f"{r['weight'] * 100:.1f}%({sess[5:].replace('-', '/')} 종가 기준)" if r["weight"] is not None else "비중 확인 필요"
        tgt = done.get("value")
        tgt_txt = f"{tgt * 100:g}%" if isinstance(tgt, (int, float)) else "확인 필요"
        title = it.get("title", sym)
        if r["state"] == "done":
            r["line"] = f"✅ 완료 확인: {title} — 지금 {wtxt}, 목표 {tgt_txt}"
            r["push"] = None
        else:
            head = "🔴 사장님 주문 할 일" if side == "sell" else "🟢 사장님 주문 할 일"
            since = f"{it.get('alerts_md', '')} 뒤 아직 계좌에 반영 안 됨"
            r["line"] = (f"{head}: {title} — 지금 {wtxt} → 목표 {tgt_txt} · {it.get('decision_short', '')} · "
                         f"{since} · 수량은 주문 전 점검 · 키움 입력은 사장 직접(시스템은 수량·가격 제안 없음)")
            r["push"] = (f"{head}: {title} — 지금 {wtxt}, 목표 {tgt_txt} · "
                         f"{it.get('alerts_md', '')} 뒤 미반영 · 키움 직접")
        out["items"].append(r)
    if not s7p:
        out["status"] = "S7_MISSING"
    print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()
