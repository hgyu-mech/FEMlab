from pathlib import Path, PurePosixPath
import csv,json,zipfile,shutil,hashlib,collections,os
BASE=Path('/work/output/FreeCAD_1.1.4_images_20261020')
SRC=Path('/work/workspace/freecad_images_build/unpacked/FreeCAD_1.1.4-Windows-x86_64-py311')
OUT=BASE/'images';OUT.mkdir(exist_ok=True)
inventory=json.loads((BASE/'loose_inventory.json').read_text())
records=[]
for i,item in enumerate(inventory):
    short=PurePosixPath(item['path']).parts[1:]
    rel=Path('filesystem').joinpath(*short)
    inp=SRC.joinpath(*short)
    target=OUT/rel
    if not inp.is_file(): raise RuntimeError('Missing: '+str(inp))
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(inp,target)
    if target.stat().st_size!=item['size']:raise RuntimeError('Size mismatch: '+str(inp))
    parts=short
    if len(parts)>2 and parts[:2]==('data','Gui'):cat='FreeCAD core GUI'
    elif len(parts)>2 and parts[:2]==('data','Mod'):cat='FreeCAD modules'
    elif parts[0]=='Mod':cat='Workbench source assets'
    elif parts[0]=='share':cat='Third-party docs'
    elif parts[0]=='lib':cat='Bundled libraries'
    elif parts[0]=='bin':cat='Bundled runtime'
    else:cat='Other'
    records.append({'source':'archive_loose','path':str(rel).replace(os.sep,'/'),'original_archive_path':item['path'],'extension':item['extension'],'bytes':item['size'],'category':cat,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
print('DIRECT copied',len(records),flush=True)
IMGEXT={'.png','.svg','.svgz','.jpg','.jpeg','.gif','.bmp','.ico','.icns','.tiff','.tif','.xpm','.tga','.apng','.ppm','.pgm','.pnm','.exr','.dds','.hdr','.cur','.jfif','.jxl','.avif'}
models=list(SRC.rglob('*.FCStd')) + list(SRC.rglob('*.fcstd')) + list(SRC.rglob('*.FCSTD'))
# suffix-insensitive and unique
models=list({str(m):m for m in models}.values())
nested=0;nonimage_count=0;corrupt=[]
for p in models:
    try:
        with zipfile.ZipFile(p) as z:
            err=z.testzip()
            if err: corrupt.append({'file':str(p),'problem':'bad member '+err}); continue
            for obj in z.infolist():
                if obj.is_dir():continue
                relobj=PurePosixPath(obj.filename)
                # Only images, not entire model!
                if relobj.suffix.lower() not in IMGEXT:continue
                data=z.read(obj)
                rel=Path('fcstd')/p.relative_to(SRC)/Path(*relobj.parts)
                target=OUT/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
                records.append({'source':'FCStd_member','path':str(rel).replace(os.sep,'/'),'original_archive_path':str(p.relative_to(SRC))+'::'+obj.filename,'extension':relobj.suffix.lower(),'bytes':len(data),'category':'FCStd embedded images','sha256':hashlib.sha256(data).hexdigest()})
                nested+=1
    except Exception as e:
        corrupt.append({'file':str(p),'problem':str(e)})
print('FCSTD',len(models),'nested images',nested,'bad',corrupt[:12],flush=True)
(BASE/'manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
(BASE/'stage2_summary.json').write_text(json.dumps({'loose':len(inventory),'models':len(models),'nested':nested,'bad':corrupt,'images_total':len(records),'image_bytes':sum(x['bytes'] for x in records)},ensure_ascii=False,indent=2),encoding='utf-8')
print('CATEGORIES',dict(collections.Counter(x['category'] for x in records)),flush=True)
