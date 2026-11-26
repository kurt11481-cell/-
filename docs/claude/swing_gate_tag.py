#!/usr/bin/env python3
"""Recovery-gate tag for swing shadow signals (preregistration docs/claude/swing-gate-tag-preregistration-2026-11-26.md).

Read-only over the swing ledger and auto-core records; does not modify swing_shadow_ledger.py, the swing ledger
or the verdict log. No order tool, no network.
  --tag-lines            print tag lines for ledger signals not yet in docs/claude/swing-gate-tag.jsonl
  --report --as-of DAY   counts per group; group mean/t and the section-4 check only when the swing verdict
                         is PASS or CLOSE (fixed swing blinding: no mean/t at CONTINUE)
  --self-test            synthetic checks (prereg 5)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TAGS = "docs/claude/swing-gate-tag.jsonl"
REPORT_LOG = "docs/claude/swing-gate-tag-report.jsonl"   # append-only: first PASS/CLOSE report, followed later
CORE = "workspace/outputs/auto-core"
LATE_DAYS = 7
EXC_MIN_CLUSTERS, EXC_T = 10, 2.3   # prereg 4 (proposed values, fixed by the user's card)


def _swing(repo: Path):
    spec = importlib.util.spec_from_file_location("swing_shadow_ledger", repo / "docs/claude/swing_shadow_ledger.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.REPO = repo
    return mod


def _jsonl(path: Path) -> list[dict]:
    try:
        return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    except OSError:
        return []


def core_records(repo: Path, session: str) -> list[tuple[Path, dict, str]]:
    """Every decision.json whose evaluation_session equals the signal's (folder names are KST run days)."""
    out = []
    for p in sorted((repo / CORE).glob("*/decision.json")):
        try:
            raw = p.read_bytes()
            j = json.loads(raw)
        except (OSError, ValueError):
            continue
        if j.get("evaluation_session") == session:
            out.append((p, j, hashlib.sha256(raw).hexdigest()))
    return out


def _rel(p: Path, repo: Path | None) -> str:
    try:
        return str(p.relative_to(repo)) if repo is not None else str(p)
    except ValueError:
        return str(p)


def tag_of(records: list[tuple[Path, dict, str]], symbol: str, repo: Path | None = None) -> dict:
    if not records:
        return {"status": None, "tag": "unknown", "why": "no core record for this evaluation_session"}
    p, j, _ = max(records, key=lambda r: r[1].get("generated_at") or "")
    cell = ((j.get("shock") or {}).get("by_symbol") or {}).get(symbol)
    if cell is None:
        return {"status": None, "tag": "unknown", "why": "no by_symbol cell", "file": _rel(p, repo)}
    st = cell.get("status")
    tag = {"no": "gate_closed", "ok": "gate_open"}.get(st, "unknown")   # status only; 'open' is not used
    return {"status": st, "tag": tag, "file": _rel(p, repo), "generated_at": j.get("generated_at")}


def tag_line(repo: Path, sig: dict, now: str) -> dict:
    recs = core_records(repo, str(sig.get("evaluation_session")))
    t = tag_of(recs, str(sig.get("symbol")), repo)
    written = str(sig.get("written_at") or "")[:10]
    late = bool(written) and (dt.date.fromisoformat(now[:10]) - dt.date.fromisoformat(written)).days > LATE_DAYS
    return {"signal_id": sig.get("signal_id"), "symbol": sig.get("symbol"),
            "evaluation_session": sig.get("evaluation_session"), **t,
            "candidates": [{"file": _rel(p, repo), "sha256": h,
                            "generated_at": j.get("generated_at")} for p, j, h in recs],
            "tagged_at": now, "late": late}


def new_tag_lines(repo: Path, now: str) -> list[dict]:
    sw = _swing(repo)
    done = {x.get("signal_id") for x in _jsonl(repo / TAGS)}
    return [tag_line(repo, s, now) for s in sw.ledger_signals(repo) if s.get("signal_id") not in done]


def rebuild(sw, as_of: str):
    """Same order and cuts as swing_shadow_ledger.run() (prereg 3); returns trades and the run() output."""
    res = sw.run(as_of)
    if "verdict" not in res:
        return [], res
    sigs = sw.ledger_signals()
    added = sw.roots_added()
    scoped = [s for s in sigs if sw.in_scope(str(s.get("symbol")), str(s.get("record_day", "")), added)]
    cut = lambda c: {d: v for d, v in c.items() if d <= as_of}
    main = [s for s in scoped if str(s.get("record_day", "")) > sw.FIX_DATE and str(s.get("record_day", "")) <= as_of]
    bench = cut(sw.load_closes(sw.BENCH))
    roots = {**{x["symbol"]: x["root"] for x in added}, **sw.ROOT_OF}
    pop = {p: cut(sw.load_closes(p)) for p in roots}
    trades = [sw.trade(x, cut(sw.load_closes(x["symbol"])), bench, sw.HOLD_SESSIONS, sw.COST_BP_ROUND_TRIP, pop)
              for x in main]
    status = {k: sum(1 for t in trades if t["status"] == k) for k in sorted({t["status"] for t in trades})}
    cl = sw.clusters(trades, roots, sw.CLUSTER_RULE)
    assert status == res["trade_status"] and len(cl) == res["clusters"], "rebuilt trades differ from run()"
    for t, s in zip(trades, main):
        t["_signal_id"] = s.get("signal_id")
    return trades, res, roots


