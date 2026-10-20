from pathlib import Path
import sys,json,struct,hashlib,zlib,bisect,re
sys.path.insert(0,'/work/workspace/freecad_audit_20261020/tools/python')
import pefile,capstone
ROOT=Path('/work/workspace/freecad_audit_20261020/extracted/FreeCAD_1.1.4-Windows-x86_64-py311')
OUT=Path('/work/output/FreeCAD_1.1.4_audit_20261020/evidence');dest=OUT/'recovered_resources';dest.mkdir(exist_ok=True)
all_reports=[]
for rel in ['lib/FemGui.pyd','lib/StartGui.pyd','bin/FreeCADApp.dll','bin/FreeCADGui.dll']:
 p=ROOT/rel;pe=pefile.PE(str(p));base=pe.OPTIONAL_HEADER.ImageBase
 imports={x.address:x.name.decode(errors='replace') for d in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]) for x in d.imports if x.name}
 imports.update({x.address:x.name.decode(errors='replace') for d in getattr(pe,'DIRECTORY_ENTRY_DELAY_IMPORT',[]) for x in d.imports if x.name})
 qrc={addr:n for addr,n in imports.items() if 'qRegisterResourceData' in n}
 print(rel,'qrc imports',qrc,flush=True)
 exc=sorted([(x.struct.BeginAddress,x.struct.EndAddress) for x in getattr(pe,'DIRECTORY_ENTRY_EXCEPTION',[])])
 md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
 report={'binary':rel,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'registrations':[]}
 thunks=set()
 for sec in pe.sections:
  if not sec.Characteristics & 0x20000000:continue
  raw0=sec.get_data()
  for mt in re.finditer(b'\xff\x25',raw0):
   j=mt.start()
   if j+6<=len(raw0) and base+sec.VirtualAddress+j+6+struct.unpack_from('<i',raw0,j+2)[0] in qrc:thunks.add(base+sec.VirtualAddress+j)
 for section in pe.sections:
  if not section.Characteristics & 0x20000000:continue
  raw=section.get_data();off=0
  while True:
   match=re.search(b'\xff[\x15\x25]|[\xe8\xe9]',raw[off:])
   if not match:break
   i=off+match.start();off=i+2
   if i+6>len(raw):continue
   rva=section.VirtualAddress+i;va=base+rva
   indirect=raw[i]==255
   addr=va+6+struct.unpack_from('<i',raw,i+2)[0] if indirect else va+5+struct.unpack_from('<i',raw,i+1)[0]
   if (indirect and addr not in qrc) or (not indirect and addr not in thunks):continue
   start=max(section.VirtualAddress,rva-80)
   index=bisect.bisect_right(exc,(rva,0xffffffff))-1
   if index>=0 and exc[index][0]<=rva<exc[index][1]:start=exc[index][0]
   if rva-start>1000:start=rva-80
   instr=list(md.disasm(pe.get_data(start,rva-start+6),base+start));regs={};lines=[]
   for ins in instr:
    lines.append(f'{ins.address:#x}: {ins.mnemonic} {ins.op_str}')
    if len(ins.operands)>=2 and ins.operands[0].type==capstone.x86.X86_OP_REG:
     reg=ins.reg_name(ins.operands[0].reg);op=ins.operands[1]
     if ins.mnemonic=='lea' and op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:regs[reg]=ins.address+ins.size+op.mem.disp
     elif ins.mnemonic=='mov' and op.type==capstone.x86.X86_OP_IMM:regs[reg]=op.imm
   # Recover RIP-relative argument loads in a bounded prefix, even for leaf tail calls without unwind entries.
   prefix_start=max(0,i-80);prefix=raw[prefix_start:i]
   for reg,opcode in [('rdx',b'\x48\x8d\x15'),('r8',b'\x4c\x8d\x05'),('r9',b'\x4c\x8d\x0d')]:
    found=list(re.finditer(re.escape(opcode),prefix))
    for mt in reversed(found):
     pos=prefix_start+mt.start()
     if pos+7<=i:regs[reg]=base+section.VirtualAddress+pos+7+struct.unpack_from('<i',raw,pos+3)[0];break
   registration={'call_rva':hex(rva),'assembly':lines,'argument_values':{k:hex(v) for k,v in regs.items()},'resources':[]}
   if not all(k in regs for k in ['rdx','r8','r9']):
    report['registrations'].append(registration);continue
   tree,names,data=regs['rdx']-base,regs['r8']-base,regs['r9']-base;version=regs.get('ecx',regs.get('rcx',3));entry_size=22 if version>=2 else 14
   visited=set()
   def read(rva,n):
    b=pe.get_data(rva,n)
    if len(b)!=n:raise ValueError('short read')
    return b
   def name_at(offset):
    n=struct.unpack('>H',read(names+offset,2))[0]
    if n>4096:raise ValueError('invalid name length')
    return read(names+offset+6,n*2).decode('utf-16-be')
   def walk(idx,parent):
    if idx in visited or len(visited)>30000:raise ValueError('cyclic or overlarge resource tree')
    visited.add(idx);node=read(tree+entry_size*idx,entry_size);no,flags=struct.unpack_from('>IH',node)
    name=name_at(no) if idx else '';path='/'.join(x for x in [parent,name] if x)
    if flags&2:
     count,first=struct.unpack_from('>II',node,6)
     if count>30000:raise ValueError('overlarge directory')
     for child in range(first,first+count):walk(child,path)
    else:
     pos=struct.unpack_from('>I',node,10)[0];n=struct.unpack('>I',read(data+pos,4))[0]
     if n>50*1024*1024:raise ValueError('overlarge payload')
     blob=read(data+pos+4,n);decoded=blob;compression='none'
     if flags&1:
      decoded=zlib.decompress(blob[4:]);compression='zlib'
     elif flags&4:
      from backports import zstd
      decoded=zstd.decompress(blob);compression='zstd'
     d={'path':path,'node_index':idx,'flags':flags,'compression':compression,'stored_bytes':n,'bytes':len(decoded),'payload_file_offset':pe.get_offset_from_rva(data+pos+4),'sha256':hashlib.sha256(decoded).hexdigest()}
     # Only preserve selected non-font assets for inspection, never repackage the program.
     if Path(path).suffix.lower() in ['.svg','.qss','.ui','.xml','.qml'] and any(s in path.lower() for s in ['contact','calculix','ccx','force','result','start','stylesheet','default','material','mesh']):
      out=dest/(p.name+'__'+path.replace('/','__'));out.write_bytes(decoded);d['saved_as']=out.name
     registration['resources'].append(d)
   try:
    walk(0,'');registration['node_count']=len(visited)
   except Exception as e:registration['parse_error']=repr(e)
   report['registrations'].append(registration)
 for r in report['registrations']:print(' reg',r['call_rva'],'regs',r['argument_values'],'resources',len(r['resources']),'err',r.get('parse_error'),flush=True)
 (OUT/('qt_resources_'+p.name+'.json')).write_text(json.dumps(report,indent=2),encoding='utf8')
 all_reports.append({'binary':rel,'registrations':len(report['registrations']),'resources':sum(len(x['resources']) for x in report['registrations']),'errors':[x.get('parse_error') for x in report['registrations'] if x.get('parse_error')]})
 pe.close()
(OUT/'qt_resources_summary.json').write_text(json.dumps(all_reports,indent=2));print(all_reports)
