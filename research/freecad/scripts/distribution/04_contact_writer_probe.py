"""Run only two reviewed, pure input-writer functions with synthetic objects.
No imports or other top-level code from FreeCAD are executed. This is NOT a solver run.
"""
from pathlib import Path
import ast,io,types,json,hashlib,difflib
root=Path('/work/workspace/freecad_audit_20261020/extracted/FreeCAD_1.1.4-Windows-x86_64-py311')
out=Path('/work/output/FreeCAD_1.1.4_audit_20261020/evidence/writer_probe');out.mkdir(exist_ok=True)
p=root/'Mod/Fem/femsolver/calculix/write_constraint_contact.py';source=p.read_text();tree=ast.parse(source)
selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['write_constraint','write_meshdata_constraint']]
assert len(selected)==2
assert not any(isinstance(n,(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal)) for f in selected for n in ast.walk(f))
ns={'__builtins__':{}}
exec(compile(ast.Module(body=selected,type_ignores=[]),str(p),'exec'),ns)
class Quantity:
 def __init__(self,value,unit):self.Value=value;self.unit=unit
 def getValueAs(self,unit):
  if unit!=self.unit:raise ValueError('Probe does not emulate unit conversion')
  return self
base={'Name':'SyntheticContact','Adjust':Quantity(0,'mm'),'SurfaceBehavior':'Hard','Slope':Quantity(1000,'MPa/mm'),'Friction':False,'FrictionCoefficient':0.2,'StickSlope':Quantity(100,'MPa/mm'),'EnableThermalContact':False,'ThermalContactConductance':[]}
cases={}
for name,change in [('hard_no_friction',{}),('hard_with_friction',{'Friction':True}),('linear_no_friction',{'SurfaceBehavior':'Linear'}),('tied_no_friction',{'SurfaceBehavior':'Tied'})]:
 obj=types.SimpleNamespace(**(base|change));f=io.StringIO()
 mesh={'ContactSlaveFaces':[(None,[(10,2)],True)],'ContactMasterFaces':[(None,[(20,4)],True)]}
 ns['write_meshdata_constraint'](f,mesh,obj,None);ns['write_constraint'](f,mesh,obj,None)
 cases[name]=f.getvalue();(out/(name+'.inp.fragment.txt')).write_text(cases[name])
diff=''.join(difflib.unified_diff(cases['hard_no_friction'].splitlines(True),cases['hard_with_friction'].splitlines(True),fromfile='friction_false',tofile='friction_true'))
(out/'friction_toggle.diff').write_text(diff)
result={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_file':str(p.relative_to(root)),'method':'AST-isolated execution of reviewed writer functions; synthetic geometry IDs and dummy quantities already expressed in requested units. No full FreeCAD environment, meshing, CalculiX, FE solve or unit conversion was executed.','cases':cases,'friction_only_diff':diff,'assertions':{'off_has_no_friction':'*FRICTION' not in cases['hard_no_friction'],'on_has_coefficient':'*FRICTION\n0.2, 100\n' in cases['hard_with_friction'],'slave_master_order':'DEPSyntheticContact, INDSyntheticContact' in cases['hard_no_friction'],'linear_keyword':'PRESSURE-OVERCLOSURE=LINEAR\n1000' in cases['linear_no_friction'],'tied_not_hard':'PRESSURE-OVERCLOSURE=TIED\n1000' in cases['tied_no_friction']}}
assert all(result['assertions'].values());(out/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