def _cut_day(res: dict, repo: Path, as_of: str) -> str:
    """cut_day of the checkpoint that ended the swing variant (PASS/CLOSE); deadline/final close -> as_of."""
    v = res.get("verdict") or {}
    for look in reversed(v.get("looks") or []):
        day = (look.get("new_log_line") or {}).get("cut_day") or look.get("cut_day")
        if day and look.get("result") in ("PASS", "CLOSE"):
            return day
    for line in reversed(_jsonl(repo / "docs/claude/swing-verdict-log.jsonl")):
        if line.get("result") in ("PASS", "CLOSE") and line.get("cut_day"):
            return line["cut_day"]
    return as_of


def report(repo: Path, as_of: str) -> dict:
    logged = _jsonl(repo / REPORT_LOG)
    if logged:
        return {**logged[0], "from_log": True}   # once only: later runs follow the first recorded result
    sw = _swing(repo)
    tags = {x["signal_id"]: x["tag"] for x in _jsonl(repo / TAGS)}
    sigs = sw.ledger_signals(repo)
    counts: dict[str, int] = {}
    for s in sigs:
        k = tags.get(s.get("signal_id"), "untagged")
        counts[k] = counts.get(k, 0) + 1
    out = {"as_of": as_of, "signal_counts": counts, "ledger_lines": len(sigs), "tag_lines": len(tags)}
    if len(tags) != len(sigs):
        out["warning"] = "ledger lines != tag lines (run --tag-lines)"
    res = sw.run(as_of)
    v = (res.get("verdict") or {}).get("verdict")
    out["swing_verdict"] = v
    if v not in ("PASS", "CLOSE"):
        return out                     # blinding: counts only
    trades, res, roots = rebuild(sw, as_of)
    cut = _cut_day(res, repo, as_of)
    trades = [t for t in trades if t["status"] == "CLOSED" and t.get("exit") and t["exit"] <= cut]
    out["cut_day"] = cut
    groups = {}
    for g in ("gate_closed", "gate_open", "unknown"):
        tg = [t for t in trades if tags.get(t["_signal_id"], "unknown") == g]
        cl = sw.clusters(tg, roots, sw.CLUSTER_RULE)
        st = sw.stats([(c["entry"], c["excess"]) for c in cl])
        groups[g] = {"clusters": len(cl), "mean": st["mean"], "t": st["t"]}
    c = groups["gate_closed"]
    out["groups"] = groups
    out["new_report_line"] = True   # append this output once to REPORT_LOG (by hand, _pending commit)
    out["exception_agenda"] = bool(c["clusters"] >= EXC_MIN_CLUSTERS and c["mean"] is not None and c["mean"] > 0
                                   and c["t"] is not None and c["t"] >= EXC_T)
    return out


def selftest() -> None:
    recs = lambda cell, gen="2026-11-25T22:45:00+00:00": [(Path("a/decision.json"), {
        "generated_at": gen, "shock": {"by_symbol": {} if cell is None else {"MU": cell}}}, "h")]
    assert tag_of(recs({"status": "no", "open": True}), "MU")["tag"] == "gate_closed"
    assert tag_of(recs({"status": "no", "open": False}), "MU")["tag"] == "gate_closed"   # official damage
    assert tag_of(recs({"status": "ok", "open": False}), "MU")["tag"] == "gate_open"
    assert tag_of(recs({"status": "unk", "open": None}), "MU")["tag"] == "unknown"
    assert tag_of(recs(None), "MU")["tag"] == "unknown"                                   # no cell (wider six)
    assert tag_of([], "MU")["tag"] == "unknown"
    two = recs({"status": "ok"}, "2026-11-25T10:00:00+00:00") + recs({"status": "no"}, "2026-11-25T22:00:00+00:00")
    assert tag_of(two, "MU")["tag"] == "gate_closed"                                      # latest generated_at
    # 5-3 / 5-4 on a temporary repo copy with fake ledger and a CONTINUE swing verdict
    import tempfile
    import types
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "docs/claude").mkdir(parents=True)
        (root / "workspace/outputs/auto-core/2026-11-03").mkdir(parents=True)
        (root / "workspace/outputs/auto-core/2026-11-03/decision.json").write_text(json.dumps(
            {"evaluation_session": "2026-11-02", "generated_at": "x",
             "shock": {"by_symbol": {"MU": {"status": "no"}}}}), encoding="utf-8")
        sig = {"signal_id": "MU-1", "symbol": "MU", "evaluation_session": "2026-11-02", "written_at": "2026-11-03"}
        fake = types.SimpleNamespace(ledger_signals=lambda repo=None: [sig],
                                     run=lambda as_of: {"verdict": {"verdict": "CONTINUE"}})
        global _swing
        real = _swing
        _swing = lambda repo: fake
        try:
            first = new_tag_lines(root, "2026-11-03T10:00:00+09:00")
            assert len(first) == 1 and first[0]["tag"] == "gate_closed" and not first[0]["file"].startswith("/")
            (root / TAGS).write_text(json.dumps(first[0]) + "\n", encoding="utf-8")
            assert new_tag_lines(root, "2026-11-04T10:00:00+09:00") == []                  # 5-3 no repeat
            rep = report(root, "2026-11-04")
            assert "groups" not in rep and "exception_agenda" not in rep                    # 5-4 counts only
            assert rep["signal_counts"] == {"gate_closed": 1}
        finally:
            _swing = real
    print("self-test ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(REPO))
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--tag-lines", action="store_true")
    g.add_argument("--report", action="store_true")
    g.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    repo = Path(a.repo)
    if a.self_test:
        selftest()
    elif a.tag_lines:
        now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds")
        for line in new_tag_lines(repo, now):
            print(json.dumps(line, ensure_ascii=False))
    else:
        print(json.dumps(report(repo, a.as_of), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
