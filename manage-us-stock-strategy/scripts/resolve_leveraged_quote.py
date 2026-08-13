#!/usr/bin/env python3
"""Attach independently sourced close evidence to a leveraged-product snapshot.

The proxy relationship is corroborative only. A proxy return can identify an
implausible leveraged-product quote, but it can never replace a direct,
same-session completed close for the leveraged product itself.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class QuoteResolutionError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QuoteResolutionError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise QuoteResolutionError("snapshot top level must be an object")
    return value


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def finite_positive(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0
    )


def valid_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def leveraged_proxy_check(
    product_row: dict[str, Any],
    proxy_row: dict[str, Any],
    *,
    proxy_symbol: str,
    leverage_multiple: float,
    maximum_tracking_error_fraction: float,
) -> dict[str, Any]:
    required = {
        "product_close": product_row.get("close"),
        "product_previous_close": product_row.get("close_prev"),
        "proxy_close": proxy_row.get("close"),
        "proxy_previous_close": proxy_row.get("close_prev"),
    }
    invalid = [name for name, value in required.items() if not finite_positive(value)]
    if invalid:
        raise QuoteResolutionError(
            "leveraged proxy check lacks positive finite inputs: " + ", ".join(invalid)
        )
    if product_row.get("bar_date") != proxy_row.get("bar_date"):
        raise QuoteResolutionError("product and proxy bar dates do not match")
    if not math.isfinite(leverage_multiple) or leverage_multiple <= 0:
        raise QuoteResolutionError("leverage multiple must be positive and finite")
    if not math.isfinite(maximum_tracking_error_fraction) or maximum_tracking_error_fraction <= 0:
        raise QuoteResolutionError("tracking-error tolerance must be positive and finite")

    product_return = float(required["product_close"]) / float(required["product_previous_close"]) - 1.0
    proxy_return = float(required["proxy_close"]) / float(required["proxy_previous_close"]) - 1.0
    expected_return = leverage_multiple * proxy_return
    tracking_error = product_return - expected_return
    corroborated = abs(tracking_error) <= maximum_tracking_error_fraction
    return {
        "status": "corroborated" if corroborated else "outside_tolerance",
        "role": "supplemental_integrity_check_not_a_quote_substitute",
        "proxy_symbol": proxy_symbol,
        "bar_date": product_row.get("bar_date"),
        "leverage_multiple": leverage_multiple,
        "product_return_fraction": product_return,
        "proxy_return_fraction": proxy_return,
        "expected_product_return_fraction": expected_return,
        "tracking_error_fraction": tracking_error,
        "maximum_tracking_error_fraction": maximum_tracking_error_fraction,
        "required_for_resolution": True,
    }


def resolve_independent_product_close(product_row: dict[str, Any], *, independent_close: float,
                                      bar_date: str) -> dict[str, Any]:
    """Resolve only the direct product close; proxy evidence is deliberately excluded."""
    if product_row.get("bar_date") != bar_date:
        raise QuoteResolutionError("direct product close and product bar date do not match")
    if not finite_positive(product_row.get("close")) or not finite_positive(independent_close):
        raise QuoteResolutionError("direct and primary product closes must be positive and finite")
    primary = float(product_row["close"])
    difference = abs(primary - float(independent_close))
    tolerance = max(0.05, 0.001 * primary)
    if difference > tolerance + 1e-12:
        raise QuoteResolutionError(f"direct independent close differs by {difference:.8f}, above {tolerance:.8f}")
    return {"status": "verified", "difference_usd": difference, "tolerance_usd": tolerance,
            "completed_close": float(independent_close)}


def evaluate_leveraged_confirmation(product_row: dict[str, Any], proxy_row: dict[str, Any], *,
                                    profile: dict[str, Any],
                                    tracking_tolerance_fraction: float | None = None) -> dict[str, Any]:
    """Evaluate a registry-driven proxy relationship without substituting the product close."""
    proxy_symbol = profile.get("confirmation_proxy")
    mode = profile.get("confirmation_mode")
    role = profile.get("confirmation_role")
    if not proxy_symbol or mode not in {"DIRECTION_ONLY", "DAILY_MULTIPLE"}:
        return {"status": "NOT_APPLICABLE", "proxy_symbol": proxy_symbol, "confirmation_mode": mode,
                "confirmation_role": role, "product_close_substitution": False}
    if product_row.get("bar_date") != proxy_row.get("bar_date"):
        return {"status": "UNAVAILABLE", "reason": "SESSION_MISMATCH", "proxy_symbol": proxy_symbol,
                "confirmation_mode": mode, "confirmation_role": role, "product_close_substitution": False}
    required = (product_row.get("close"), product_row.get("close_prev"), proxy_row.get("close"), proxy_row.get("close_prev"))
    if not all(finite_positive(value) for value in required):
        return {"status": "UNAVAILABLE", "reason": "RETURN_INPUT_UNAVAILABLE", "proxy_symbol": proxy_symbol,
                "confirmation_mode": mode, "confirmation_role": role, "product_close_substitution": False}
    product_return = float(product_row["close"]) / float(product_row["close_prev"]) - 1.0
    proxy_return = float(proxy_row["close"]) / float(proxy_row["close_prev"]) - 1.0
    common = {"proxy_symbol": proxy_symbol, "confirmation_mode": mode, "confirmation_role": role,
              "daily_target_multiple": profile.get("daily_target_multiple"),
              "product_return_fraction": product_return, "proxy_return_fraction": proxy_return,
              "product_close_substitution": False}
    if mode == "DIRECTION_ONLY":
        aligned = product_return == 0 or proxy_return == 0 or (product_return > 0) == (proxy_return > 0)
        return {**common, "status": "ALIGNED" if aligned else "DIVERGED",
                "exact_multiple_comparison_performed": False}
    multiple = profile.get("daily_target_multiple")
    if not isinstance(multiple, (int, float)) or not math.isfinite(float(multiple)) or float(multiple) <= 0:
        return {**common, "status": "UNAVAILABLE", "reason": "DAILY_TARGET_MULTIPLE_UNVERIFIED"}
    expected = float(multiple) * proxy_return
    tracking = product_return - expected
    if tracking_tolerance_fraction is None:
        return {**common, "status": "SHADOW_ONLY", "expected_product_return_fraction": expected,
                "tracking_difference_fraction": tracking, "tolerance_authority": "SHADOW_ONLY_UNAPPROVED"}
    if not math.isfinite(tracking_tolerance_fraction) or tracking_tolerance_fraction <= 0:
        raise QuoteResolutionError("policy-supplied tracking tolerance must be positive and finite")
    return {**common, "status": "ALIGNED" if abs(tracking) <= tracking_tolerance_fraction else "DIVERGED",
            "expected_product_return_fraction": expected, "tracking_difference_fraction": tracking,
            "maximum_tracking_error_fraction": tracking_tolerance_fraction,
            "tolerance_authority": "POLICY_SUPPLIED"}
def resolve(
    snapshot: dict[str, Any],
    *,
    symbol: str,
    independent_close: float,
    source: str,
    source_url: str,
    source_field: str,
    bar_date: str,
    proxy_symbol: str | None = None,
    leverage_multiple: float | None = None,
    maximum_tracking_error_fraction: float | None = None,
    conflict_note: str | None = None,
) -> dict[str, Any]:
    symbols = snapshot.get("symbols")
    if not isinstance(symbols, dict) or not isinstance(symbols.get(symbol), dict):
        raise QuoteResolutionError(f"snapshot is missing symbol {symbol}")
    row = symbols[symbol]
    session_date = (snapshot.get("session") or {}).get("us_session_date")
    if not isinstance(session_date, str) or not session_date:
        raise QuoteResolutionError("snapshot session date is missing")
    if bar_date != session_date or row.get("bar_date") != session_date:
        raise QuoteResolutionError("direct quote, product bar, and session must share one date")
    if not finite_positive(independent_close) or not finite_positive(row.get("close")):
        raise QuoteResolutionError("direct and builder closes must be positive and finite")
    if not source.strip() or not valid_https_url(source_url):
        raise QuoteResolutionError("direct independent quote provenance is incomplete")
    if source_field != "raw_completed_regular_session_close":
        raise QuoteResolutionError(
            "independent source field must be raw_completed_regular_session_close"
        )

    direct_result = resolve_independent_product_close(row, independent_close=independent_close, bar_date=bar_date)
    direct_close = direct_result["completed_close"]
    difference = direct_result["difference_usd"]
    tolerance = direct_result["tolerance_usd"]

    proxy_check = None
    if proxy_symbol is not None or leverage_multiple is not None:
        if not proxy_symbol or leverage_multiple is None:
            raise QuoteResolutionError("proxy symbol and leverage multiple must be supplied together")
        proxy_row = symbols.get(proxy_symbol)
        if not isinstance(proxy_row, dict):
            raise QuoteResolutionError(f"snapshot is missing proxy symbol {proxy_symbol}")
        profile = {"confirmation_proxy": proxy_symbol, "confirmation_role": "DIRECT_UNDERLYING",
                   "confirmation_mode": "DAILY_MULTIPLE", "daily_target_multiple": leverage_multiple}
        proxy_check = evaluate_leveraged_confirmation(row, proxy_row, profile=profile,
                                                      tracking_tolerance_fraction=maximum_tracking_error_fraction)
        if maximum_tracking_error_fraction is not None and proxy_check["status"] == "DIVERGED":
            raise QuoteResolutionError("direct close passed but the leveraged proxy relationship is outside policy tolerance")
        if maximum_tracking_error_fraction is not None:
            # Preserve the v2.4 validator envelope while the canonical v2.5
            # evaluator remains registry-driven and separately callable.
            proxy_check = {
                **proxy_check,
                "status": "corroborated" if proxy_check["status"] == "ALIGNED" else "outside_tolerance",
                "role": "supplemental_integrity_check_not_a_quote_substitute",
                "bar_date": row.get("bar_date"),
                "leverage_multiple": float(leverage_multiple),
                "tracking_error_fraction": proxy_check.get("tracking_difference_fraction"),
                "maximum_tracking_error_fraction": maximum_tracking_error_fraction,
                "required_for_resolution": True,
            }

    row["quote_crosscheck"] = {
        "status": "verified",
        "independent_of_builder": True,
        "source": source.strip(),
        "source_url": source_url,
        "source_field": source_field,
        "bar_date": bar_date,
        "completed_close": direct_close,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "difference_usd": difference,
        "tolerance_usd": tolerance,
        "conflict_status": "resolved_with_direct_close_and_proxy_corroboration"
        if conflict_note
        else "none_reported",
        "conflict_note": conflict_note,
        "leveraged_proxy_check": proxy_check,
    }
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--bar-date", required=True)
    parser.add_argument("--independent-close", type=float, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument(
        "--source-field",
        default="raw_completed_regular_session_close",
        choices=["raw_completed_regular_session_close"],
    )
    parser.add_argument("--proxy-symbol")
    parser.add_argument("--leverage-multiple", type=float)
    parser.add_argument("--maximum-tracking-error-fraction", type=float)
    parser.add_argument("--conflict-note")
    args = parser.parse_args()
    try:
        resolved = resolve(
            read_json(args.snapshot),
            symbol=args.symbol,
            independent_close=args.independent_close,
            source=args.source,
            source_url=args.source_url,
            source_field=args.source_field,
            bar_date=args.bar_date,
            proxy_symbol=args.proxy_symbol,
            leverage_multiple=args.leverage_multiple,
            maximum_tracking_error_fraction=args.maximum_tracking_error_fraction,
            conflict_note=args.conflict_note,
        )
        atomic_write_json(args.output, resolved)
        print(json.dumps(resolved["symbols"][args.symbol]["quote_crosscheck"], indent=2))
        return 0
    except QuoteResolutionError as exc:
        print(f"QUOTE_RESOLUTION_ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
