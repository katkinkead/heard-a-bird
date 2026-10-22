#!/usr/bin/env python3
"""Developer-only stored BirdNET -> production relay -> real server check.

Stop the disposable lab's audio publisher and let pending detections settle first.
This reads an already-running pinned BirdNET API, then creates and removes a
private temporary Songsketch server and relay outbox. Only literal HTTP loopback
lab ports are accepted. No settings, real station, credentials, artwork, email
provider or AI service are changed. The background maintenance worker is disabled.

Example:
  python3 scripts/qa-birdnet-delivery.py --url http://127.0.0.1:18080 \
    --expected-species 'Strix aluco' --report /tmp/songsketch-delivery-evidence.json

The saved report verifies delivery of stored detections, not their audio provenance
or physical microphone accuracy. Current audio health is observed separately:
a stopped lab stream need not be healthy for stored-history delivery to pass.
"""
import argparse
from collections import Counter
import datetime as dt
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import threading
import time
import urllib.parse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from songsketch.server import App, Server
from songsketch.store import iso, timestamp

SPEC = importlib.util.spec_from_file_location("delivery_lab_api", ROOT / "scripts/qa-birdnet-api.py")
api_lab = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api_lab)
pi = api_lab.commission.relay


class LabError(Exception):
    def __init__(self, code):
        self.code = code


def read_snapshot(api, day, config):
    """Read bounded real API pages; never create or substitute a detection."""
    records = {}
    offset, limit, total = 0, 200, None
    for _ in range(20):
        query = urllib.parse.urlencode({"start_date": day.isoformat(), "end_date": day.isoformat(),
                                      "sortBy": "date_asc", "numResults": limit, "offset": offset})
        response = api.request("/api/v2/detections?" + query)
        if (not isinstance(response, dict) or type(response.get("total")) is not int
                or not isinstance(response.get("data"), list)
                or not 0 <= response["total"] <= 4000):
            raise LabError("invalid_detection_page")
        if total is not None and total != response["total"]:
            raise LabError("upstream_changed_stop_publisher_and_retry")
        total = response["total"]
        rows = response["data"]
        if len(rows) > limit or offset + len(rows) > total or not rows and offset < total:
            raise LabError("invalid_detection_page")
        for row in rows:
            if not isinstance(row, dict): raise LabError("invalid_detection_record")
            try:
                normalized = pi.normalize_detection(row, config)
            except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
                raise LabError("invalid_detection_record") from None
            if normalized:
                # Keep arbitrary upstream strings out of the evidence report.
                for key in ("scientific_name", "common_name"):
                    value = normalized[key]
                    if not isinstance(value, str) or not value.strip() or len(value) > 120 or any(ord(c) < 32 for c in value):
                        raise LabError("invalid_detection_record")
                if normalized["event_id"] in records:
                    raise LabError("duplicate_upstream_record")
                records[normalized["event_id"]] = normalized
        offset += len(rows)
        if offset == total:
            return records, total
    raise LabError("detection_limit_exceeded")


def expected_rows(records, threshold):
    return {event: {"event_id": event, "station_id": value["station_id"],
                   "scientific_name": value["scientific_name"], "common_name": value["common_name"],
                   "confidence": value["confidence"], "observed_at": iso(timestamp(value["observed_at"])),
                   "test": 0, "qualifies": int(value["confidence"] >= threshold)}
            for event, value in records.items()}


def server_rows(app):
    rows = app.store.query("SELECT event_id,station_id,scientific_name,common_name,confidence,observed_at,test,qualifies FROM detections")
    return {row["event_id"]: row for row in rows}


def drain(relay):
    # A delivery recovery can append a report. Bounded rounds keep failures visible.
    for _ in range(4):
        relay.deliver(now=time.time() + 1000)
        if not relay.store.snapshot()["pending"]:
            return


