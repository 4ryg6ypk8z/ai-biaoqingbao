"""Verify and publish the approved 100-item v002 delivery without regenerating artwork."""
from pathlib import Path
import csv, hashlib, json, shutil, zipfile
R=Path(__file__).resolve().parents[1]
source=R/'deliverables/differentiation-v002/unpacked'
rows=list(csv.DictReader((source/'001-020/index/DELIVERY-INDEX-ALL-100.csv').open(encoding='utf-8-sig')))
assert [r['id'] for r in rows]==[f'{i:03}' for i in range(1,101)]
catalog=json.loads((R/'docs/catalog.json').read_text())
record=R/'production/published-v002';record.mkdir(parents=True,exist_ok=True)
verified=[]
for row,item in zip(rows,catalog):
 ident=row['id']; lo=((int(ident)-1)//20)*20+1
 batch=source/f'{lo:03}-{lo+19:03}'
 for size,target in [('240',R/'docs/media'),('512',R/'stickers/512')]:
  file=batch/f'assets/{size}/{ident}.gif'
  digest=hashlib.sha256(file.read_bytes()).hexdigest()
  assert digest==row[f'gif{size}_sha256'],(ident,size)
  target.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target/file.name)
  verified.append({'id':ident,'size':int(size),'sha256':digest})
 shutil.copy2(batch/f'design-prompts/{ident}.txt',R/f'production/prompts/{ident}.txt')
 if int(ident)>=17:item['meaning']=row['meaning']
(R/'docs/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
(record/'manifest.json').write_text(json.dumps({'version':'v002','source':'deliverables/differentiation-v002','items':verified},ensure_ascii=False,indent=2)+'\n')
(record/'delivery-index.csv').write_text((source/'001-020/index/DELIVERY-INDEX-ALL-100.csv').read_text(encoding='utf-8-sig'))
notice=R/'NOTICE.txt'
text=notice.read_text().replace('本包包含100个512×512循环GIF及对应PNG静态图。','本项目提供100个中文循环GIF，含240×240轻量版和512×512清晰版。\n当前发布：v002 全套修订，2026-10-25；100个编号全部替换。')
notice.write_text(text)
for size,folder in [('240',R/'docs/media'),('512',R/'stickers/512')]:
 with zipfile.ZipFile(R/f'downloads/dafeiyu-{size}.zip','w',zipfile.ZIP_DEFLATED) as z:
  for item in catalog:z.write(folder/f'{item["id"]}.gif',f'{item["id"]}-{item["label"]}.gif')
  z.write(notice,'来源与许可说明.txt')
print('Verified hashes and replaced 200 GIFs, 100 prompts, both download archives, and v002 provenance.')
