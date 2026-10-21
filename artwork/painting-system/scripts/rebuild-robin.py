#!/usr/bin/env python3
"""Rebuild the frozen, approved Robin fragment from this skill's own assets."""

import argparse
import base64
import hashlib
import json
from pathlib import Path


def build(package: Path) -> bytes:
    runtime = package / "assets" / "runtime"
    records = json.loads((runtime / "species-config.json").read_text())["species"]
    config = next(record for record in records if record["id"] == "robin")
    config["source"] = "robin"
    config["backgroundChroma"] = 40
    config["backgroundLuminance"] = 180
    configs = {"robin": config}
    sources = {
        "robin": "data:image/webp;base64,"
        + base64.b64encode((runtime / "robin-inline.webp").read_bytes()).decode()
    }
    text = (runtime / "study-template.html").read_text()
    replacements = {
        "/* __CONFIGS__ */": "const configs="
        + json.dumps(configs, separators=(",", ":"))
        + ";",
        "/* __OPENING_BUILDER__ */": (runtime / "opening-builder.js").read_text(),
        "/* __FINISH_BUILDER__ */": (runtime / "finish-builder.js").read_text(),
        "/* __MARK_RENDERER__ */": (runtime / "mark-renderer.js").read_text(),
        "/* __RETIME_ROBIN__ */": (runtime / "retime-robin.js").read_text(),
        "/* __LIVE_MARKS__ */": (runtime / "live-marks.js").read_text(),
        "/* __SOURCES__ */": json.dumps(sources, separators=(",", ":")),
    }
    for marker, value in replacements.items():
        if text.count(marker) != 1:
            raise ValueError(f"Missing or repeated marker: {marker}")
        text = text.replace(marker, value)
    text = text.replace(
        "}))).then(async()=>{", "}))).then(async()=>{\n      prepareLiveMarks();"
    )
    return text.encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    package = Path(__file__).resolve().parents[1]
    data = build(package)
    baseline = (
        package / "assets" / "benchmarks" / "robin-approved-75s.html"
    ).read_bytes()
    if data != baseline:
        raise SystemExit(
            "Rebuild differs from the approved baseline. No output written; "
            "inspect runtime/version changes before claiming reproduction."
        )
    if len(data) >= 1_000_000:
        raise SystemExit("Fragment exceeds the inline size limit.")
    output = args.output.expanduser().resolve()
    if output == package or package in output.parents:
        raise SystemExit("Choose an output outside this skill to preserve the baseline.")
    if output.exists() and not args.force:
        raise SystemExit("Output exists; choose a new path or pass --force.")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    print(json.dumps({
        "output": str(output),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "matches_approved_baseline": True,
    }))


if __name__ == "__main__":
    main()
