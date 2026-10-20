from pathlib import Path
import json,sys,struct,bisect
sys.path.insert(0,'/work/workspace/freecad_audit_20261020/tools/python')
import pefile,capstone
root=Path('/work/workspace/freecad_audit_20261020/extracted/FreeCAD_1.1.4-Windows-x86_64-py311');out=Path('/work/output/FreeCAD_1.1.4_audit_20261020/evidence')
p=root/'lib/FemGui.pyd';pe=pefile.PE(str(p));base=pe.OPTIONAL_HEADER.ImageBase
imp={x.address:x.name.decode(errors='replace') for d in pe.DIRECTORY_ENTRY_IMPORT for x in d.imports if x.name}
exp={base+x.address:x.name.decode(errors='replace') for x in pe.DIRECTORY_ENTRY_EXPORT.symbols if x.name}
name='?setEdit@ViewProviderFemConstraintContact@FemGui@@MEAA_NH@Z';va=next(k for k,v in exp.items() if v==name);rva=va-base
ranges=sorted((x.struct.BeginAddress,x.struct.EndAddress) for x in pe.DIRECTORY_ENTRY_EXCEPTION);ix=bisect.bisect_right(ranges,(rva,0xffffffff))-1;end=ranges[ix][1]
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
rows=[]
def resolve(target):
 if target in exp:return exp[target]
 if target in imp:return imp[target]
 if base<=target<base+pe.OPTIONAL_HEADER.SizeOfImage:
  b=pe.get_data(target-base,6)
  if len(b)==6 and b[:2]==b'\xff\x25':return imp.get(target+6+struct.unpack('<i',b[2:])[0],'import thunk, unresolved name')
 return 'internal function or unnamed target'
for ins in md.disasm(pe.get_data(rva,end-rva),va):
 row={'va':hex(ins.address),'rva':hex(ins.address-base),'bytes':ins.bytes.hex(),'instruction':ins.mnemonic+' '+ins.op_str}
 if ins.mnemonic in ['call','jmp'] and ins.operands:
  op=ins.operands[0]
  if op.type==capstone.x86.X86_OP_IMM:row['target']=resolve(op.imm)
  elif op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:row['target']=resolve(ins.address+ins.size+op.mem.disp)
 rows.append(row)
report={'binary':'lib/FemGui.pyd','symbol':name,'rva':hex(rva),'unwind_function_end_rva':hex(end),'instructions':rows,'limitation':'Disassembly of one exported function only. Imported names resolved via IAT/thunks. Hidden internal constructors are not assigned names without independent evidence. No dynamic execution.'}
(out/'native_contact_setEdit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
# Read both ASCII and UTF16LE strings from the launcher; do not run it.
b=(root/'FreeCAD.exe').read_bytes();import re
strings=[m.group().decode('ascii','replace') for m in re.finditer(rb'[\x20-\x7e]{8,}',b)]+[m.group().decode('utf-16-le','replace') for m in re.finditer(rb'(?:[\x20-\x7e]\x00){8,}',b)]
hits=[s for s in strings if 'freecad' in s.lower() or '\\bin\\' in s.lower()]
(out/'launcher_strings.json').write_text(json.dumps(hits,indent=2));print('LAUNCHER',hits)
