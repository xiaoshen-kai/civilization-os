#!/usr/bin/env python3
"""Check cached event records against selected snapshots; no network or writes."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from datetime import date, datetime
from fractions import Fraction
from pathlib import Path
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
RENDERER_PATH = Path(__file__).with_name("event_records.py")
EXPECTED = {
    "fdic": {"start": 101, "count": 300, "source": "R-FDIC", "domain": "finance"},
    "cfpb": {"start": 401, "count": 200, "source": "R-CFPB", "domain": "regulatory_action"},
    "clinical": {"start": 601, "count": 250, "source": "R-CTG", "domain": "clinical_research"},
    "nobel": {"start": 851, "count": 150, "source": "R-NOBEL", "domain": "scientific_awards"},
}
CUTOFF = date(2025, 12, 31)
RELATED_CFPB_URLS = {
    "https://www.consumerfinance.gov/enforcement/actions/goldman-sachs-bank-usa"
}
NOTE = ("仅验证 900 条缓存事件与选定字段快照、来源映射和生成规则一致；"
        "不证明快照来自官方，不构成独立因果识别、当前法律状态或医疗结论。")


class EventError(ValueError):
    pass


def load_renderer():
    try:
        spec = importlib.util.spec_from_file_location("_civilization_event_renderer", RENDERER_PATH)
        if spec is None or spec.loader is None:
            raise EventError("event_records.py: no renderer loader")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not isinstance(getattr(module, "DATASETS", None), dict) or not callable(
            getattr(module, "render_dataset", None)
        ):
            raise EventError("event_records.py: invalid renderer interface")
        return module
    except (OSError, ValueError, TypeError, ImportError, SyntaxError) as exc:
        detail = str(exc) if isinstance(exc, EventError) else type(exc).__name__
        raise EventError(f"event_records.py: cannot load renderer ({detail})") from exc


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise EventError(f"{field} must be nonempty text")
    return value


def iso_date(value, field, cutoff=False):
    text(value, field)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise EventError(f"{field} must be YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise EventError(f"{field} is not a calendar date") from exc
    if cutoff and parsed > CUTOFF:
        raise EventError(f"{field} exceeds the 2025 cutoff")
    return parsed


def integer(value, field, minimum=0):
    if type(value) is not int or value < minimum:
        raise EventError(f"{field} must be an integer >= {minimum}")
    return value


def object_value(value, field):
    if not isinstance(value, dict):
        raise EventError(f"{field} must be an object")
    return value


def list_value(value, field, nonempty=True):
    if not isinstance(value, list) or (nonempty and not value):
        raise EventError(f"{field} must be a nonempty array" if nonempty else f"{field} must be an array")
    return value


def numeric_or_null(value, field):
    if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
        raise EventError(f"{field} must be a finite number or null")


def value_cell(value, field):
    if isinstance(value, str):
        text(value, field)
    elif type(value) in (int, float) and math.isfinite(value):
        return
    else:
        raise EventError(f"{field} must preserve a nonempty text/numeric cell")


def linked_path(path):
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def load_json(path, label, errors):
    try:
        if linked_path(path):
            raise EventError("symbolic links/junctions are not allowed")
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError) as exc:
        detail = str(exc) if isinstance(exc, EventError) else type(exc).__name__
        errors.append(f"{label}: cannot read JSON ({detail})")
        return None


def canonical_url(value):
    text(value, "URL")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise EventError("URL must be absolute HTTPS without credentials")
    return f"https://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"


def canonical_event_key(value):
    value = text(value, "event_key")
    dataset, separator, key = value.partition(":")
    if not separator or not key:
        raise EventError("event_key must contain dataset and row identity")
    if dataset == "cfpb":
        key = canonical_url(key)
    return dataset + ":" + key


def deep_episode_keys(refs, errors):
    episode_keys = set()
    business_urls = set()
    event_names = {f"cases-events-{dataset}.json" for dataset in EXPECTED}
    for path in sorted(refs.glob("cases*.json")):
        if path.name in event_names:
            continue
        rows = load_json(path, path.name, errors)
        if not isinstance(rows, list):
            errors.append(f"{path.name}: expected a case array")
            continue
        for index, row in enumerate(rows):
            label = f"{path.name}[{index}]"
            if not isinstance(row, dict):
                errors.append(f"{label}: expected a case object")
                continue
            if row.get("record_type", "deep_case") != "deep_case":
                errors.append(f"{label}: event records must stay in the four fixed event shards")
                continue
            key = row.get("event_key")
            if key is not None:
                try:
                    normalized = canonical_event_key(key)
                    if normalized in episode_keys:
                        errors.append(f"{label}: duplicate deep episode key")
                    episode_keys.add(normalized)
                    if path.name == "cases-business-deep.json":
                        if not normalized.startswith("cfpb:"):
                            raise EventError("business exclusion record must have a CFPB episode key")
                        business_urls.add(normalized[len("cfpb:"):])
                except (EventError, ValueError) as exc:
                    errors.append(f"{label}: {exc}")
    if len(business_urls) != 30:
        errors.append("cases-business-deep.json: expected 30 distinct CFPB exclusion URLs")
    return episode_keys, business_urls


def validate_fdic(record, seen_names, seen_certs):
    fields = record["fields"]
    for field in ("ID", "NAME", "CITY", "PSTALP", "FAILDATE"):
        text(fields.get(field), field)
    if fields.get("RESTYPE") != "FAILURE":
        raise EventError("RESTYPE must remain FAILURE")
    if record["record_key"] != fields["ID"]:
        raise EventError("record_key must equal the original FDIC ID")
    try:
        failed = datetime.strptime(fields["FAILDATE"], "%m/%d/%Y").date()
    except ValueError as exc:
        raise EventError("FAILDATE must preserve a parseable MM/DD/YYYY source date") from exc
    year = fields.get("FAILYR")
    if type(year) not in (str, int) or not re.fullmatch(r"\d{4}", str(year)):
        raise EventError("FAILYR must be a four-digit year")
    if int(year) != failed.year or failed > CUTOFF:
        raise EventError("FAILYR/date must agree and not exceed 2025")
    for field in ("QBFASSET", "QBFDEP"):
        if field not in fields:
            raise EventError(f"{field} must be retained, including null")
        numeric_or_null(fields[field], field)
    name = " ".join(re.sub(r"[^\w]+", " ", fields["NAME"].casefold()).split())
    if not name:
        raise EventError("NAME must retain a nonempty canonical bank identity")
    episode = (name, failed)
    if episode in seen_names:
        raise EventError("duplicate canonical NAME + FAILDATE episode under another ID")
    seen_names.add(episode)
    cert = fields.get("CERT")
    if cert is not None:
        if type(cert) not in (str, int) or not str(cert).isdigit():
            raise EventError("CERT must be numeric or null")
        episode_cert = (str(int(cert)), failed)
        if episode_cert in seen_certs:
            raise EventError("duplicate CERT + FAILDATE episode under another ID")
        seen_certs.add(episode_cert)
    if urlsplit(record["record_url"]).netloc != "api.fdic.gov":
        raise EventError("record_url must remain the FDIC API URL")


def validate_cfpb(record, seen_urls, excluded):
    fields = record["fields"]
    text(fields.get("title"), "title")
    iso_date(fields.get("date_filed"), "date_filed", cutoff=True)
    integer(fields.get("index_page"), "index_page", minimum=1)
    url = canonical_url(record["record_url"])
    if not url.startswith("https://www.consumerfinance.gov/enforcement/actions/"):
        raise EventError("record_url must remain a CFPB enforcement-action URL")
    if canonical_url(fields.get("url")) != url or record["record_key"] != url:
        raise EventError("CFPB fields.url, record_url and canonical record_key must agree")
    if url in seen_urls:
        raise EventError("duplicate canonical CFPB directory URL")
    seen_urls.add(url)
    if url in excluded or url in RELATED_CFPB_URLS:
        raise EventError("CFPB event duplicates a deep or related Goldman episode")


def validate_clinical(record):
    fields = record["fields"]
    nct = text(fields.get("nct_id"), "nct_id")
    if not re.fullmatch(r"NCT\d{8}", nct) or record["record_key"] != nct:
        raise EventError("record_key must preserve the NCT study ID")
    if record["record_url"] != "https://clinicaltrials.gov/study/" + nct:
        raise EventError("record_url must match the ClinicalTrials.gov study ID")
    if fields.get("allocation") != "RANDOMIZED" or fields.get("overall_status") != "COMPLETED":
        raise EventError("clinical sample must remain RANDOMIZED and COMPLETED")
    text(fields.get("brief_title"), "brief_title")
    submitted = iso_date(fields.get("results_first_submit_date"), "results_first_submit_date", cutoff=True)
    posted = object_value(fields.get("results_first_post_date_struct"), "results_first_post_date_struct")
    public = iso_date(posted.get("date"), "results_first_post_date_struct.date", cutoff=True)
    if posted.get("type") not in ("ACTUAL", "ESTIMATED"):
        raise EventError("results date must preserve ACTUAL/ESTIMATED")
    if public < submitted:
        raise EventError("results public date must not precede submission")
    enrollment = object_value(fields.get("enrollment_info"), "enrollment_info")
    integer(enrollment.get("count"), "enrollment_info.count")
    if enrollment.get("type") not in ("ACTUAL", "ESTIMATED"):
        raise EventError("enrollment must preserve ACTUAL/ESTIMATED")
    integer(fields.get("primary_index"), "primary_index")
    if fields.get("primary_type") != "PRIMARY":
        raise EventError("primary_type must remain PRIMARY")
    for field in ("primary_title", "time_frame", "param_type", "unit_of_measure", "measurement_scope"):
        text(fields.get(field), field)
    for field in ("dispersion_type", "type_units_analyzed", "denom_units_selected"):
        if field in fields and fields[field] is not None:
            text(fields[field], field + " (text or null)")
    for value in list_value(fields.get("conditions"), "conditions", nonempty=False):
        text(value, "conditions[]")
    groups = list_value(fields.get("groups"), "groups")
    group_ids = set()
    for group in groups:
        group = object_value(group, "groups[]")
        group_id = text(group.get("id"), "groups[].id")
        text(group.get("title"), "groups[].title")
        if group_id in group_ids:
            raise EventError("duplicate clinical group ID")
        group_ids.add(group_id)
    measurements = list_value(fields.get("measurements"), "measurements")
    if len(measurements) > 4:
        raise EventError("selected clinical snapshot must preserve at most four measurement cells")
    for measurement in measurements:
        measurement = object_value(measurement, "measurements[]")
        if measurement.get("groupId") not in group_ids:
            raise EventError("measurement groupId is absent from original groups")
        value_cell(measurement.get("value"), "measurements[].value")
        for field in ("class_index", "category_index", "measurement_index"):
            integer(measurement.get(field), "measurements[]." + field)
    covered = set()
    for denominator in list_value(fields.get("denoms"), "denoms"):
        denominator = object_value(denominator, "denoms[]")
        text(denominator.get("units"), "denoms[].units")
        for count in list_value(denominator.get("counts"), "denoms[].counts"):
            count = object_value(count, "denoms[].counts[]")
            if count.get("groupId") not in group_ids:
                raise EventError("denominator groupId is absent from original groups")
            value_cell(count.get("value"), "denoms[].counts[].value")
            covered.add(count["groupId"])
    if measurements[0]["groupId"] not in covered:
        raise EventError("first measurement must retain a denominator cell and denominator units")


def validate_nobel(record, seen_awards, categories):
    fields = record["fields"]
    year = text(fields.get("award_year"), "award_year")
    if not re.fullmatch(r"\d{4}", year) or not 1901 <= int(year) <= 2025:
        raise EventError("award_year must be between 1901 and 2025")
    category = text(fields.get("category_code"), "category_code")
    names = {"phy": "Physics", "che": "Chemistry", "med": "Physiology or Medicine"}
    if category not in names or fields.get("category") != names[category]:
        raise EventError("Nobel category code and title must match the three selected categories")
    key = category + ":" + year
    if record["record_key"] != key or key in seen_awards:
        raise EventError("Nobel annual category must have one unique canonical key")
    seen_awards.add(key)
    categories[category] += 1
    if record["record_url"] != f"https://api.nobelprize.org/2/nobelPrize/{category}/{year}":
        raise EventError("record_url must match the Nobel annual category")
    # Historical prizes can be awarded in a later year; preserve both fields.
    iso_date(fields.get("date_awarded"), "date_awarded", cutoff=True)
    laureates = list_value(fields.get("laureates"), "laureates")
    ids, total = set(), Fraction(0)
    for laureate in laureates:
        laureate = object_value(laureate, "laureates[]")
        laureate_id = text(laureate.get("id"), "laureates[].id")
        if not laureate_id.isdigit() or laureate_id in ids:
            raise EventError("laureate IDs must be numeric and unique within an award")
        ids.add(laureate_id)
        text(laureate.get("name"), "laureates[].name")
        text(laureate.get("motivation"), "laureates[].motivation")
        portion = text(laureate.get("portion"), "laureates[].portion")
        try:
            share = Fraction(portion)
        except (ValueError, ZeroDivisionError) as exc:
            raise EventError("laureate portion must preserve a positive award fraction") from exc
        if not 0 < share <= 1:
            raise EventError("laureate portion must preserve a positive award fraction")
        total += share
    if total != 1:
        raise EventError("all annual-category laureates and their portions must sum to one")


def first_difference(expected, actual, path="record"):
    if type(expected) is not type(actual):
        return path + ".type"
    if isinstance(expected, dict):
        if expected.keys() != actual.keys():
            return path + ".keys"
        for key in expected:
            difference = first_difference(expected[key], actual[key], path + "." + key)
            if difference:
                return difference
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            return path + ".length"
        for index, (left, right) in enumerate(zip(expected, actual)):
            difference = first_difference(left, right, f"{path}[{index}]")
            if difference:
                return difference
    elif expected != actual:
        return path
    return None


def verify_events(root=ROOT):
    root = Path(root).resolve()
    refs = root / "references"
    event_data = refs / "event-data"
    errors = []
    summary = {}
    try:
        renderer = load_renderer()
    except EventError as exc:
        return {"valid": False, "events": 0, "datasets": {}, "error_count": 1,
                "errors": [str(exc)], "note": NOTE}
    if linked_path(refs) or linked_path(event_data):
        return {"valid": False, "events": 0, "datasets": {}, "error_count": 1,
                "errors": ["event-data: linked input directories are not allowed"], "note": NOTE}
    deep_keys, excluded_cfpb = deep_episode_keys(refs, errors)
    all_event_keys, all_ids = set(), set()
    for dataset, config in EXPECTED.items():
        if renderer.DATASETS.get(dataset) != config:
            errors.append(f"{dataset}: renderer range/source/domain contract differs")
            continue
        snapshot_path = event_data / (dataset + ".json")
        case_path = refs / f"cases-events-{dataset}.json"
        before = len(errors)
        snapshot = load_json(snapshot_path, dataset + ".snapshot", errors)
        cases = load_json(case_path, dataset + ".cases", errors)
        if not isinstance(snapshot, dict):
            errors.append(f"{dataset}: snapshot must be an object")
            continue
        if snapshot.get("dataset") != dataset or snapshot.get("source_id") != config["source"]:
            errors.append(f"{dataset}: snapshot dataset/source mapping differs")
        rows = snapshot.get("records")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            errors.append(f"{dataset}: records must be an array of objects")
            continue
        if len(rows) != config["count"]:
            errors.append(f"{dataset}: expected {config['count']} snapshot records")
        if not isinstance(cases, list) or any(not isinstance(row, dict) for row in cases):
            errors.append(f"{dataset}: cases must be an array of objects")
            continue
        if len(cases) != config["count"]:
            errors.append(f"{dataset}: expected {config['count']} derived cases")
        keys, names, certs, urls, awards = set(), set(), set(), set(), set()
        categories = Counter()
        for index, record in enumerate(rows):
            try:
                key = text(record.get("record_key"), "record_key")
                if key in keys:
                    raise EventError("duplicate record_key")
                keys.add(key)
                object_value(record.get("fields"), "fields")
                canonical_url(record.get("record_url"))
                if dataset == "fdic":
                    validate_fdic(record, names, certs)
                elif dataset == "cfpb":
                    validate_cfpb(record, urls, excluded_cfpb)
                elif dataset == "clinical":
                    validate_clinical(record)
                else:
                    validate_nobel(record, awards, categories)
            except (EventError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
                detail = str(exc) if isinstance(exc, EventError) else type(exc).__name__
                errors.append(f"{dataset}.records[{index}]: {detail}")
        if dataset == "nobel" and categories != Counter({"phy": 50, "che": 50, "med": 50}):
            errors.append("nobel: expected exactly 50 annual awards in each of phy/che/med")
        for index, row in enumerate(cases):
            case_id = f"C{config['start'] + index:03d}"
            if row.get("id") != case_id or case_id in all_ids:
                errors.append(f"{dataset}.cases[{index}]: fixed ID range/order differs")
            all_ids.add(case_id)
            provenance = row.get("provenance")
            if not isinstance(provenance, dict):
                errors.append(f"{case_id}: provenance must be an object")
                continue
            requested = provenance.get("snapshot_file")
            # Exact relative paths prevent traversal before any requested path is read.
            if requested != f"event-data/{dataset}.json":
                errors.append(f"{case_id}: snapshot_file must exactly match its dataset inside event-data")
            else:
                resolved = (refs / requested).resolve()
                if event_data.resolve() not in resolved.parents or linked_path(refs / requested):
                    errors.append(f"{case_id}: snapshot path escapes event-data or is linked")
            try:
                key = canonical_event_key(row.get("event_key"))
                if key in all_event_keys:
                    errors.append(f"{case_id}: duplicate canonical event episode")
                if key in deep_keys:
                    errors.append(f"{case_id}: event episode is already a deep case")
                all_event_keys.add(key)
            except (EventError, ValueError, TypeError) as exc:
                detail = str(exc) if isinstance(exc, EventError) else type(exc).__name__
                errors.append(f"{case_id}: {detail}")
        if len(errors) == before:
            try:
                expected = renderer.render_dataset(dataset, root)
                for case_id, original, actual in zip(
                    (f"C{config['start'] + index:03d}" for index in range(len(expected))), expected, cases
                ):
                    difference = first_difference(original, actual)
                    if difference:
                        errors.append(f"{case_id}: derived content differs at {difference}")
                snapshot_hash = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
                summary[dataset] = {"records": len(rows), "derived_cases": len(cases),
                                    "source_id": config["source"], "snapshot_sha256": snapshot_hash}
            except (OSError, ValueError, TypeError, KeyError, AttributeError, StopIteration) as exc:
                errors.append(f"{dataset}: rendering cannot complete ({type(exc).__name__})")
    total = sum(value["derived_cases"] for value in summary.values())
    if len(all_ids) != 900 or len(all_event_keys) != 900:
        errors.append("events: expected 900 unique fixed IDs and canonical episode keys")
    return {"valid": not errors, "events": total, "datasets": summary,
            "error_count": len(errors), "errors": errors[:20], "note": NOTE}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Skill directory; mainly for offline fixtures")
    args = parser.parse_args(argv)
    try:
        result = verify_events(args.root)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        result = {"valid": False, "events": 0, "datasets": {}, "error_count": 1,
                  "errors": [f"verification cannot complete ({type(exc).__name__})"], "note": NOTE}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

