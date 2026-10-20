from pathlib import Path, PurePosixPath
import os,json,collections,subprocess,hashlib
import py7zr
ARCHIVE=Path('/work/input/FreeCAD_1.1.4-Windows-x86_64-py311.7z')
BASE=Path('/work/output/FreeCAD_1.1.4_images_20261020')
TMP=Path('/work/workspace/freecad_images_build')
BINARY_BASE=Path('/work/workspace/freecad_audit_20261020/extracted/FreeCAD_1.1.4-Windows-x86_64-py311')
SEVEN='/work/workspace/freecad_audit_20261020/tools/7zip/7zz'
BASE.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
IMGEXT={'.png','.svg','.svgz','.jpg','.jpeg','.gif','.bmp','.ico','.icns','.tiff','.tif','.xpm','.tga','.apng','.ppm','.pgm','.pnm','.exr','.dds','.hdr','.cur','.jfif','.jxl','.avif'}
MODEL_EXT={'.fcstd','.fcstd1'}
with py7zr.SevenZipFile(ARCHIVE) as z: entries=z.list()
imgs=[x for x in entries if not x.is_directory and PurePosixPath(x.filename).suffix.lower() in IMGEXT]
models=[x for x in entries if not x.is_directory and PurePosixPath(x.filename).suffix.lower() in MODEL_EXT]
print('images',len(imgs),'models',len(models),flush=True)
selected=imgs+models
targets=TMP/'target_names.txt'
targets.write_text('\n'.join(x.filename for x in selected)+'\n',encoding='utf-8')
args=[SEVEN,'x','-y','-bso0','-bsp0','-bse1',str(ARCHIVE),'-o'+str(TMP/'unpacked'),'-i@'+str(targets)]
r=subprocess.run(args,text=True,capture_output=True)
print('7z return',r.returncode,'stdout',r.stdout[:1000],'stderr',r.stderr[-1600:],flush=True)
if r.returncode:raise RuntimeError('Archive extraction failed')
items=[{'path':x.filename,'extension':PurePosixPath(x.filename).suffix.lower(),'size':x.uncompressed} for x in imgs]
(BASE/'loose_inventory.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
(BASE/'progress.json').write_text(json.dumps({'archive_images':len(imgs),'archive_models':len(models),'archive_image_bytes':sum(x.uncompressed for x in imgs),'by_extension':dict(collections.Counter(x['extension'] for x in items)), 'stage':'direct_and_models_extracted'},ensure_ascii=False,indent=2),encoding='utf-8')
print('EXTRACTED',len(list((TMP/'unpacked').rglob('*'))),'f',len(list((TMP/'unpacked').rglob('*.*'))),flush=True)
