#!/usr/bin/env python3
"""Build standalone painting pages from bundled, frozen 75-second studies.

Uses only Python's standard library. Never reads an external workspace, fetches
images, or regenerates artwork. Re-running is deterministic.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artwork"
SOURCES = {
    "garden-birds-approved-75s.html": "4f1f04b294e81adb236a1eef3ecc4875d2b0137b37b2ce046182d2ea394415ed",
    "goldfinch-approved-75s.html": "2b35e8b557e1736b852de2d1cbb51970aa4875b84891594879d7be576c447c8b",
}
BIRDS = [
    ("robin", "Robin", "Erithacus rubecula", ["European Robin"]),
    ("goldfinch", "Goldfinch", "Carduelis carduelis", ["European Goldfinch"]),
    ("blue-tit", "Blue tit", "Cyanistes caeruleus", ["Eurasian Blue Tit", "Parus caeruleus"]),
    ("blackbird", "Blackbird", "Turdus merula", ["Common Blackbird", "Eurasian Blackbird"]),
    ("wren", "Wren", "Troglodytes troglodytes", ["Eurasian Wren"]),
]

BRIDGE = r"""
<script>
(() => {
  'use strict';
  const root = document.querySelector('[data-songsketch-painting]');
  const species = document.body.dataset.species;
  let activeEvent = null, lastReportedTime = null;
  const send = value => { if (parent !== window) parent.postMessage(value, location.origin); };
  const ready = new Promise((resolve, reject) => {
    const began = performance.now();
    function check() {
      if (root.drawingStudy?.getState().loaded) return resolve(root.drawingStudy);
      if (performance.now() - began > 60000) return reject(new Error('Painting preparation timed out'));
      setTimeout(check, 50);
    }
    check();
  });
  async function play(eventId, elapsed = 0) {
    const study = await ready;
    activeEvent = String(eventId);
    lastReportedTime = null;
    study.playFrom(Math.max(0, Math.min(75, Number(elapsed) || 0)));
    send({type:'songsketch:started', event_id:activeEvent, species});
  }
  window.SongsketchPainting = {
    ready, play,
    async renderAt(seconds) { (await ready).renderAt(seconds); },
    async pause() { (await ready).pausePlayback(); },
    getState() { return root.drawingStudy?.getState() || {loaded:false}; }
  };
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || event.source !== parent) return;
    const data = event.data;
    if (!data || data.type !== 'songsketch:play' || !data.event_id) return;
    play(data.event_id, data.elapsed_seconds).catch(error => send({type:'songsketch:error', message:error.message}));
  });
  ready.then(() => send({type:'songsketch:ready', species})).catch(error => {
    document.body.dataset.failed = 'true';
    send({type:'songsketch:error', message:error.message});
  });
  function progress() {
    if (activeEvent) {
      const state = root.drawingStudy.getState();
      if (lastReportedTime === state.time) return;
      lastReportedTime = state.time;
      send({type:'songsketch:progress', event_id:activeEvent, seconds:state.time, duration_seconds:75, complete:state.time>=75});
    }
  }
  setInterval(progress, 200);
})();
</script>
"""


def standalone(fragment, bird_id):
    is_gold = bird_id == "goldfinch"
    root_id = "goldfinch-drawing-75" if is_gold else "garden-birds-completed-75"
    fragment = fragment.replace(f'<div id="{root_id}">', f'<div id="{root_id}" data-songsketch-painting>')
    # Filter only illustrative status marks AFTER the frozen retimer has run.
    # All bird/name/background strokes retain their original seed and schedule.
    needle = "for(const s of strokes)resample(s);"
    assert fragment.count(needle) == 1
    fragment = fragment.replace(needle, """// Live state comes from the server overlay, never from reference art.
      strokes=strokes.filter(s=>!['Singing now','Live ripple','handwritten Singing now','perspective live ripple'].includes(s.contextSection));
      """ + needle)
    api = "root.drawingStudy={"
    assert fragment.count(api) == 1
    fragment = fragment.replace(api, api + """
      playFrom(t){pause();firstPlay=false;redraw(clamp(t,0,D),true);if(time<D){playing=true;lastNow=performance.now();update();frameId=requestAnimationFrame(tick);}},
      pausePlayback(){pause();},
      annotationState(){return {bakedLiveMarks:strokes.filter(s=>/Singing now|live ripple/i.test(s.contextSection||'')).length};},
    """)
    # Production playback doesn't use Codex's optional widget persistence.
    start = fragment.index("    function save(){")
    end = fragment.index("\n", start)
    fragment = fragment[:start] + "    function save(){}" + fragment[end:]
    if not is_gold:
        assert "let species='wren'" in fragment
        fragment = fragment.replace("let species='wren'", f"let species='{bird_id}'")
        assert "state.bird:'wren'" in fragment
        fragment = fragment.replace("state.bird:'wren'", f"state.bird:'{bird_id}'")
    # Child painting continues locally during network interruptions. Hidden-tab
    # recovery is controlled by the outer display from authoritative start time.
    fragment = fragment.replace(" The corner status is an artwork example.", "")
    css = """html,body{margin:0;width:100%;height:100%;background:#f3eee5;overflow:hidden}
      [data-songsketch-painting]{width:100%;height:100%}
      .gd-choice,.gd-controls,.gd-feel,.gd-phase,.gf75-controls,.gf75-feel,.gf75-phase{display:none!important}
      .gd-art,.gf75-art{display:block!important;width:100%!important;height:100%!important}
      canvas{display:block;width:100%!important;height:100%!important;object-fit:contain}
    """
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{bird_id} · Songsketch painting</title><style>{css}</style></head><body data-species="{bird_id}">{fragment}{BRIDGE}</body></html>\n'


def main():
    ART.joinpath("animations").mkdir(parents=True, exist_ok=True)
    sources = {}
    for name, expected in SOURCES.items():
        data = (ART / "source" / name).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if expected and actual != expected:
            raise SystemExit(f"Frozen artwork source changed: {name}")
        sources[name] = {"sha256":actual, "bytes":len(data)}
    entries = []
    for bird_id, common, scientific, aliases in BIRDS:
        source = "goldfinch-approved-75s.html" if bird_id == "goldfinch" else "garden-birds-approved-75s.html"
        text = standalone((ART / "source" / source).read_text(), bird_id)
        target = ART / "animations" / f"{bird_id}.html"
        target.write_text(text)
        entries.append({
            "id":bird_id, "common_name":common, "scientific_name":scientific,
            "aliases":[common, scientific, *aliases], "approved":True,
            "artwork_approved":True, "animation_ready":True,
            "approval_basis":"User authorised reuse of the five existing 75-second paintings for the MVP.",
            "duration_seconds":75, "image_url":f"/artwork/thumbnails/{bird_id}.png",
            "animation_url":f"/artwork/animations/{bird_id}.html",
            "animation_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
            "source_file":f"source/{source}", "source_sha256":sources[source]["sha256"],
        })
    catalogue = {"version":1,"duration_seconds":75,"style_guide_url":"/artwork/style-guide.html","birds":entries}
    (ART / "catalogue.json").write_text(json.dumps(catalogue, indent=2)+"\n")
    (ART / "source-manifest.json").write_text(json.dumps(sources, indent=2)+"\n")
    print(f"Packaged {len(entries)} existing paintings. Source imagery and choreography preserved; illustrative live labels disabled.")


if __name__ == "__main__":
    main()
