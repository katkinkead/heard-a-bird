#!/usr/bin/env python3
"""Read-only package preflight; no private configuration or external services."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import sys
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FILES = (
    "README.md", "AGENTS.md", "CLAUDE.md", "guide/index.html", "guide/project.js",
    "guide/assets/guide.js", "guide/assets/installer-source.js",
    "static/display.html", "static/display.js", "static/dashboard.html", "pi/relay.py",
    "scripts/ai-bootstrap.py", "scripts/setup-assistant.py", "scripts/commission-pi.py",
    "scripts/github-install.py", "scripts/github-install.command", "scripts/github-install.zip",
    "songsketch/commissioning.py", "songsketch/setup_client.py", "songsketch/github_launcher.py",
    "docs/ai-setup.md", "docs/friend-start-here.md", "docs/artwork.md",
    "artwork/index.html", "artwork/catalogue.json", "artwork/registry.json",
    "artwork/import-snapshot.json", "artwork/style-guide.html", "artwork/animation-guide.md",
    "artwork/ui/index.html", "artwork/ui/status-marks.svg",
    "artwork/pending-animations/README.md", "artwork/tools/sync-fork.py",
)
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")


def check_package(root=ROOT):
    root = Path(root).resolve()
    art = root / "artwork"
    errors = []
    checked_hashes = set()
    if sys.version_info < (3, 9):
        errors.append("Python 3.9 or newer is required")
    try:
        ZoneInfo("Europe/London")
    except Exception:
        errors.append("Timezone database is missing (install tzdata on Linux)")

    def local_path(base, value, label):
        # Report field labels, never the supplied value or a path outside the package.
        if not isinstance(value, str) or not value or "\\" in value or any(ord(c) < 32 for c in value):
            errors.append("Invalid local path: " + label)
            return None
        parts = PurePosixPath(value)
        if parts.is_absolute() or any(p in (".", "..") for p in value.split("/")):
            errors.append("Non-portable local path: " + label)
            return None
        try:
            target = base.joinpath(*parts.parts)
            if base.resolve() not in target.resolve().parents:
                errors.append("Path leaves package: " + label)
                return None
            relative = target.relative_to(base)
            if any(base.joinpath(*relative.parts[:i]).is_symlink() for i in range(1, len(relative.parts) + 1)):
                errors.append("Symlinked asset is not portable: " + label)
                return None
            if not target.is_file():
                errors.append("Missing package file: " + label)
                return None
            return target
        except (OSError, RuntimeError, ValueError):
            errors.append("Cannot inspect package path: " + label)
            return None

    def artwork_url(value, label):
        if not isinstance(value, str):
            errors.append("Invalid artwork URL: " + label)
            return None
        try:
            url = urlsplit(value)
        except ValueError:
            errors.append("Invalid artwork URL: " + label)
            return None
        if url.scheme or url.netloc or url.query or url.fragment or not url.path.startswith("/artwork/"):
            errors.append("Artwork URL must stay inside /artwork/: " + label)
            return None
        return local_path(art, unquote(url.path[len("/artwork/"):]), label)

    def read_object(relative):
        path = local_path(root, relative, relative)
        if path is None:
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            errors.append("Unreadable package JSON: " + relative)
            return {}
        if not isinstance(value, dict):
            errors.append("Expected a JSON object: " + relative)
            return {}
        return value

    def entries(document, label):
        rows = document.get("birds")
        if not isinstance(rows, list) or not rows:
            errors.append("Expected a nonempty bird list: " + label)
            return {}
        found = {}
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not ID.fullmatch(row["id"]):
                errors.append("Invalid bird record at index %d: %s" % (index, label))
                continue
            identity = row["id"]
            if identity in found:
                errors.append("Duplicate bird ID in %s: %s" % (label, identity))
                continue
            found[identity] = row
        return found

    def verify_hash(path, expected, label):
        if not isinstance(expected, str) or not SHA256.fullmatch(expected):
            errors.append("Missing or invalid SHA-256: " + label)
            return
        if path is None:
            return
        key = (path, expected)
        if key in checked_hashes:
            return
        try:
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected:
                errors.append("SHA-256 mismatch: " + label)
            checked_hashes.add(key)
        except OSError:
            errors.append("Cannot read package asset: " + label)

    for relative in REQUIRED_FILES:
        local_path(root, relative, relative)
    catalogue = read_object("artwork/catalogue.json")
    registry = read_object("artwork/registry.json")
    playable = entries(catalogue, "catalogue")
    references = entries(registry, "registry")
    if type(registry.get("total_species")) is not int or registry["total_species"] != len(references):
        errors.append("Registry total_species does not match its bird records")
    guides = registry.get("guides")
    if not isinstance(guides, dict) or not guides:
        errors.append("Registry has no guide entry points")
    else:
        for index, value in enumerate(guides.values()):
            local_path(art, value, "registry guide %d" % index)
    artwork_url(catalogue.get("style_guide_url"), "catalogue style guide")

    completed = {}
    for identity, bird in references.items():
        label = "registry " + identity
        reference = local_path(art, bird.get("reference_path"), label + " reference")
        verify_hash(reference, bird.get("reference_sha256"), label + " reference")
        if type(bird.get("animation_ready")) is not bool:
            errors.append("animation_ready must be a boolean: " + label)
        if bird.get("animation_ready") is True:
            completed[identity] = bird
            if bird.get("animation_status") != "complete" or bird.get("final_art_accepted") is not True:
                errors.append("Completed animation lacks accepted art or complete status: " + identity)
            page = local_path(art, bird.get("animation_path"), label + " animation")
            verify_hash(page, bird.get("animation_sha256"), label + " animation")
        elif bird.get("animation_status") == "complete":
            errors.append("Complete animation is not marked ready: " + identity)

    if type(registry.get("completed_animation_count")) is not int or registry["completed_animation_count"] != len(completed):
        errors.append("Registry completed_animation_count does not match its ready entries")
    if set(playable) != set(completed):
        errors.append("Playback catalogue IDs differ from completed registry animations")

    for identity, bird in playable.items():
        label = "catalogue " + identity
        if any(bird.get(key) is not True for key in ("approved", "artwork_approved", "animation_ready")):
            errors.append("Playback entry is not approved and ready: " + identity)
        artwork_url(bird.get("image_url"), label + " image")
        page = artwork_url(bird.get("animation_url"), label + " animation")
        verify_hash(page, bird.get("animation_sha256"), label + " animation")
        ready = completed.get(identity)
        if ready is not None:
            if bird.get("scientific_name") != ready.get("scientific_name"):
                errors.append("Scientific name differs between catalogue and registry: " + identity)
            expected_url = "/artwork/" + ready.get("animation_path", "") if isinstance(ready.get("animation_path"), str) else None
            if bird.get("animation_url") != expected_url or bird.get("animation_sha256") != ready.get("animation_sha256"):
                errors.append("Animation path/hash differs between catalogue and registry: " + identity)

    try:
        db = sqlite3.connect(":memory:")
        try:
            db.execute("CREATE TABLE package_check (id INTEGER)")
        finally:
            db.close()
    except sqlite3.Error:
        errors.append("SQLite in-memory database check failed")
    return {"ok": not errors, "python": sys.version.split()[0],
            "approved_birds": len(playable), "reference_birds": len(references),
            "completed_animations": len(completed), "asset_hashes_checked": len(checked_hashes),
            "errors": list(dict.fromkeys(errors)),
            "not_checked": ["real Pi", "microphone", "reboot recovery", "SMTP delivery", "paid AI access"]}


if __name__ == "__main__":
    result = check_package()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)
