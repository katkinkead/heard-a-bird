"""Read-only presentation of existing setup evidence, not a new health probe.

Call from an authenticated local response with fresh commissioning/diagnostic
snapshots. This module does no I/O, executes no repairs, and never exposes the
raw job inputs, logs, credentials, reports, microphone names or coordinates.
"""
from datetime import datetime, timezone
import hashlib
import math
import re

from .store import redact


COMPONENTS = (
    ("server", "Indoor server", "This computer"),
    ("garden_pi", "Garden Pi", "Garden Pi and its network connection"),
    ("power", "Power & performance", "Garden Pi · supply and firmware flags"),
    ("thermal", "Temperature", "Garden Pi · SoC temperature and cooling"),
    ("microphone", "Microphone", "Garden Pi · audio input"),
    ("birdnet", "Bird recognition", "Garden Pi · BirdNET-Go"),
    ("delivery", "Reports reaching home", "Garden Pi → indoor server"),
    ("display", "Painting page", "Display browser"),
)
LOCATIONS = {key: place for key, _, place in COMPONENTS}
LOCATIONS["system"] = "Not yet isolated"
CODE_GROUPS = {
    "server": {"ssh_missing", "package_incomplete", "package_invalid", "helper_error"},
    "garden_pi": {"host_unreachable", "host_key_changed", "ambiguous_host_key",
                  "authentication_failed", "sudo_required", "unexpected_connection",
                  "unsupported_platform", "clock_unsynchronized", "timezone_failed",
                  "low_disk", "installer_failed", "remote_command_failed", "missing_result",
                  "operation_timeout", "excessive_output", "commissioning_in_progress"},
    "microphone": {"capture_missing", "capture_choice_required", "capture_choice_changed",
                   "device_contract_changed"},
    "birdnet": {"birdnet_access_required", "birdnet_unreachable", "birdnet_http_error",
                "birdnet_version_mismatch", "birdnet_ownership_unverified", "csrf_missing",
                "app_contract_changed", "settings_contract_changed", "settings_not_verified",
                "settings_rejected", "unmanaged_configuration", "existing_configuration_complex",
                "container_timezone_mismatch", "restart_required", "history_contract_changed"},
    "delivery": {"server_unreachable", "relay_start_failed", "relay_verification_pending"},
}
ISSUE_COMPONENTS = {
    "backup-failed": "server", "low-disk": "server", "database-integrity": "server",
    "maintenance-failed": "server", "server-restarted": "server",
    "pi-disconnected": "garden_pi", "audio-unavailable": "birdnet",
}
REPORT_COMPONENTS = {
    "audio": "microphone", "inference": "birdnet", "birdnet_history": "birdnet",
    "birdnet_version": "birdnet", "server_delivery": "delivery",
    "server_heartbeat": "delivery", "storage": "garden_pi", "maintenance": "garden_pi",
    "power": "power", "thermal": "thermal",
}
NEXT_ACTIONS = {
    "server": "Inspect the local setup diagnostic packet and the server's saved service evidence.",
    "garden_pi": "Check the current Pi address, power and network, then run the guarded Pi diagnostics.",
    "power": "Check the specified Pi supply and cable under load. Capping or throttling alone does not identify the cause; preserve the measured flags.",
    "thermal": "Inspect enclosure ventilation and the fitted cooling. The 75°C alert is a provisional operational warning; no automatic shutdown is performed.",
    "microphone": "Check the connected microphone and input power; use the actual capture choices and live audio check.",
    "birdnet": "Inspect BirdNET capture, model and access evidence; preserve its existing settings and authentication.",
    "delivery": "Check the relay and server LAN route; preserve queued detections and reports while diagnosing.",
    "display": "Open the painting page and observe a labelled test painting; the server cannot see the browser's pixels.",
    "system": "Use the local diagnostic packet to identify the affected component before choosing a repair.",
}


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _time(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def _stamp(value):
    parsed = _time(value)
    return parsed.isoformat().replace("+00:00", "Z") if parsed else None


def _code(value, default="unknown"):
    return value if isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,79}", value) else default


