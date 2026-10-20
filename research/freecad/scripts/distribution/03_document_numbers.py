from pathlib import Path
import xml.etree.ElementTree as ET,struct,json,math,hashlib,collections
R=Path('/work/workspace/freecad_audit_20261020/extracted/FreeCAD_1.1.4-Windows-x86_64-py311/_document_inspection/FEMExample')
O=Path('/work/output/FreeCAD_1.1.4_audit_20261020/evidence')
doc=ET.fromstring((R/'Document.xml').read_bytes());gui=ET.fromstring((R/'GuiDocument.xml').read_bytes())
objects={o.get('name'):o for o in doc.findall('./ObjectData/Object')}
def prop(name,key):return objects[name].find('./Properties/Property[@name="'+key+'"]')
def value(name,key):
 p=prop(name,key)
 return p[0].attrib if p is not None and len(p) else None
results=[]
for name,ob in objects.items():
 p=prop(name,'DisplacementLengths')
 if p is None:continue
 row={'object':name,'label':value(name,'Label'),'mesh':value(name,'Mesh'),'fields':{}}
 for key,comp in [('DisplacementLengths',1),('DisplacementVectors',3),('vonMises',1),('Stats',1)]:
  pr=prop(name,key)
  if pr is None:continue
  fn=pr[0].get('file');b=(R/fn).read_bytes();count=struct.unpack('<I',b[:4])[0]
  if len(b)!=4+8*count*comp:raise ValueError('Unrecognized serialization')
  xs=struct.unpack('<'+str(count*comp)+'d',b[4:]);row['fields'][key]={'file':fn,'header_count_uint32_le':count,'components':comp,'length_bytes':len(b),'finite':all(math.isfinite(x) for x in xs),'min':min(xs) if xs else None,'max':max(xs) if xs else None}
  if key=='DisplacementVectors':
   vm=[math.sqrt(sum(xs[3*i+j]**2 for j in range(3))) for i in range(count)]
   lb=(R/prop(name,'DisplacementLengths')[0].get('file')).read_bytes();ls=struct.unpack('<'+str(count)+'d',lb[4:]);row['vector_length_max_abs_difference']=max(abs(a-b) for a,b in zip(vm,ls))
  if key=='Stats':row['fields'][key]['values']=xs
 row['NodeNumbers_count']=int(prop(name,'NodeNumbers')[0].get('count'))
 results.append(row)
# Numeric cross-check is a derived check, not a new FEM solve.
L=8000.;b=h=1000.;E=210000.;P=9000000.;I=b*h**3/12;delta=P*L**3/(3*E*I)
for r in results:r['max_deflection_relative_to_EB_reference_percent']=100*(r['fields']['DisplacementLengths']['max']/delta-1)
# View/state information independent of scientific result data.
views=[]
for vp in gui.findall('.//ViewProvider'):
 d={'name':vp.get('name')}
 for pr in vp.findall('./Properties/Property'):
  if pr.get('name') in ['Visibility','DisplayMode','Field','VectorMode','LookupTable','Deformation','ShowColorBar','ShowNodes','LineWidth','PointSize','DrawStyle','ColorBar','Coloring','NodeColor','LineColor','ShapeColor','ShapeAppearance','ElementColors','NodeColorArray','ElementColorArray','Ranges','UseNewSelectionModel','Selectable','Transparency']:
   d[pr.get('name')]=ET.tostring(pr,encoding='unicode')[:650]
 if len(d)>1:views.append(d)
report={'source_document_sha256':hashlib.sha256((R/'Document.xml').read_bytes()).hexdigest(),'numeric_format':'For inspected FloatList/VectorList files: little-endian uint32 count, then IEEE754 float64 values; VectorList has three doubles per item. Verified by exact length and vector-norm cross-check.','results':results,'derived_Euler_Bernoulli_reference':{'force_N':P,'length_mm':L,'E_MPa':E,'I_mm4':I,'tip_mm':delta,'note':'Analytical cross-check against stored results, not a new solver run.'},'view_states':views}
(O/'document_numbers.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='view_states'},indent=2));print('View samples',json.dumps(views[:4],indent=2));print('GUI root',gui.attrib)
# UNV data record summary and coordinates for inspection.
for p in R.glob('FemMesh*.unv'):
 lines=p.read_text(errors='replace').splitlines();parts={};i=0
 while i<len(lines):
  if lines[i].strip()=='-1' and i+1<len(lines) and lines[i+1].strip() not in ['-1','']:
   key=lines[i+1].strip();j=i+2
   while j<len(lines) and lines[j].strip()!='-1':j+=1
   parts.setdefault(key,[]).append(lines[i+2:j]);i=j
  i+=1
 print('UNV',p.name,{k:len(v[0]) for k,v in parts.items()},'NODE SAMPLE',parts.get('2411',[[]])[0][:6])
