#!/usr/bin/env python3
"""Deterministic SAVE Daily PDF offline replay pipeline."""

from __future__ import annotations

import argparse
import ast
import hashlib
import html
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from validation_common import file_hash, load_json, validate_instance


ROOT = Path(__file__).resolve().parents[2]
PIPELINE_VERSION = "0.1"
RUN_MODE = "OFFLINE_REPLAY"
DEFAULT_OUTPUT_ROOT = ROOT / "workspace/outputs/save-daily-offline-replay"
DEFAULT_RULES_PATH = ROOT / "manage-us-stock-strategy/assets/save-daily-rules-v0.1.json"
DEFAULT_LOCALE_PATH = ROOT / "manage-us-stock-strategy/assets/locales/save-daily-ko-KR.json"
EVENTS_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/save-daily-normalized-events.schema.json"
VALIDATION_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/save-daily-validation-report.schema.json"
MANIFEST_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/save-daily-run-manifest.schema.json"
DEFAULT_PORTFOLIO_PATH = ROOT / "stock-strategy-system/portfolio_state.json"
DEFAULT_POLICY_PATH = ROOT / "stock-strategy-system/alert_policy.json"

MATERIALITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
IMPACT_RANK = {
    "NO_CHANGE": 0,
    "WATCH": 1,
    "REPRICE_REQUIRED": 2,
    "ASSET_REVIEW_REQUIRED": 3,
    "PORTFOLIO_RECOMPILE_REQUIRED": 4,
}
VERIFICATION_RANK = {
    "NOT_VERIFIED": 0,
    "SAVE_REPORTED": 1,
    "ORIGINAL_LINK_AVAILABLE": 2,
    "CONFLICTING": 3,
    "OFFICIAL_SOURCE_VERIFIED": 4,
}
HIGH_EVENT_TYPES = {
    "EARNINGS", "GUIDANCE", "CUSTOMER_CONTRACT", "DILUTION", "CONVERTIBLE",
    "REGULATORY", "LEGAL",
}
ROOT_MATERIAL_EVENT_TYPES = {
    "EARNINGS", "GUIDANCE", "CUSTOMER_CONTRACT", "DILUTION", "CONVERTIBLE",
    "REGULATORY", "SUPPLY_CHAIN", "CAPACITY",
}


