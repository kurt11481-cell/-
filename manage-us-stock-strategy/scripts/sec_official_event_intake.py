#!/usr/bin/env python3
"""Read-only SEC EDGAR official event intake v0.1.

This module intentionally owns no scheduler, broker, portfolio mutation, policy
mutation, or order path. Network access is constrained to the two SEC hosts in
``ALLOWED_HOSTS`` and every HTTP attempt is counted exactly.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from validation_common import file_hash, load_json, validate_instance


ROOT = Path(__file__).resolve().parents[2]
PIPELINE_VERSION = "0.1"
RUN_MODE = "ONE_SHOT_LIVE_SHADOW"
DEFAULT_LOOKBACK_DAYS = 14
MAX_REQUESTS_PER_SECOND = 1
MIN_REQUEST_INTERVAL_SECONDS = 1.0
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RETRIES = 3
ALLOWED_HOSTS = frozenset({"www.sec.gov", "data.sec.gov"})
TICKER_ASSOCIATION_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SUBMISSIONS_URL_TEMPLATE = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_API_DOCUMENTATION_URL = "https://www.sec.gov/edgar/sec-api-documentation"
SEC_FAIR_ACCESS_URL = "https://www.sec.gov/about/developer-resources"

DEFAULT_OUTPUT_ROOT = ROOT / "workspace/outputs/official-event-intake/sec"
DEFAULT_RULES_PATH = ROOT / "manage-us-stock-strategy/assets/sec-official-event-intake-rules-v0.1.json"
EVENTS_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/sec-official-normalized-events.schema.json"
VALIDATION_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/sec-official-validation-report.schema.json"
MANIFEST_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/sec-official-run-manifest.schema.json"
DEFAULT_PORTFOLIO_ARTIFACT_ROOT = ROOT / "workspace/outputs/manual-portfolio-analysis"
DEFAULT_PORTFOLIO_PATH = ROOT / "stock-strategy-system/portfolio_state.json"
DEFAULT_POLICY_PATH = ROOT / "stock-strategy-system/alert_policy.json"

IMPACT_RANK = {
    "NO_CHANGE": 0,
    "WATCH": 1,
    "ASSET_REVIEW_REQUIRED": 2,
    "PORTFOLIO_RECOMPILE_REQUIRED": 3,
}
MATERIALITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

DISPLAY_LABELS = {
    "ASSET_REVIEW_REQUIRED": "확인 필요한 종목이 있습니다",
    "PORTFOLIO_RECOMPILE_REQUIRED": "포트폴리오 재검토가 필요합니다",
    "WATCH": "관찰 필요",
    "NO_CHANGE": "별도 행동 필요 없음",
    "CURRENT_RUN": "최신 자동 실행 결과",
    "LAST_KNOWN": "이전 정상 결과",
    "BASELINE_ONLY": "비교할 이전 결과 없음",
    "READ_FILING": "공시 내용 확인 필요",
    "NONE": "별도 행동 필요 없음",
}
FORM_LABELS = {
    "10-Q": "분기보고서",
    "10-K": "연차보고서",
    "8-K": "중요 수시공시",
    "6-K": "해외기업 수시공시",
    "424B2": "증권 발행 관련 보충자료",
    "424B3": "증권 발행 관련 보충자료",
}
MATERIALITY_LABELS = {"HIGH": "높음", "MEDIUM": "보통", "LOW": "낮음"}


class IntakeError(RuntimeError):
    """Deterministic fail-closed intake error."""

    def __init__(self, code: str, detail: str = "", *, scope: str = "RUN") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail
        self.scope = scope


@dataclass(frozen=True)
class SecResponse:
    """Raw response plus non-secret retrieval metadata."""

    url: str
    endpoint: str
    status: int
    content_type: str
    body: bytes
    headers: dict[str, str]
    retrieved_at: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()


@dataclass
class RequestAccounting:
    http_request_count: int = 0
    successful_request_count: int = 0
    failed_request_count: int = 0
    retry_count: int = 0
    host_counts: dict[str, int] = field(default_factory=dict)
    endpoint_counts: dict[str, int] = field(default_factory=dict)
    status_code_counts: dict[str, int] = field(default_factory=dict)

    def record_attempt(self, url: str, endpoint: str) -> None:
        host = urlparse(url).hostname or "UNKNOWN"
        self.http_request_count += 1
        self.host_counts[host] = self.host_counts.get(host, 0) + 1
        self.endpoint_counts[endpoint] = self.endpoint_counts.get(endpoint, 0) + 1

    def record_status(self, status: int | str) -> None:
        key = str(status)
        self.status_code_counts[key] = self.status_code_counts.get(key, 0) + 1
        if status == 200:
            self.successful_request_count += 1
        else:
            self.failed_request_count += 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "http_request_count": self.http_request_count,
            "successful_request_count": self.successful_request_count,
            "failed_request_count": self.failed_request_count,
            "retry_count": self.retry_count,
            "host_counts": dict(sorted(self.host_counts.items())),
            "endpoint_counts": dict(sorted(self.endpoint_counts.items())),
            "status_code_counts": dict(sorted(self.status_code_counts.items())),
        }


Transport = Callable[[str, dict[str, str], float], tuple[int, dict[str, str], bytes]]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_sec_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise IntakeError("NETWORK_SCOPE_VIOLATION", url)
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise IntakeError("NETWORK_SCOPE_VIOLATION", url)


def _default_transport(url: str, headers: dict[str, str], timeout: float) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), dict(exc.headers.items()) if exc.headers else {}, exc.read()


class SecAdapter:
    """Strict sequential SEC client with bounded retries and exact accounting."""

    def __init__(
        self,
        *,
        user_agent: str | None = None,
        transport: Transport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._user_agent = (user_agent if user_agent is not None else os.environ.get("SEC_USER_AGENT", "")).strip()
        self._transport = transport or _default_transport
        self._sleep = sleep
        self._monotonic = monotonic
        self.timeout_seconds = float(timeout_seconds)
        self.max_retries = int(max_retries)
        self.accounting = RequestAccounting()
        self._last_request_started: float | None = None

    @property
    def user_agent_configured(self) -> bool:
        return bool(self._user_agent)

    @property
    def user_agent_sha256(self) -> str | None:
        if not self._user_agent:
            return None
        return hashlib.sha256(self._user_agent.encode("utf-8")).hexdigest()

    def _require_user_agent(self) -> None:
        if not self._user_agent:
            raise IntakeError("SEC_USER_AGENT_REQUIRED")

    def _wait_for_rate_limit(self) -> None:
        now = self._monotonic()
        if self._last_request_started is not None:
            remaining = MIN_REQUEST_INTERVAL_SECONDS - (now - self._last_request_started)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_started = self._monotonic()

    def request_json(self, url: str, endpoint: str) -> tuple[SecResponse, Any]:
        self._require_user_agent()
        validate_sec_url(url)
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }
        for attempt in range(self.max_retries + 1):
            self._wait_for_rate_limit()
            self.accounting.record_attempt(url, endpoint)
            try:
                status, response_headers, body = self._transport(url, headers, self.timeout_seconds)
            except (OSError, TimeoutError, urllib.error.URLError) as exc:
                self.accounting.record_status("NETWORK_ERROR")
                if attempt < self.max_retries:
                    self.accounting.retry_count += 1
                    self._sleep(min(2**attempt, 8))
                    continue
                raise IntakeError("SEC_PARTIAL_SOURCE", type(exc).__name__, scope=endpoint) from exc

            self.accounting.record_status(status)
            content_type = next(
                (value for key, value in response_headers.items() if key.casefold() == "content-type"),
                "",
            )
            response = SecResponse(
                url=url,
                endpoint=endpoint,
                status=int(status),
                content_type=content_type,
                body=body,
                headers=response_headers,
                retrieved_at=utc_now(),
            )
            if status == 403:
                raise IntakeError("SEC_ACCESS_BLOCKED", endpoint, scope=endpoint)
            if status == 429:
                if attempt < self.max_retries:
                    self.accounting.retry_count += 1
                    self._sleep(min(2**attempt, 8))
                    continue
                raise IntakeError("SEC_RATE_LIMITED", endpoint, scope=endpoint)
            if 500 <= status <= 599:
                if attempt < self.max_retries:
                    self.accounting.retry_count += 1
                    self._sleep(min(2**attempt, 8))
                    continue
                raise IntakeError("SEC_PARTIAL_SOURCE", f"HTTP_{status}", scope=endpoint)
            if status != 200:
                raise IntakeError("SEC_PARTIAL_SOURCE", f"HTTP_{status}", scope=endpoint)
            if "json" not in content_type.casefold():
                raise IntakeError("SEC_SOURCE_INVALID", "EXPECTED_JSON_CONTENT_TYPE", scope=endpoint)
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise IntakeError("SEC_SOURCE_INVALID", "INVALID_JSON", scope=endpoint) from exc
            return response, payload
        raise AssertionError("bounded retry loop exhausted unexpectedly")


def parse_ticker_association(payload: Any, requested: list[str]) -> dict[str, dict[str, str]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("fields"), list) or not isinstance(payload.get("data"), list):
        raise IntakeError("SEC_SOURCE_INVALID", "TICKER_ASSOCIATION_TOP_LEVEL")
    fields = payload["fields"]
    required = {"cik", "name", "ticker", "exchange"}
    if not required.issubset(set(fields)):
        raise IntakeError("SEC_SOURCE_INVALID", "TICKER_ASSOCIATION_FIELDS")
    matches: dict[str, list[dict[str, str]]] = {ticker: [] for ticker in requested}
    for row in payload["data"]:
        if not isinstance(row, list) or len(row) != len(fields):
            continue
        value = dict(zip(fields, row))
        ticker = str(value.get("ticker", ""))
        if ticker in matches:
            cik_raw = str(value.get("cik", ""))
            if not cik_raw.isdigit() or not str(value.get("name", "")).strip():
                raise IntakeError("SEC_SOURCE_INVALID", f"INVALID_IDENTITY_ROW:{ticker}")
            matches[ticker].append({
                "ticker": ticker,
                "cik": cik_raw.zfill(10),
                "company_name": str(value["name"]).strip(),
                "exchange": str(value.get("exchange", "")),
            })
    result: dict[str, dict[str, str]] = {}
    for ticker, rows in matches.items():
        if len(rows) != 1:
            raise IntakeError("SEC_IDENTITY_CONFLICT", f"{ticker}:MATCH_COUNT={len(rows)}", scope=ticker)
        result[ticker] = rows[0]
    return result


def _same_official_company_name(left: str, right: str) -> bool:
    return " ".join(left.split()).casefold() == " ".join(right.split()).casefold()


def validate_submission_identity(payload: Any, identity: dict[str, str]) -> None:
    if not isinstance(payload, dict):
        raise IntakeError("SEC_SOURCE_INVALID", "SUBMISSIONS_TOP_LEVEL", scope=identity["ticker"])
    required = {"cik", "name", "tickers", "filings"}
    if not required.issubset(payload):
        raise IntakeError("SEC_SOURCE_INVALID", "SUBMISSIONS_FIELDS", scope=identity["ticker"])
    payload_cik = str(payload["cik"])
    if not payload_cik.isdigit() or payload_cik.zfill(10) != identity["cik"]:
        raise IntakeError("SEC_IDENTITY_CONFLICT", f"{identity['ticker']}:CIK", scope=identity["ticker"])
    tickers = payload.get("tickers")
    if not isinstance(tickers, list) or identity["ticker"] not in tickers:
        raise IntakeError("SEC_IDENTITY_CONFLICT", f"{identity['ticker']}:TICKER", scope=identity["ticker"])
    if not _same_official_company_name(identity["company_name"], str(payload.get("name", ""))):
        raise IntakeError("SEC_IDENTITY_CONFLICT", f"{identity['ticker']}:COMPANY_NAME", scope=identity["ticker"])


def split_items(value: Any) -> list[str]:
    if value is None:
        return []
    parts = re.split(r"[,;]", str(value))
    return list(dict.fromkeys(part.strip() for part in parts if part.strip()))


def map_event_type(form: str, rules: dict[str, Any]) -> str | None:
    value = rules["form_event_types"].get(form)
    return str(value) if value else None


def route_materiality(
    *, ticker: str, form: str, event_type: str, items: list[str], rules: dict[str, Any]
) -> tuple[str, str, str]:
    holding = ticker in rules["holdings"]
    if not holding:
        return "MEDIUM", "CHALLENGER", "WATCH"
    if event_type in rules["high_candidate_event_types"]:
        return "HIGH", "HOLDING", "ASSET_REVIEW_REQUIRED"
    if event_type == "CURRENT_REPORT":
        if any(item in rules["material_8k_items"] for item in items):
            return "HIGH", "HOLDING", "ASSET_REVIEW_REQUIRED"
        if items and all(item in rules["administrative_8k_items"] for item in items):
            return "LOW", "HOLDING", "NO_CHANGE"
        return "MEDIUM", "HOLDING", "WATCH"
    return "MEDIUM", "HOLDING", "WATCH"


def normalize_submissions(
    *,
    payload: dict[str, Any],
    identity: dict[str, str],
    response: SecResponse,
    decision_as_of: datetime,
    lookback_days: int,
    rules: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool]:
    validate_submission_identity(payload, identity)
    filings = payload.get("filings")
    recent = filings.get("recent") if isinstance(filings, dict) else None
    if not isinstance(recent, dict):
        raise IntakeError("SEC_SOURCE_INVALID", "FILINGS_RECENT", scope=identity["ticker"])
    required_columns = {"accessionNumber", "filingDate", "form"}
    if not required_columns.issubset(recent):
        raise IntakeError("SEC_SOURCE_INVALID", "FILINGS_RECENT_COLUMNS", scope=identity["ticker"])
    columns = {
        key: value for key, value in recent.items() if isinstance(value, list)
    }
    required_lengths = [len(columns.get(key, [])) for key in required_columns]
    if not required_lengths or min(required_lengths) == 0 and max(required_lengths) > 0:
        raise IntakeError("SEC_PARTIAL_SOURCE", "FILINGS_RECENT_LENGTH", scope=identity["ticker"])
    row_count = min(required_lengths) if required_lengths else 0
    partial = any(len(value) < row_count for value in columns.values())
    cutoff = decision_as_of.date()
    start = cutoff - timedelta(days=lookback_days - 1)
    seen: set[str] = set()
    events: list[dict[str, Any]] = []

    def column(name: str, index: int) -> Any:
        values = columns.get(name, [])
        return values[index] if index < len(values) else None

    for index in range(row_count):
        accession = str(column("accessionNumber", index) or "").strip()
        form = str(column("form", index) or "").strip()
        filing_date_raw = str(column("filingDate", index) or "").strip()
        if not accession or accession in seen:
            continue
        seen.add(accession)
        event_type = map_event_type(form, rules)
        if event_type is None:
            continue
        try:
            filing_date = date.fromisoformat(filing_date_raw)
        except ValueError:
            partial = True
            continue
        if filing_date > cutoff or filing_date < start:
            continue
        items = split_items(column("items", index))
        materiality, relevance, impact = route_materiality(
            ticker=identity["ticker"], form=form, event_type=event_type, items=items, rules=rules
        )
        relation = rules.get("derived_relations", {}).get(identity["ticker"])
        event_seed = f"OFFICIAL_SEC|{identity['ticker']}|{accession}"
        events.append({
            "event_id": "sec-" + hashlib.sha256(event_seed.encode("utf-8")).hexdigest()[:24],
            "source_authority": "OFFICIAL_SEC",
            "source_name": "SEC_EDGAR_COMPANY_SUBMISSIONS",
            "source_url": response.url,
            "ticker": identity["ticker"],
            "cik": identity["cik"],
            "company_name": str(payload["name"]),
            "accession_number": accession,
            "form": form,
            "filing_date": filing_date.isoformat(),
            "accepted_at": str(column("acceptanceDateTime", index)) if column("acceptanceDateTime", index) else None,
            "report_date": str(column("reportDate", index)) if column("reportDate", index) else None,
            "primary_document": str(column("primaryDocument", index)) if column("primaryDocument", index) else None,
            "items_if_available": items,
            "event_type": event_type,
            "materiality": materiality,
            "portfolio_relevance": relevance,
            "root_theses": list(rules.get("root_theses", {}).get(identity["ticker"], [])),
            "verification_status": "OFFICIAL_SOURCE_VERIFIED",
            "interpretation_status": "DERIVED_RULE_BASED",
            "decision_impact": impact,
            "retrieved_at": response.retrieved_at,
            "raw_source_sha256": response.sha256,
            "underlying_company_relevance": relation is not None,
            "leveraged_vehicle": relation.get("leveraged_vehicle") if relation else None,
            "derived_relation_status": relation.get("relation_status") if relation else None,
        })
    events.sort(key=lambda item: (item["filing_date"], item["accepted_at"] or "", item["accession_number"]), reverse=True)
    return events, partial


def create_only_write(path: Path, payload: str | bytes) -> None:
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def create_only_json(path: Path, value: Any) -> None:
    create_only_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def create_only_utf8_dashboard(path: Path, payload: str) -> None:
    """Write a Windows-friendly create-only dashboard without changing JSON encoding."""
    create_only_write(path, b"\xef\xbb\xbf" + payload.encode("utf-8"))


def _git(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, encoding="utf-8", errors="replace",
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNAVAILABLE"


def _validate_or_raise(value: dict[str, Any], schema: Path, code: str) -> None:
    errors = validate_instance(value, schema)
    if errors:
        raise IntakeError(code, "; ".join(errors))


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else None


def discover_portfolio_context(
    artifact_root: str | Path = DEFAULT_PORTFOLIO_ARTIFACT_ROOT,
    *,
    decision_as_of: datetime,
) -> dict[str, Any]:
    root = Path(artifact_root)
    candidates: list[tuple[datetime, Path, dict[str, Any]]] = []
    if root.is_dir():
        for path in root.glob("*/manual-portfolio-analysis.json"):
            try:
                value = load_json(path)
            except (OSError, ValueError):
                continue
            provenance = value.get("provenance") if isinstance(value, dict) else None
            as_of = _parse_datetime(str(value.get("decision_as_of", ""))) if isinstance(value, dict) else None
            genuine = (
                isinstance(provenance, dict)
                and value.get("evidence_grade") == "GRADE_B"
                and provenance.get("evidence_grade") == "GRADE_B"
                and value.get("manual_data_verification_status") == "VERIFIED_REAL_DATA"
                and value.get("run_provenance_status") == "VERIFIED_MANUAL"
                and value.get("preflight_status") == "PASS"
                and value.get("order_authority") is False
            )
            if genuine and as_of and as_of.astimezone(timezone.utc) <= decision_as_of.astimezone(timezone.utc):
                candidates.append((as_of, path.resolve(), value))
    if not candidates:
        return {"status": "NOT_VERIFIED", "as_of": None, "source_path": None, "source_sha256": None}
    as_of, path, _ = max(candidates, key=lambda item: item[0])
    return {
        "status": "LAST_KNOWN",
        "as_of": as_of.isoformat(),
        "source_path": str(path),
        "source_sha256": file_hash(path),
    }


def raw_metadata(response: SecResponse, *, ticker: str | None, cik: str | None, identity_status: str) -> dict[str, Any]:
    def header(name: str) -> str | None:
        return next((value for key, value in response.headers.items() if key.casefold() == name.casefold()), None)

    return {
        "source_url": response.url,
        "retrieved_at": response.retrieved_at,
        "http_status": response.status,
        "content_type": response.content_type,
        "etag": header("etag"),
        "last_modified": header("last-modified"),
        "sha256": response.sha256,
        "ticker": ticker,
        "cik": cik,
        "identity_status": identity_status,
    }


def validation_check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"check": name, "status": status, "detail": detail}


def overall_result(events: list[dict[str, Any]]) -> str:
    if not events:
        return "NO_CHANGE"
    return max((event["decision_impact"] for event in events), key=IMPACT_RANK.__getitem__)


def user_action(events: list[dict[str, Any]]) -> str:
    result = overall_result(events)
    if result in {"ASSET_REVIEW_REQUIRED", "PORTFOLIO_RECOMPILE_REQUIRED"}:
        return "ASSET_REVIEW_REQUIRED"
    if result == "WATCH":
        return "READ_FILING"
    return "NONE"


def _filing_ordinal(event: dict[str, Any]) -> int:
    try:
        return date.fromisoformat(str(event.get("filing_date", ""))).toordinal()
    except ValueError:
        return 0


def _event_timestamp(event: dict[str, Any]) -> float:
    accepted_at = event.get("accepted_at")
    if accepted_at:
        parsed = _parse_datetime(str(accepted_at))
        if parsed is not None:
            return parsed.astimezone(timezone.utc).timestamp()
    try:
        filing = date.fromisoformat(str(event.get("filing_date", "")))
    except ValueError:
        return 0.0
    return datetime(filing.year, filing.month, filing.day, tzinfo=timezone.utc).timestamp()


def dashboard_event_sort_key(event: dict[str, Any]) -> tuple[Any, ...]:
    """Impact, materiality, and recency ordering for presentation only."""
    return (
        -IMPACT_RANK[event["decision_impact"]],
        -MATERIALITY_RANK[event["materiality"]],
        -_event_timestamp(event),
        -_filing_ordinal(event),
        str(event.get("accession_number", "")),
    )


def sort_dashboard_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(events, key=dashboard_event_sort_key)


def is_routine_prospectus_watch(event: dict[str, Any]) -> bool:
    return (
        event.get("portfolio_relevance") == "CHALLENGER"
        and event.get("event_type") == "OFFERING_PROSPECTUS"
        and event.get("decision_impact") == "WATCH"
    )


def aggregate_routine_prospectus(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for event in events:
        if is_routine_prospectus_watch(event):
            groups.setdefault((event["ticker"], event["form"]), []).append(event)
    aggregates: list[dict[str, Any]] = []
    for (ticker, form), members in sorted(groups.items()):
        ordered = sort_dashboard_events(members)
        dates = sorted(str(event["filing_date"]) for event in members)
        latest = ordered[0]
        aggregates.append({
            "ticker": ticker,
            "form": form,
            "count": len(members),
            "earliest_filing_date": dates[0],
            "latest_filing_date": dates[-1],
            "latest_accession": latest["accession_number"],
            "decision_impact": "WATCH",
            "source_authority": "OFFICIAL_SEC",
            "label": "Routine Prospectus / Structured-Note Metadata",
        })
    return aggregates


def materiality_rule_reason(event: dict[str, Any]) -> str:
    relation = "Direct holding underlying" if event.get("underlying_company_relevance") else (
        "Direct holding" if event.get("portfolio_relevance") == "HOLDING" else "Direct challenger"
    )
    event_type = str(event["event_type"])
    impact = str(event["decision_impact"])
    if event_type == "CURRENT_REPORT":
        items = ", ".join(event.get("items_if_available", [])) or "not available"
        return (
            f"{relation} + CURRENT_REPORT + SEC item metadata ({items}) -> {impact}. "
            "Filing content not interpreted in v0.1; read filing required."
        )
    if event_type == "FOREIGN_CURRENT_REPORT":
        return (
            f"{relation} + FOREIGN_CURRENT_REPORT -> Conservative review candidate ({impact}). "
            "Filing content materiality not interpreted in v0.1; read filing required."
        )
    return (
        f"{relation} + {event_type} -> {impact}. "
        "Filing content not interpreted in v0.1; read filing required."
    )


def display_label(value: Any) -> str:
    return DISPLAY_LABELS.get(str(value), str(value))


def form_label(form: Any) -> str:
    code = str(form)
    return f"{FORM_LABELS.get(code, 'SEC 공시')} ({code})"


def korean_rule_reason(event: dict[str, Any]) -> str:
    relation = "현재 보유와 직접 관련된 기업" if event.get("underlying_company_relevance") else (
        "현재 보유 종목" if event.get("portfolio_relevance") == "HOLDING" else "현재 관심종목"
    )
    event_type = str(event.get("event_type"))
    if event_type == "PERIODIC_FINANCIAL":
        return f"{relation}의 정기 실적 공시입니다. 공시 본문이 실적이나 전망에 미치는 영향은 아직 분석하지 않았습니다."
    if event_type == "CURRENT_REPORT":
        return f"{relation}의 중요 수시공시입니다. SEC 항목 메타데이터만 확인했으며 공시 내용 자체의 중요도는 아직 분석하지 않았습니다."
    if event_type == "FOREIGN_CURRENT_REPORT":
        return f"{relation}의 해외기업 수시공시입니다. 공시 내용 자체의 중요도는 아직 분석하지 않았습니다."
    return f"{relation}의 {FORM_LABELS.get(str(event.get('form')), 'SEC 공시')}입니다. 공시 본문 영향은 아직 분석하지 않았습니다."


def _routine_ticker_groups(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for item in aggregates:
        group = groups.setdefault(item["ticker"], {"ticker": item["ticker"], "count": 0, "forms": {}})
        group["count"] += item["count"]
        group["forms"][item["form"]] = item["count"]
    return [groups[ticker] for ticker in sorted(groups)]


def _event_action(event: dict[str, Any]) -> str:
    return f"{event['ticker']} {FORM_LABELS.get(str(event['form']), str(event['form']))} 내용 검토"


def build_dashboard_view(
    events: list[dict[str, Any]], scheduled_summary: dict[str, Any] | None = None
) -> dict[str, Any]:
    high_events = sort_dashboard_events([
        event for event in events if event["materiality"] == "HIGH" and not is_routine_prospectus_watch(event)
    ])
    routine_aggregates = aggregate_routine_prospectus(events)
    other_material_offerings = [
        event for event in events
        if event["event_type"] in {"SHELF_REGISTRATION", "OFFERING_PROSPECTUS"}
        and not is_routine_prospectus_watch(event)
    ]
    scheduled = scheduled_summary or {}
    recent_count = scheduled.get("filings_in_lookback_window", len(events))
    current_high_count = scheduled.get("high_filings_in_lookback_window", len(high_events))
    new_count = scheduled.get("new_since_previous_count")
    new_high_count = scheduled.get("new_high_since_previous_count")
    freshness = scheduled.get("freshness_status", "CURRENT_RUN")
    return {
        "result": overall_result(events),
        "result_display": display_label(overall_result(events)),
        "action": user_action(events),
        "action_display": display_label(user_action(events)),
        "high_events": high_events,
        "high_event_count": len(high_events),
        "current_high_count": current_high_count,
        "recent_filing_count": recent_count,
        "new_filing_count": new_count,
        "new_high_count": new_high_count,
        "freshness": freshness,
        "freshness_display": display_label(freshness),
        "user_actions": [_event_action(event) for event in high_events],
        "buy_sell_signal": "없음 (매수·매도 신호를 추론하지 않음)",
        "routine_aggregates": routine_aggregates,
        "routine_ticker_groups": _routine_ticker_groups(routine_aggregates),
        "routine_event_count": sum(item["count"] for item in routine_aggregates),
        "individual_routine_top_events": 0,
        "confirmed_convertible_dilution": "NOT_VERIFIED",
        "other_material_offering_count": len(other_material_offerings),
    }


def _event_label(event: dict[str, Any]) -> str:
    return f"{event['ticker']} {event['form']} ({event['filing_date']}) - {event['decision_impact']}"


def _ticker_summary(events: list[dict[str, Any]], ticker: str) -> str:
    matches = [event for event in events if event["ticker"] == ticker]
    if not matches:
        return "\uc0c8 \uad00\uc2ec filing \uc5c6\uc74c"
    strongest = max(matches, key=lambda item: (IMPACT_RANK[item["decision_impact"]], MATERIALITY_RANK[item["materiality"]]))
    return f"{len(matches)}\uac74 / {strongest['form']} / {strongest['decision_impact']}"


def render_dashboard_markdown(
    *,
    run_time: str,
    source_status: str,
    context: dict[str, Any],
    lookback_days: int,
    events: list[dict[str, Any]],
    ownership_coverage: str,
    company_status: dict[str, str],
    scheduled_summary: dict[str, Any] | None = None,
) -> str:
    view = build_dashboard_view(events, scheduled_summary)
    periodic = [event for event in events if event["event_type"] == "PERIODIC_FINANCIAL"]
    unknowns = [f"{ticker}: {status}" for ticker, status in company_status.items() if status != "PASS"]
    if ownership_coverage != "VERIFIED":
        unknowns.append("기업 제출자료만으로는 Form 4/144 보유 변동 공시의 전체 범위를 확인할 수 없습니다.")
    count = lambda value: "비교 기준 없음" if value is None else f"{value}건"
    lines = [
        "# SEC 공시 자동 분석", "",
        f"- 실행 시각: {run_time}",
        f"- 데이터 상태: {view['freshness_display']} ({view['freshness']})",
        f"- SEC 수집 상태: {source_status}",
        f"- 포트폴리오 기준: {display_label(context['status'])} / {context.get('as_of') or '확인되지 않음'}", "",
        "## 오늘의 결론", "", f"**{view['result_display']}**", "",
        f"- 최근 {lookback_days}일 공시 수: **{count(view['recent_filing_count'])}**",
        f"- 이전 실행 이후 새 공시 수: **{count(view['new_filing_count'])}**",
        f"- 새 HIGH 공시 수: **{count(view['new_high_count'])}**",
        f"- 현재 HIGH 검토 공시 수: **{count(view['current_high_count'])}**",
        f"- 매수/매도 신호: **{view['buy_sell_signal']}**", "",
        "> 전체 공시 수와 새 공시 수는 서로 다른 값입니다. 이 화면은 검토 대상을 보여주며 주문 신호를 만들지 않습니다.", "",
        "## 지금 할 일", "",
    ]
    if view["user_actions"]:
        lines.extend(f"{index}. {value}" for index, value in enumerate(view["user_actions"], 1))
    else:
        lines.append("1. 별도 행동 필요 없음")
    lines.extend(["", "**현재 주문: 없음**", "", "## 지금 확인할 중요 공시", ""])
    if view["high_events"]:
        for index, event in enumerate(view["high_events"], 1):
            lines.extend([
                f"### {index}. {event['ticker']} · {form_label(event['form'])}", "",
                f"- **종목:** {event['ticker']}",
                f"- **공시 종류:** {form_label(event['form'])}",
                f"- **중요도:** {MATERIALITY_LABELS.get(event['materiality'], event['materiality'])} ({event['materiality']})",
                f"- **왜 중요한가:** {korean_rule_reason(event)}",
                "- **확인된 사실:**",
                "  - ✓ 공식 SEC filing 존재",
                "  - ✓ ticker/company 연결",
                "- **아직 모르는 것:**",
                "  - ? filing 본문 영향",
                "  - ? 실적/가이던스 변화",
                "  - ? Portfolio Thesis 영향",
                f"- **지금 할 일:** {_event_action(event)}", "",
                "<details><summary>개발용 세부정보</summary>", "",
                f"- Accession: {event['accession_number']}",
                f"- Accepted At: {event.get('accepted_at') or 'NOT_AVAILABLE'}",
                f"- Filing Date: {event['filing_date']}",
                f"- Rule Code: {event['event_type']}",
                f"- Rule Reason: {materiality_rule_reason(event)}",
                f"- Decision Impact: {event['decision_impact']}",
                f"- Verification: {event['verification_status']}", "", "</details>", "",
            ])
    else:
        lines.append("1. 현재 HIGH 검토 공시가 없습니다.")
    lines.extend(["", "## 기타 자동 수집 공시", ""])
    if view["routine_ticker_groups"]:
        for index, aggregate in enumerate(view["routine_ticker_groups"], 1):
            lines.extend([
                f"### {index}. {aggregate['ticker']}", "",
                f"일상적인 증권 발행 관련 공시 **{aggregate['count']}건**",
                "현재 별도 행동 필요 없음", "",
                "상세:",
            ])
            lines.extend(f"- {form}: {form_count}건" for form, form_count in sorted(aggregate["forms"].items()))
    else:
        lines.append("1. 집계된 일상 공시가 없습니다.")
    lines.extend([
        "", "## 보유종목 / 관심종목", "",
        f"MRVL -> MVLL: {_ticker_summary(events, 'MRVL')} / DERIVED_MAPPING_NOT_ENTITY_EQUIVALENCE",
        f"NBIS: {_ticker_summary(events, 'NBIS')}",
        "SOXL: 섹터/ETF 전용 데이터에서 별도 확인", "",
        "### 관심종목", "",
        f"PGR: {_ticker_summary(events, 'PGR')}",
        f"JPM: {_ticker_summary(events, 'JPM')}",
        f"CME: {_ticker_summary(events, 'CME')}",
        f"V: {_ticker_summary(events, 'V')}", "",
        "## 자금조달 관련 공시", "",
        f"- 전환증권·희석 조건 확인 여부: {view['confirmed_convertible_dilution']}",
        f"- 일상적인 증권 발행 관련 공시: {view['routine_event_count']}건",
        f"- 그 밖의 중요 자금조달 공시: {view['other_material_offering_count']}건",
        "- 증권 발행 보충자료의 메타데이터만으로 전환 조건이나 경제적 희석을 확정하지 않습니다.", "",
        f"- 정기 실적 공시(10-Q / 10-K / 20-F): {len(periodic)}건", "",
        "## 아직 확인하지 못한 정보", "",
    ])
    if unknowns:
        lines.extend(f"{index}. {value}" for index, value in enumerate(unknowns, 1))
    else:
        lines.append("1. \uc5c6\uc74c")
    lines.extend([
        "", "## 안전 상태", "",
        "- ✓ 자동 주문 없음",
        "- ✓ Broker 호출 없음",
        "- ✓ Portfolio 자동 변경 없음",
        "- ✓ SEC 공식 데이터 사용", "",
        "<details><summary>개발용 상태값</summary>", "",
        "- order_authority=false",
        "- execution_quantity=null",
        "- automatic_order=false",
        "- source_authority=OFFICIAL_SEC",
        f"- freshness_status={view['freshness']}",
        f"- source_status={source_status}", "", "</details>", "",
    ])
    return "\n".join(lines)


def render_dashboard_html(markdown_model: dict[str, Any]) -> str:
    events = markdown_model["events"]
    view = build_dashboard_view(events, markdown_model.get("scheduled_summary"))
    periodic_count = sum(event.get("event_type") == "PERIODIC_FINANCIAL" for event in events)
    count = lambda value: "비교 기준 없음" if value is None else f"{value}건"
    cards = "".join(
        "<article class='event-card'><div class='tag'>중요도 "
        + html.escape(MATERIALITY_LABELS.get(event["materiality"], event["materiality"]))
        + " (" + html.escape(event["materiality"]) + ")</div><h3>"
        + html.escape(event["ticker"] + " · " + form_label(event["form"]))
        + "</h3><dl class='primary'><dt>종목</dt><dd>" + html.escape(event["ticker"])
        + "</dd><dt>공시 종류</dt><dd>" + html.escape(form_label(event["form"]))
        + "</dd><dt>중요도</dt><dd>" + html.escape(MATERIALITY_LABELS.get(event["materiality"], event["materiality"]))
        + "</dd></dl><h4>왜 중요한가</h4><p>" + html.escape(korean_rule_reason(event))
        + "</p><div class='facts'><div><h4>확인된 사실</h4><p>✓ 공식 SEC filing 존재<br>✓ ticker/company 연결</p></div>"
        + "<div><h4>아직 모르는 것</h4><p>? filing 본문 영향<br>? 실적/가이던스 변화<br>? Portfolio Thesis 영향</p></div></div>"
        + "<h4>지금 할 일</h4><p><strong>" + html.escape(_event_action(event))
        + "</strong></p><details><summary>개발용 세부정보</summary><dl><dt>Accession</dt><dd>"
        + html.escape(event["accession_number"]) + "</dd><dt>Accepted At</dt><dd>"
        + html.escape(str(event.get("accepted_at") or "NOT_AVAILABLE"))
        + "</dd><dt>Filing Date</dt><dd>" + html.escape(event["filing_date"])
        + "</dd><dt>Rule Code</dt><dd>" + html.escape(event["event_type"])
        + "</dd><dt>Rule Reason</dt><dd>" + html.escape(materiality_rule_reason(event))
        + "</dd><dt>Decision Impact</dt><dd>" + html.escape(event["decision_impact"])
        + "</dd></dl></details></article>"
        for event in view["high_events"]
    ) or "<article><h3>현재 HIGH 검토 공시가 없습니다.</h3><p>별도 행동 필요 없음</p></article>"
    aggregate_rows = "".join(
        "<div class='routine-card'><h3>" + html.escape(item["ticker"])
        + "</h3><p>일상적인 증권 발행 관련 공시 <strong>" + str(item["count"])
        + "건</strong><br>현재 별도 행동 필요 없음</p><details><summary>상세</summary><ul>"
        + "".join("<li>" + html.escape(form) + " " + str(form_count) + "건</li>" for form, form_count in sorted(item["forms"].items()))
        + "</ul></details></div>" for item in view["routine_ticker_groups"]
    ) or "<p>집계된 일상 공시가 없습니다.</p>"
    summaries = "".join(
        "<div class='row'><strong>" + html.escape(ticker) + "</strong><span>" + html.escape(_ticker_summary(events, ticker)) + "</span></div>"
        for ticker in ("MRVL", "NBIS", "PGR", "JPM", "CME", "V")
    )
    unknowns = [f"{ticker}: {status}" for ticker, status in markdown_model["company_status"].items() if status != "PASS"]
    if markdown_model["ownership_coverage"] != "VERIFIED":
        unknowns.append("기업 제출자료만으로는 Form 4/144 보유 변동 공시의 전체 범위를 확인할 수 없습니다.")
    unknown_html = "".join("<li>" + html.escape(item) + "</li>" for item in unknowns) or "<li>\uc5c6\uc74c</li>"
    actions = "".join("<li>" + html.escape(value) + "</li>" for value in view["user_actions"]) or "<li>별도 행동 필요 없음</li>"
    return """<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SEC 공시 자동 분석</title><style>
