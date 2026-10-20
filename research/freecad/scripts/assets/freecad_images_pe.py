from pathlib import Path
import sys,hashlib,json,struct,collections
sys.path.insert(0,'/work/workspace/freecad_audit_20261020/tools/python')
import pefile
OUT=Path('/work/output/FreeCAD_1.1.4_images_20261020/images/pe_embedded')
OUT.mkdir(parents=True,exist_ok=True)
NATIVE=Path('/work/workspace/freecad_images_build/natives/FreeCAD_1.1.4-Windows-x86_64-py311')
INSTALLER=Path('/work/input/FreeCAD_1.1.4-Windows-x86_64-py311-installer.exe')
FILES=sorted(set([*NATIVE.glob('lib/*.pyd'),*NATIVE.glob('bin/*.dll')]))
FILES.extend([Path('/work/workspace/freecad_audit_20261020/extracted/FreeCAD_1.1.4-Windows-x86_64-py311/bin/freecad.exe'),
Path('/work/workspace/freecad_audit_20261020/extracted/FreeCAD_1.1.4-Windows-x86_64-py311/FreeCAD.exe'),INSTALLER])
data_records=[];errors=[]
for p in FILES:
  if not p.exists():continue
  try:
    if p==INSTALLER:
        with p.open('rb') as f:raw=f.read(2*1024*1024)
        pe=pefile.PE(data=raw)
    else:pe=pefile.PE(str(p))
  except Exception as e:
    errors.append((str(p),str(e)));continue
  if not hasattr(pe,'DIRECTORY_ENTRY_RESOURCE'):continue
  name=p.name if p!=INSTALLER else 'NSIS_installer.exe'
  icon_blobs={}
  for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    tid=entry.id
    if tid not in (2,3,10,14,24):continue
    for x in (entry.directory.entries if hasattr(entry,'directory') else []):
      for leaf in (x.directory.entries if hasattr(x,'directory') else []):
        if not hasattr(leaf,'data'):continue
        size=leaf.data.struct.Size;rva=leaf.data.struct.OffsetToData
        if size<30 or size>20_000_000:continue
        raw=pe.get_data(rva,size)
        if len(raw)!=size:continue
        fid=f'{x.id if x.id is not None else x.name}_{leaf.id}'
        if tid==3:
            icon_blobs[x.id]=raw
            if raw[:8]==b'\x89PNG\r\n\x1a\n':
                data=raw;ext='.png'
            else:
                if len(raw)<40:continue
                width,height,planes,bpp=struct.unpack_from('<iiHH',raw,4)
                if width<1 or width>10000 or height<2 or height>10000:continue
                iw=width if width<256 else 0;ih=height//2 if height//2<256 else 0
                head=struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',iw,ih,0,0,max(planes,1),max(bpp,1),len(raw),22)
                data=head+raw;ext='.ico'
        elif tid==2:
            if len(raw)<40:continue
            header_size, width,height,planes,bpp=struct.unpack_from('<IiiHH',raw,0)
            if header_size<40 or header_size>512:continue
            ncolors=(1<<bpp) if bpp<=8 else 0
            offbits=14+header_size+4*ncolors
            data=b'BM'+struct.pack('<IHHI',len(raw)+14,0,0,offbits)+raw;ext='.bmp'
        elif raw.startswith(b'\x89PNG\r\n\x1a\n'):data=raw;ext='.png'
        elif raw.startswith(b'\xff\xd8\xff'):data=raw;ext='.jpg'
        elif raw.startswith((b'GIF89a',b'GIF87a')):data=raw;ext='.gif'
        elif raw.lstrip().startswith(b'<svg'):data=raw;ext='.svg'
        elif raw.startswith(b'RIFF') and raw[8:12]==b'WEBP':data=raw;ext='.webp'
        else:continue
        target=OUT/name/(f'TYPE{tid}_{fid}'+ext)
        target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes(data)
        data_records.append({'source':'PE_resource','path':'pe_embedded/'+name+'/'+target.name,'bytes':len(data),'extension':ext,'type':tid,'sha256':hashlib.sha256(data).hexdigest(),'input':str(p)})
  pe.close()
print('PE resource images',len(data_records),'types',dict(collections.Counter(a['type'] for a in data_records)),'modules',dict(collections.Counter(a['input'].split('/')[-1] for a in data_records).most_common(20)),flush=True)
evidence=OUT.parent.parent/'pe_embedded_inventory.json'
evidence.write_text(json.dumps({'records':data_records,'errors':errors},indent=2))
