#!/usr/bin/env python3
"""Inspect or explicitly configure the named Pi 5 production power profile.

Read docs/production.md first. This does not measure total supply current,
certify PoE hardware, change EEPROM, reboot, or run during normal commissioning.
"""
import argparse
import errno
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
import uuid

PROFILE = "waveshare-25w-pi5"
CONFIG = Path("/boot/firmware/config.txt")
MODEL = Path("/proc/device-tree/model")
POWER = Path("/proc/device-tree/chosen/power")
BEGIN = "# BEGIN SONGSKETCH PI5 USB POWER"
END = "# END SONGSKETCH PI5 USB POWER"
BLOCK = BEGIN + "\n[all]\n[pi5]\nusb_max_current_enable=1\n[all]\n" + END + "\n"


class PowerError(Exception):
    def __init__(self, code, message):
        super().__init__(message); self.code = code


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=5, check=False,
                                env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C"})
        return result.stdout.strip()[:4096] if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired): return None


def throttle_flags(raw):
    match = re.fullmatch(r"throttled=(0x[0-9a-fA-F]+)", raw or "")
    if not match: return None
    value = int(match.group(1), 16)
    names = {0: "undervoltage_now", 1: "frequency_capped_now", 2: "throttled_now",
             3: "soft_temperature_limit_now", 16: "undervoltage_occurred",
             17: "frequency_capping_occurred", 18: "throttling_occurred",
             19: "soft_temperature_limit_occurred"}
    return {name: bool(value & (1 << bit)) for bit, name in names.items()}


def inspect(model_path=MODEL, power_path=POWER, runner=command):
    try: model = model_path.read_text().rstrip("\0\n")[:120]
    except OSError: model = None
    values = {}
    for name in ("max_current", "usb_max_current_enable", "usb_over_current_detected", "reset_event"):
        try:
            data = (power_path / name).read_bytes()
            values[name] = int.from_bytes(data, "big") if len(data) == 4 else None
        except OSError: values[name] = None
    throttle = runner(["/usr/bin/vcgencmd", "get_throttled"])
    config = runner(["/usr/bin/vcgencmd", "get_config", "usb_max_current_enable"])
    match = re.fullmatch(r"usb_max_current_enable=([01])", config or "")
    active = values["usb_max_current_enable"]
    if active not in (0, 1): active = int(match.group(1)) if match else None
    temp = runner(["/usr/bin/vcgencmd", "measure_temp"])
    match = re.fullmatch(r"temp=([0-9]+(?:\.[0-9]+)?)'C", temp or "")
    adc = runner(["/usr/bin/vcgencmd", "pmic_read_adc"])
    # Supply voltage only: other PMIC ADC readings cannot establish USB/total load.
    voltage = re.search(r"\bEXT5V_V\s+volt\(([0-9.]+)V\)", adc or "")
    return {"model": model, "pi5": bool(re.match(r"^Raspberry Pi 5 Model B(?:\s|$)", model or "")),
            "device_tree_power": values, "usb_high_limit_active": active,
            "throttle": throttle_flags(throttle),
            "temperature_c": float(match.group(1)) if match else None,
            "input_voltage_v": float(voltage.group(1)) if voltage else None,
            "total_current_measured": False, "hardware_load_verified": False}


def proposed_config(original):
    """Preserve unrelated text; refuse includes or pre-existing power decisions."""
    try: text = original.decode("utf-8")
    except UnicodeError: raise PowerError("config_encoding", "The boot configuration is not UTF-8; review it manually.") from None
    if "\0" in text: raise PowerError("config_encoding", "The boot configuration contains invalid text.")
    count = (text.count(BEGIN), text.count(END))
    managed = count == (1, 1) and BLOCK in text
    if count != (0, 0) and not managed:
        raise PowerError("managed_block_changed", "The Songsketch power block was edited; preserve it and review the changes.")
    remainder = text.replace(BLOCK, "", 1) if managed else text
    for raw in remainder.splitlines():
        line = raw.split("#", 1)[0].strip()
        if re.match(r"include(?:\s|=)", line, re.I):
            raise PowerError("included_config", "This boot configuration includes another file. Review power settings across includes before changing it.")
        if re.match(r"usb_max_current_enable\s*=", line, re.I):
            raise PowerError("existing_power_setting", "An existing USB power setting belongs to another setup. It was preserved; review it manually.")
    if managed: return original
    newline = "" if not text or text.endswith("\n") else "\n"
    return (text + newline + "\n" + BLOCK).encode()


def read_config(path=CONFIG):
    try:
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise PowerError("unsafe_config", "The boot configuration path contains a symbolic link; no change was made.")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode): raise PowerError("unsafe_config", "The boot configuration is not a regular file.")
            raw = source.read(262145)
        if len(raw) > 262144: raise PowerError("config_too_large", "The boot configuration needs manual review.")
        return raw, stat.S_IMODE(info.st_mode)
    except OSError: raise PowerError("config_unavailable", "Cannot read /boot/firmware/config.txt; this helper requires Raspberry Pi OS's boot layout.") from None


