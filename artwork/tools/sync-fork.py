#!/usr/bin/env python3
"""Verify the portable snapshot; explicitly stage a completed animation handoff.

No network, execution of imported code, live-catalogue changes or automatic promotion.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile

ART = Path(__file__).resolve().parents[1]
SCHEMA = "songsketch-animation-handoff-v1"
HEX = re.compile(r"^[a-f0-9]{64}$")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    raw = path.read_bytes()
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("Manifest exceeds the 4 MiB limit")
    return raw, json.loads(raw.decode("utf-8"))


def safe_path(root, value):
    if not isinstance(value, str) or "\\" in value:
        raise ValueError("Manifest paths must be relative POSIX paths")
    part = PurePosixPath(value)
    if part.is_absolute() or not part.parts or any(x in (".", "..") for x in part.parts):
        raise ValueError("Manifest path escapes its source root")
    candidate = root.joinpath(*part.parts)
    if any(p.is_symlink() for p in [candidate] + list(candidate.parents) if p != root.parent):
        raise ValueError("Symlinked source paths are not imported")
    if root.resolve() not in candidate.resolve().parents:
        raise ValueError("Manifest path escapes its source root")
    return candidate


def verify_package(source=None):
    _, snapshot = read_json(ART / "import-snapshot.json")
    _, registry = read_json(ART / "registry.json")
    errors = []
    for row in snapshot["files"]:
        bundled = safe_path(ART, row["path"])
        if not bundled.is_file() or digest(bundled.read_bytes()) != row["sha256"]:
            errors.append("Packaged asset missing or changed: " + row["path"])
        if source is not None and row["origin"] == "fork":
            src = safe_path(source, row["source_path"])
            expected = row.get("source_sha256", row["sha256"])
            if not src.is_file() or digest(src.read_bytes()) != expected:
                errors.append("Source changed since snapshot: " + row["source_path"])
    for bird in registry["birds"]:
        ref = safe_path(ART, bird["reference_path"])
        if digest(ref.read_bytes()) != bird["reference_sha256"]:
            errors.append("Reference hash differs: " + bird["id"])
        if bird["animation_ready"]:
            page = safe_path(ART, bird["animation_path"])
            if digest(page.read_bytes()) != bird["animation_sha256"]:
                errors.append("Completed animation changed: " + bird["id"])
    return {"ok": not errors, "reference_species": len(registry["birds"]),
            "completed_animations": sum(b["animation_ready"] for b in registry["birds"]),
            "files_checked": len(snapshot["files"]), "errors": errors,
            "live_catalogue_modified": False}


def stage_animations(source, manifest_relative):
    manifest_path = safe_path(source, manifest_relative)
    raw, manifest = read_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA or manifest.get("status") != "complete":
        raise ValueError("Only a completed animation handoff manifest may be staged")
    for key, flag in (("validation", "complete"), ("approval", "accepted")):
        evidence = manifest.get(key, {})
        if not isinstance(evidence, dict) or evidence.get(flag) is not True or not isinstance(evidence.get("evidence"), str) or not evidence["evidence"].strip():
            raise ValueError("Handoff needs explicit " + key + " evidence")
    files = manifest.get("files")
    if not isinstance(files, list) or not files or len(files) > 2000:
        raise ValueError("Handoff must list 1–2000 files")
    _, registry = read_json(ART / "registry.json")
    known = {b["id"]: b for b in registry["birds"]}
    birds = manifest.get("birds")
    if not isinstance(birds, list) or not birds:
        raise ValueError("Handoff must identify its birds")
    bird_ids = []
    for bird in birds:
        if not isinstance(bird, dict):
            raise ValueError("Every bird must have a structured record")
        identity = bird.get("id")
        if identity not in known or identity in bird_ids or known[identity]["animation_ready"]:
            raise ValueError("Unknown, duplicate or already-completed bird in handoff")
        if bird.get("duration_seconds") != 75:
            raise ValueError("This collection requires 75-second animation evidence")
        bird_ids.append(identity)
    planned = []
    seen = set()
    total = 0
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("Every handoff file needs a relative path")
        rel = entry.get("path")
        if rel in seen:
            raise ValueError("Duplicate handoff file path")
        seen.add(rel)
        path = safe_path(source, rel)
        expected = entry.get("sha256", "")
        size = entry.get("bytes")
        if not isinstance(expected, str) or not HEX.fullmatch(expected) or type(size) is not int or size < 0:
            raise ValueError("Every file needs an exact SHA-256 and byte size")
        total += size
        if total > 2 * 1024 ** 3:
            raise ValueError("Handoff exceeds 2 GiB; review release packaging first")
        if not path.is_file() or path.stat().st_size != size or digest(path.read_bytes()) != expected:
            raise ValueError("Missing, incomplete or changed handoff file: " + rel)
        planned.append((path, rel, expected))
    if manifest_path.read_bytes() != raw:
        raise ValueError("Manifest changed during validation; wait for a finished handoff")
    pending = ART / "pending-animations"
    pending.mkdir(exist_ok=True)
    target = pending / digest(raw)[:16]
    if target.exists():
        if (target / "handoff-manifest.json").read_bytes() != raw:
            raise ValueError("Existing staging directory has different evidence")
        for _, rel, expected in planned:
            copy = safe_path(target / "files", rel)
            if not copy.is_file() or digest(copy.read_bytes()) != expected:
                raise ValueError("Existing staging directory is incomplete or changed")
        return {"ok": True, "already_staged": True, "staged_path": str(target.relative_to(ART)), "birds": bird_ids, "promoted": False}
    temp = Path(tempfile.mkdtemp(prefix=".staging-", dir=pending))
    try:
        for path, rel, expected in planned:
            data = path.read_bytes()
            if digest(data) != expected:
                raise ValueError("Source changed during copy: " + rel)
            dest = temp / "files" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        if manifest_path.read_bytes() != raw:
            raise ValueError("Manifest changed during copy; no handoff staged")
        (temp / "handoff-manifest.json").write_bytes(raw)
        (temp / "README.txt").write_text("Staged for integration review only. This directory is not served by the live catalogue.\nCheck the actual final frame, timing, branch layers and player contract before promotion.\n")
        temp.rename(target)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return {"ok": True, "staged_path": str(target.relative_to(ART)), "birds": bird_ids,
            "files": len(planned), "bytes": total, "promoted": False,
            "live_catalogue_modified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, help="Explicit local birdsong-art source; never inferred from a developer home directory")
    parser.add_argument("--stage-animations", action="store_true", help="Stage a complete handoff without promoting it")
    parser.add_argument("--manifest", help="Manifest path relative to --source-root")
    args = parser.parse_args()
    if args.source_root is not None:
        if args.source_root.is_symlink() or not args.source_root.is_dir():
            parser.error("Source root must be a real local directory")
        args.source_root = args.source_root.resolve()
    if args.stage_animations and (args.source_root is None or not args.manifest):
        parser.error("Staging needs --source-root and --manifest")
    if args.manifest and not args.stage_animations:
        parser.error("--manifest is only used with --stage-animations")
    try:
        result = stage_animations(args.source_root, args.manifest) if args.stage_animations else verify_package(args.source_root)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "live_catalogue_modified": False}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