def run_check(url, expected_species, timezone="Europe/London", api=None):
    base = api_lab.lab_url(url)  # Must run before any network or temporary server.
    if not isinstance(expected_species, str) or not re.fullmatch(r"[A-Z][a-z]+ [a-z]+(?: [a-z]+)?", expected_species):
        raise ValueError("Expected species must be its scientific name, for example Strix aluco.")
    zone = ZoneInfo(timezone)
    day = dt.datetime.now(zone).date()
    result = {"schema_version": 1, "kind": "birdnet_delivery_lab", "status": "failed",
              "tested_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "expected_release": api_lab.commission.RELEASE, "expected_species": expected_species,
              "lab_port": urllib.parse.urlsplit(base).port, "observation_date": day.isoformat(),
              "station_timezone": timezone, "confidence_threshold": .7,
              "checks": {}, "errors": [], "current_pipeline": {"audio": "unknown", "inference": "unknown"},
              "evidence_limits": {"audio_fixture_provenance_verified": False, "physical_pi_verified": False,
                                  "microphone_verified": False, "external_email_verified": False,
                                  "artwork_playback_verified": False},
              "isolation": {"temporary_server_and_outbox": True, "background_workers": False,
                            "external_email_sent": False, "ai_called": False,
                            "catalogue": "empty isolated missing-art catalogue"}}
    api = api or api_lab.commission.BirdNET(base)
    try:
        bootstrap = api.bootstrap()
        result["checks"]["pinned_no_key_api"] = (isinstance(bootstrap, dict)
            and bootstrap.get("version") == api_lab.commission.RELEASE
            and bootstrap.get("security", {}).get("enabled") is False)
        if not result["checks"]["pinned_no_key_api"]:
            return result
        with tempfile.TemporaryDirectory(prefix="songsketch-birdnet-delivery-") as directory:
            path = Path(directory)
            catalogue = path / "catalogue.json"
            catalogue.write_text(json.dumps({"version": 1, "birds": []}))
            app = relay = server = thread = None
            try:
                app = App(path / "server-state", catalogue, background=False)
                app.config.update({"timezone": timezone, "station_id": "delivery-lab", "confidence_threshold": .7})
                server = Server(("127.0.0.1", 0), app)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                token_file = path / "station.token"
                token_file.write_text(app.config.secrets["station_token"])
                token_file.chmod(0o600)
                config = {"station_id": "delivery-lab", "source_instance_id": "delivery-lab-source",
                          "server_url": "http://127.0.0.1:" + str(server.server_port), "birdnet_url": base,
                          "token_file": str(token_file), "data_dir": str(path / "relay-state"),
                          "timezone": timezone, "initial_history_days": 0, "poll_seconds": 5,
                          "heartbeat_seconds": 15, "model_id": "BirdNET_V2.4"}
                baseline, total = read_snapshot(api, day, config)
                expected = expected_rows(baseline, .7)
                result["upstream_stored_records"] = total
                result["normalized_records"] = len(expected)
                result["checks"]["expected_species_detected"] = any(
                    item["scientific_name"] == expected_species and item["qualifies"] for item in expected.values())
                if not result["checks"]["expected_species_detected"]:
                    return result
                relay = pi.Relay(config)  # Unmodified production HTTP transport and normalization.
                relay.poll(day)
                drain(relay)
                first = server_rows(app)
                relay.poll(day)
                drain(relay)
                second = server_rows(app)
                after, final_total = read_snapshot(api, day, config)
                stable = baseline == after and total == final_total
                result["checks"]["upstream_snapshot_stable"] = stable
                if not stable:
                    result["errors"].append({"code": "upstream_changed_stop_publisher_and_retry"})
                result["checks"]["exact_event_ids_and_values"] = first == expected
                result["checks"]["repeat_poll_idempotent"] = first == second
                expected_counts = dict(Counter(row["scientific_name"] for row in expected.values() if row["qualifies"]))
                summary = app.store.summary("all")
                actual_counts = {row["scientific_name"]: row["count"] for row in summary}
                result["checks"]["qualifying_counts_match"] = actual_counts == expected_counts
                result["checks"]["relay_outbox_empty"] = relay.store.snapshot()["pending"] == 0
                mail = app.store.query("SELECT species,status,attempts FROM email_outbox")
                result["checks"]["missing_art_pending_without_send"] = (
                    len(mail) == len(expected_counts) and {row["species"] for row in mail} == set(expected_counts)
                    and all(row["status"] == "pending" and row["attempts"] == 0 for row in mail))
                result["delivered_records"] = len(second)
                result["qualifying_records"] = sum(actual_counts.values())
                result["missing_art_notifications_queued_locally"] = len(mail)
                record_counts = Counter(row["scientific_name"] for row in second.values())
                result["species"] = [{"scientific_name": name, "records": count, "qualifying_records": actual_counts.get(name, 0),
                    "confidence_min": min(row["confidence"] for row in second.values() if row["scientific_name"] == name),
                    "confidence_max": max(row["confidence"] for row in second.values() if row["scientific_name"] == name)}
                    for name, count in sorted(record_counts.items())]
                try:
                    relay.heartbeat()
                    result["current_pipeline"] = {"audio": relay.audio_status, "inference": relay.inference_status,
                                                  "server_listening": app.store.station_status()["listening"]}
                    drain(relay)
                    result["health_reports_delivered"] = app.store.query("SELECT COUNT(*) n FROM reports")[0]["n"]
                except Exception:
                    # Current live health is a separate observation, never fabricated.
                    result["health_observation_error"] = "current_health_unavailable"
                result["checks"]["relay_outbox_empty"] = relay.store.snapshot()["pending"] == 0
            finally:
                if server:
                    if thread and thread.is_alive(): server.shutdown()
                    server.server_close()
                if thread: thread.join(timeout=5)
                if relay: relay.store.close()
                if app: app.close()
    except Exception as exc:
        # This is a developer lab; the transcript/report must not contain URLs,
        # response bodies, cookies, private paths or arbitrary exception messages.
        code = exc.code if isinstance(exc, LabError) else getattr(exc, "code", "lab_check_failed")
        allowed = {"invalid_detection_page", "invalid_detection_record", "duplicate_upstream_record",
                   "upstream_changed_stop_publisher_and_retry", "detection_limit_exceeded"} | set(api_lab.ERROR_CODES)
        result["errors"].append({"code": code if isinstance(code, str) and code in allowed else "lab_check_failed"})
    result["status"] = "passed" if result["checks"] and all(result["checks"].values()) and not result["errors"] else "failed"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="Disposable loopback BirdNET lab endpoint, excluding port 8080.")
    parser.add_argument("--expected-species", required=True, help="Scientific name that must qualify in today's stored detections.")
    parser.add_argument("--timezone", default="Europe/London", help="Lab station timezone, default Europe/London.")
    parser.add_argument("--report", required=True, type=Path, help="Local selected-evidence JSON file, mode 0600.")
    args = parser.parse_args(argv)
    try:
        result = run_check(args.url, args.expected_species, args.timezone)
    except (ValueError, KeyError):
        parser.error("Use a valid literal HTTP loopback lab URL, scientific species name and station timezone.")
    api_lab.commission.private_json(args.report, result)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