class PipelineError(RuntimeError):
    """A fail-closed pipeline input, parsing, validation, or output error."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class PdfDocument:
    source_path: Path
    source_sha256: str
    source_file_size: int
    source_accessed_at: str
    page_count: int
    page_texts: tuple[str, ...]
    metadata: dict[str, str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_stream(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_pdf(path: str | Path) -> PdfDocument:
    source = Path(path).resolve()
    accessed_at = utc_now()
    if not source.is_file():
        raise PipelineError("EXTERNAL_FIXTURE_ACCESS_BLOCKED", str(source))
    try:
        size = source.stat().st_size
        if size <= 0:
            raise PipelineError("INVALID_PDF", "empty source file")
        digest = sha256_stream(source)
        reader = PdfReader(source, strict=True)
        if reader.is_encrypted:
            raise PipelineError("INVALID_PDF", "encrypted PDF is unsupported")
        if len(reader.pages) == 0:
            raise PipelineError("INVALID_PDF", "zero pages")
        page_texts = tuple(page.extract_text() or "" for page in reader.pages)
        metadata = {str(key): str(value) for key, value in (reader.metadata or {}).items()}
    except PipelineError:
        raise
    except (OSError, PdfReadError, ValueError, TypeError) as exc:
        raise PipelineError("INVALID_PDF", str(exc)) from exc
    return PdfDocument(
        source_path=source,
        source_sha256=digest,
        source_file_size=size,
        source_accessed_at=accessed_at,
        page_count=len(page_texts),
        page_texts=page_texts,
        metadata=metadata,
    )


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_date(value: str) -> str | None:
    compact = clean_text(value)
    iso_match = re.search(r"(?<!\d)(20\d{2})[-./](\d{1,2})[-./](\d{1,2})(?!\d)", compact)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))).isoformat()
        except ValueError:
            return None
    korean_match = re.search(
        r"(?<!\d)(20\d{2})\s*\ub144\s*(\d{1,2})\s*\uc6d4\s*([\d\s]{1,4})\s*\uc77c",
        compact,
    )
    if korean_match:
        day_text = re.sub(r"\s+", "", korean_match.group(3))
        try:
            return date(int(korean_match.group(1)), int(korean_match.group(2)), int(day_text)).isoformat()
        except ValueError:
            return None
    return None


def extract_metadata_date(metadata: dict[str, str]) -> str | None:
    for key in ("/CreationDate", "/ModDate"):
        value = metadata.get(key, "")
        match = re.search(r"D:(20\d{2})(\d{2})(\d{2})", value)
        if match:
            try:
                return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
            except ValueError:
                continue
    return None


def validate_source(
    document: PdfDocument,
    rules: dict[str, Any],
    expected_report_date: str | None = None,
) -> dict[str, Any]:
    page_one = clean_text(document.page_texts[0])
    cover_date = extract_date(page_one)
    filename_date = extract_date(document.source_path.name)
    news_label = str(rules["news_section_label"])
    section_date = None
    for text in document.page_texts:
        normalized = clean_text(text)
        if news_label in normalized:
            candidate = extract_date(normalized)
            if candidate:
                section_date = candidate
                break
    metadata_date = extract_metadata_date(document.metadata)
    candidates = {
        "cover_page": cover_date,
        "news_section": section_date,
        "filename": filename_date,
        "pdf_metadata": metadata_date,
        "expected": expected_report_date,
    }
    available = [value for value in candidates.values() if value]
    unique = sorted(set(available))
    if not available:
        status = "BLOCKED"
        report_date = None
    elif len(unique) > 1:
        status = "CONFLICTING"
        report_date = expected_report_date or cover_date or filename_date or unique[0]
    else:
        report_date = unique[0]
        required = (cover_date, filename_date, section_date)
        status = "PASS" if all(required) else "PARTIAL"
    title = re.split(r"20\d{2}", page_one, maxsplit=1)[0].strip() or None
    return {
        "report_title": title,
        "report_date": report_date,
        "status": status,
        "date_evidence": candidates,
    }


def _contains(value: str, keyword: str) -> bool:
    if re.fullmatch(r"[A-Za-z0-9]+", keyword) and len(keyword) <= 4:
        return re.search(
            r"(?<![A-Za-z0-9])" + re.escape(keyword) + r"(?![A-Za-z0-9])",
            value,
            flags=re.IGNORECASE,
        ) is not None
    if keyword == "\ube44\uc790":
        return re.search(r"(?<![\uac00-\ud7a3])\ube44\uc790(?![\uac00-\ud7a3])", value) is not None
    return keyword.casefold() in value.casefold()


def extract_tickers(value: str, rules: dict[str, Any]) -> list[str]:
    found: set[str] = set()
    for ticker, aliases in rules["ticker_aliases"].items():
        for alias in aliases:
            if _contains(value, str(alias)):
                found.add(str(ticker))
                break
    for match in re.finditer(r"(?<![A-Za-z0-9])\$([A-Z][A-Z0-9.-]{0,4})(?![A-Za-z0-9])", value):
        found.add(match.group(1))
    return sorted(found)


def map_root_theses(
    value: str,
    rules: dict[str, Any],
    tickers: list[str] | None = None,
    event_type: str | None = None,
) -> list[str]:
    resolved_tickers = set(tickers if tickers is not None else extract_tickers(value, rules))
    resolved_event_type = event_type or map_event_type(value, rules)
    roots = []
    for root in rules["root_theses"]:
        evidence = rules["root_thesis_evidence"][root]
        ticker_match = bool(resolved_tickers & set(evidence["explicit_tickers"]))
        phrase_match = any(_contains(value, phrase) for phrase in evidence["strong_phrases"])
        group_match = any(
            all(_contains(value, keyword) for keyword in group)
            for group in evidence["keyword_groups"]
        )
        event_domains = evidence.get("event_type_domains", {}).get(resolved_event_type, [])
        event_domain_match = bool(event_domains) and any(
            _contains(value, keyword) for keyword in event_domains
        )
        if ticker_match or phrase_match or group_match or event_domain_match:
            roots.append(str(root))
    return roots


def map_event_type(value: str, rules: dict[str, Any]) -> str:
    for item in rules["event_type_rules"]:
        if any(_contains(value, keyword) for keyword in item["keywords"]):
            return str(item["event_type"])
    return "OTHER"


def detect_source(value: str, rules: dict[str, Any]) -> tuple[str, str]:
    names = []
    for source_name, aliases in rules["source_aliases"].items():
        if any(_contains(value, alias) for alias in aliases):
            names.append(str(source_name))
    if not names:
        return "SAVE", "SAVE_ONLY"
    return names[0], "SAVE_ATTRIBUTED"


def extract_article_title(text: str, rules: dict[str, Any]) -> tuple[str, str, str]:
    normalized = clean_text(text)
    news_label = str(rules["news_section_label"])
    company_roundup_label = str(rules["company_roundup_label"])
    marker_index = normalized.find(news_label)
    confidence = "MEDIUM"
    if normalized.startswith(company_roundup_label):
        raw = company_roundup_label
        confidence = "MEDIUM"
    elif marker_index > 0:
        raw = normalized[:marker_index].strip()
        confidence = "HIGH"
    elif marker_index == 0:
        body = normalized[len(news_label):].strip()
        raw = re.split(r"\s+-\s+", body, maxsplit=1)[0]
    elif normalized.startswith("\uac1c\ubcc4 \uae30\uc5c5"):
        raw = normalized.split(" ", 2)[0] + " " + normalized.split(" ", 2)[1]
    else:
        raw = re.split(r"\s+-\s+", normalized, maxsplit=1)[0]
    crypto_label = "\uc554\ud638\ud654\ud3d0 \uc8fc\uc694 \uc18c\uc2dd"
    if crypto_label in raw:
        raw = raw[raw.index(crypto_label):]
    raw = raw[:260].strip(" -")
    original_pattern = r"\(\s*" + re.escape(str(rules["original_link_label"])) + r"\s*\)"
    title = clean_text(re.sub(original_pattern, "", raw)).strip(" -")
    if not title:
        title = clean_text(normalized[:160]).strip(" -")
        confidence = "LOW"
    return raw, title, confidence


def map_portfolio_relevance(
    title: str,
    full_text: str,
    tickers: list[str],
    roots: list[str],
    event_type: str,
    rules: dict[str, Any],
) -> list[str]:
    title_tickers = set(extract_tickers(title, rules))
    relevant: set[str] = set()
    holdings = set(rules["holdings"])
    challengers = set(rules["challengers"])
    relevant.update(title_tickers & holdings)
    relevant.update(title_tickers & challengers)
    if "MRVL" in title_tickers:
        relevant.update({"MRVL", "MVLL"})
    if "SEMICONDUCTOR" in roots:
        relevant.add("SOXL")
    nbis_terms = rules["nbis_relevance_keywords"]
    if (
        any(_contains(full_text, term) for term in nbis_terms)
        and ("AI_INFRASTRUCTURE" in roots or "DATA_CENTER_POWER" in roots or event_type in {"CONVERTIBLE", "DILUTION", "CUSTOMER_CONTRACT"})
    ):
        relevant.add("NBIS")
    allowed = holdings | challengers
    return sorted(relevant & allowed)


def route_materiality(
    title: str,
    full_text: str,
    event_type: str,
    roots: list[str],
    relevance: list[str],
    rules: dict[str, Any],
) -> tuple[str, str, str, str]:
    title_tickers = set(extract_tickers(title, rules))
    direct_holdings = title_tickers & set(rules["holdings"])
    direct_challengers = title_tickers & set(rules["challengers"])
    direct_portfolio = direct_holdings | direct_challengers
    if direct_portfolio and event_type in HIGH_EVENT_TYPES | {"CAPITAL_STRUCTURE", "SUPPLY_CHAIN", "CAPACITY"}:
        materiality = "HIGH"
        materiality_reason = "DIRECT_PORTFOLIO_TICKER_AND_MATERIAL_EVENT_TYPE"
    elif relevance and roots and event_type in ROOT_MATERIAL_EVENT_TYPES:
        materiality = "HIGH"
        materiality_reason = "APPROVED_ROOT_THESIS_AND_PORTFOLIO_RELEVANCE"
    elif (
        event_type == "FED"
        and _time_sensitivity(full_text) == "NEXT_48_HOURS"
        and bool(set(roots) & {"BANK_CREDIT", "MARKET_VOLATILITY"})
    ):
        materiality = "HIGH"
        materiality_reason = "NEAR_TERM_FED_PORTFOLIO_RISK_CONTEXT"
    elif relevance or roots or event_type == "ANALYST_ACTION":
        materiality = "MEDIUM"
        materiality_reason = "INDIRECT_PORTFOLIO_OR_ROOT_THESIS_RELEVANCE"
    else:
        materiality = "LOW"
        materiality_reason = "NO_PORTFOLIO_CHALLENGER_OR_ROOT_THESIS_RELEVANCE"
    if direct_holdings:
        if event_type in {"EARNINGS", "GUIDANCE", "CAPITAL_STRUCTURE", "DILUTION", "CONVERTIBLE"}:
            impact = "REPRICE_REQUIRED"
            impact_reason = "DIRECT_HOLDING_REPRICE_EVENT"
        else:
            impact = "ASSET_REVIEW_REQUIRED"
            impact_reason = "DIRECT_HOLDING_MATERIAL_EVENT"
    elif direct_challengers and materiality == "HIGH":
        impact = "ASSET_REVIEW_REQUIRED"
        impact_reason = "DIRECT_CHALLENGER_MATERIAL_EVENT"
    elif relevance or roots:
        impact = "WATCH"
        impact_reason = "INDIRECT_RELEVANCE_REQUIRES_ATTENTION_ONLY"
    else:
        impact = "NO_CHANGE"
        impact_reason = "NO_RELEVANCE_NO_DECISION_CHANGE"
    return materiality, impact, materiality_reason, impact_reason


def _time_sensitivity(value: str) -> str:
    terms = ("\uc624\ub298", "\uae08\uc694\uc77c", "\ub2e4\uc74c \ub0a0", "48\uc2dc\uac04", "\uc7a5 \uc2dc\uc791 \uc804")
    return "NEXT_48_HOURS" if any(term in value for term in terms) else "ONGOING"


def _significant_tokens(title: str, rules: dict[str, Any]) -> set[str]:
    stopwords = {str(item).casefold() for item in rules["title_stopwords"]}
    tokens = {
        token.casefold()
        for token in re.findall(r"[A-Za-z0-9\uac00-\ud7a3]+", title)
        if len(token) >= 2 and token.casefold() not in stopwords
    }
    return tokens


def event_fingerprint(report_date: str, title: str, event_type: str, tickers: list[str]) -> str:
    payload = "|".join([report_date, clean_text(title).casefold(), event_type, ",".join(sorted(tickers))])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_duplicate(left: dict[str, Any], right: dict[str, Any], rules: dict[str, Any]) -> bool:
    if left["event_fingerprint"] == right["event_fingerprint"]:
        return True
    if left["event_type"] != right["event_type"]:
        return False
    if abs(left["page_number"] - right["page_number"]) > 3:
        return False
    common = _significant_tokens(left["title"], rules) & _significant_tokens(right["title"], rules)
    return len(common) >= 2


def _merge_event(target: dict[str, Any], item: dict[str, Any]) -> None:
    target["page_numbers"] = sorted(set(target["page_numbers"] + item["page_numbers"]))
    target["source_names"] = sorted(set(target["source_names"] + item["source_names"]))
    target["source_count"] = len(target["source_names"])
    target["article_count"] += item["article_count"]
    target["tickers"] = sorted(set(target["tickers"] + item["tickers"]))
    target["root_theses"] = sorted(set(target["root_theses"] + item["root_theses"]))
    target["portfolio_relevance"] = sorted(set(target["portfolio_relevance"] + item["portfolio_relevance"]))
    target["duplicate_status"] = "CLUSTERED"
    if len(target["source_names"]) > 1:
        target["source_name"] = "MULTIPLE_SAVE_ATTRIBUTED_SOURCES"
        target["source_status"] = "MULTIPLE_SAVE_ATTRIBUTED_SOURCES"
    if MATERIALITY_RANK[item["materiality"]] > MATERIALITY_RANK[target["materiality"]]:
        target["materiality"] = item["materiality"]
        target["materiality_reason"] = item["materiality_reason"]
    if IMPACT_RANK[item["decision_impact"]] > IMPACT_RANK[target["decision_impact"]]:
        target["decision_impact"] = item["decision_impact"]
        target["decision_impact_reason"] = item["decision_impact_reason"]
    if VERIFICATION_RANK[item["verification_status"]] > VERIFICATION_RANK[target["verification_status"]]:
        target["verification_status"] = item["verification_status"]
    if item["original_link_status"] == "AVAILABLE_LABEL_ONLY":
        target["original_link_status"] = "AVAILABLE_LABEL_ONLY"


def extract_events(
    page_texts: tuple[str, ...] | list[str],
    report_date: str,
    rules: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    news_label = str(rules["news_section_label"])
    news_cover = None
    schedule_start = None
    for page_number, raw_text in enumerate(page_texts, 1):
        text = clean_text(raw_text)
        if news_cover is None and news_label in text and extract_date(text):
            news_cover = page_number
            continue
        if news_cover is not None and any(label in text for label in rules["schedule_section_labels"]):
            schedule_start = page_number
            break
    if news_cover is None:
        return [], 0
    end_page = schedule_start or (len(page_texts) + 1)
    candidates: list[dict[str, Any]] = []
    for page_number in range(news_cover + 1, end_page):
        text = clean_text(page_texts[page_number - 1])
        if len(text) < 120:
            continue
        raw_title, title, confidence = extract_article_title(text, rules)
        tickers = extract_tickers(text, rules)
        event_type = map_event_type(text, rules)
        if title == str(rules["company_roundup_label"]):
            event_type = "OTHER"
        roots = map_root_theses(text, rules, tickers, event_type)
        source_name, source_status = detect_source(text, rules)
        original_available = _contains(text, str(rules["original_link_label"]))
        verification = "ORIGINAL_LINK_AVAILABLE" if original_available else "SAVE_REPORTED"
        relevance = map_portfolio_relevance(title, text, tickers, roots, event_type, rules)
        materiality, impact, materiality_reason, impact_reason = route_materiality(
            title, text, event_type, roots, relevance, rules,
        )
        fingerprint = event_fingerprint(report_date, title, event_type, tickers)
        event = {
            "event_id": "save-" + fingerprint[:20],
            "event_fingerprint": fingerprint,
            "report_date": report_date,
            "page_number": page_number,
            "page_numbers": [page_number],
            "section": "TODAY_NEWS",
            "title": title,
            "raw_title": raw_title,
            "source_name": source_name,
            "source_names": [source_name],
            "source_status": source_status,
            "source_count": 1,
            "article_count": 1,
            "published_at": None,
            "tickers": tickers,
            "root_theses": roots,
            "event_type": event_type,
            "verification_status": verification,
            "materiality": materiality,
            "materiality_reason": materiality_reason,
            "time_sensitivity": _time_sensitivity(text),
            "decision_impact": impact,
            "decision_impact_reason": impact_reason,
            "claim_summary": text[:420],
            "raw_text_excerpt": text[:420],
            "original_link_status": "AVAILABLE_LABEL_ONLY" if original_available else "NOT_PRESENT",
            "extraction_method": "PDF_TEXT_LAYER",
            "extraction_confidence": confidence,
            "duplicate_status": "UNIQUE",
            "portfolio_relevance": relevance,
        }
        candidates.append(event)
    clusters: list[dict[str, Any]] = []
    for candidate in candidates:
        match = next((event for event in clusters if _is_duplicate(event, candidate, rules)), None)
        if match is None:
            clusters.append(candidate)
        else:
            _merge_event(match, candidate)
    return clusters, len(candidates)


def _schedule_text_evidence(page_texts: tuple[str, ...] | list[str], rules: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = []
    for page_number, raw_text in enumerate(page_texts, 1):
        text = clean_text(raw_text)
        if not any(label in text for label in rules["schedule_section_labels"]):
            continue
        year_week = re.search(r"(20\d{2})\s*\ub144\s*(\d{1,2})\s*\uc6d4\s*(\d{1,2})\s*\uc8fc(?:\s*\ucc28)?", text)
        month_day = re.search(r"(?<!\d)(\d{1,2})\s*\uc6d4\s*(\d{1,2})\s*\uc77c(?:\s*\(\s*[\uac00-\ud7a3]\s*\))?", text)
        if year_week:
            evidence.append({
                "page_number": page_number,
                "extracted_value": year_week.group(0),
                "date_kind": "YEAR_MONTH_WEEK",
                "date_components": list(year_week.groups()),
                "observation_method": "PDF_TEXT_LAYER",
                "verification_status": "EXTRACTED_TEXT_ONLY",
            })
        if month_day:
            evidence.append({
                "page_number": page_number,
                "extracted_value": month_day.group(0),
                "date_kind": "MONTH_DAY",
                "date_components": list(month_day.groups()),
                "observation_method": "PDF_TEXT_LAYER",
                "verification_status": "EXTRACTED_TEXT_ONLY",
            })
    return evidence


def validate_schedule(
    page_texts: tuple[str, ...] | list[str],
    report_date: str,
    rules: dict[str, Any],
) -> dict[str, Any]:
    text_evidence = _schedule_text_evidence(page_texts, rules)
    report = date.fromisoformat(report_date)
    text_conflict = False
    for item in text_evidence:
        if item["date_kind"] == "YEAR_MONTH_WEEK":
            year, month, _week = item["date_components"]
            text_conflict = text_conflict or int(year) != report.year or int(month) != report.month
        elif item["date_kind"] == "MONTH_DAY":
            month, day = item["date_components"]
            text_conflict = text_conflict or int(month) != report.month or int(day) != report.day
    if not text_evidence:
        return {
            "status": "PARTIAL",
            "auto_use": "NO",
            "date_conflict_status": "NOT_VERIFIED",
            "visual_validation": "NOT_VERIFIED",
            "text_evidence": [],
        }
    return {
        "status": "CONFLICTING" if text_conflict else "PASS",
        "auto_use": "NO" if text_conflict else "YES",
        "date_conflict_status": "SECTION_DATE_CONFLICT" if text_conflict else "NONE",
        "visual_validation": "NOT_VERIFIED",
        "text_evidence": text_evidence,
    }


def portfolio_context(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "LAST_KNOWN", "as_of": None, "source_path": str(path.resolve()), "source_sha256": None}
    value = load_json(path)
    return {
        "status": "LAST_KNOWN",
        "as_of": value.get("last_updated_at"),
        "source_path": str(path.resolve()),
        "source_sha256": file_hash(path),
    }


def _top_events(events: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    return sorted(
        events,
        key=lambda item: (
            -IMPACT_RANK[item["decision_impact"]],
            -MATERIALITY_RANK[item["materiality"]],
            item["page_number"],
        ),
    )[:limit]


def overall_result(events: list[dict[str, Any]]) -> str:
    if not events:
        return "NO_CHANGE"
    return max((event["decision_impact"] for event in events), key=lambda value: IMPACT_RANK[value])


def _impact_summary(events: list[dict[str, Any]], key: str, locale: dict[str, Any]) -> str:
    matches = [event for event in _top_events(events, len(events)) if key in event["portfolio_relevance"]]
    if not matches:
        return str(locale["no_direct_event"])
    return "; ".join(event["title"] for event in matches[:2])


def _root_summary(events: list[dict[str, Any]], root: str, locale: dict[str, Any]) -> str:
    matches = [event for event in _top_events(events, len(events)) if root in event["root_theses"]]
    if not matches:
        return str(locale["no_events"])
    return f"{len(matches)} - {matches[0]['title']}"


def render_dashboard_markdown(
    *,
    report_date: str,
    pipeline_status: str,
    source_status: str,
    schedule: dict[str, Any],
    context: dict[str, Any],
    events: list[dict[str, Any]],
    locale: dict[str, Any],
) -> str:
    result = overall_result(events)
    summary = locale["no_change"] if result == "NO_CHANGE" else (locale["watch"] if result == "WATCH" else locale["review"])
    action = "NONE" if result == "NO_CHANGE" else ("READ_EVENT" if result == "WATCH" else "ASSET_REVIEW_REQUIRED")
    top = _top_events(events)
    lines = [
        "# SAVE DAILY PORTFOLIO RADAR",
        "",
        f"Report Date: {report_date}",
        f"Pipeline Status: {pipeline_status}",
        f"Source Validation: {source_status}",
        f"Schedule Status: {schedule['status']}",
        f"Portfolio Context As-of: {context.get('as_of') or 'NOT_VERIFIED'} ({context['status']})",
        "",
        "## TODAY'S RESULT",
        "",
        f"**{result}**",
        "",
        str(summary),
        "",
        "## TOP PORTFOLIO EVENTS",
        "",
    ]
    if top:
        for index, event in enumerate(top, 1):
            affected = ", ".join(event["portfolio_relevance"]) or ", ".join(event["root_theses"]) or "NONE"
            lines.extend([
                f"{index}. **{event['title']}**",
                f"   - {locale['affected']}: {affected}",
                f"   - {locale['reason']}: {event['materiality']} / {event['event_type']} / page {','.join(map(str, event['page_numbers']))}",
                f"   - {locale['verification']}: {event['verification_status']}",
            ])
    else:
        lines.append(f"1. {locale['no_events']}")
    lines.extend([
        "",
        "## HOLDINGS IMPACT",
        "",
        f"MRVL / MVLL: {_impact_summary(events, 'MRVL', locale) if any('MRVL' in e['portfolio_relevance'] or 'MVLL' in e['portfolio_relevance'] for e in events) else locale['no_direct_event']}",
        f"NBIS: {_impact_summary(events, 'NBIS', locale)}",
        f"SOXL: {_impact_summary(events, 'SOXL', locale)}",
        "",
        "## CHALLENGER IMPACT",
        "",
        f"PGR: {_impact_summary(events, 'PGR', locale)}",
        f"JPM: {_impact_summary(events, 'JPM', locale)}",
        f"CME: {_impact_summary(events, 'CME', locale)}",
        f"V: {_impact_summary(events, 'V', locale)}",
        "",
        "## ROOT-THESIS IMPACT",
        "",
        f"AI Infrastructure: {_root_summary(events, 'AI_INFRASTRUCTURE', locale)}",
        f"Semiconductor: {_root_summary(events, 'SEMICONDUCTOR', locale)}",
        f"Data-center Power: {_root_summary(events, 'DATA_CENTER_POWER', locale)}",
        f"Bank Credit: {_root_summary(events, 'BANK_CREDIT', locale)}",
        f"Insurance: {_root_summary(events, 'INSURANCE_PRICING', locale)}",
        f"Market Volatility: {_root_summary(events, 'MARKET_VOLATILITY', locale)}",
        f"Payment Networks: {_root_summary(events, 'PAYMENT_NETWORKS', locale)}",
        "",
        "## NEXT 48 HOURS",
        "",
        f"Status: {schedule['status']}",
        str(locale["schedule_auto_use_no"] if schedule["auto_use"] == "NO" else "Schedule auto-use: YES"),
        "",
        "## MATERIAL UNKNOWNS",
        "",
        f"1. {locale['not_verified']}",
        f"2. {locale['schedule_conflict'] if schedule['status'] == 'CONFLICTING' else locale['schedule_auto_use_no']}",
        f"3. {locale['portfolio_stale']}",
        "",
        "## USER ACTION",
        "",
        f"**{action}**",
        "",
        str(locale["no_action"] if action == "NONE" else (locale["read_event"] if action == "READ_EVENT" else locale["asset_review"])),
        "",
        "## EXECUTION STATUS",
        "",
        "SAVE Authority: EXTERNAL_REFERENCE",
        "Portfolio Context: LAST_KNOWN",
        "Canonical Portfolio Price: KIWOOM when valid",
        "Order Authority: FALSE",
        "Execution Quantity: NULL",
        "Automatic Order: OFF",
        "",
        f"> {locale['source_notice']}",
        "",
    ])
    return "\n".join(lines)


def render_dashboard_html(
    *,
    report_date: str,
    pipeline_status: str,
    source_status: str,
    schedule: dict[str, Any],
    context: dict[str, Any],
    events: list[dict[str, Any]],
    locale: dict[str, Any],
) -> str:
    result = overall_result(events)
    summary = locale["no_change"] if result == "NO_CHANGE" else (locale["watch"] if result == "WATCH" else locale["review"])
    action = "NONE" if result == "NO_CHANGE" else ("READ_EVENT" if result == "WATCH" else "ASSET_REVIEW_REQUIRED")
    top_cards = []
    for event in _top_events(events):
        affected = ", ".join(event["portfolio_relevance"]) or ", ".join(event["root_theses"]) or "NONE"
        top_cards.append(
            "<article class='event'><div class='eyebrow'>"
            + html.escape(f"{event['materiality']} / {event['event_type']} / PAGE {','.join(map(str, event['page_numbers']))}")
            + "</div><h3>" + html.escape(event["title"]) + "</h3><p>"
            + html.escape(f"{locale['affected']}: {affected}") + "</p><span class='pill'>"
            + html.escape(event["verification_status"]) + "</span></article>"
        )
    if not top_cards:
        top_cards.append("<article class='event'><h3>" + html.escape(str(locale["no_events"])) + "</h3></article>")
    holdings = {
        "MRVL / MVLL": _impact_summary(events, "MRVL", locale) if any("MRVL" in e["portfolio_relevance"] or "MVLL" in e["portfolio_relevance"] for e in events) else locale["no_direct_event"],
        "NBIS": _impact_summary(events, "NBIS", locale),
        "SOXL": _impact_summary(events, "SOXL", locale),
    }
    challengers = {key: _impact_summary(events, key, locale) for key in ("PGR", "JPM", "CME", "V")}
    roots = {
        "AI Infrastructure": _root_summary(events, "AI_INFRASTRUCTURE", locale),
        "Semiconductor": _root_summary(events, "SEMICONDUCTOR", locale),
        "Data-center Power": _root_summary(events, "DATA_CENTER_POWER", locale),
        "Bank Credit": _root_summary(events, "BANK_CREDIT", locale),
        "Insurance": _root_summary(events, "INSURANCE_PRICING", locale),
        "Market Volatility": _root_summary(events, "MARKET_VOLATILITY", locale),
        "Payment Networks": _root_summary(events, "PAYMENT_NETWORKS", locale),
    }

    def rows(values: dict[str, str]) -> str:
        return "".join(
            "<div class='impact-row'><strong>" + html.escape(key) + "</strong><span>" + html.escape(str(value)) + "</span></div>"
            for key, value in values.items()
        )

    return """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAVE Daily Portfolio Radar</title>
