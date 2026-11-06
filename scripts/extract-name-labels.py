#!/usr/bin/env python3
"""Extract existing reference name strokes without changing source art or scores."""
import base64,gzip,json,hashlib,html
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'artwork/branch/name-labels-v1';out.mkdir(exist_ok=True)
manifest={}
for bird in json.loads((root/'artwork/branch/manifest.json').read_text())['birds']:
    id=bird['id'];source=root/f'artwork/branch/animations/clarity-v3/scores/{id}.js'
    raw=source.read_bytes();packet=json.loads(gzip.decompress(base64.b64decode(raw.decode().split('"',6)[5])))
    strokes=[s for s in packet['strokes'] if s.get('layer')=='name']
    assert strokes,(id,'missing name')
    assert all(s.get('finishStyle')=='reference' for s in strokes),(id,'unexpected renderer')
    x0=min(p[0]-s['width']/2 for s in strokes for p in s['points'])-1
    y0=min(p[1]-s['width']/2 for s in strokes for p in s['points'])-1
    x1=max(p[0]+s['width']/2 for s in strokes for p in s['points'])+1
    y1=max(p[1]+s['width']/2 for s in strokes for p in s['points'])+1
    paths=[]
    for s in strokes:
        d='M'+' L'.join(f'{x},{y}' for x,y in s['points'])
        color=','.join(str(int(v+0.5)) for v in s['color'])
        paths.append(f'<path d="{d}" stroke="rgb({color})" stroke-width="{s["width"]}" opacity="{s["opacity"]}"/>')
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{x1-x0}" height="{y1-y0}" viewBox="{x0} {y0} {x1-x0} {y1-y0}" fill="none" stroke-linecap="round" stroke-linejoin="round"><title>{html.escape(bird["common_name"])}</title>'+''.join(paths)+'</svg>\n'
    (out/f'{id}.svg').write_text(svg)
    manifest[id]={'name':bird['common_name'],'width':x1-x0,'height':y1-y0,'strokes':len(strokes),'source':str(source.relative_to(root)),'source_sha256':hashlib.sha256(raw).hexdigest(),'svg_sha256':hashlib.sha256(svg.encode()).hexdigest()}
    print(id,len(strokes),flush=True)
    del packet,raw,strokes
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'manifest.js').write_text('window.BirdNameLabels = '+json.dumps({id:{k:v for k,v in b.items() if k in ('name','width','height')} for id,b in manifest.items()})+';\n')
