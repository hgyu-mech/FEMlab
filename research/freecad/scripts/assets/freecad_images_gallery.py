from pathlib import Path
import os,hashlib,collections,json,csv,time,html,re,zipfile,io,math
from urllib.parse import quote
from datetime import datetime,timezone
BASE=Path('/work/output/FreeCAD_1.1.4_images_20261020')
IMG=BASE/'images'
def category(path):
    s=path.split('/')
    if s[0]=='filesystem':
        if s[1:3]==['data','Gui']:return 'FreeCAD UI / themes'
        if s[1:3]==['data','Mod']:return 'Workbench templates'
        if len(s)>1 and s[1]=='Mod':return 'Workbench assets'
        if len(s)>1 and s[1]=='share':return 'Bundled documentation'
        if s[1:3]==['lib','qt6']:return 'Qt bundled libraries'
        if len(s)>1 and s[1]=='lib':return 'Bundled libraries'
        if len(s)>1 and s[1]=='bin':return 'Bundled runtime'
        return 'Other file assets'
    if s[0]=='qt_embedded':
        if s[1].lower().startswith('qt6'):return 'Qt binary resources'
        return 'FreeCAD compiled GUI'
    if s[0]=='fcstd':return 'FCStd embedded'
    if s[0]=='pe_embedded':return 'PE binary icons'
    if s[0]=='installer_extra':return 'Installer graphics'
    return 'Other'
assets=[]
for p in sorted(IMG.rglob('*')):
    if not p.is_file():continue
    rel=p.relative_to(IMG).as_posix()
    data=p.read_bytes()
    assets.append({'file':rel, 'name':p.name,'bytes':len(data),'type':p.suffix.lower().lstrip('.'),'category':category(rel),'sha256':hashlib.sha256(data).hexdigest()})