<style>
:root{--ink:#172033;--muted:#667085;--line:#e4e7ec;--panel:#fff;--bg:#f4f6fb;--blue:#405cf5;--navy:#121a35;--amber:#f5a524}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"Noto Sans KR","Segoe UI",sans-serif;line-height:1.55}
.shell{max-width:1180px;margin:0 auto;padding:40px 24px 72px}.hero{background:linear-gradient(135deg,var(--navy),#26366d);color:#fff;border-radius:24px;padding:32px;box-shadow:0 18px 50px #1d2a5526}
.brand{font-size:13px;letter-spacing:.14em;font-weight:800;color:#aeb8ff}.hero h1{margin:8px 0 18px;font-size:clamp(28px,5vw,52px);line-height:1.05}.meta{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}.meta div{background:#ffffff12;border:1px solid #ffffff24;border-radius:14px;padding:12px}.meta small{display:block;color:#bac1d8}.meta strong{display:block;margin-top:3px}
.result{margin-top:20px;background:var(--panel);border-radius:22px;padding:26px;border-left:7px solid var(--amber)}.result .label,.eyebrow{font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);font-weight:800}.result h2{font-size:38px;margin:4px 0;color:#ab6400}.result p{margin:0;max-width:800px}
h2.section{margin:34px 0 14px;font-size:22px}.events{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.event,.panel{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:20px}.event h3{margin:6px 0 10px;font-size:18px}.event p{color:var(--muted)}.pill{display:inline-block;border-radius:999px;background:#eef1ff;color:#3347bd;font-size:12px;font-weight:800;padding:6px 10px}
.columns{display:grid;grid-template-columns:1fr 1fr;gap:16px}.impact-row{display:grid;grid-template-columns:155px 1fr;gap:12px;padding:12px 0;border-bottom:1px solid var(--line)}.impact-row:last-child{border-bottom:0}.impact-row span{color:var(--muted)}
.notice{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}.warning{border:1px solid #ffd28a;background:#fff8eb}.action{border:1px solid #b9c4ff;background:#f3f5ff}.safety{margin-top:18px;background:#10182f;color:#e7eaff}.safety-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.safety-grid div{background:#ffffff0c;border-radius:12px;padding:10px}.safety-grid small{display:block;color:#aeb7d2}.footer{color:var(--muted);font-size:13px;margin-top:18px}
@media(max-width:820px){.meta,.events,.columns,.notice,.safety-grid{grid-template-columns:1fr}.impact-row{grid-template-columns:1fr}.shell{padding:18px 14px 44px}.hero{padding:24px}.result h2{font-size:30px}}
</style></head><body><main class="shell">
<section class="hero"><div class="brand">SAVE DAILY / OFFLINE REPLAY</div><h1>SAVE DAILY PORTFOLIO RADAR</h1><div class="meta">
<div><small>Report Date</small><strong>""" + html.escape(report_date) + """</strong></div>
<div><small>Pipeline</small><strong>""" + html.escape(pipeline_status) + """</strong></div>
<div><small>Source</small><strong>""" + html.escape(source_status) + """</strong></div>
<div><small>Schedule</small><strong>""" + html.escape(schedule["status"]) + """</strong></div>
<div><small>Portfolio As-of</small><strong>""" + html.escape(str(context.get("as_of") or "NOT_VERIFIED")) + """</strong></div>
</div></section>
<section class="result"><div class="label">TODAY'S RESULT</div><h2>""" + html.escape(result) + """</h2><p>""" + html.escape(str(summary)) + """</p></section>
<h2 class="section">TOP PORTFOLIO EVENTS</h2><section class="events">""" + "".join(top_cards) + """</section>
<h2 class="section">PORTFOLIO IMPACT</h2><section class="columns"><div class="panel"><h3>HOLDINGS IMPACT</h3>""" + rows(holdings) + """</div><div class="panel"><h3>CHALLENGER IMPACT</h3>""" + rows(challengers) + """</div></section>
<h2 class="section">ROOT-THESIS IMPACT</h2><section class="panel">""" + rows(roots) + """</section>
<section class="notice"><div class="panel warning"><div class="eyebrow">NEXT 48 HOURS</div><h3>""" + html.escape(schedule["status"]) + """</h3><p>""" + html.escape(str(locale["schedule_conflict"] if schedule["status"] == "CONFLICTING" else locale["schedule_auto_use_no"])) + """</p></div><div class="panel action"><div class="eyebrow">USER ACTION</div><h3>""" + html.escape(action) + """</h3><p>""" + html.escape(str(locale["no_action"] if action == "NONE" else (locale["read_event"] if action == "READ_EVENT" else locale["asset_review"]))) + """</p></div></section>
<h2 class="section">MATERIAL UNKNOWNS</h2><section class="panel"><ol><li>""" + html.escape(str(locale["not_verified"])) + """</li><li>""" + html.escape(str(locale["schedule_conflict"])) + """</li><li>""" + html.escape(str(locale["portfolio_stale"])) + """</li></ol></section>
<section class="panel safety"><h3>EXECUTION STATUS</h3><div class="safety-grid"><div><small>SAVE Authority</small>EXTERNAL_REFERENCE</div><div><small>Portfolio Context</small>LAST_KNOWN</div><div><small>Canonical Portfolio Price</small>KIWOOM when valid</div><div><small>Order Authority</small>FALSE</div><div><small>Execution Quantity</small>NULL</div><div><small>Automatic Order</small>OFF</div></div></section>
<p class="footer">""" + html.escape(str(locale["source_notice"])) + """</p>
</main></body></html>"""


def validation_check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"check": name, "status": status, "detail": detail}


def audit_static_paths() -> dict[str, Any]:
    network_imports = {"requests", "httpx", "socket", "urllib", "selenium", "playwright"}
    broker_imports = {"pykiwoom", "kiwoom", "alpaca_trade_api", "ib_insync"}
    order_calls = {"submit_order", "place_order", "send_order", "cancel_order", "modify_order"}
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    called = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    return {
        "network_path_present": bool(imported & network_imports),
        "broker_path_present": bool(imported & broker_imports),
        "order_path_present": bool(called & order_calls),
        "imported_modules": sorted(imported),
    }


def create_only_write(path: Path, payload: str | bytes) -> None:
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def create_only_json(path: Path, value: Any) -> None:
    create_only_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


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
        raise PipelineError(code, "; ".join(errors))


def generate_run_id(report_date: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"save-daily-{report_date}-{stamp}"


def _validate_run_id(run_id: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", run_id) is None:
        raise PipelineError("INVALID_RUN_ID", run_id)
    return run_id


def build_implementation_provenance(
    rules_path: str | Path,
    locale_path: str | Path,
) -> dict[str, Any]:
    schema_paths = {
        "normalized_events": EVENTS_SCHEMA,
        "validation_report": VALIDATION_SCHEMA,
        "run_manifest": MANIFEST_SCHEMA,
    }
    return {
        "save_daily_pipeline.py": file_hash(Path(__file__)),
        "rules_asset": file_hash(rules_path),
        "locale_asset": file_hash(locale_path),
        "schemas": {name: file_hash(path) for name, path in schema_paths.items()},
    }


def build_dependency_provenance() -> dict[str, str | None]:
    requirement_lines = (ROOT / "manage-us-stock-strategy/requirements.txt").read_text(encoding="utf-8").splitlines()
    declared = next((line.strip() for line in requirement_lines if line.strip().casefold().startswith("pypdf")), None)
    return {
        "declared_pypdf_requirement": declared,
        "runtime_pypdf_version": importlib.metadata.version("pypdf"),
        "python_version": platform.python_version(),
    }


def run_pipeline(
    *,
    source_path: str | Path,
    expected_report_date: str | None = None,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    run_id: str | None = None,
    rules_path: str | Path = DEFAULT_RULES_PATH,
    locale_path: str | Path = DEFAULT_LOCALE_PATH,
    portfolio_path: str | Path = DEFAULT_PORTFOLIO_PATH,
    policy_path: str | Path = DEFAULT_POLICY_PATH,
) -> dict[str, Any]:
    started_at = utc_now()
    rules = load_json(rules_path)
    locale = load_json(locale_path)
    document = load_pdf(source_path)
    if not any(clean_text(text) for text in document.page_texts):
        raise PipelineError("EMPTY_EXTRACTION", str(document.source_path))
    source_validation = validate_source(document, rules, expected_report_date)
    if source_validation["status"] == "BLOCKED" or not source_validation["report_date"]:
        raise PipelineError("REPORT_DATE_BLOCKED")
    report_date = str(source_validation["report_date"])
    events, extracted_item_count = extract_events(document.page_texts, report_date, rules)
    if not events:
        raise PipelineError("EVENT_EXTRACTION_EMPTY")
    schedule = validate_schedule(document.page_texts, report_date, rules)
    context = portfolio_context(Path(portfolio_path))
    static_paths = audit_static_paths()
    if any(static_paths[key] for key in ("network_path_present", "broker_path_present", "order_path_present")):
        raise PipelineError("OFFLINE_BOUNDARY_VIOLATION")
    protected_paths = {
        "portfolio_state": Path(portfolio_path).resolve(),
        "alert_policy": Path(policy_path).resolve(),
    }
    protected_before = {
        name: file_hash(path) if path.is_file() else None for name, path in protected_paths.items()
    }
    run_id_value = _validate_run_id(run_id or generate_run_id(report_date))
    root = Path(output_root).resolve()
    run_directory = root / report_date / run_id_value
    if run_directory.exists():
        raise PipelineError("RUN_COLLISION", str(run_directory))
    run_directory.mkdir(parents=True, exist_ok=False)

    pipeline_status = "PASS" if source_validation["status"] == "PASS" and schedule["status"] == "PASS" else "PARTIAL"
    normalized = {
        "schema_version": PIPELINE_VERSION,
        "report_date": report_date,
        "generated_at": started_at,
        "events": events,
    }
    _validate_or_raise(normalized, EVENTS_SCHEMA, "NORMALIZED_EVENTS_SCHEMA_INVALID")
    markdown = render_dashboard_markdown(
        report_date=report_date,
        pipeline_status=pipeline_status,
        source_status=source_validation["status"],
        schedule=schedule,
        context=context,
        events=events,
        locale=locale,
    )
    html_dashboard = render_dashboard_html(
        report_date=report_date,
        pipeline_status=pipeline_status,
        source_status=source_validation["status"],
        schedule=schedule,
        context=context,
        events=events,
        locale=locale,
    )

    artifact_paths = {
        "run_manifest": str((run_directory / "run-manifest.json").resolve()),
        "normalized_events": str((run_directory / "normalized-events.json").resolve()),
        "validation_report": str((run_directory / "validation-report.json").resolve()),
        "dashboard_html": str((run_directory / "dashboard.html").resolve()),
        "dashboard_md": str((run_directory / "dashboard.md").resolve()),
    }
    create_only_json(run_directory / "normalized-events.json", normalized)
    create_only_write(run_directory / "dashboard.html", html_dashboard)
    create_only_write(run_directory / "dashboard.md", markdown)

    protected_after = {
        name: file_hash(path) if path.is_file() else None for name, path in protected_paths.items()
    }
    if protected_before != protected_after:
        raise PipelineError("PROTECTED_INPUT_MUTATION_DETECTED")
    schedule_check_status = "CONFLICTING" if schedule["status"] == "CONFLICTING" else schedule["status"]
    checks = [
        validation_check("SOURCE_FILE_ACCESS", "PASS", str(document.source_path)),
        validation_check("SHA256_CALCULATED", "PASS", document.source_sha256),
        validation_check("PAGE_COUNT", "PASS", str(document.page_count)),
        validation_check("REPORT_DATE", "PASS", report_date),
        validation_check("REPORT_DATE_CONSISTENCY", source_validation["status"] if source_validation["status"] != "BLOCKED" else "FAIL", json.dumps(source_validation["date_evidence"], ensure_ascii=False, sort_keys=True)),
        validation_check("TEXT_EXTRACTION", "PASS", f"{sum(bool(clean_text(text)) for text in document.page_texts)}/{document.page_count} pages contain text"),
        validation_check("VISUAL_VALIDATION", "PASS" if schedule["visual_validation"] == "PASS" else "NOT_VERIFIED", schedule["visual_validation"]),
        validation_check("SCHEDULE_DATE_CONSISTENCY", schedule_check_status, schedule["date_conflict_status"]),
        validation_check("EVENT_EXTRACTION", "PASS", f"{extracted_item_count} items -> {len(events)} clusters"),
        validation_check("TICKER_MAPPING", "PASS", "deterministic alias rules applied"),
        validation_check("ROOT_THESIS_MAPPING", "PASS", "explicit ticker, strong phrase, grouped keyword, and event-domain rules applied"),
        validation_check("DUPLICATE_HANDLING", "PASS", f"{extracted_item_count - len(events)} duplicate or near-duplicate items clustered"),
        validation_check("DASHBOARD_GENERATION", "PASS", "HTML and Markdown generated"),
        validation_check("OUTPUT_CREATE_ONLY", "PASS", "exclusive-create writes and new run directory"),
        validation_check("NETWORK_ACCESS", "PASS", "NO; static network path absent"),
        validation_check("SAVE_LOGIN", "PASS", "NO"),
        validation_check("TASK_SCHEDULER_ACTIVATED", "PASS", "NO"),
        validation_check("BROKER_ACCESS", "PASS", "NO"),
        validation_check("PORTFOLIO_MUTATION", "PASS", "protected hash unchanged"),
        validation_check("POLICY_MUTATION", "PASS", "protected hash unchanged"),
        validation_check("ORDER_PATH", "PASS", "order authority false; static order path absent"),
        validation_check("REQUEST_ACCOUNTING", "NOT_VERIFIED", "exact request counters are not instrumented"),
    ]
    validation_report = {
        "schema_version": PIPELINE_VERSION,
        "run_id": run_id_value,
        "generated_at": utc_now(),
        "overall_status": pipeline_status,
        "checks": checks,
    }
    _validate_or_raise(validation_report, VALIDATION_SCHEMA, "VALIDATION_REPORT_SCHEMA_INVALID")
    create_only_json(run_directory / "validation-report.json", validation_report)

    finished_at = utc_now()
    artifact_hashes = {
        "normalized-events.json": file_hash(run_directory / "normalized-events.json"),
        "validation-report.json": file_hash(run_directory / "validation-report.json"),
        "dashboard.html": file_hash(run_directory / "dashboard.html"),
        "dashboard.md": file_hash(run_directory / "dashboard.md"),
    }
    git_branch = _git(["branch", "--show-current"])
    git_commit = _git(["rev-parse", "HEAD"])
    manifest = {
        "schema_version": PIPELINE_VERSION,
        "run_id": run_id_value,
        "pipeline_version": PIPELINE_VERSION,
        "run_mode": RUN_MODE,
        "pipeline_status": pipeline_status,
        "started_at": started_at,
        "finished_at": finished_at,
        "source_path": str(document.source_path),
        "source_sha256": document.source_sha256,
        "source_file_size": document.source_file_size,
        "source_page_count": document.page_count,
        "source_accessed_at": document.source_accessed_at,
        "report_title": source_validation["report_title"],
        "report_date": report_date,
        "source_validation_status": source_validation["status"],
        "extraction_status": "PASS",
        "schedule_status": schedule["status"],
        "schedule_auto_use": schedule["auto_use"],
        "visual_validation": schedule["visual_validation"],
        "schedule_observations": schedule["text_evidence"],
        "event_count": len(events),
        "material_event_count": sum(event["materiality"] == "HIGH" for event in events),
        "portfolio_context_status": context["status"],
        "portfolio_context_as_of": context["as_of"],
        "network_access": "NO",
        "save_login": "NO",
        "task_scheduler_activated": "NO",
        "broker_call": "NO",
        "portfolio_mutation": "NO",
        "policy_mutation": "NO",
        "request_accounting": "NOT_VERIFIED",
        "orders": "NONE",
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
        "git_branch": git_branch,
        "git_commit": git_commit,
        "code_provenance": {
            "git_branch": git_branch,
            "git_head": git_commit,
            "git_dirty": bool(_git(["status", "--porcelain"])),
        },
        "implementation_provenance": build_implementation_provenance(rules_path, locale_path),
        "dependency_provenance": build_dependency_provenance(),
        "artifact_hashes": artifact_hashes,
        "static_path_evidence": {
            "network_path_present": static_paths["network_path_present"],
            "broker_path_present": static_paths["broker_path_present"],
            "order_path_present": static_paths["order_path_present"],
        },
        "protected_input_hashes": protected_after,
        "artifact_paths": artifact_paths,
    }
    _validate_or_raise(manifest, MANIFEST_SCHEMA, "RUN_MANIFEST_SCHEMA_INVALID")
    create_only_json(run_directory / "run-manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SAVE Daily v0.1 in offline replay mode")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--expected-report-date")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    try:
        manifest = run_pipeline(
            source_path=args.source,
            expected_report_date=args.expected_report_date,
            output_root=args.output_root,
            run_id=args.run_id,
        )
    except PipelineError as exc:
        print(json.dumps({"status": "BLOCKED", "code": exc.code, "detail": exc.detail}, ensure_ascii=True), file=sys.stderr)
        return 2
    print(json.dumps({
        "status": manifest["pipeline_status"],
        "run_id": manifest["run_id"],
        "run_directory": str(Path(manifest["artifact_paths"]["run_manifest"]).parent),
        "event_count": manifest["event_count"],
        "material_event_count": manifest["material_event_count"],
        "schedule_status": manifest["schedule_status"],
        "order_authority": False,
    }, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
