from pathlib import Path
import json,math,collections,struct,xml.etree.ElementTree as ET
R=Path('/work/workspace/freecad_audit_20261020/extracted/FreeCAD_1.1.4-Windows-x86_64-py311/_document_inspection/FEMExample');O=Path('/work/output/FreeCAD_1.1.4_audit_20261020/evidence')
def datasets(p):
 ls=p.read_text().splitlines();d={};i=0
 while i<len(ls):
  if ls[i].strip()=='-1' and i+1<len(ls) and ls[i+1].strip() not in ['-1','']:
   key=ls[i+1].strip();j=i+2
   while j<len(ls) and ls[j].strip()!='-1':j+=1
   d[key]=ls[i+2:j];i=j
  i+=1
 return d
reports={};nodes_by_file={}
for p in R.glob('FemMesh*.unv'):
 ds=datasets(p);ls=ds['2411'];assert len(ls)%2==0
 nodes={int(ls[i].split()[0]):tuple(float(x.replace('D','E')) for x in ls[i+1].split()) for i in range(0,len(ls),2)};nodes_by_file[p.name]=nodes
 ls=ds['2412'];i=0;elements=[]
 while i<len(ls):
  header=[int(x) for x in ls[i].split()];assert len(header)==6,(p.name,i,header)
  eid,desc,_,_,_,nn=header;i+=1
  if desc in {11,21,22,23,24}:i+=1
  ids=[]
  while len(ids)<nn:ids.extend(int(x) for x in ls[i].split());i+=1
  assert len(ids)==nn and all(x in nodes for x in ids)
  elements.append({'id':eid,'unv_descriptor':desc,'node_count':nn,'nodes':ids})
 reports[p.name]={'nodes':len(nodes),'elements':len(elements),'types':dict(collections.Counter(f'{e["unv_descriptor"]}/{e["node_count"]}-node' for e in elements)),'coordinate_bounds':{a:[min(v[j] for v in nodes.values()),max(v[j] for v in nodes.values())] for j,a in enumerate('xyz')},'all_element_nodes_resolve':True}
(O/'mesh_mapping.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports,indent=2))
