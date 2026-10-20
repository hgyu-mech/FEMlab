"""Isolate one reviewed GUI completion handler. All GUI/solver objects are test doubles."""
from pathlib import Path
import ast,types,json,hashlib
S=types.SimpleNamespace
root=Path('/work/workspace/freecad_audit_20261020/extracted/FreeCAD_1.1.4-Windows-x86_64-py311');p=root/'Mod/Fem/femtaskpanels/task_solver_ccxtools.py'
tree=ast.parse(p.read_text());nodes=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='calculixFinished'];assert len(nodes)==1
f=nodes[0];assert not any(isinstance(n,(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal)) for n in ast.walk(f))
results=[]
for name,code,status,stdout_ok in [('normal_success',0,0,True),('normal_exit_reported_error',1,0,False),('abnormal_exit',1,1,False)]:
 calls=[]
 def note(x):calls.append(x)
 ns={'__builtins__':{'Exception':Exception},'FreeCAD':S(Console=S(PrintLog=lambda _:None,PrintError=lambda x:note('console_error'))),'QtCore':S(QDir=S(setCurrent=lambda _:note('restore_cwd')),QProcess=S(ExitStatus=S(NormalExit=0))),'QApplication':S(setOverrideCursor=lambda _:None,restoreOverrideCursor=lambda:None),'Qt':S(WaitCursor=1),'time':S(time=lambda:1)}
 exec(compile(ast.Module(body=[f],type_ignores=[]),str(p),'exec'),ns)
 fea=S(reset_mesh_purge_results_checked=lambda:note('reset_mesh_purge_results_checked'),inp_file_name='synthetic',get_ccx_version=lambda:(2,22),load_results=lambda:note('load_results'),analysis=S(Document=S(getObject=lambda _:None)))
 self=S(Calculix=S(state=lambda:0),cwd='synthetic',Timer=S(stop=lambda:None),form=S(pb_run_ccx=S(setText=lambda s:note('button:'+s)),l_time=S(setText=lambda _:None)),printCalculiXstdout=lambda:stdout_ok,calculixNoError=lambda:note('calculixNoError'),calculixError=lambda:note('calculixError'),femConsoleMessage=lambda s:note('message:'+s),fea=fea,Start=0,CCX_mesh_visibility=False)
 ns['calculixFinished'](self,code,status)
 results.append({'case':name,'exit_code':code,'exit_status':status,'stdout_check_ok':stdout_ok,'calls':calls})
report={'source':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'method':'AST-isolated execution of calculixFinished with synthetic test doubles. No Qt GUI, FreeCAD, ccx or real result parser execution.','observations':results,'interpretation':'In the tested normal-exit/failed-stdout-check branch, calculixError does not terminate this handler and load_results is still called. This alone does not prove incorrect user-visible results; partial-result behavior or further parser validation may be intentional. A separate live failure-case test is required.'}
q=Path('/work/output/FreeCAD_1.1.4_audit_20261020/evidence/solver_finish_probe.json');q.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
