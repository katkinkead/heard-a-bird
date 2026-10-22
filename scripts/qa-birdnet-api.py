#!/usr/bin/env python3
"""Developer-only API check against a disposable, already-running BirdNET lab.

No Docker, Pi installation, credentials, audio fixtures or hardware bypasses are
created here. The default is read-only and verifies the expected saved settings.
Explicit --allow-lab-settings exercises
the production commissioner's source-independent configuration with its real
cookie/CSRF client. Use only your disposable lab, never an existing station.

Example:
  python3 scripts/qa-birdnet-api.py --url http://127.0.0.1:18080 \
    --allow-lab-settings --report /tmp/songsketch-api-evidence.json

An API pass is not microphone, species-recognition or Raspberry Pi verification.
RTSP lab sources remain intact; a made-up physical capture source is never sent.
Reports contain only selected contract results, never response bodies or cookies.
"""
import argparse
import copy
import datetime as dt
import importlib.util
import json
import math
from pathlib import Path
import sys
import urllib.parse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("qa_commission_pi", ROOT / "scripts/commission-pi.py")
commission = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(commission)
SECTIONS = ("birdnet", "models", "realtime", "output", "audio")
ERROR_CODES = frozenset(("csrf_missing", "birdnet_access_required", "birdnet_http_error",
                         "birdnet_unreachable", "app_contract_changed", "birdnet_version_mismatch",
                         "settings_contract_changed", "existing_configuration_complex"))


def lab_url(value):
    """No DNS resolution, redirects, user info or default production endpoint."""
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
        if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "::1")
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or port is None or not 1024 <= port <= 65535 or port == 8080):
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("Use an explicit HTTP loopback lab port, excluding production port 8080.") from None
    host = "[::1]" if parsed.hostname == "::1" else "127.0.0.1"
    return "http://" + host + ":" + str(port)


def source_independent_plan(settings):
    """Derive real commissioning patches without replacing a lab's audio source.

    The production planner intentionally rejects RTSP/multiple inputs. Project
    only its input-selection fields into an empty planning copy, then discard
    the entire capture-source patch. The actual settings and device configuration
    are never changed by that projection. Other planner protections still apply.
    """
    planning = copy.deepcopy(settings)
    if not isinstance(planning, dict):
        raise commission.CommissionError("settings_contract_changed", "Settings are unfamiliar.")
    realtime = planning.get("realtime")
    if not isinstance(realtime, dict):
        raise commission.CommissionError("settings_contract_changed", "Settings are unfamiliar.")
    audio = realtime.get("audio", {})
    if not isinstance(audio, dict):
        raise commission.CommissionError("settings_contract_changed", "Settings are unfamiliar.")
    realtime["audio"] = dict(audio, sources=[])
    realtime["rtsp"] = {"streams": []}
    plan = commission.settings_plan(planning, {"latitude": 50.72, "longitude": -2.44},
                                    {"id": "planning-only-never-submitted"})
    return [(section, {k: v for k, v in patch.items() if k in ("quietHours", "export")}
             if section == "audio" else patch) for section, patch in plan]


def threshold_evidence(birdnet, realtime):
    """A 0.7 baseline is not a fixed floor when adaptive thresholds are enabled."""
    evidence = {}
    if not isinstance(birdnet, dict) or not isinstance(realtime, dict): return evidence
    dynamic = realtime.get("dynamicThreshold", {})
    if not isinstance(dynamic, dict): dynamic = {}
    for name, value in (("baseline", birdnet.get("threshold")), ("dynamic_trigger", dynamic.get("trigger")),
                        ("dynamic_minimum", dynamic.get("min")), ("dynamic_valid_hours", dynamic.get("validHours"))):
        if type(value) in (int, float) and math.isfinite(value): evidence[name] = value
    if type(dynamic.get("enabled")) is bool: evidence["dynamic_enabled"] = dynamic["enabled"]
    return evidence


