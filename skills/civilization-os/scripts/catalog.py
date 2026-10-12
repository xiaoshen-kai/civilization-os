#!/usr/bin/env python3
"""Read-only lookup and integrity checks for the Civilization OS library."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
KINDS = {"theorem", "law", "theory", "empirical", "heuristic", "contested"}
DOMAINS = {"mathematics", "physics", "life", "behavior", "business", "strategy"}
RECORD_TYPES = {"deep_case", "evidence_event"}
RESULT_TYPES = {"failure", "near_miss", "reported_success", "reported_practice",
                "causal_study_success_with_limits", "causal_study_with_limits",
                "experimental_demonstration", "technical_application", "regulatory_action", "documented_event"}
CONFIDENCE = {"high", "medium", "low"}
SOURCE_TYPES = {"primary", "official_summary", "academic_secondary"}
EVIDENCE_TYPES = {"direct", "reported", "causal_study"}
MODEL_TEXT = ("id", "name", "domain", "kind", "core", "mechanism", "question",
              "limits", "misuse", "origin")
SOURCE_TEXT = ("id", "title", "url", "publisher", "source_type", "checked_on", "supports")
# Negative transfer conditions and evidence limitations do not create positive matches.
SEARCH_FIELDS = ("domain", "core", "mechanism", "question", "inputs", "use_when",
                 "formula", "context", "decision_context", "facts", "actions",
                 "observed_actions", "outcomes")
TOKEN = re.compile(r"[\s,，、;；]+")
PROTECTED = re.compile(r"(\x60[^\x60]*\x60|https?://[^\s)]+)")
STABLE_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*")


def read_rows(path: Path) -> list[dict]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, list) or any(not isinstance(x, dict) for x in value):
        raise ValueError(f"{path.name}: expected an array of objects")
    return value


def load_database(root: Path = ROOT) -> dict[str, list[dict]]:
    refs = root / "references"
    models = read_rows(refs / "models-01.json") + read_rows(refs / "models-02.json")
    case_paths = [refs / "cases.json", *sorted(refs.glob("cases-*.json"))]
    cases = [row for path in case_paths for row in read_rows(path)]
    source_paths = sorted(refs.glob("sources-*.json"))
    if not source_paths:
        raise ValueError("Missing sources-*.json")
    sources = [row for path in source_paths for row in read_rows(path)]
    research = [row for path in sorted(refs.glob("award-research-*.json")) for row in read_rows(path)]
    return {"models": models, "cases": cases, "sources": sources, "research": research}


def record_type(row: dict) -> str:
    return row.get("record_type", "deep_case")


def origin_group(row: dict) -> str:
    """A grouping key identifies information origin, not independent replication."""
    value = row.get("origin_group", row.get("publisher", ""))
    return value if isinstance(value, str) else ""


APPLICATIONS = {"direct", "conditional", "learning_only"}
RESEARCH_KINDS = {"theorem", "empirical", "theoretical", "official_synthesis"}


def check_research(rows: object, model_ids: set[str], occupied: set[str]) -> list[str]:
    """Check traceability structure; reading scope and scientific validity need review."""
    errors = []
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return ["research: expected an array of objects"]
    seen = set(occupied)
    source_ids = set()
    claim_ids = set()

    def text(obj: dict, key: str, label: str) -> None:
        if not isinstance(obj.get(key), str) or not obj[key].strip():
            errors.append(f"{label}: missing/non-text {key}")

    def strings(obj: dict, key: str, label: str, allow_empty=False) -> list[str]:
        value = obj.get(key)
        if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
            errors.append(f"{label}: {key} must be a string array")
            return []
        if not value and not allow_empty:
            errors.append(f"{label}: {key} cannot be empty")
        if len(set(value)) != len(value):
            errors.append(f"{label}: duplicate {key}")
        return value

    def date_value(value: object, label: str) -> None:
        try:
            if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError
            date.fromisoformat(value)
        except ValueError:
            errors.append(f"{label}: invalid checked_on date")

    def object_field(obj: dict, key: str, label: str) -> dict:
        value = obj.get(key)
        if not isinstance(value, dict):
            errors.append(f"{label}: {key} must be an object")
            return {}
        return value

    for row in rows:
        label = str(row.get("id", "research"))
        if not re.fullmatch(r"A\d{3,}", label) or label in seen:
            errors.append(f"{label}: invalid/duplicate research ID")
        seen.add(label)
        for key in ("title", "transfer_note"):
            text(row, key, label)
        for key in ("keywords", "use_when", "misuse"):
            strings(row, key, label)
        for mid in strings(row, "model_ids", label, allow_empty=True):
            if mid not in model_ids:
                errors.append(f"{label}: unknown model {mid}")
        award = object_field(row, "award", label)
        for key in ("name", "relation"):
            text(award, key, label + ".award")
        if type(award.get("year")) is not int or not 1901 <= award["year"] <= 9999:
            errors.append(f"{label}: invalid award year")
        strings(award, "laureates", label + ".award")
        research = object_field(row, "research", label)
        for key in ("problem", "principle"):
            text(research, key, label + ".research")
        for key in ("assumptions", "limitations"):
            strings(research, key, label + ".research")
        kind = research.get("evidence_type")
        if not isinstance(kind, str) or kind not in RESEARCH_KINDS:
            errors.append(f"{label}: invalid research evidence_type")
        if "formal_statement" not in research or (research["formal_statement"] is not None and
                                                   not isinstance(research["formal_statement"], str)):
            errors.append(f"{label}: formal_statement must be text or null")
        app = object_field(row, "decision_application", label)
        status = app.get("status")
        if not isinstance(status, str) or status not in APPLICATIONS:
            errors.append(f"{label}: invalid application status")
        text(app, "mechanism", label + ".application")
        strings(app, "steps", label + ".application")
        strings(app, "stop_conditions", label + ".application")
        example = object_field(app, "example", label + ".application")
        for key in ("scenario", "application", "boundary"):
            text(example, key, label + ".example")
        verification = object_field(row, "verification", label)
        if verification.get("status") != "checked":
            errors.append(f"{label}: unchecked research must stay outside library")
        date_value(verification.get("checked_on"), label)
        text(verification, "limitations", label + ".verification")
        sources = row.get("sources")
        if not isinstance(sources, list) or not sources or any(not isinstance(x, dict) for x in sources):
            errors.append(f"{label}: sources must be a nonempty object array")
            sources = []
        local_sources = set()
        types = set()
        for source in sources:
            sid = source.get("id")
            if not isinstance(sid, str) or not re.fullmatch(re.escape("AS-" + label) + r"-\d+", sid):
                errors.append(f"{label}: invalid local source ID")
                continue
            if sid in source_ids or sid in seen:
                errors.append(f"{label}: duplicate/global collision source ID {sid}")
            source_ids.add(sid)
            local_sources.add(sid)
            for key in ("title", "publisher", "locator", "supports", "reading_scope"):
                text(source, key, sid)
            try:
                raw_url = source.get("url") if isinstance(source.get("url"), str) else ""
                url = urlparse(raw_url)
                valid_url = (url.scheme in {"http", "https"} and bool(url.hostname)
                             and not any(c.isspace() for c in raw_url)
                             and url.username is None and url.password is None)
                # Accessing port also validates bracket/port syntax.
                url.port
            except ValueError:
                valid_url = False
            if not valid_url:
                errors.append(f"{sid}: invalid absolute URL")
            date_value(source.get("checked_on"), sid)
            st = source.get("source_type")
            if not isinstance(st, str) or st not in {"primary", "official_summary"}:
                errors.append(f"{sid}: invalid source_type")
            else:
                types.add(st)
        if not {"primary", "official_summary"}.issubset(types):
            errors.append(f"{label}: award summary and primary research reading required")
        claims = row.get("claims")
        if not isinstance(claims, list) or not claims or any(not isinstance(x, dict) for x in claims):
            errors.append(f"{label}: claims must be a nonempty object array")
            claims = []
        used_sources = set()
        for claim in claims:
            cid = claim.get("id")
            if not isinstance(cid, str) or not re.fullmatch(re.escape(label) + r"-K\d+", cid):
                errors.append(f"{label}: invalid claim ID")
            elif cid in claim_ids or cid in seen or cid in source_ids:
                errors.append(f"{label}: duplicate/global collision claim ID {cid}")
            else:
                claim_ids.add(cid)
            text(claim, "text", label + ".claim")
            for sid in strings(claim, "source_ids", label + ".claim"):
                if sid not in local_sources:
                    errors.append(f"{label}: claim source {sid} is not card-local")
                used_sources.add(sid)
        if local_sources - used_sources:
            errors.append(f"{label}: unused research source")
    return errors


def search_research(rows: list[dict], query: str, limit: int,
                    application: str | None = None, model: str | None = None) -> list[dict]:
    terms = [x.casefold() for x in TOKEN.split(query.strip()) if x]
    if not terms:
        raise ValueError("Search requires at least one keyword")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("--limit must be between 1 and 100")
    matches = []
    for row in rows:
        app = row["decision_application"]
        if application and app["status"] != application:
            continue
        if model and model not in row["model_ids"]:
            continue
        title = row["title"].casefold()
        words = " ".join(row["keywords"]).casefold()
        body = " ".join([row["research"]["problem"], row["research"]["principle"],
                         *row["use_when"], app["mechanism"], *app["steps"],
                         row["award"]["name"], *row["award"]["laureates"]]).casefold()
        score = sum(10 if x in title else 4 if x in words else 1 if x in body else 0 for x in terms)
        if score:
            matches.append({"id": row["id"], "title": row["title"], "match_score": score,
                            "award": row["award"], "model_ids": row["model_ids"],
                            "application_status": app["status"],
                            "checked_on": row["verification"]["checked_on"],
                            "limitation": row["verification"]["limitations"]})
    return sorted(matches, key=lambda x: (-x["match_score"], x["id"]))[:limit]


def check_database(db: dict[str, list[dict]], root: Path | None = None) -> list[str]:
    errors: list[str] = []

    def error(message: str) -> None:
        errors.append(message)

    def text_fields(row: dict, fields: tuple[str, ...], label: str) -> None:
        for field in fields:
            if not isinstance(row.get(field), str) or not row[field].strip():
                error(f"{label}: missing/non-text {field}")

    def enum_field(value: object, choices: set[str], label: str) -> None:
        if not isinstance(value, str) or value not in choices:
            error(f"{label}: invalid enum value")

    def strings(row: dict, field: str, label: str, empty: bool = False) -> list[str]:
        values = row.get(field)
        if not isinstance(values, list) or any(
            not isinstance(v, str) or not v.strip() for v in values
        ):
            error(f"{label}: {field} must be a string array")
            return []
        if not empty and not values:
            error(f"{label}: {field} cannot be empty")
        if len(set(values)) != len(values):
            error(f"{label}: duplicate {field}")
        return values

    def prose(row: dict, field: str, label: str) -> None:
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            return
        strings(row, field, label)

    def unique_ids(key: str) -> set[str]:
        ids = [x.get("id") for x in db[key]]
        usable = [v for v in ids if isinstance(v, str) and v.strip()]
        if len(set(usable)) != len(usable):
            error(f"{key}: duplicate IDs")
        if len(usable) != len(ids):
            error(f"{key}: missing IDs")
        return set(usable)

    for key in ("models", "cases", "sources"):
        if not isinstance(db.get(key), list) or any(
            not isinstance(row, dict) for row in db[key]
        ):
            return [f"{key}: expected an array of objects"]
    model_ids = unique_ids("models")
    case_ids = unique_ids("cases")
    source_ids = unique_ids("sources")
    for left, right, a, b in (("models", "cases", model_ids, case_ids),
                             ("models", "sources", model_ids, source_ids),
                             ("cases", "sources", case_ids, source_ids)):
        for collision in sorted(a & b):
            error(f"global ID collision: {collision} appears in {left} and {right}")
    expected_ids = {f"P{i:03d}" for i in range(1, 101)}
    if len(db["models"]) != 100 or model_ids != expected_ids:
        error("models: expected exactly P001-P100, with 100 records")
    names = [x.get("name") for x in db["models"] if isinstance(x.get("name"), str)]
    if len(set(names)) != len(names):
        error("models: duplicate names")
    if not db["cases"]:
        error("cases: at least one checked case is required")

    def date_field(value: object, label: str) -> None:
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            error(f"{label}: expected YYYY-MM-DD")
            return
        try:
            date.fromisoformat(value)
        except ValueError:
            error(f"{label}: invalid calendar date")

    def references(values: list[str], known: set[str], label: str) -> None:
        for v in values:
            if v not in known:
                error(f"{label}: unknown reference {v}")

    for row in db["sources"]:
        label = str(row.get("id", "source"))
        text_fields(row, SOURCE_TEXT, label)
        try:
            parsed = urlparse(row.get("url") if isinstance(row.get("url"), str) else "")
            valid_url = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        except ValueError:
            valid_url = False
        if not valid_url:
            error(f"{label}: URL must be absolute HTTP(S)")
        enum_field(row.get("source_type"), SOURCE_TYPES, label + ".source_type")
        if not isinstance(row.get("limitations"), str):
            error(f"{label}: missing/non-text limitations")
        if "origin_group" in row:
            text_fields(row, ("origin_group",), label)
        date_field(row.get("checked_on"), label + ".checked_on")

    for row in db["models"]:
        label = str(row.get("id", "model"))
        text_fields(row, MODEL_TEXT, label)
        enum_field(row.get("domain"), DOMAINS, label + ".domain")
        enum_field(row.get("kind"), KINDS, label + ".kind")
        for field in ("use_when", "inputs", "keywords"):
            strings(row, field, label)
        formula = row.get("formula")
        if "formula" not in row or (formula is not None and not isinstance(formula, str)):
            error(f"{label}: formula must be text or null")
        references(strings(row, "source_ids", label), source_ids, label)
        references(strings(row, "case_ids", label, empty=True), case_ids, label)

    source_map = {row["id"]: row for row in db["sources"] if isinstance(row.get("id"), str)}
    seen_events: dict[str, str] = {}
    seen_claim_ids: dict[str, str] = {}
    for row in db["cases"]:
        label = str(row.get("id", "case"))
        text_fields(row, ("id", "title", "event_time", "domain"), label)
        if not re.fullmatch(r"C\d{3,}", str(row.get("id", ""))):
            error(f"{label}: invalid case ID")
        tier = record_type(row)
        enum_field(tier, RECORD_TYPES, label + ".record_type")
        enum_field(row.get("result_type"), RESULT_TYPES, label + ".result_type")
        if tier == "evidence_event" and row.get("result_type") != "documented_event":
            error(f"{label}: evidence_event must use documented_event result_type")
        if tier == "deep_case":
            if row.get("result_type") == "documented_event":
                error(f"{label}: deep_case cannot use documented_event result_type")
            text_fields(row, ("decision_context", "model_mapping_note"), label)
            actions = row.get("observed_actions")
            action_status = row.get("observed_actions_status")
            if "observed_actions_status" in row:
                enum_field(action_status, {"reported", "not_reported"},
                           label + ".observed_actions_status")
            if action_status == "not_reported":
                if actions != []:
                    error(f"{label}: not_reported observed_actions must be an empty array")
            else:
                prose(row, "observed_actions", label)
            for field in ("outcomes", "transfer_conditions", "non_transfer_conditions"):
                prose(row, field, label)
        else:
            for field in ("decision_context", "model_mapping_note"):
                if field in row:
                    text_fields(row, (field,), label)
            for field in ("observed_actions", "outcomes", "transfer_conditions",
                          "non_transfer_conditions"):
                if field in row:
                    prose(row, field, label)
        prose(row, "facts", label)
        if "keywords" in row:
            strings(row, "keywords", label, empty=True)

        event_key = row.get("event_key")
        if tier == "evidence_event" or "event_key" in row:
            text_fields(row, ("event_key",), label)
            if isinstance(event_key, str) and event_key.strip():
                if event_key in seen_events:
                    error(f"{label}: duplicate event_key also used by {seen_events[event_key]}")
                else:
                    seen_events[event_key] = label
        case_sources = strings(row, "source_ids", label)
        references(case_sources, source_ids, label)
        references(strings(row, "model_ids", label), model_ids, label)

        if tier == "evidence_event" or "provenance" in row:
            provenance = row.get("provenance")
            if not isinstance(provenance, dict):
                error(f"{label}: missing provenance object")
            else:
                text_fields(provenance, ("source_id", "row_key", "locator"), label + ".provenance")
                provenance_id = provenance.get("source_id")
                if isinstance(provenance_id, str):
                    references([provenance_id], source_ids, label + ".provenance")
                    if provenance_id not in case_sources:
                        error(f"{label}: provenance source is absent from case.source_ids")

        verification = row.get("verification")
        if not isinstance(verification, dict):
            error(f"{label}: missing verification object")
        else:
            if verification.get("status") != "checked":
                error(f"{label}: unchecked cases must stay outside the checked library")
            date_field(verification.get("checked_on"), label + ".verification.checked_on")
            for axis in ("fact_confidence", "causal_confidence"):
                enum_field(verification.get(axis), CONFIDENCE, label + "." + axis)
            if tier == "evidence_event" and verification.get("causal_confidence") != "low":
                error(f"{label}: evidence_event causal_confidence must be low")
            text_fields(verification, ("limitations",), label + ".verification")
            groups = verification.get("independent_source_groups")
            if type(groups) is not int or groups < 1:
                error(f"{label}: independent_source_groups must be a positive integer")
            else:
                actual_groups = {origin_group(source_map[sid]) for sid in case_sources
                                 if sid in source_map}
                if groups != len(actual_groups):
                    error(f"{label}: independent_source_groups {groups} differs from "
                          f"actual origin groups {len(actual_groups)}")

        claims = row.get("claims")
        if not isinstance(claims, list) or not claims:
            error(f"{label}: missing claims")
            continue
        claim_ids: set[str] = set()
        for n, claim in enumerate(claims, 1):
            claim_label = f"{label}.claim[{n}]"
            if not isinstance(claim, dict):
                error(f"{claim_label}: expected an object")
                continue
            text_fields(claim, ("claim", "locator", "causal_limit"), claim_label)
            if "claim_id" in claim:
                cid = claim.get("claim_id")
                if not isinstance(cid, str) or not STABLE_KEY.fullmatch(cid):
                    error(f"{claim_label}: claim_id must be a stable non-empty identifier")
                elif cid in claim_ids:
                    error(f"{claim_label}: duplicate claim_id {cid}")
                else:
                    claim_ids.add(cid)
                    if cid in seen_claim_ids:
                        error(f"global claim_id collision: {cid} in {label} and {seen_claim_ids[cid]}")
                    else:
                        seen_claim_ids[cid] = label
            values = strings(claim, "source_ids", claim_label)
            references(values, source_ids, claim_label)
            if not set(values).issubset(set(case_sources)):
                error(f"{claim_label}: source is absent from case.source_ids")
            enum_field(claim.get("evidence_strength"), EVIDENCE_TYPES,
                       claim_label + ".evidence_strength")

    model_map = {x["id"]: x for x in db["models"] if isinstance(x.get("id"), str)}
    case_map = {x["id"]: x for x in db["cases"] if isinstance(x.get("id"), str)}
    for model_id, model in model_map.items():
        values = model.get("case_ids")
        if isinstance(values, list):
            for case_id in values:
                if isinstance(case_id, str) and case_id in case_map:
                    reverse = case_map[case_id].get("model_ids")
                    if isinstance(reverse, list) and model_id not in reverse:
                        error(f"{model_id}: case {case_id} lacks reverse model link")
    for case_id, case in case_map.items():
        values = case.get("model_ids")
        if isinstance(values, list):
            for model_id in values:
                if isinstance(model_id, str) and model_id in model_map:
                    reverse = model_map[model_id].get("case_ids")
                    if isinstance(reverse, list) and case_id not in reverse:
                        error(f"{case_id}: model {model_id} lacks reverse case link")

    occupied = model_ids | case_ids | source_ids | set(seen_claim_ids)
    errors.extend(check_research(db.get("research", []), model_ids, occupied))

    if root is not None:
        for path in sorted(root.rglob("*.md")):
            body = path.read_text(encoding="utf-8-sig")
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
                target = target.split("#", 1)[0]
                if not target or "://" in target or target.startswith("#"):
                    continue
                if not (path.parent / target).is_file():
                    error(f"{path.name}: broken local link {target}")
        manifest_path = root / "references" / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
                errors.extend(check_manifest(manifest, db))
            except (OSError, ValueError):
                error("manifest: cannot read a JSON object")
    return errors


def check_manifest(manifest: object, db: dict[str, list[dict]]) -> list[str]:
    if not isinstance(manifest, dict):
        return ["manifest: expected an object"]
    errors = []
    if manifest.get("schema_version") != "2.0":
        errors.append("manifest: schema_version must be 2.0")
    version = manifest.get("library_version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append("manifest: library_version must be MAJOR.MINOR.PATCH")
    checked_on = manifest.get("checked_on")
    try:
        if not isinstance(checked_on, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", checked_on):
            raise ValueError
        date.fromisoformat(checked_on)
    except ValueError:
        errors.append("manifest: checked_on must be a valid YYYY-MM-DD date")
    counts = manifest.get("counts")
    actual = database_counts(db)
    if not isinstance(counts, dict):
        return errors + ["manifest: missing counts object"]
    for key, value in actual.items():
        if type(counts.get(key)) is not int or counts[key] != value:
            errors.append(f"manifest: counts.{key} must equal {value}")
    return errors


def database_counts(db: dict[str, list[dict]]) -> dict[str, int]:
    counts = {"models": len(db["models"]), "cases": len(db["cases"]),
              "sources": len(db["sources"]),
              "deep_cases": sum(record_type(row) == "deep_case" for row in db["cases"]),
              "evidence_events": sum(record_type(row) == "evidence_event" for row in db["cases"]),
              "claims": sum(len(row["claims"]) for row in db["cases"]
                            if isinstance(row.get("claims"), list))}
    rows = db.get("research", [])
    # Legacy schema 2.0 libraries need no research counters. Invalid research data
    # remains reportable by check_research rather than crashing manifest checks.
    if isinstance(rows, list) and rows:
        counts.update({"research_cards": len(rows),
                       "research_sources": sum(len(row["sources"]) for row in rows
                                               if isinstance(row, dict) and isinstance(row.get("sources"), list)),
                       "research_claims": sum(len(row["claims"]) for row in rows
                                              if isinstance(row, dict) and isinstance(row.get("claims"), list))})
    return counts


def positive_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(positive_text(item) for item in value)
    return ""


def search_rows(rows: list[dict], query: str, limit: int,
                domain: str | None = None, kind: str | None = None,
                case_record_type: str | None = None, model: str | None = None,
                case_domain: str | None = None) -> list[dict]:
    terms = [v.casefold() for v in TOKEN.split(query.strip()) if v]
    if not terms:
        raise ValueError("Search requires at least one keyword")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("--limit must be between 1 and 100")
    matches = []
    for row in rows:
        if domain and row.get("domain") != domain:
            continue
        if kind and row.get("kind") != kind:
            continue
        if case_record_type and record_type(row) != case_record_type:
            continue
        if model and model not in row.get("model_ids", []):
            continue
        if case_domain and row.get("domain") != case_domain:
            continue
        title = positive_text(row.get("name", row.get("title", ""))).casefold()
        words = positive_text(row.get("keywords", [])).casefold()
        body = " ".join(positive_text(row.get(field)) for field in SEARCH_FIELDS)
        claims = row.get("claims")
        if isinstance(claims, list):
            body += " " + " ".join(positive_text(x.get("claim"))
                                    for x in claims if isinstance(x, dict))
        body = body.casefold()
        score = sum((10 if term in title else 4 if term in words else 1 if term in body else 0)
                    for term in terms)
        if score:
            summary = {"id": row["id"], "name": row.get("name", row.get("title")),
                       "domain": row.get("domain"), "kind": row.get("kind"),
                       "match_score": score, "source_ids": row.get("source_ids", [])}
            if isinstance(claims, list):
                verification = row.get("verification", {})
                if not isinstance(verification, dict):
                    verification = {}
                summary.update({"record_type": record_type(row),
                                "result_type": row.get("result_type"),
                                "model_ids": row.get("model_ids", []),
                                "fact_confidence": verification.get("fact_confidence"),
                                "causal_confidence": verification.get("causal_confidence"),
                                "checked_on": verification.get("checked_on"),
                                "claim_count": len(claims),
                                "limitation": verification.get("limitations")})
            matches.append(summary)
    return sorted(matches, key=lambda x: (-x["match_score"], x["id"]))[:limit]


def database_stats(db: dict[str, list[dict]]) -> dict:
    mapped = Counter(mid for row in db["cases"] for mid in row.get("model_ids", [])
                     if isinstance(mid, str))
    groups = Counter(origin_group(row) for row in db["sources"])
    source_map = {row["id"]: row for row in db["sources"]}
    case_groups = {origin_group(source_map[sid]) for row in db["cases"]
                   for sid in row.get("source_ids", []) if sid in source_map}
    return {**database_counts(db),
            "research_applications": dict(sorted(Counter(x["decision_application"]["status"]
                                                         for x in db.get("research", [])).items())),
            "record_types": dict(sorted(Counter(record_type(row) for row in db["cases"]).items())),
            "model_kinds": dict(sorted(Counter(x["kind"] for x in db["models"]).items())),
            "case_domains": dict(sorted(Counter(x["domain"] for x in db["cases"]).items())),
            "model_coverage": {"mapped_models": len(mapped), "case_model_links": sum(mapped.values()),
                               "unmapped_model_ids": sorted(x["id"] for x in db["models"]
                                                            if x["id"] not in mapped)},
            "source_origin_groups": len(groups), "case_source_origin_groups": len(case_groups),
            "largest_source_groups": [{"origin_group": key, "source_records": count}
                                      for key, count in groups.most_common(10)],
            "source_checked_dates": sorted({x["checked_on"] for x in db["sources"]}),
            "note": "来源群表示信息出处分组，不表示独立实验。统计与结构校验不等于事实、因果或当前有效性验证。"}


def render_text(value: str) -> str:
    """Normalize prose while preserving URLs, code spans and stored data."""
    parts = PROTECTED.split(value)
    for i in range(0, len(parts), 2):
        text = parts[i].replace("\u2014", "--").replace("\u2013", "--")
        text = re.sub(r"([\u3400-\u9fff])([A-Za-z0-9])", r"\1 \2", text)
        text = re.sub(r"([A-Za-z0-9])([\u3400-\u9fff])", r"\1 \2", text)
        for plain, full in [(",", "，"), (":", "："), (";", "；"), ("!", "！"), ("?", "？")]:
            text = re.sub(r"(?<=[\u3400-\u9fff])" + re.escape(plain), full, text)
            text = re.sub(re.escape(plain) + r"(?=[\u3400-\u9fff])", full, text)
        parts[i] = text
    return "".join(parts)


def markdown_record(row: dict) -> str:
    lines = [f"# {row.get('id', '')} {render_text(row.get('name', row.get('title', '')))}", ""]
    for key, value in row.items():
        if key in {"id", "name", "title"}:
            continue
        lines.extend([f"## {key}", ""])
        if isinstance(value, str):
            lines.extend([value if key in {"formula", "url"} else render_text(value), ""])
        elif isinstance(value, list) and all(isinstance(x, str) for x in value):
            lines.extend(["- " + render_text(x) for x in value])
            lines.append("")
        else:
            lines.extend(["\x60\x60\x60json", json.dumps(value, ensure_ascii=False, indent=2),
                          "\x60\x60\x60", ""])
    return "\n".join(lines)


def output(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="Search short keywords, without network or writes")
    search.add_argument("query")
    selection = search.add_mutually_exclusive_group()
    selection.add_argument("--cases", action="store_true")
    selection.add_argument("--research", action="store_true", help="Search award research cards")
    search.add_argument("--application", choices=sorted(APPLICATIONS))
    search.add_argument("--limit", type=int, default=8)
    search.add_argument("--domain", choices=sorted(DOMAINS))
    search.add_argument("--kind", choices=sorted(KINDS))
    search.add_argument("--record-type", choices=sorted(RECORD_TYPES))
    search.add_argument("--model", help="Filter cases or research linked to a model, e.g. P058")
    search.add_argument("--case-domain", help="Filter by the exact case domain string")
    show = commands.add_parser("show", help="Show a model, case, research card or source by ID")
    show.add_argument("id")
    show.add_argument("--format", choices=["json", "md"], default="json")
    commands.add_parser("stats")
    commands.add_parser("validate", help="Check structure and links; does not verify factual truth")
    args = parser.parse_args(argv)
    try:
        db = load_database()
        if args.command == "search":
            if args.application and not args.research:
                raise ValueError("--application requires --research")
            if args.research:
                if args.kind or args.domain or args.record_type or args.case_domain:
                    raise ValueError("--research cannot combine with model/case-only filters")
                model = args.model.upper() if args.model else None
                if model and model not in {row["id"] for row in db["models"]}:
                    raise ValueError(f"Unknown model ID: {args.model}")
                output({"note": "获奖研究卡的生活应用是本次分析；learning_only 用于知识学习，不能直接给人生建议。",
                        "results": search_research(db["research"], args.query, args.limit,
                                                   args.application, model)})
                return 0
            if args.cases and (args.kind or args.domain):
                raise ValueError("--cases cannot combine with model --kind or --domain")
            if not args.cases and (args.record_type or args.model or args.case_domain):
                raise ValueError("--record-type, --model and --case-domain require --cases")
            model = args.model.upper() if args.model else None
            if model and model not in {row["id"] for row in db["models"]}:
                raise ValueError(f"Unknown model ID: {args.model}")
            rows = search_rows(db["cases" if args.cases else "models"], args.query,
                               args.limit, args.domain, args.kind, args.record_type,
                               model, args.case_domain)
            if not args.cases:
                for match in rows:
                    match["research_card_ids"] = [card["id"] for card in db["research"]
                                                   if match["id"] in card["model_ids"]]
            output({"note": "匹配分数只用于检索排序，不是决策权重；证据事件不能等同于完整决策或因果复盘。",
                    "results": rows})
        elif args.command == "show":
            records = [x for group in db.values() for x in group]
            records.extend(source for row in db["research"] for source in row["sources"])
            matches = [x for x in records if x.get("id") == args.id.upper()]
            if not matches:
                raise ValueError(f"Unknown ID: {args.id}")
            if len(matches) != 1:
                raise ValueError(f"Ambiguous ID: {args.id}")
            if args.format == "md":
                print(markdown_record(matches[0]))
            else:
                output(matches[0])
        elif args.command == "stats":
            output(database_stats(db))
        else:
            errors = check_database(db, ROOT)
            output({"valid": not errors, "error_count": len(errors), "errors": errors[:50],
                    "note": "仅检查结构、引用、来源分组、计数和本地链接；不证明内容真实。"})
            return 1 if errors else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"catalog error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

