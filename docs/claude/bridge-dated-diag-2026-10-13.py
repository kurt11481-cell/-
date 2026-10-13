# Read-only check of the auto-core bridge's other dated account reads with their exact bridge bodies:
# ust21150 (daily fills) and ust21610 (day trades), after ust21100 failed on a required empty field (1511).
# Cowork, 2026-10-13. Run with the Kiwoom runtime python (same as the bridge worker). ASCII only.
# Calls each (/api/us/acnt, account inquiry) for two dates and prints only return_code, the return_msg with
# account-like numbers masked, the row count and the non-date body keys.
# No row content, no account label, no order route, no file written, no token reissue beyond normal reuse.
import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "manage-us-stock-strategy" / "scripts"))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import kiwoom_runtime_bridge as rb  # noqa: E402
import kiwoom_account_readonly_bridge as ab  # noqa: E402

policy = json.loads((REPO / "workspace" / "policies" / "kiwoom-readonly-policy.json").read_text(encoding="utf-8"))
runtime = Path(policy["official_runtime_path"]).resolve()
os.chdir(runtime)
rb._load_env_without_echo(runtime / ".env")
session = rb._runtime_session(runtime, 0.5, 1, 1.0, set(), set(), 1, 0, 1, 1)
checks = [
    ("D_ust21150_daily_fills_20261009", "account_daily_fills_read", {"ord_dt": "20261009"}),
    ("E_ust21150_daily_fills_20261012", "account_daily_fills_read", {"ord_dt": "20261012"}),
    ("F_ust21610_day_trades_20261009", "account_day_trades_read", {"base_dt": "20261009"}),
    ("G_ust21610_day_trades_20261012", "account_day_trades_read", {"base_dt": "20261012"}),
]


def mask(text):
    text = re.sub(r"\d{2,}-\d{2,}-\d{1,}", "<ACNT>", text)
    return re.sub(r"\d{8,}", "<N>", text)


for name, operation, params in checks:
    api_id, path = ab.ACCOUNT_APIS[operation]
    if path != "/api/us/acnt" or api_id not in ("ust21150", "ust21610"):
        raise SystemExit("UNEXPECTED_ROUTE")
    body = ab.request_body(ab.validate_request({"operation": operation, "params": params}))
    keys = {k: v for k, v in body.items() if k not in ("ord_dt", "base_dt")}
    try:
        session["pacer"]()
        response = session["client"].fetch_page(api_id=api_id, path=path, body=body, cont_yn=None, next_key=None)
        payload = getattr(response, "body", None)
        if not isinstance(payload, dict):
            print(name, "NON_DICT_PAYLOAD", type(payload).__name__)
        else:
            rows = payload.get("result_list")
            print(name, "return_code=%r" % (payload.get("return_code"),),
                  "msg=" + mask(str(payload.get("return_msg"))),
                  "rows=%s" % (len(rows) if isinstance(rows, list) else None),
                  "body_keys=" + json.dumps(keys))
    except Exception as exc:  # print the type and a masked, short message only
        print(name, "EXCEPTION", type(exc).__name__, mask(str(exc))[:200], "body_keys=" + json.dumps(keys))
    time.sleep(1.0)
print("BRIDGE_DATED_DIAG_DONE")
