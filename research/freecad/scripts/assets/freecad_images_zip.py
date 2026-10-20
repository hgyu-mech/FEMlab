from pathlib import Path
from collections import Counter
import json,zipfile,hashlib,os,re,time
B=Path('/work/output/FreeCAD_1.1.4_images_20261020')
m=json.loads((B/'IMAGE_MANIFEST.json').read_text())
rows=m['items']; cat=Counter(x['category'] for x in rows)
n=len(rows)
preview=json.loads((B/'contact_sheets'/'preview_index.json').read_text())
intro=f"""# FreeCAD 1.1.4 Windows 배포본 이미지 추출 결과

- 총 이미지 파일: **{n:,}개**
- SHA-256 기준 서로 다른 데이터: **{m['unique_sha256']:,}개**
- 중복 데이터의 추가 저장 위치: **{m['duplicate_image_instances']:,}개**
- 이미지 미리보기 Contact Sheet: **{len(preview['items'])}장**
- Contact Sheet에서 렌더링에 실패하거나 건너뛴 이미지: **{preview['failed_preview_count']}개**. 실제 원본 파일은 삭제하지 않았습니다.
- 제품 배포본에서 실제 추출한 형식: PNG / SVG / JPG / GIF / ICO / XPM / PPM / BMP.
- 외부 글꼴 파일, 소스 바이너리, 설치 파일은 이 결과물에 포함하지 않았습니다.

## 열어보는 순서

1. \`index.html\`을 더블클릭하면 원본 이미지 {n:,}개를 분류하고 검색하는 갤러리가 열립니다.
2. \`contact_sheets/INDEX.html\`을 더블클릭하면 그룹별 묶음 PNG {len(preview['items'])}장을 볼 수 있습니다.
3. \`images/\`에는 추출한 이미지 원본이 **추출 출처별 폴더 구조**로 들어 있습니다.
4. \`IMAGE_MANIFEST.csv\`는 Excel에서 검색·정렬할 수 있고, \`IMAGE_MANIFEST.json\`에는 각 이미지의 SHA-256을 기록했습니다.

## 추출 범위

| 위치 | 수 |
|---|---:|
"""
for k,v in cat.most_common():intro+=f'| {k} | {v:,} |\n'
intro+="""
### 한계와 정확한 의미
- Portable 압축파일에서 개별 이미지 파일 2,187개를 파일명 기준으로 추출했습니다.
- Portable에 포함된 FCStd 문서 45개를 ZIP으로 읽고 그 내부에서 이미지 38개를 추출했습니다.
- 주요 FreeCAD 확장 모듈(pyd)과 선택한 Qt 공용 binary의 Qt resource table에서 image payload 1,229개를 추출했습니다. 이 검사는 배포본의 모든 제3자 executable(약 1,700여 개)을 빠짐없이 decompile한 것은 아닙니다.
- 선별 PE binary에서 추출한 아이콘/bitmap 16개와 installer에만 있는 2개 BMP를 추가했습니다. Installer에 있는 일반 이미지 1,823개는 portable에 같은 상대 경로가 있어 중복 복사를 생략했습니다. 동일 경로의 전체 내용이 byte-identical하다는 뜻은 아닙니다.
- SVG 원본은 원본 bytes를 보존했습니다. Contact Sheet 이미지 중 일부는 외부 참조 방지나 renderer 제한으로 preview를 만들지 않았지만 갤러리/원본 경로로 열 수 있습니다.
- 파일은 실행/설치하지 않고 구조를 해석해 추출했습니다.
- 공개된 FreeCAD의 asset과 제3자 library의 icon은 각 저작권/라이선스를 유지합니다. 공개 GitHub나 외부 제품에 일괄 복제하기 전에 사용권한을 검토해야 합니다.

대상 원본: 사용자 제공 \`FreeCAD_1.1.4-Windows-x86_64-py311.7z\`와 NSIS Installer EXE.
"""
(B/'README_IMAGES_KO.md').write_text(intro,encoding='utf-8')
p=B/'index.html'
html=p.read_text(encoding='utf-8')
anchor='<section class="tools">'
if anchor in html and 'contact_sheets/INDEX.html' not in html:
    html=html.replace(anchor, '<p style="margin:0 0 14px;color:var(--muted)">전체 이미지 미리보기: <a href="contact_sheets/INDEX.html">Contact Sheet '+str(len(preview['items']))+'장 열기</a> · <a href="README_IMAGES_KO.md">추출 설명</a></p>\n'+anchor,1)
    p.write_text(html,encoding='utf-8')
start=time.monotonic()
def pack(path,include,extras):
    files=[B/'images'/x['file'] for x in include]
    files += [B/n for n in extras]
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for i,f in enumerate(files):
            if not f.exists():raise RuntimeError(str(f))
            z.write(f,f.relative_to(B).as_posix())
            if (i+1)%600==0:print('ZIP',path.name,'progress',i+1,'/',len(files),'elapsed',round(time.monotonic()-start,2),flush=True)
    with zipfile.ZipFile(path) as z:
        if len(z.infolist())!=len(files):raise RuntimeError('zip entry count incorrect')
        err=z.testzip()
        if err:raise RuntimeError(f'zip corrupt member {err}')
    print('ZIP_DONE',path.name,len(files),path.stat().st_size,hashlib.sha256(path.read_bytes()).hexdigest(),flush=True)
    return {'filename':path.name,'entries':len(files),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
extras=['index.html','IMAGE_MANIFEST.csv','IMAGE_MANIFEST.json','README_IMAGES_KO.md','loose_inventory.json','stage2_summary.json','pe_embedded_inventory.json','contact_sheets/INDEX.html','contact_sheets/preview_index.json']
sheets=[x.relative_to(B).as_posix() for x in sorted((B/'contact_sheets').glob('*.png'))]
full=pack(B/f'FreeCAD_1.1.4_ALL_Images_{n}.zip',rows,extras+sheets)
curated=[x for x in rows if (x['file'].startswith('filesystem/data/Gui/') or x['file'].startswith('filesystem/data/Mod/') or x['file'].startswith('filesystem/Mod/') or (x['file'].startswith('qt_embedded/') and not x['file'].startswith('qt_embedded/Qt6')) or x['file'].startswith(('fcstd/','pe_embedded/','installer_extra/')))]
core=pack(B/f'FreeCAD_1.1.4_GUI_Workbench_Images_{len(curated)}.zip',curated,['README_IMAGES_KO.md','IMAGE_MANIFEST.csv'])
print('CORE_ITEMS',len(curated),flush=True)
(B/'ZIP_CHECKSUMS.json').write_text(json.dumps({'full':full,'gui_core':core},ensure_ascii=False,indent=2),encoding='utf-8')
