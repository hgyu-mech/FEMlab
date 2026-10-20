from pathlib import Path
import hashlib,json,collections
base=Path('/work/workspace/freecad_audit_20261020');root=base/'extracted/FreeCAD_1.1.4-Windows-x86_64-py311';inst=base/'installer_extracted';out=Path('/work/output/FreeCAD_1.1.4_audit_20261020/evidence')
rows=[]
for rel in (base/'installer_targets.txt').read_text().splitlines():
 a=root/rel;b=inst/rel
 if not a.exists() or not b.exists():rows.append({'path':rel,'missing':True});continue
 ah=hashlib.sha256(a.read_bytes()).hexdigest();bh=hashlib.sha256(b.read_bytes()).hexdigest()
 rows.append({'path':rel,'portable_bytes':a.stat().st_size,'installer_bytes':b.stat().st_size,'portable_sha256':ah,'installer_sha256':bh,'byte_identical':ah==bh})
(out/'package_comparison.json').write_text(json.dumps(rows,indent=2));print('PACKAGE COMPARISON',json.dumps(rows,indent=2))
# Compare embedded Qt resources with loose files in this exact build.
ui=[];resources={}
for binary in ['FemGui.pyd','StartGui.pyd','FreeCADApp.dll']:
 d=json.loads((out/('qt_resources_'+binary+'.json')).read_text());rs={r['path']:r for reg in d['registrations'] for r in reg['resources']};resources[binary]={'unique_resources':len(rs),'by_prefix':dict(collections.Counter(x.split('/')[0] for x in rs))}
 if binary=='FemGui.pyd':
  for name,r in rs.items():
   if not name.startswith('ui/'):continue
   p=root/'Mod/Fem/Resources'/name
   ui.append({'resource':name,'loose_file_present':p.exists(),'identical_sha256':p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']})
(out/'qt_loose_embedded_comparison.json').write_text(json.dumps({'resources':resources,'ui':ui},indent=2));print('RESOURCE SUMMARY',resources,'Embedded UI matches',sum(r['identical_sha256'] for r in ui),'of',len(ui))
# Refine the saved result comparison: component magnitude is NOT the vector norm.
p=out/'document_numbers.json';d=json.loads(p.read_text())
import struct
for r in d['results']:
 fn=root/'_document_inspection/FEMExample'/r['fields']['DisplacementVectors']['file'];raw=fn.read_bytes();n=struct.unpack('<I',raw[:4])[0];a=struct.unpack('<'+str(3*n)+'d',raw[4:]);r['component_ranges']={name:{'min':min(a[j::3]),'max':max(a[j::3])} for j,name in enumerate(['Ux','Uy','Uz'])}
 r['norm_reference_difference_percent_not_a_validation_error']=r.pop('max_deflection_relative_to_EB_reference_percent')
print('RESULT RANGES',json.dumps([{'object':r['object'],'nodes':r['NodeNumbers_count'],'max_norm':r['fields']['DisplacementLengths']['max'],'ranges':r['component_ranges'],'norm_diff':r['norm_reference_difference_percent_not_a_validation_error']} for r in d['results']],indent=2))
p.write_text(json.dumps(d,indent=2))