:root{--navy:#10233f;--blue:#246bfd;--ink:#172231;--muted:#66758a;--line:#dfe6ee;--bg:#f4f7fb;--white:#fff;--amber:#e99b18}
*{box-sizing:border-box;font-family:"Malgun Gothic","맑은 고딕","Segoe UI",Arial,sans-serif !important}body{margin:0;background:var(--bg);color:var(--ink);line-height:1.6}.shell{max-width:1120px;margin:auto;padding:32px 20px 64px}
.hero{background:linear-gradient(135deg,#0c1d35,#173f70);color:white;border-radius:24px;padding:30px;box-shadow:0 18px 45px #10233f22}.eyebrow{font-size:12px;letter-spacing:.08em;font-weight:800;color:#9ec3ff}.hero h1{font-size:clamp(30px,5vw,50px);line-height:1.2;margin:10px 0 24px}.meta{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.meta div{background:#ffffff10;border:1px solid #ffffff24;border-radius:12px;padding:12px}.meta small{display:block;color:#b9cbe1}.result{background:white;border-left:7px solid var(--amber);border-radius:18px;padding:22px;margin-top:18px}.result h2{font-size:32px;margin:3px 0;color:#a56100}.section{margin:28px 0 12px}.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}article,.panel,.routine-card{background:white;border:1px solid var(--line);border-radius:16px;padding:18px}.tag{font-size:12px;color:var(--blue);font-weight:800}.columns,.facts{display:grid;grid-template-columns:1fr 1fr;gap:14px}.facts>div{background:#f7f9fc;border-radius:12px;padding:12px}.primary{display:grid;grid-template-columns:100px 1fr}.primary dt,.primary dd{padding:6px 0;margin:0}.row{display:grid;grid-template-columns:100px 1fr;padding:10px 0;border-bottom:1px solid var(--line)}.row span,small,summary{color:var(--muted)}.routine-card{margin-bottom:10px}.safety{background:var(--navy);color:white}.safety-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.safety-grid div{background:#ffffff10;border-radius:10px;padding:12px}.action{background:#edf3ff;border-color:#b9ccff}.unknown{background:#fff8e9;border-color:#f0d7a6}.dev{font-size:12px;margin-top:14px}@media(max-width:760px){.meta,.cards,.columns,.facts,.safety-grid{grid-template-columns:1fr}}
</style></head><body><main class="shell"><section class="hero"><div class="eyebrow">SEC 공식 데이터 · 자동 분석 결과</div><h1>SEC 공시 자동 분석</h1><p>""" + html.escape(view["freshness_display"]) + """ · 실행 시각 """ + html.escape(markdown_model["run_time"]) + """</p><div class="meta">
<div><small>최근 """ + str(markdown_model["lookback_days"]) + """일 공시 수</small><strong>""" + html.escape(count(view["recent_filing_count"])) + """</strong></div><div><small>이전 실행 이후 새 공시 수</small><strong>""" + html.escape(count(view["new_filing_count"])) + """</strong></div><div><small>새 HIGH 공시 수</small><strong>""" + html.escape(count(view["new_high_count"])) + """</strong></div><div><small>현재 HIGH 검토 공시 수</small><strong>""" + html.escape(count(view["current_high_count"])) + """</strong></div></div></section>
<section class="result"><small>오늘의 결론</small><h2>""" + html.escape(view["result_display"]) + """</h2><p>매수/매도 신호: <strong>""" + html.escape(view["buy_sell_signal"]) + """</strong></p><p>전체 공시 수와 새 공시 수는 서로 다른 값입니다.</p></section>
<h2 class="section">지금 할 일</h2><section class="panel action"><ol>""" + actions + """</ol><p><strong>현재 주문: 없음</strong></p></section>
<h2 class="section">지금 확인할 중요 공시</h2><section class="cards">""" + cards + """</section>
<h2 class="section">기타 자동 수집 공시</h2><section class="panel">""" + aggregate_rows + """</section>
<h2 class="section">자금조달 관련 공시</h2><section class="panel"><p><strong>전환증권·희석 조건 확인 여부:</strong> """ + html.escape(view["confirmed_convertible_dilution"]) + """</p><p><strong>일상적인 증권 발행 관련 공시:</strong> """ + str(view["routine_event_count"]) + """건</p><p><strong>그 밖의 중요 자금조달 공시:</strong> """ + str(view["other_material_offering_count"]) + """건</p><p><strong>정기 실적 공시(10-Q / 10-K / 20-F):</strong> """ + str(periodic_count) + """건</p><p>증권 발행 보충자료의 메타데이터만으로 전환 조건이나 경제적 희석을 확정하지 않습니다.</p></section>
<h2 class="section">보유종목 / 관심종목</h2><section class="columns"><div class="panel">""" + summaries + """<div class="row"><strong>SOXL</strong><span>섹터/ETF 전용 데이터에서 별도 확인</span></div></div><div class="panel"><h3>MRVL -&gt; MVLL</h3><p>관련성은 파생 매핑이며 MVLL을 MRVL의 SEC 법인 또는 CIK와 동일시하지 않습니다.</p><h3>보유 변동 공시 범위</h3><p>""" + html.escape(markdown_model["ownership_coverage"]) + """</p></div></section>
<h2 class="section">아직 확인하지 못한 정보</h2><section class="panel unknown"><ol>""" + unknown_html + """</ol></section>
<h2 class="section">안전 상태</h2><section class="panel safety"><div class="safety-grid"><div>✓ 자동 주문 없음</div><div>✓ Broker 호출 없음</div><div>✓ Portfolio 자동 변경 없음</div><div>✓ SEC 공식 데이터 사용</div></div><details class="dev"><summary>개발용 상태값</summary><p>order_authority=false<br>execution_quantity=null<br>automatic_order=false<br>source_authority=OFFICIAL_SEC<br>freshness_status=""" + html.escape(view["freshness"]) + """<br>source_status=""" + html.escape(markdown_model["source_status"]) + """</p></details></section>
</main></body></html>"""


def audit_static_boundaries() -> dict[str, Any]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    broker_imports = {"pykiwoom", "kiwoom", "alpaca_trade_api", "ib_insync"}
    order_calls = {"submit_order", "place_order", "send_order", "cancel_order", "modify_order"}
    scheduler_calls = {"schtasks", "register_scheduled_task", "create_schedule"}
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    called = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    return {
        "broker_path_present": bool(imported & broker_imports),
        "order_path_present": bool(called & order_calls),
        "scheduler_path_present": bool(called & scheduler_calls),
        "allowed_network_hosts": sorted(ALLOWED_HOSTS),
    }


def generate_run_id(decision_as_of: datetime) -> str:
    return "sec-official-" + decision_as_of.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def validate_run_id(run_id: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", run_id) is None:
        raise IntakeError("INVALID_RUN_ID", run_id)
    return run_id


def run_pipeline(
    *,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    run_id: str | None = None,
    decision_as_of: datetime | None = None,
    rules_path: str | Path = DEFAULT_RULES_PATH,
    portfolio_artifact_root: str | Path = DEFAULT_PORTFOLIO_ARTIFACT_ROOT,
    portfolio_path: str | Path = DEFAULT_PORTFOLIO_PATH,
    policy_path: str | Path = DEFAULT_POLICY_PATH,
    adapter: SecAdapter | None = None,
) -> dict[str, Any]:
    if lookback_days < 1:
        raise IntakeError("INVALID_LOOKBACK_DAYS", str(lookback_days))
    sec = adapter or SecAdapter()
    sec._require_user_agent()
    as_of = decision_as_of or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        raise IntakeError("DECISION_AS_OF_TIMEZONE_REQUIRED")
    as_of = as_of.astimezone(timezone.utc)
    started_at = as_of.isoformat()
    rules = load_json(rules_path)
    watchlist = [str(value) for value in rules["corporate_watchlist"]]
    run_id_value = validate_run_id(run_id or generate_run_id(as_of))
    run_directory = Path(output_root).resolve() / as_of.date().isoformat() / run_id_value
    if run_directory.exists():
        raise IntakeError("RUN_COLLISION", str(run_directory))
    run_directory.mkdir(parents=True, exist_ok=False)
    raw_root = run_directory / "raw"
    submissions_root = raw_root / "submissions"
    submissions_root.mkdir(parents=True, exist_ok=False)

    protected_paths = {
        "portfolio_state": Path(portfolio_path).resolve(),
        "alert_policy": Path(policy_path).resolve(),
    }
    protected_before = {
        name: file_hash(path) if path.is_file() else None for name, path in protected_paths.items()
    }
    boundaries = audit_static_boundaries()
    if boundaries["broker_path_present"] or boundaries["order_path_present"] or boundaries["scheduler_path_present"]:
        raise IntakeError("AUTHORITY_BOUNDARY_VIOLATION")

    raw_records: list[dict[str, Any]] = []
    raw_source_hashes: dict[str, str] = {}
    company_status: dict[str, str] = {}
    all_events: list[dict[str, Any]] = []

    association_response, association_payload = sec.request_json(TICKER_ASSOCIATION_URL, "ticker_association")
    association_path = raw_root / "company_tickers_exchange.json"
    create_only_write(association_path, association_response.body)
    raw_source_hashes["raw/company_tickers_exchange.json"] = association_response.sha256

    identities: dict[str, dict[str, str]] = {}
    for ticker in watchlist:
        try:
            identities.update(parse_ticker_association(association_payload, [ticker]))
        except IntakeError as exc:
            company_status[ticker] = exc.code
    association_identity_status = "VERIFIED" if len(identities) == len(watchlist) else "PARTIAL"
    raw_records.append(raw_metadata(
        association_response, ticker=None, cik=None, identity_status=association_identity_status
    ))

    for ticker in watchlist:
        identity = identities.get(ticker)
        if identity is None:
            continue
        url = SUBMISSIONS_URL_TEMPLATE.format(cik=identity["cik"])
        endpoint = f"submissions/{ticker}"
        try:
            response, payload = sec.request_json(url, endpoint)
        except IntakeError as exc:
            company_status[ticker] = exc.code
            continue
        raw_path = submissions_root / f"{ticker}.json"
        create_only_write(raw_path, response.body)
        raw_source_hashes[f"raw/submissions/{ticker}.json"] = response.sha256
        try:
            events, partial = normalize_submissions(
                payload=payload,
                identity=identity,
                response=response,
                decision_as_of=as_of,
                lookback_days=lookback_days,
                rules=rules,
            )
        except IntakeError as exc:
            company_status[ticker] = exc.code
            raw_records.append(raw_metadata(
                response, ticker=ticker, cik=identity["cik"], identity_status=exc.code
            ))
            continue
        company_status[ticker] = "SEC_PARTIAL_SOURCE" if partial else "PASS"
        all_events.extend(events)
        raw_records.append(raw_metadata(
            response,
            ticker=ticker,
            cik=identity["cik"],
            identity_status="VERIFIED" if not partial else "SEC_PARTIAL_SOURCE",
        ))

    all_events.sort(
        key=lambda item: (item["filing_date"], item["accepted_at"] or "", item["ticker"], item["accession_number"]),
        reverse=True,
    )
    create_only_json(raw_root / "source-metadata.json", {"schema_version": "0.1", "sources": raw_records})
    context = discover_portfolio_context(portfolio_artifact_root, decision_as_of=as_of)
    ownership_coverage = "PARTIAL" if any(status in {"PASS", "SEC_PARTIAL_SOURCE"} for status in company_status.values()) else "NOT_VERIFIED"
    pipeline_status = "PASS" if company_status and all(status == "PASS" for status in company_status.values()) else "PARTIAL"
    normalized = {
        "schema_version": "0.1",
        "pipeline_version": PIPELINE_VERSION,
        "decision_as_of": as_of.isoformat(),
        "lookback_days": lookback_days,
        "ownership_coverage": ownership_coverage,
        "portfolio_context": context,
        "deferred_symbols": dict(rules["deferred_symbols"]),
        "events": all_events,
    }
    _validate_or_raise(normalized, EVENTS_SCHEMA, "NORMALIZED_EVENTS_SCHEMA_INVALID")

    dashboard_model = {
        "run_time": as_of.isoformat(),
        "source_status": pipeline_status,
        "context": context,
        "lookback_days": lookback_days,
        "events": all_events,
        "ownership_coverage": ownership_coverage,
        "company_status": company_status,
    }
    dashboard_md = render_dashboard_markdown(**dashboard_model)
    dashboard_html = render_dashboard_html(dashboard_model)
    create_only_json(run_directory / "normalized-events.json", normalized)
    create_only_utf8_dashboard(run_directory / "dashboard.html", dashboard_html)
    create_only_utf8_dashboard(run_directory / "dashboard.md", dashboard_md)

    protected_after = {
        name: file_hash(path) if path.is_file() else None for name, path in protected_paths.items()
    }
    if protected_before != protected_after:
        raise IntakeError("PROTECTED_INPUT_MUTATION_DETECTED")
    company_check_status = "PASS" if pipeline_status == "PASS" else "PARTIAL"
    checks = [
        validation_check("SEC_USER_AGENT", "PASS", "configured; plaintext not persisted"),
        validation_check("HOST_ALLOWLIST", "PASS", ",".join(sorted(ALLOWED_HOSTS))),
        validation_check("HTTPS_ONLY", "PASS", "all requested SEC URLs validated before transport"),
        validation_check("TICKER_CIK_MAPPING", company_check_status, json.dumps(company_status, sort_keys=True)),
        validation_check("LOOKBACK_CUTOFF", "PASS", f"{lookback_days} calendar days; future filing dates excluded"),
        validation_check("ACCESSION_DEDUP", "PASS", "ticker-local accession number deduplication applied"),
        validation_check("FORM_NORMALIZATION", "PASS", "only configured forms present in submissions are emitted"),
        validation_check("DASHBOARD_GENERATION", "PASS", "HTML and Markdown generated"),
        validation_check("RAW_EVIDENCE_CAPTURE", "PASS", f"{len(raw_source_hashes)} immutable responses"),
        validation_check("OUTPUT_CREATE_ONLY", "PASS", "exclusive create writes in a new run directory"),
        validation_check("REQUEST_ACCOUNTING", "PASS", json.dumps(sec.accounting.as_dict(), sort_keys=True)),
        validation_check("OWNERSHIP_COVERAGE", "PARTIAL" if ownership_coverage == "PARTIAL" else "NOT_VERIFIED", ownership_coverage),
        validation_check("BROKER_CALL", "PASS", "NO"),
        validation_check("PORTFOLIO_MUTATION", "PASS", "protected hash unchanged"),
        validation_check("POLICY_MUTATION", "PASS", "protected hash unchanged"),
        validation_check("TASK_SCHEDULER_ACTIVATED", "PASS", "NO"),
        validation_check("ORDER_PATH", "PASS", "order authority false; no static order path"),
    ]
    validation_report = {
        "schema_version": "0.1",
        "run_id": run_id_value,
        "generated_at": utc_now(),
        "overall_status": pipeline_status,
        "checks": checks,
        "company_source_status": company_status,
    }
    _validate_or_raise(validation_report, VALIDATION_SCHEMA, "VALIDATION_REPORT_SCHEMA_INVALID")
    create_only_json(run_directory / "validation-report.json", validation_report)

    schema_paths = {
        "normalized_events": EVENTS_SCHEMA,
        "validation_report": VALIDATION_SCHEMA,
        "run_manifest": MANIFEST_SCHEMA,
    }
    artifact_paths = {
        "run_manifest": str((run_directory / "run-manifest.json").resolve()),
        "raw_source_root": str(raw_root.resolve()),
        "normalized_events": str((run_directory / "normalized-events.json").resolve()),
        "validation_report": str((run_directory / "validation-report.json").resolve()),
        "dashboard_html": str((run_directory / "dashboard.html").resolve()),
        "dashboard_md": str((run_directory / "dashboard.md").resolve()),
    }
    artifact_hashes = {
        name: file_hash(run_directory / name)
        for name in ("normalized-events.json", "validation-report.json", "dashboard.html", "dashboard.md")
    }
    artifact_hashes["raw/source-metadata.json"] = file_hash(raw_root / "source-metadata.json")
    git_branch = _git(["branch", "--show-current"])
    git_commit = _git(["rev-parse", "HEAD"])
    finished_at = utc_now()
    manifest = {
        "schema_version": "0.1",
        "pipeline_version": PIPELINE_VERSION,
        "run_id": run_id_value,
        "run_mode": RUN_MODE,
        "pipeline_status": pipeline_status,
        "git_branch": git_branch,
        "git_commit": git_commit,
        "git_worktree_dirty": bool(_git(["status", "--porcelain"])),
        "started_at": started_at,
        "finished_at": finished_at,
        "decision_as_of": as_of.isoformat(),
        "source_contract_urls": {
            "api_documentation": SEC_API_DOCUMENTATION_URL,
            "fair_access": SEC_FAIR_ACCESS_URL,
            "ticker_association": TICKER_ASSOCIATION_URL,
            "company_submissions_template": "https://data.sec.gov/submissions/CIK##########.json",
        },
        "allowed_hosts": sorted(ALLOWED_HOSTS),
        "lookback_days": lookback_days,
        "watchlist": watchlist,
        "implementation_hashes": {
            "sec_official_event_intake.py": file_hash(Path(__file__)),
            "validation_common.py": file_hash(Path(__file__).with_name("validation_common.py")),
        },
        "schema_hashes": {name: file_hash(path) for name, path in schema_paths.items()},
        "rules_hashes": {Path(rules_path).name: file_hash(rules_path)},
        "raw_source_hashes": dict(sorted(raw_source_hashes.items())),
        "artifact_hashes": dict(sorted(artifact_hashes.items())),
        "request_accounting": sec.accounting.as_dict(),
        "company_source_status": company_status,
        "event_count": len(all_events),
        "high_event_count": sum(event["materiality"] == "HIGH" for event in all_events),
        "ownership_coverage": ownership_coverage,
        "portfolio_context_status": context["status"],
        "portfolio_context_as_of": context["as_of"],
        "user_agent_configured": True,
        "user_agent_sha256": sec.user_agent_sha256,
        "network_access": "SEC_OFFICIAL_ONLY",
        "save_access": False,
        "broker_call": False,
        "portfolio_mutation": False,
        "policy_mutation": False,
        "task_scheduler_activated": False,
        "orders": "NONE",
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
        "protected_input_hashes": {
            name: {"before": protected_before[name], "after": protected_after[name]}
            for name in protected_paths
        },
        "artifact_paths": artifact_paths,
    }
    _validate_or_raise(manifest, MANIFEST_SCHEMA, "RUN_MANIFEST_SCHEMA_INVALID")
    create_only_json(run_directory / "run-manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SEC Official Event Intake v0.1 one-shot live shadow")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    try:
        manifest = run_pipeline(
            output_root=args.output_root,
            lookback_days=args.lookback_days,
            run_id=args.run_id,
        )
    except IntakeError as exc:
        print(json.dumps({
            "status": "BLOCKED",
            "code": exc.code,
            "scope": exc.scope,
            "detail": exc.detail,
            "order_authority": False,
        }, ensure_ascii=True, separators=(",", ":")), file=sys.stderr)
        return 2
    accounting = manifest["request_accounting"]
    print(json.dumps({
        "status": manifest["pipeline_status"],
        "run_id": manifest["run_id"],
        "run_directory": str(Path(manifest["artifact_paths"]["run_manifest"]).parent),
        "event_count": manifest["event_count"],
        "high_event_count": manifest["high_event_count"],
        "http_request_count": accounting["http_request_count"],
        "successful_request_count": accounting["successful_request_count"],
        "failed_request_count": accounting["failed_request_count"],
        "retry_count": accounting["retry_count"],
        "order_authority": False,
    }, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
