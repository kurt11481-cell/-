#!/usr/bin/env python3
"""Two-window, point-in-time event ingestion without historical backfill."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Iterable

from current_event_risk import PRIMARY_SOURCE_TYPES


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("TIMEZONE_AWARE_TIMESTAMP_REQUIRED")
    return parsed


def build_refresh_windows(*, previous_post_close_cutoff: str,
                          preopen_cutoff: str, postclose_cutoff: str) -> dict[str, Any]:
    previous = _time(previous_post_close_cutoff)
    preopen = _time(preopen_cutoff)
    postclose = _time(postclose_cutoff)
    if not previous < preopen < postclose:
        raise ValueError("EVENT_REFRESH_WINDOW_ORDER_INVALID")
    return {
        "PRE_OPEN_EVENT_REFRESH": {"start_exclusive": previous_post_close_cutoff, "end_inclusive": preopen_cutoff},
        "POST_CLOSE_EVENT_REFRESH": {"start_exclusive": preopen_cutoff, "end_inclusive": postclose_cutoff},
        "order_authority": False,
    }


def ingest_window(events: Iterable[dict[str, Any]], *, window: dict[str, str],
                  run_id: str, previously_seen_event_ids: set[str]) -> dict[str, Any]:
    start, end = _time(window["start_exclusive"]), _time(window["end_inclusive"])
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen = set(previously_seen_event_ids)
    for original in events:
        event = deepcopy(original)
        event_id = str(event.get("event_id") or "")
        if not event_id or event_id in seen:
            rejected.append({"event_id": event_id, "reason": "DUPLICATE_EVENT_ID"})
            continue
        try:
            published = _time(str(event.get("published_at")))
            retrieved = _time(str(event.get("retrieved_at")))
            cutoff = _time(str(event.get("analysis_cutoff")))
        except (TypeError, ValueError):
            rejected.append({"event_id": event_id, "reason": "EVENT_TIMESTAMP_INVALID"})
            continue
        if event.get("source_type") not in PRIMARY_SOURCE_TYPES:
            rejected.append({"event_id": event_id, "reason": "PRIMARY_SOURCE_REQUIRED"})
            continue
        if published > cutoff or retrieved > cutoff or cutoff != end:
            rejected.append({"event_id": event_id, "reason": "FUTURE_OR_CUTOFF_VIOLATION"})
            continue
        if not start < published <= end:
            rejected.append({"event_id": event_id, "reason": "OUTSIDE_REFRESH_WINDOW"})
            continue
        event["first_seen_run_id"] = event.get("first_seen_run_id") or run_id
        event["newly_discovered"] = event_id not in previously_seen_event_ids
        event["order_authority"] = False
        accepted.append(event)
        seen.add(event_id)
    return {"events": accepted, "rejected": rejected,
            "seen_event_ids": sorted(seen), "order_authority": False}
