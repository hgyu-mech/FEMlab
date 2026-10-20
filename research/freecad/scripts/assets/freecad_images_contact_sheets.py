from pathlib import Path
import os,io,json,time,math,re,collections
from PIL import Image,ImageDraw,ImageFont,ImageOps
import cairosvg
B=Path('/work/output/FreeCAD_1.1.4_images_20261020')
IM=B/'images';DEST=B/'contact_sheets';DEST.mkdir(exist_ok=True)
ITEMS=json.loads((B/'IMAGE_MANIFEST.json').read_text())['items']
W,H=124,131;IC=100;COLS=12;ROWS=10;PER=COLS*ROWS
font=ImageFont.load_default()
count_ok=0;count_fail=0;fails=[];cache={}
def thumbnail(rec):
  global count_ok,count_fail
  digest=rec['sha256']
  if digest in cache:return cache[digest].copy() if cache[digest] else None
  p=IM/rec['file']
  try:
    if rec['type'] in ('svg','svgz'):
      txt=p.read_bytes()
      # Do not follow external resources from bundled SVGs during report generation.
      if re.search(rb'<image\b|(?:xlink:)?href\s*=\s*["\x27](?:https?:|file:|\.\./)|url\(\s*["\x27]?(?:https?:|file:)',txt,re.I):
        raise ValueError('external or embedded image reference; see gallery original')
      raw=cairosvg.svg2png(bytestring=txt,output_width=96,output_height=96)
      image=Image.open(io.BytesIO(raw))
    else:
      image=Image.open(p)
    image.seek(0)
    image.load()
    image=ImageOps.contain(image.convert('RGBA'),(IC,IC),Image.Resampling.LANCZOS)
    count_ok+=1
    if len(cache)<4000:cache[digest]=image.copy()
    return image
  except Exception as e:
    count_fail+=1
    if len(fails)<100:fails.append({'file':rec['file'],'error':str(e)[:150]})
    cache[digest]=None
    return None
def card(draw,mosaic,rec,index,x,y):
    draw.rectangle((x+1,y+1,x+W-2,y+H-2),fill=(246,247,249),outline=(211,217,224),width=1)
    im=thumbnail(rec)
    if im:
      px=x+(W-im.width)//2;py=y+5+(IC-im.height)//2
      mosaic.paste(im,(px,py),im)
    else:
      draw.text((x+20,y+38),'NO PREVIEW',fill=(168,65,65),font=font)
    name=rec['name']
    if len(name)>19:name=name[:16]+'...'
    draw.text((x+5,y+107),name,fill=(22,31,40),font=font)
    draw.text((x+5,y+120),str(index)+' · '+rec['type'].upper(),fill=(101,112,122),font=font)
groups=collections.OrderedDict()
fem=[]
for rec in ITEMS:
  groups.setdefault(rec['category'],[]).append(rec)
  if rec['file'].startswith('qt_embedded/FemGui.pyd/') or rec['file'].startswith('filesystem/Mod/Fem/'):
    fem.append(rec)
groups=collections.OrderedDict([('FEM Workbench',fem),*groups.items()])
links=[]
started=time.monotonic()
for label,lst in groups.items():
  if not lst:continue
  for pagei in range(math.ceil(len(lst)/PER)):
    page=lst[pagei*PER:(pagei+1)*PER]
    png_name=re.sub(r'[^A-Za-z0-9]+','_',label).strip('_')+'_'+str(pagei+1).zfill(2)+'.png'
    mosaic=Image.new('RGB',(COLS*W,ROWS*H),(221,228,235))
    d=ImageDraw.Draw(mosaic)
    for k,rec in enumerate(page):
        x=k%COLS*W;y=k//COLS*H
        card(d,mosaic,rec,pagei*PER+k+1,x,y)
    mosaic.save(DEST/png_name,optimize=True)
    links.append({'category':label,'page':pagei+1,'file':png_name,'items':len(page),'bytes':(DEST/png_name).stat().st_size})
    print('SHEET',label,pagei+1,'items',len(page),'counted',count_ok,'not-rendered',count_fail,'elapsed',round(time.monotonic()-started,1),flush=True)
(DEST/'preview_index.json').write_text(json.dumps({'items':links,'failed_preview_count':count_fail,'examples':fails,'successful_render_operations':count_ok},ensure_ascii=False,indent=2))
css="body{font:15px system-ui;background:#11171d;color:#eceff4;padding:30px;max-width:1020px;margin:auto}a{color:#83cad9;text-decoration:none}img{display:block;max-width:100%;border:1px solid #42515e;margin:12px 0 35px}nav a{display:inline-block;margin:0 12px 12px 0;padding:8px;background:#26333e;border-radius:5px}p{color:#b3bac5}"
links_html=''.join('<li><a href="'+z['file']+'">'+z['category']+' '+str(z['page'])+' ('+str(z['items'])+')</a></li>' for z in links)
(DEST/'INDEX.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>FreeCAD contact sheets</title><style>'+css+'</style><h1>FreeCAD 1.1.4 Contact Sheets</h1><p>모든 이미지 원본은 상위 images/ 폴더에 있습니다. 원본을 검색하려면 <a href="../index.html">이미지 갤러리</a>를 여세요. 미리보기를 렌더링하지 못한 SVG라도 원본 파일은 포함되어 있습니다.</p><ol>'+links_html+'</ol>'+'</html>',encoding='utf8')
print('FINISHED total_sheets',len(links),'ok',count_ok,'preview_fail',count_fail,'elapsed_sec',round(time.monotonic()-started,2),flush=True)
