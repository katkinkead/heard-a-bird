#!/usr/bin/env python3
"""Import a stable completed fork collection for review, never live promotion.

The source is read only. Exact reference PNGs already in this package replace
duplicate inline PNGs; the unchanged renderer builds its authored marks locally.
Optional prepared-score caches and branch/gallery code are deliberately omitted.
"""
import argparse
import base64
import hashlib
import html
import json
from pathlib import Path
import re

ART = Path(__file__).resolve().parents[1]
RUNTIME = ("approved-retimers.js", "collection-retimer.js", "opening-builder.js",
           "finish-builder.js", "goldfinch-builder.js", "engine.js")
ORIGINALS = {"robin", "goldfinch", "blue-tit", "blackbird", "wren"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def page(identity, name):
    scripts = "".join('<script src="review-runtime/%s"></script>' % x for x in RUNTIME)
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s · Songsketch animation review</title><link rel="stylesheet" href="review-runtime/player.css"></head>
<body data-bird="%s"><main><canvas id="painting" width="1000" height="750" aria-label="%s painting"></canvas>
<p id="loading" role="status">Preparing the painting…</p></main>
<nav id="review-controls" hidden aria-label="Painting review controls"><span>Completed animation · fidelity review pending</span>
<button id="play" type="button">Play</button><input id="time" type="range" min="0" max="75" step="0.1" value="0" aria-label="Painting time">
<output id="clock">0 / 75 s</output><a href="../references/final-art/%s.png">Finished-art reference</a></nav>
<section id="review-checks" hidden><div aria-label="Painting checkpoints"><button data-time="0">0 s</button><button data-time="10">10 s</button><button data-time="40">40 s</button><button data-time="65">65 s</button><button data-time="75">75 s</button></div><details><summary>Local preparation and completion</summary><output id="painting-diagnostics">Preparing</output></details></section>
%s<script src="review-runtime/player.js"></script></body></html>
''' % (html.escape(name), identity, html.escape(name), identity, scripts)


def import_collection(source_root):
    source_root = Path(source_root).resolve()
    source = source_root / "animations"
    inputs = {}

    def read(relative):
        path = source / relative
        if path.is_symlink() or not path.is_file() or source not in path.resolve().parents:
            raise ValueError("Missing or nonportable source asset: " + relative)
        raw = path.read_bytes()
        inputs[relative] = {"sha256": digest(raw), "bytes": len(raw)}
        return raw

    build_raw = read("build-record.json")
    build = json.loads(build_raw)
    source_catalogue = json.loads(read("catalog.json"))
    registry = json.loads((ART / "registry.json").read_text())
    live_raw = (ART / "catalogue.json").read_bytes()
    live = json.loads(live_raw)
    live_ids = {b["id"] for b in live["birds"]}
    if live_ids != ORIGINALS:
        raise ValueError("Review importer expects the frozen five-bird live baseline")
    frozen = {b["animation_url"].removeprefix("/artwork/"): b["animation_sha256"] for b in live["birds"]}
    for path, sha in frozen.items():
        if digest((ART / path).read_bytes()) != sha:
            raise ValueError("Live baseline differs: " + path)
    records = {b["id"]: b for b in registry["birds"]}
    evidence = {b["id"]: b for b in build.get("birds", [])}
    species = source_catalogue.get("species", [])
    if set(evidence) != set(records) or {b["id"] for b in species} != set(records):
        raise ValueError("Completed source and reference library species differ")
    if build.get("totalBirds") != len(records) or source_catalogue.get("total") != len(records):
        raise ValueError("Source collection count is incomplete")
    if build.get("durationSeconds") != 75 or build.get("defaultFluidity") != .78:
        raise ValueError("Unexpected painting duration or material settings")
    outputs = {}
    for name in ("player.js", "player.css"):
        outputs["animations/review-runtime/" + name] = (ART / "animations/review-runtime" / name).read_bytes()
    for name in RUNTIME:
        rel = "runtime/" + name
        data = read(rel)
        if digest(data) != build.get("runtimeFiles", {}).get(rel):
            raise ValueError("Renderer changed since its completion record: " + name)
        outputs["animations/review-runtime/" + name] = data
    profile_provenance = []
    review_birds = list(live["birds"])
    for item in species:
        identity = item["id"]
        if not re.fullmatch(r"[a-z0-9-]+", identity):
            raise ValueError("Invalid species identity")
        proof = evidence[identity]
        if not (proof.get("preparedScoreVerified") is True and proof.get("finalMarksComplete") is True
                and proof.get("durationSeconds") == 75
                and proof.get("cachedFinalPixelComparison", {}).get("equivalent") is True):
            raise ValueError("Incomplete painting evidence: " + identity)
        profile_raw = read("species/" + identity + ".json")
        profile = json.loads(profile_raw)
        if profile.get("id") != identity or profile.get("scoreKey") != proof["scoreKey"] or profile.get("sourceSha256") != proof["sourceSha256"]:
            raise ValueError("Registration differs from completed score evidence: " + identity)
        profile_provenance.append({"id": identity, "profile_sha256": digest(profile_raw),
                                   "source_sha256": proof["sourceSha256"], "score_key": proof["scoreKey"],
                                   "original_retained": identity in ORIGINALS})
        if identity in ORIGINALS:
            continue
        record = records[identity]
        ref = ART / record["reference_path"]
        if digest(ref.read_bytes()) != record["reference_sha256"] or proof["sourceSha256"] != record["reference_sha256"]:
            raise ValueError("Completed animation uses a different accepted reference: " + identity)
        packet_raw = read("species/" + identity + ".js")
        packet_text = packet_raw.decode("utf-8").strip()
        prefix = "window.BirdsongAssets.receive("
        if not packet_text.startswith(prefix) or not packet_text.endswith(");"):
            raise ValueError("Unexpected species registration format: " + identity)
        packet = json.loads(packet_text[len(prefix):-2])
        if packet["config"] != profile:
            raise ValueError("Profile and runnable packet differ: " + identity)
        image = packet["source"]
        if not image.startswith("data:image/png;base64,") or digest(base64.b64decode(image.split(",", 1)[1], validate=True)) != record["reference_sha256"]:
            raise ValueError("Inline source is not the exact accepted PNG: " + identity)
        profile["sourceFile"] = "references/final-art/" + identity + ".png"
        profile.pop("scoreFile", None)  # unchanged engine's documented local mark-builder path
        packet["config"] = profile
        packet["source"] = "../references/final-art/" + identity + ".png"
        outputs["animations/species/" + identity + ".json"] = encoded(profile).encode()
        outputs["animations/species/" + identity + ".js"] = (prefix + json.dumps(packet, ensure_ascii=False, separators=(",", ":")) + ");\n").encode()
        outputs["animations/thumbnails/" + identity + ".webp"] = read("thumbnails/" + identity + ".webp")
        target = "animations/" + identity + ".html"
        outputs[target] = page(identity, record["common_name"]).encode()
        sha = digest(outputs[target])
        record.update(animation_status="completed_awaiting_review", animation_ready=False,
                      review_animation_ready=True, review_animation_path=target, review_animation_sha256=sha,
                      review_duration_seconds=75,
                      animation_review_note="Completed source snapshot; later fork feedback requests improved final clarity. Not promoted to connected playback.")
        aliases = list(dict.fromkeys(record.get("aliases", []) + [record["common_name"], record["scientific_name"]]))
        review_birds.append({"id": identity, "common_name": record["common_name"],
                            "scientific_name": record["scientific_name"], "aliases": aliases,
                            "approved": False, "artwork_approved": record["final_art_accepted"],
                            "animation_ready": True, "production_eligible": False,
                            "review_status": "completed_awaiting_review", "duration_seconds": 75,
                            "approval_basis": record["approval_basis"],
                            "image_url": "/artwork/animations/thumbnails/" + identity + ".webp",
                            "reference_url": "/artwork/" + record["reference_path"],
                            "animation_url": "/artwork/" + target, "animation_sha256": sha,
                            "source_sha256": record["reference_sha256"]})
    snapshot_id = digest(build_raw)[:16]
    proof_path = "provenance/animation-review/" + snapshot_id + "/build-record.source.json"
    outputs[proof_path] = build_raw
    outputs["provenance/animation-review/" + snapshot_id + "/catalog.source.json"] = encoded(source_catalogue).encode()
    registry["completed_review_animation_count"] = len(review_birds) - len(live_ids)
    registry["completed_asset_count"] = len(review_birds)
    registry["animation_review_snapshot"] = "animation-review-snapshot.json"
    outputs["registry.json"] = encoded(registry).encode()
    outputs["review-catalogue.json"] = encoded({
        "version": 1, "purpose": "isolated_simulator_and_visual_review_only", "production_catalogue": "catalogue.json",
        "duration_seconds": 75, "style_guide_url": "/artwork/style-guide.html", "snapshot_id": snapshot_id,
        "warning": "New animations await fidelity review. approved:false remains false; never load this catalogue for normal garden playback.",
        "birds": review_birds}).encode()
    # Validate the whole input set again before writing anything: an active fork
    # must not yield a mixture of old and newly rewritten registration/runtime.
    for relative, meta in inputs.items():
        if digest((source / relative).read_bytes()) != meta["sha256"]:
            raise ValueError("Source changed during snapshot; nothing imported: " + relative)
    snapshot = {"schema_version": 1, "snapshot_id": snapshot_id, "source_thread": "01a1540f-e061-7172-92cc-a50dd9c423ff",
                "source_completed_at": build["createdAt"], "imported_on": "2026-10-22",
                "state": "completed_awaiting_fidelity_review", "production_promoted": False,
                "completed_source_count": len(evidence), "original_live_preserved": sorted(live_ids),
                "new_review_count": len(review_birds) - len(live_ids), "source_build_record": proof_path,
                "review_context": {"completed_message_id": "msg_0d99fc4e87d7286b016ad8f2218898819189f4f16fa2556e90",
                    "later_user_message_id": "01a16222-ca4a-7ba1-bfe2-77f26bb7cadf",
                    "later_feedback": "Final result of some birds is off from approved artwork; fragmentation and lack of clarity.",
                    "shared_branch": "Not imported. Separate composition work is active."},
                "adaptations": ["Unmodified shared painting renderer and builders.",
                    "Duplicate embedded PNG bytes replaced by exact existing local PNG paths.",
                    "Absolute development sourceFile replaced by portable reference metadata.",
                    "Optional scoreFile omitted; same authored marks are compiled locally by the source renderer.",
                    "Same-origin player control wrapper added; no illustrative status marks added."],
                "validation_limit": "Source evidence establishes cache/generated-renderer equivalence, not visual identity to the approved raster. Local wrapper browser evidence is separate.",
                "profiles": profile_provenance,
                "source_files": [{"path": key, **value} for key, value in sorted(inputs.items())],
                "files": [{"path": key, "sha256": digest(value), "bytes": len(value)} for key, value in sorted(outputs.items()) if key not in ("registry.json", "review-catalogue.json")],
                "runtime_generated_marks": True, "prepared_score_cache_included": False}
    outputs["animation-review-snapshot.json"] = encoded(snapshot).encode()
    for relative, data in outputs.items():
        destination = ART / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    if (ART / "catalogue.json").read_bytes() != live_raw or any(digest((ART / p).read_bytes()) != sha for p, sha in frozen.items()):
        raise ValueError("Live baseline changed concurrently; inspect before continuing")
    return {"ok": True, "snapshot_id": snapshot_id, "live_unchanged": len(live_ids),
            "review_imported": len(review_birds) - len(live_ids), "bytes_written": sum(map(len, outputs.values()))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path, help="Read-only Birdsong authoring output folder")
    args = parser.parse_args()
    try:
        print(encoded(import_collection(args.source_root)), end="")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, "Review import stopped: %s\n" % exc)