def _component(code, stage, checks):
    for component, codes in CODE_GROUPS.items():
        if code in codes:
            return component
    if code == "audio_pipeline_not_ready":
        return "microphone" if checks.get("audio") == "failed" else "birdnet"
    if stage in ("host_key", "connect", "transfer", "provision", "preflight", "installing"):
        return "garden_pi"
    if stage in ("connecting", "configuring", "verifying"):
        return "birdnet"
    if stage == "starting_relay":
        return "delivery"
    return "system"


def build_setup_health(setup, diagnostics, *, heartbeat_timeout_seconds=150,
                       secrets=(), now=None):
    """Build a bounded, JSON-safe component summary from existing observations.

    `healthy` is scoped to the stated evidence, never whole-installation approval.
    A previous commissioning pass is historical evidence, not live liveness.
    `now` exists for deterministic tests; production callers should omit it.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("The observation time must include a timezone")
    now = now.astimezone(timezone.utc)
    generated = now.isoformat().replace("+00:00", "Z")
    private_values = tuple(secrets)

    def text(value, limit=500):
        if not isinstance(value, str):
            return ""
        safe = redact(value, private_values)
        return " ".join(safe.split())[:limit]

    def evidence(check, status, observed, expected, at=None, source="server_diagnostics"):
        if isinstance(observed, str):
            observed = text(observed, 180)
        elif isinstance(observed, float) and not math.isfinite(observed):
            observed = None
        elif not isinstance(observed, (bool, int, float, type(None))):
            observed = None
        return {"check": check, "status": status, "observed": observed,
                "expected": expected, "observed_at": _stamp(at), "source": source}

    setup, diagnostics = _mapping(setup), _mapping(diagnostics)
    job = _mapping(setup.get("job"))
    result = _mapping(job.get("result"))
    checks = _mapping(result.get("checks"))
    state, stage = _code(job.get("state"), "not_started"), _code(job.get("stage"), "not_started")
    observed = _stamp(diagnostics.get("generated_at")) or generated
    components = {key: {"id": key, "label": label, "location": location,
                        "status": "unverified", "stage": "not_checked", "code": "not_checked",
                        "message": "No current evidence is available.", "evidence": [],
                        "next_action": NEXT_ACTIONS[key]}
                  for key, label, location in COMPONENTS}
    problems = []

    def set_component(key, status, code, message, items, action=None, checkpoint=None):
        components[key].update(status=status, code=code, message=message, evidence=items,
                               next_action=action or NEXT_ACTIONS[key], stage=checkpoint or code)

    def problem(identifier, component, code, message, failed, action=None, severity="error",
                source="setup_job", at=None, checkpoint=None):
        item = {"id": identifier, "component": component, "location": LOCATIONS[component],
                "severity": severity, "stage": checkpoint or stage, "code": code,
                "message": text(message) or "A recorded checkpoint needs review.", "failed_evidence": failed,
                "next_action": text(action) or NEXT_ACTIONS[component],
                "source": source, "observed_at": _stamp(at)}
        problems.append(item)
        if component in components and severity in ("error", "warning"):
            components[component].update(status="attention", stage=item["stage"], code=code,
                                         message=item["message"], next_action=item["next_action"])
            components[component]["evidence"].extend(failed)

    database = _mapping(diagnostics.get("database_check")).get("quick_check")
    db_evidence = evidence("database_quick_check", "passed" if database == "ok" else "failed" if database else "unknown",
                           "ok" if database == "ok" else "check failed" if database else None,
                           "ok", observed)
    set_component("server", "healthy" if database == "ok" else "unverified",
                  "server_responding" if database == "ok" else "database_unverified",
                  "This server returned diagnostics and its database check passed." if database == "ok" else "The response does not include a passing database check.",
                  [db_evidence], checkpoint="local_server")
    if database and database != "ok":
        problem("database-check", "server", "database_check_failed", "The server database check did not pass.",
                [], source="server_diagnostics", at=observed, checkpoint="local_server")
        problems[-1]["failed_evidence"] = [db_evidence]

    supervisor = _mapping(diagnostics.get("supervisor"))
    supervisor_state = _code(supervisor.get("state"), "unknown")
    supervisor_at = _time(supervisor.get("updated_at"))
    supervisor_fresh = supervisor_at is not None and -30 <= (now - supervisor_at).total_seconds() <= 120
    if supervisor:
        supervisor_evidence = evidence("supervisor_snapshot", "recorded" if supervisor_fresh else "stale",
                                       supervisor_state, "Recent supervisor observation; the API is responding now",
                                       supervisor.get("updated_at"), "supervisor_snapshot")
        components["server"]["evidence"].append(supervisor_evidence)
        if supervisor_fresh and supervisor_state in ("failed", "restarting", "checking"):
            problem("supervisor-check", "server", "supervisor_" + supervisor_state,
                    "The supervisor recently recorded %s. This API is responding; review its recovery evidence before intervening." % supervisor_state,
                    [], severity="warning", source="supervisor_snapshot", at=supervisor.get("updated_at"), checkpoint="local_server")
            problems[-1]["failed_evidence"] = [supervisor_evidence]

    station = _mapping(diagnostics.get("station"))
    heartbeat = _time(station.get("last_heartbeat"))
    age = (now - heartbeat).total_seconds() if heartbeat else None
    timeout = heartbeat_timeout_seconds if isinstance(heartbeat_timeout_seconds, (int, float)) and not isinstance(heartbeat_timeout_seconds, bool) and 0 < heartbeat_timeout_seconds <= 3600 else 150
    fresh = station.get("connected") is True and age is not None and -30 <= age <= timeout
    seen = station.get("ever_connected") is True or heartbeat is not None
    heartbeat_evidence = evidence("station_heartbeat", "passed" if fresh else "stale" if seen else "unknown",
                                 round(max(0, age)) if age is not None else None,
                                 "A connected station report within %s seconds" % timeout,
                                 station.get("last_heartbeat"), "station_heartbeat")
    set_component("garden_pi", "healthy" if fresh else "unverified" if seen else "not_started",
                  "pi_reporting" if fresh else "pi_report_stale" if seen else "pi_not_reported",
                  "The configured garden station has checked in recently." if fresh else "The last Pi report is no longer current; its power and network state are unknown." if seen else "No report from the configured garden station has arrived yet.",
                  [heartbeat_evidence], checkpoint="station_connection")
    set_component("delivery", "healthy" if fresh else "unverified",
                  "report_delivered" if fresh else "delivery_unverified",
                  "A recent station report reached this server. A real bird record still needs its own check." if fresh else "Current Pi-to-server delivery has not been established.",
                  [dict(heartbeat_evidence)], checkpoint="station_delivery")
    if seen and not fresh:
        problem("heartbeat-stale", "garden_pi", "pi_report_stale",
                "The Pi has stopped checking in; this does not identify whether power, network or its software failed.",
                [], severity="warning", source="station_heartbeat", at=station.get("last_heartbeat"), checkpoint="station_connection")
        problems[-1]["failed_evidence"] = [heartbeat_evidence]

    for key, field, label in (("microphone", "audio_status", "audio capture"), ("birdnet", "inference_status", "recognition")):
        value = station.get(field) if fresh and station.get(field) in ("healthy", "failed") else "unknown"
        item = evidence(field, "passed" if value == "healthy" else "failed" if value == "failed" else "unknown",
                        value, "healthy in a fresh station report", station.get("last_heartbeat"), "station_heartbeat")
        set_component(key, "healthy" if value == "healthy" else "unverified", field,
                      "The latest Pi report describes healthy %s." % label if value == "healthy" else "Current %s is not verified. Silence alone is not a fault." % label,
                      [item], checkpoint="listening")
        if value == "failed":
            problem(field, key, field + "_failed", "The connected Pi reports a fault in %s." % label,
                    [], source="station_heartbeat", at=station.get("last_heartbeat"), checkpoint="listening")
            problems[-1]["failed_evidence"] = [item]

    hardware = _mapping(station.get("hardware"))
    hardware_at = _time(hardware.get("observed_at"))
    hardware_fresh = fresh and hardware_at is not None and -30 <= (now - hardware_at).total_seconds() <= timeout
    for key in ("power", "thermal"):
        reported = hardware.get(key + "_status")
        value = reported if hardware_fresh and reported in ("healthy", "warning") else "unknown"
        items = [evidence(key + "_sample", "passed" if value == "healthy" else "failed" if value == "warning" else "unknown",
                          value, "A recent measured hardware sample", hardware.get("observed_at"), "station_hardware")]
        if key == "power":
            for field in ("current_flags", "historical_flags"):
                flags = hardware.get(field)
                if isinstance(flags, list):
                    allowed = [flag for flag in flags[:4] if isinstance(flag, str) and flag in ("under_voltage", "frequency_capped", "throttled", "soft_temperature_limit")]
                    items.append(evidence(field, "recorded" if hardware_fresh else "stale", ", ".join(allowed) or "none recorded",
                                          "Current flags and earlier firmware flags interpreted separately", hardware.get("observed_at"), "station_hardware"))
            message = "The fresh firmware sample has no current under-voltage, frequency-capping or throttling flag. Historical flags are separate." if value == "healthy" else "Current power and performance flags are not verified."
        else:
            temperature = hardware.get("temperature_c")
            if isinstance(temperature, (int, float)) and not isinstance(temperature, bool) and math.isfinite(temperature) and -40 <= temperature <= 150:
                items.append(evidence("temperature_c", "recorded" if hardware_fresh else "stale", temperature,
                                      "Below the provisional 75°C warning threshold", hardware.get("observed_at"), "station_hardware"))
            message = "A fresh temperature reading is below the provisional 75°C warning threshold; no current soft limit was observed." if value == "healthy" else "A current temperature reading is not verified."
        set_component(key, "healthy" if value == "healthy" else "unverified", key + "_sample", message, items, checkpoint="hardware")
        if value == "warning":
            problem("hardware-" + key, key, key + "_warning",
                    "The Pi reports a current power or performance flag; inspect the measured flags to identify it." if key == "power" else
                    "The Pi reports a temperature warning or active soft limit; review cooling. This does not trigger a shutdown.",
                    [], source="station_hardware", at=hardware.get("observed_at"), checkpoint="hardware")
            problems[-1]["failed_evidence"] = items
    set_component("display", "unverified", "browser_not_observed",
                  "The server has no evidence that a browser has rendered the painting correctly.",
                  [evidence("browser_render", "unknown", None, "Observe a labelled test painting", source="not_instrumented")],
                  checkpoint="visual_check")

    # Saved commissioning is useful evidence, but cannot override live faults or
    # turn a diagnostic result into a fresh successful installation.
    successful = _mapping(job.get("last_successful_install"))
    if job.get("commissioned") is True and successful:
        item = evidence("saved_software_commissioning", "recorded", True,
                        "Inspect saved checks separately from current health", successful.get("at"), "saved_commissioning")
        components["garden_pi"]["evidence"].append(item)
    if state in ("probing", "running", "cancelling"):
        component = _component("", stage, checks)
        if component in components and components[component]["status"] not in ("attention",):
            components[component].update(status="working", stage=stage, code="setup_in_progress",
                                         message="A setup operation is in progress; completion has not been established.")
    if state == "awaiting_trust":
        problem("ssh-trust", "garden_pi", "ssh_identity_needs_confirmation",
                "Confirm the Pi's SSH identity before allowing the setup connection.",
                [evidence("ssh_identity_confirmation", "pending", False, "Explicit confirmation of the actual Pi identity", job.get("updated_at"), "setup_job")],
                "Compare the displayed fingerprint with the Pi or a trusted record, then confirm it.",
                severity="info", at=job.get("updated_at"), checkpoint="host_key")

    error = _mapping(job.get("error"))
    remote_code = _code(result.get("code"), "")
    code = _code(error.get("code"), remote_code or state)
    has_failure = state in ("failed", "needs_input", "interrupted", "cancelled")
    diagnostic_fault = job.get("operation") == "diagnose" and remote_code not in ("", "commissioned")
    if has_failure or diagnostic_fault:
        component = _component(code, stage, checks)
        failed = []
        for check in ("audio", "inference", "history_readable", "relay_service_active", "inference_advancing", "server_heartbeat_acknowledged", "relay_scan_verified"):
            value = checks.get(check)
            if value is False or value in ("failed", "unknown"):
                failed.append(evidence(check, "failed" if value is False or value == "failed" else "unknown", value,
                                       "Passing evidence from the corresponding Pi check", job.get("updated_at"), "setup_job"))
        if not failed:
            failed.append(evidence("setup_checkpoint", "incomplete", code, "Checkpoint completed with passing evidence", job.get("updated_at"), "setup_job"))
        problem("setup-checkpoint", component, code,
                error.get("message") or result.get("message") or "Setup did not establish a completed, verified checkpoint.",
                failed, job.get("human_action") or result.get("human_action"),
                severity="warning" if state in ("needs_input", "interrupted", "cancelled") else "error",
                at=job.get("updated_at"))
    # A read-only snapshot may contain failing checks without an error code.
    if job.get("operation") == "diagnose" and not has_failure and not diagnostic_fault:
        for check, component in (("audio", "microphone"), ("inference", "birdnet"), ("history_readable", "birdnet"), ("relay_service_active", "delivery")):
            value = checks.get(check)
            if value is False or value == "failed":
                problem("diagnostic-" + check, component, "diagnostic_check_failed",
                        "The saved Pi diagnostic did not pass its %s check; verify the current state before repairing." % check.replace("_", " "),
                        [evidence(check, "failed", value, "Passing Pi check", job.get("updated_at"), "saved_diagnostic")],
                        source="saved_diagnostic", at=job.get("updated_at"), checkpoint="diagnostics")

    report_locations = {}
    reports = diagnostics.get("reports") if isinstance(diagnostics.get("reports"), list) else []
    for report in reports[:30]:
        report = _mapping(report)
        details = _mapping(report.get("details"))
        component = details.get("component")
        station_id = report.get("station_id")
        if isinstance(component, str) and component in REPORT_COMPONENTS and isinstance(station_id, str) and len(station_id) <= 80:
            fingerprint = hashlib.sha256((station_id + ":" + component).encode()).hexdigest()[:24]
            report_locations.setdefault(fingerprint, REPORT_COMPONENTS[component])
    issues = diagnostics.get("issues") if isinstance(diagnostics.get("issues"), list) else []
    for issue in issues[:50]:
        issue = _mapping(issue)
        if issue.get("resolved") not in (False, 0):
            continue
        identifier = issue.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", identifier):
            continue
        # Do not redisplay a known old heartbeat warning after a newer positive
        # live observation, while the maintenance worker catches up.
        issue_time = _time(issue.get("last_seen"))
        newer_heartbeat = fresh and issue_time is not None and heartbeat >= issue_time
        if newer_heartbeat and (identifier == "pi-disconnected" or
                identifier == "audio-unavailable" and station.get("audio_status") == station.get("inference_status") == "healthy"):
            continue
        component = ISSUE_COMPONENTS.get(identifier, report_locations.get(identifier, "system"))
        severity = issue.get("severity") if issue.get("severity") in ("info", "warning", "error") else "warning"
        problem("issue-" + identifier, component, "unresolved_recorded_issue",
                issue.get("message") or "A recorded issue still needs review.",
                [evidence("recorded_issue", "unresolved", True, "Review or verify recovery; this is a recorded observation", issue.get("last_seen"), "recorded_issue")],
                severity=severity, source="recorded_issue", at=issue.get("last_seen"), checkpoint="maintenance")

    overall = "attention" if any(p["severity"] in ("warning", "error") for p in problems) else "working" if state in ("probing", "running", "cancelling") else "unverified"
    return redact({"schema_version": 1, "generated_at": generated, "overall": overall,
                   "components": list(components.values()), "problems": problems,
                   "limits": ["This summary reads existing evidence; it does not contact the Pi or perform a repair.",
                              "Saved diagnostics and commissioning checks are timestamped snapshots, not proof of current hardware health.",
                              "The browser must mark this view stale if it cannot refresh; an offline server cannot report its own outage.",
                              "A quiet garden is normal. Audio quality, a real bird, rendered pixels and reboot recovery need separate checks."]}, private_values)