counts=collections.Counter(x['category'] for x in assets)
types=collections.Counter(x['type'] for x in assets)
hashes=collections.Counter(x['sha256'] for x in assets)
manifest={'source':'Uploaded FreeCAD 1.1.4 Windows portable + installer and embedded subresources','generated_at_utc':datetime.now(timezone.utc).isoformat(),'total_image_files':len(assets),'unique_sha256':len(hashes),'duplicate_image_instances':sum(n-1 for n in hashes.values()),'categories':dict(counts),'types':dict(types),'items':assets}
(BASE/'IMAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
with (BASE/'IMAGE_MANIFEST.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(assets[0]));w.writeheader();w.writerows(assets)
# Single local file-based browser application; no network requests, no fetch() needed
css="""
:root{--bg:#11171d;--surface:#1c252e;--text:#e9edf2;--muted:#a8b2bd;--stroke:#34424f;--accent:#73c6df}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif}
main{max-width:1480px;margin:auto;padding:22px}header{padding:22px 0 18px;display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px}
h1{font-size:26px;margin:0 0 5px;letter-spacing:-.5px}p{margin:0;color:var(--muted)}.stats{display:flex;flex-wrap:wrap;gap:8px;align-self:center}
.stat{padding:9px 12px;border:1px solid var(--stroke);border-radius:9px;color:var(--muted)}.stat b{color:var(--text)}
section.tools{position:sticky;top:0;z-index:10;background:var(--bg);padding:13px 0;border-bottom:1px solid var(--stroke)}
.search{width:100%;padding:11px 14px;background:var(--surface);border:1px solid var(--stroke);border-radius:9px;color:var(--text);font-size:15px}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:11px 0 1px}button{border:1px solid var(--stroke);background:var(--surface);color:var(--muted);border-radius:9px;padding:7px 11px;cursor:pointer}
button.active,button:hover{border-color:var(--accent);color:var(--text)}.row{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:5px;margin:18px 0 11px}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(164px,1fr));gap:12px}.card{border:1px solid var(--stroke);border-radius:11px;overflow:hidden;background:var(--surface);min-width:0}
.preview{height:156px;display:grid;place-items:center;background-color:#e6eaec;background-image:linear-gradient(45deg,#d7dce0 25%,transparent 25%),linear-gradient(-45deg,#d7dce0 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#d7dce0 75%),linear-gradient(-45deg,transparent 75%,#d7dce0 75%);background-size:20px 20px;background-position:0 0,0 10px,10px -10px,-10px 0}
.preview img{width:93%;height:93%;object-fit:contain}.meta{padding:9px 10px}.meta strong{display:block;overflow-wrap:anywhere;line-height:1.35;font-size:12px;max-height:2.7em;overflow:hidden}
.meta small{display:block;color:var(--muted);margin-top:5px}.origin{color:var(--muted);font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:block;margin-top:4px}
.more{margin:25px auto;display:block;font-weight:600;padding:13px 40px}.note{font-size:12px;margin:10px 0 20px}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
"""
# Use data URLs? no. emit safe JSON with escaping
jsdata=json.dumps([{'f':x['file'],'n':x['name'],'b':x['bytes'],'t':x['type'],'c':x['category']} for x in assets],ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
countsdata=json.dumps(dict(counts),ensure_ascii=False).replace('<','\\u003c')
index=f"""<!doctype html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FreeCAD 1.1.4 | Extracted Image Explorer</title><style>{css}</style></head>
<body><main><header><div><h1>FreeCAD 1.1.4 Image Explorer</h1><p>배포본에서 직접 추출한 이미지 · 원본 폴더 구조 유지 · 파일을 클릭하면 원본 이미지 열기</p></div>
<div class="stats"><span class="stat"><b>{len(assets):,}</b> assets</span><span class="stat"><b>{len(hashes):,}</b> unique SHA-256</span><span class="stat"><b>{len(counts)}</b> groups</span></div></header>
<section class="tools"><input class="search" id="search" autocomplete="off" placeholder="파일 이름 · 경로 검색 (예: FEM, Sketcher, png)">
<div id="chips" class="chips"></div></section>
<div class="row"><b id="status"></b><span style="color:var(--muted)">클릭하면 원본 크기로 열림 · 순차 표시 방식</span></div>
<div id="grid"></div><button class="more" id="more">더 보기</button>
<p class="note">모든 파일은 이 폴더에 저장되어 있어 오프라인에서 열립니다. 중복 경로/내장 리소스는 별도 보관합니다. 외부 library 및 third-party asset은 FreeCAD 배포본에 포함된 원본입니다.</p>
<script>
const ITEMS={jsdata},COUNTS={countsdata};
let active='모두',query='',start=0,matching=[];
const grid=document.getElementById('grid'),btn=document.getElementById('more'),status=document.getElementById('status');
const safePath=p=>'images/'+p.split('/').map(encodeURIComponent).join('/');
const humanSize=n=>n<1024?n+' B':n<1048576?(n/1024).toFixed(1)+' KB':(n/1048576).toFixed(2)+' MB';
const chips=document.getElementById('chips');
function buildChips(){{
  chips.replaceChildren(); [['모두',ITEMS.length],...Object.entries(COUNTS)].forEach(([name,count])=>{{
    let b=document.createElement('button');b.textContent=name+' ('+count.toLocaleString()+')';
    b.className=name===active?'active':'';b.onclick=()=>{{active=name;buildChips();refresh();}};
    chips.appendChild(b);
  }});
}}
function makeCard(x){{
 const card=document.createElement('div');card.className='card';
 const link=document.createElement('a');link.className='preview';link.href=safePath(x.f);link.target='_blank';link.rel='noopener';
 const im=document.createElement('img');im.loading='lazy';im.decoding='async';im.src=safePath(x.f);im.alt=x.n;
 im.onerror=()=>{{im.alt='Preview unsupported: '+x.t;}};link.appendChild(im);
 const info=document.createElement('div');info.className='meta';
 const title=document.createElement('strong');title.textContent=x.n;title.title=x.f;
 const sub=document.createElement('small');sub.textContent=x.t.toUpperCase()+' · '+humanSize(x.b);
 const loc=document.createElement('span');loc.className='origin';loc.textContent=x.f;loc.title=x.f;
 info.append(title,sub,loc);card.append(link,info);return card;
}}
function appendPage(){{
 const next=matching.slice(start,start+144);const frag=document.createDocumentFragment();
 next.forEach(x=>frag.appendChild(makeCard(x)));grid.append(frag);start+=next.length;
 status.textContent=matching.length.toLocaleString()+'개 중 '+start.toLocaleString()+'개 표시';
 btn.hidden=start>=matching.length;
}}
function refresh(){{
 query=document.getElementById('search').value.trim().toLocaleLowerCase();
 matching=ITEMS.filter(x=>(active==='모두'||x.c===active)&&(!query||(x.f+' '+x.c).toLocaleLowerCase().includes(query)));
 start=0;grid.replaceChildren();appendPage();
}}
document.getElementById('search').addEventListener('input',refresh);btn.onclick=appendPage;buildChips();refresh();
</script></main></body></html>"""
(BASE/'index.html').write_text(index,encoding='utf-8')
print('MANIFEST_DONE',len(assets),'categories',dict(counts),'types',dict(types),'dupes',manifest['duplicate_image_instances'],'html_bytes',len(index.encode()),flush=True)