def assess(snapshot, supply_verified=False, usb_budget_ma=None, total_budget_ma=None, usb_boot=False):
    reasons = []
    if not snapshot.get("pi5"): reasons.append("Confirm this is a Raspberry Pi 5 Model B.")
    if not supply_verified:
        reasons.append("Verify the exact Waveshare 5V5A splitter, U-PoE+ chain, cable, surge compatibility and available power under the intended load.")
    if usb_budget_ma is None or not 0 <= usb_budget_ma <= 1600:
        reasons.append("Supply the maximum combined USB peripheral budget (0–1600mA), from actual device ratings.")
    if total_budget_ma is None or not 0 < total_budget_ma <= 5000 or (usb_budget_ma is not None and total_budget_ma <= usb_budget_ma):
        reasons.append("Supply the whole Pi + USB + fan/accessory budget, including startup margin; it must fit the verified supply and be at most5000mA.")
    if snapshot.get("usb_high_limit_active") is None:
        reasons.append("The active USB current limit could not be read; investigate firmware diagnostics before forcing it.")
    flags = snapshot.get("throttle")
    if flags is None:
        reasons.append("Power/throttle telemetry is unavailable; inspect the Pi before increasing its USB allowance.")
    elif any(flags.values()):
        reasons.append("Power or throttling flags are present; investigate power/cooling and repeat diagnostics after a deliberate reboot and load check.")
    if snapshot.get("device_tree_power", {}).get("usb_over_current_detected"):
        reasons.append("USB over-current was recorded during boot; inspect peripherals and cabling before proceeding.")
    necessary = (usb_budget_ma is not None and usb_budget_ma > 600) or usb_boot
    return {"profile": PROFILE, "ready_to_change": not reasons,
            "override_needed_for_declared_load": necessary,
            "usb_budget_ma": usb_budget_ma, "total_budget_ma": total_budget_ma,
            "supply_verification": "operator_attested" if supply_verified else "not_verified",
            "next_actions": reasons,
            "note": "This raises the USB allowance to1.6A; it does not create power or verify the outdoor installation."}


def write_with_backup(path, original, replacement, mode):
    if original == replacement: return None
    # Recheck just before replacement, rather than overwrite a concurrent editor.
    if read_config(path)[0] != original:
        raise PowerError("config_changed", "The boot configuration changed during review; no change was made.")
    backup = path.with_name(path.name + ".songsketch-power-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8] + ".bak")
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "wb") as out:
        out.write(original); out.flush(); os.fsync(out.fileno())
    fd, name = tempfile.mkstemp(prefix=".songsketch-power-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(replacement); out.flush(); os.fsync(out.fileno()); os.fchmod(out.fileno(), mode)
        if read_config(path)[0] != original:
            raise PowerError("config_changed", "The boot configuration changed during backup; no change was made.")
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            try: os.fsync(directory)
            except OSError as exc:
                if exc.errno != errno.EINVAL: raise
        finally: os.close(directory)
    finally:
        if os.path.exists(name): os.unlink(name)
    return str(backup)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true", help="Read-only proposed configuration and missing evidence")
    mode.add_argument("--diagnose", action="store_true", help="Read-only power and thermal evidence")
    mode.add_argument("--apply", action="store_true", help="Apply this production setting with backup; never reboot")
    parser.add_argument("--profile", choices=[PROFILE], default=PROFILE)
    parser.add_argument("--supply-verified", action="store_true", help="Operator has verified this exact PoE chain's supply capacity; not an automatic hardware test")
    parser.add_argument("--usb-budget-ma", type=int)
    parser.add_argument("--total-budget-ma", type=int)
    parser.add_argument("--usb-boot", action="store_true", help="USB boot is required and its peripheral draw is included in the budget")
    args = parser.parse_args(argv)
    lock = None
    try:
        if args.apply:
            if os.geteuid() != 0: raise PowerError("root_required", "Apply requires sudo on the target Pi; plan and diagnose are read-only.")
            lock = os.open("/run/songsketch-power.lock", os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
            try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise PowerError("power_update_running", "Another production power change is running.") from None
        snapshot = inspect()
        if args.diagnose:
            print(json.dumps({"status": "diagnostic", "checks": snapshot})); return 0
        plan = assess(snapshot, args.supply_verified, args.usb_budget_ma, args.total_budget_ma, args.usb_boot)
        original, filemode = read_config(CONFIG)
        replacement = proposed_config(original)
        plan.update(checks=snapshot, config=str(CONFIG), proposed_block=BLOCK, changed=False,
                    reboot_required=False, status="plan")
        if args.apply:
            if not plan["ready_to_change"]:
                plan["status"] = "needs_input"; print(json.dumps(plan)); return 2
            if not plan["override_needed_for_declared_load"] or snapshot["usb_high_limit_active"] == 1:
                plan.update(status="unchanged", message="No override is needed for this declared load or the high USB limit is already active.")
            else:
                backup = write_with_backup(CONFIG, original, replacement, filemode)
                plan.update(status="configured" if backup else "unchanged", changed=bool(backup), backup=backup,
                            reboot_required=True, message="The boot setting is ready. Reboot deliberately, then repeat diagnostics and the real BirdNET load test.")
        print(json.dumps(plan)); return 0
    except PowerError as exc:
        print(json.dumps({"status": "needs_input", "code": exc.code, "message": str(exc), "changed": False})); return 2
    except OSError:
        print(json.dumps({"status": "failed", "code": "filesystem_error", "message": "Power configuration could not finish. Inspect config.txt and any timestamped backup before retrying; no reboot was attempted."})); return 1
    finally:
        if lock is not None: os.close(lock)


if __name__ == "__main__": raise SystemExit(main())
