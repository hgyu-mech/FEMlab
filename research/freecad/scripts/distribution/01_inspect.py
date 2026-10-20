from pathlib import Path
import json,zipfile,hashlib,collections,xml.etree.ElementTree as ET,re,sys
sys.path.insert(0,'/work/workspace/freecad_audit_20261020/tools/python')
import pefile
ROOT=Path('/work/workspace/freecad_audit_20261020/extracted/FreeCAD_1.1.4-Windows-x86_64-py311')
OUT=Path('/work/output/FreeCAD_1.1.4_audit_20261020/evidence')
def save(name,x): (OUT/name).write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf8')
def text(b):return b.decode('utf8','replace') if isinstance(b,bytes) else str(b)
# Analyze original PE files without loading or running them.
summary=[]
for rel in ['FreeCAD.exe','bin/freecad.exe','bin/FreeCADApp.dll','bin/FreeCADGui.dll','lib/Fem.pyd','lib/FemGui.pyd','lib/Part.pyd','lib/StartGui.pyd','bin/ccx.exe','bin/gmsh.exe']:
 p=ROOT/rel
 if not p.exists():continue
 pe=pefile.PE(str(p),fast_load=False)
 imports={text(e.dll):[{'name':text(s.name) if s.name else '#'+str(s.ordinal),'iat_va':hex(s.address)} for s in e.imports] for e in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[])}
 exports=[{'name':text(s.name) if s.name else '#'+str(s.ordinal),'rva':hex(s.address)} for s in getattr(getattr(pe,'DIRECTORY_ENTRY_EXPORT',None),'symbols',[])]
 version={}
 for fi in getattr(pe,'FileInfo',[]):
  for v in fi:
   for st in getattr(v,'StringTable',[]):version.update({text(k):text(val) for k,val in st.entries.items()})
 d={'path':rel,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'machine':hex(pe.FILE_HEADER.Machine),'image_base':hex(pe.OPTIONAL_HEADER.ImageBase),'entry_rva':hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),'version':version,'imports':imports,'exports':exports,'sections':[{'name':text(s.Name.rstrip(b'\0')),'rva':hex(s.VirtualAddress),'raw_offset':s.PointerToRawData,'raw_size':s.SizeOfRawData,'virtual_size':s.Misc_VirtualSize} for s in pe.sections]}
 save('pe_'+p.name.replace('.','_')+'.json',d)
 qrc=[x for items in imports.values() for x in items if 'qRegisterResourceData' in x['name']]
 summary.append({'path':rel,'bytes':p.stat().st_size,'machine':d['machine'],'version':version,'import_dlls':list(imports),'export_count':len(exports),'qrc_imports':qrc,'contact_exports':[e for e in exports if 'Contact' in e['name']][:18]})
 pe.close()
save('pe_summary.json',summary)
print('PE SUMMARY',json.dumps(summary,ensure_ascii=False,indent=2)[:18000])
# Decode ZIP/XML document storage.
zs=[]
for p in (ROOT/'data/examples').glob('*.FCStd'):
 with zipfile.ZipFile(p) as z:
  d={'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bad_member':z.testzip(),'members':[{'name':i.filename,'bytes':i.file_size,'compressed':i.compress_size,'method':i.compress_type} for i in z.infolist()]}
  if 'Document.xml' in z.namelist():
   raw=z.read('Document.xml');doc=ET.fromstring(raw)
   d['document_header']=doc.attrib
   d['objects']=[x.attrib for x in doc.findall('.//Objects/Object')]
   d['object_properties']={x.get('name'):[{'name':prop.get('name'),'type':prop.get('type'),'value_xml':ET.tostring(prop,encoding='unicode')[:1400]} for prop in x.findall('./Properties/Property')] for x in doc.findall('./ObjectData/Object')}
  if p.name=='FEMExample.FCStd':
   folder=ROOT/'_document_inspection'/'FEMExample';folder.mkdir(parents=True,exist_ok=True)
   for n in z.namelist():
    if Path(n).name==n and z.getinfo(n).file_size<30*1024**2:(folder/n).write_bytes(z.read(n))
   print('FEM ZIP',json.dumps(d['members'],indent=2))
   print('FEM OBJECTS',json.dumps(d.get('objects'),indent=2))
  save('document_'+p.stem+'.json',d);zs.append({'file':p.name,'members':len(d['members']),'objects':len(d.get('objects',[])),'bad_member':d['bad_member']})
print('DOCUMENT SUMMARY',json.dumps(zs));save('document_summary.json',zs)
# UI resource inventory (parse XML, do not execute embedded code).
ui=[]
for p in (ROOT/'Mod/Fem').rglob('*.ui'):
 try:
  doc=ET.parse(p).getroot();widgets=doc.findall('.//widget')
  ui.append({'path':str(p.relative_to(ROOT)),'class':doc.findtext('class'),'widgets':[w.attrib for w in widgets],'strings':[s.text for s in doc.findall('.//string') if s.text]})
 except Exception as e:ui.append({'path':str(p.relative_to(ROOT)),'error':str(e)})
save('fem_ui_inventory.json',ui)
print('FEM UI',len(ui),[(Path(x['path']).name,len(x.get('widgets',[]))) for x in ui])
print('QSS FILES',[str(p.relative_to(ROOT)) for p in (ROOT/'data/Gui').rglob('*') if p.suffix in ['.qss','.cfg','.xml','.json']])