def run_check(url, allow_lab_settings=False, api=None, timezone="Europe/London"):
    base = lab_url(url)  # Refuse unsafe targets even when a caller supplies a client.
    if type(allow_lab_settings) is not bool:
        raise ValueError("Settings permission must be explicit.")
    try:
        zone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, TypeError, ValueError):
        raise ValueError("Use a valid IANA timezone matching the disposable BirdNET lab.") from None
    observed_at = dt.datetime.now(dt.timezone.utc)
    query_day = observed_at.astimezone(zone).date().isoformat()
    # Explicit date scoping exercises stored history instead of the upstream
    # default recent-detection cache, which can be empty while SQLite has birds.
    history_path = "/api/v2/detections?" + urllib.parse.urlencode({
        "start_date": query_day, "end_date": query_day, "numResults": 1, "sortBy": "date_asc"})
    api = api or commission.BirdNET(base)
    result = {
        "schema_version": 1, "kind": "birdnet_api_lab", "status": "failed",
        "tested_at": observed_at.isoformat(), "query_day": query_day, "query_timezone": timezone,
        "expected_release": commission.RELEASE, "lab_port": urllib.parse.urlsplit(base).port,
        "settings_requested": allow_lab_settings, "settings_mutated": False,
        "settings_write_attempted": False, "settings_write_outcome": "not_attempted",
        "restart_required": False, "checks": {}, "errors": [],
        "evidence_limits": {
            "physical_pi_verified": False, "microphone_verified": False,
            "known_audio_recognition_verified": False, "source_configuration_verified": False,
        },
    }

    def error(check, exc):
        # Do not export arbitrary exception strings, URLs, auth or response text.
        code = getattr(exc, "code", "unexpected_response")
        if not isinstance(code, str) or code not in ERROR_CODES:
            code = "unexpected_response"
        result["checks"][check] = False
        result["errors"].append({"check": check, "code": code})

    try:
        app = api.bootstrap()
        result["checks"]["pinned_release"] = app.get("version") == commission.RELEASE
        result["checks"]["no_key_bootstrap"] = app.get("security", {}).get("enabled") is False
        result["checks"]["csrf_provided"] = isinstance(app.get("csrfToken"), str) and bool(app["csrfToken"])
    except Exception as exc:
        error("bootstrap", exc)
        return result
    # A client or test double must never enable writes by returning an unchecked
    # version/authentication response. Production BirdNET.bootstrap also guards it.
    if not all(result["checks"].values()):
        return result

    try:
        settings = api.request("/api/v2/settings")
        valid = isinstance(settings, dict) and all(isinstance(settings.get(k), dict)
                                                   for k in ("birdnet", "models", "realtime", "output"))
        result["checks"]["settings_shape"] = valid
        policy = {key: settings[key] for key in ("birdnet", "realtime")} if valid else {}
        if valid: result["threshold_policy"] = threshold_evidence(**policy)
        if valid:
            plan = source_independent_plan(settings)
            for section, patch in plan:
                if allow_lab_settings:
                    # The server can commit a PATCH before its acknowledgement
                    # is lost. Record uncertainty before sending; an exception
                    # must never turn that into a claim that nothing changed.
                    result["settings_write_attempted"] = True
                    result["settings_write_outcome"] = "uncertain"
                    result["settings_mutated"] = None
                    response = api.request("/api/v2/settings/" + section, "PATCH", patch)
                    result["settings_mutated"] = True
                    result["settings_write_outcome"] = "acknowledged"
                    accepted = isinstance(response, dict) and not response.get("skippedFields")
                    result["checks"][section + "_patch_accepted"] = accepted
                    if not accepted:
                        break  # Preserve the first failure; never retry/repair silently.
                    result["restart_required"] |= response.get("restart_required") is True
                actual = api.request("/api/v2/settings/" + section)
                if section in policy:
                    policy[section] = actual
                    result["threshold_policy"] = threshold_evidence(**policy)
                result["checks"][section + "_readback"] = commission.matches(actual, patch)
                if not result["checks"][section + "_readback"]:
                    break
    except Exception as exc:
        error("settings", exc)

    for label, endpoint in (
        ("capture_devices", "/api/v2/system/audio/devices"),
        ("audio_health", "/api/v2/health/audio"),
        ("inference", "/api/v2/system/inference"),
        ("stored_detections", history_path),
    ):
        try:
            value = api.request(endpoint)
            if label == "capture_devices":
                valid = isinstance(value, list)
                if valid: result["capture_device_count"] = len(value)
            elif label == "audio_health":
                valid = isinstance(value, dict) and isinstance(value.get("sources"), list)
                if valid: result["audio_source_count"] = len(value["sources"])
                audio_health = value
            elif label == "inference":
                valid = isinstance(value, dict) and isinstance(value.get("models"), list)
                if valid:
                    result["birdnet_model_present"] = any(
                        isinstance(m, dict) and m.get("id") == "BirdNET_V2.4" for m in value["models"])
                inference = value
            else:
                valid = (isinstance(value, dict) and isinstance(value.get("data"), list)
                         and type(value.get("total")) is int and value["total"] >= 0)
                if valid:
                    result["stored_detection_count"] = value["total"]
                    result["returned_detection_count"] = len(value["data"])
            result["checks"][label + "_shape"] = valid
        except Exception as exc:
            error(label, exc)

    if result["checks"].get("audio_health_shape") and result["checks"].get("inference_shape"):
        try:
            audio, model = commission.relay.interpret_health(audio_health, inference, {"model_id": "BirdNET_V2.4"})
            result["observed_pipeline"] = {"audio": audio, "inference": model}
        except (TypeError, ValueError, KeyError, AttributeError):
            error("pipeline_health", ValueError())
    result["status"] = "passed" if all(result["checks"].values()) and not result["errors"] else "failed"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="Disposable HTTP loopback lab endpoint; never port 8080.")
    parser.add_argument("--report", required=True, type=Path, help="Local JSON evidence file, written with mode 0600.")
    parser.add_argument("--timezone", default="Europe/London",
                        help="IANA timezone used by the lab; scopes stored detections to today (default: Europe/London).")
    parser.add_argument("--allow-lab-settings", action="store_true",
                        help="Confirm this is your disposable lab and permit source-independent settings changes.")
    args = parser.parse_args(argv)
    try:
        result = run_check(args.url, args.allow_lab_settings, timezone=args.timezone)
    except ValueError as exc:
        parser.error(str(exc))
    commission.private_json(args.report, result)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
