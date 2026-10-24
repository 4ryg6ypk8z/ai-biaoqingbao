"""Build a dashboard-uploadable static site; keep every asset below Pages' 25 MiB limit."""
from pathlib import Path
import shutil,json,zipfile
R=Path(__file__).resolve().parents[1];D=R/'output/edgeone-site';D.mkdir(parents=True,exist_ok=True)

for name in ['index.html','site.css','catalog.json','robots.txt','sitemap.xml','llms.txt','.nojekyll']:
 shutil.copy2(R/'docs'/name,D/name)
shutil.copytree(R/'docs/media',D/'media',dirs_exist_ok=True)
(D/'downloads').mkdir(exist_ok=True)
shutil.copy2(R/'downloads/dafeiyu-240.zip',D/'downloads/dafeiyu-240.zip')
shutil.copy2(R/'NOTICE.txt',D/'NOTICE.txt')
files=sorted((R/'stickers/512').glob('*.gif'));groups=[];batch=[];size=0
for f in files:
 if size+f.stat().st_size>23*1024*1024 and batch:groups.append(batch);batch=[];size=0
 batch.append(f);size+=f.stat().st_size
if batch:groups.append(batch)
links=[]
for i,group in enumerate(groups,1):
 name=f'dafeiyu-512-part-{i}.zip'
 with zipfile.ZipFile(D/'downloads'/name,'w',zipfile.ZIP_DEFLATED) as z:
  for f in group:z.write(f,f.name)
  z.write(R/'NOTICE.txt','来源与许可说明.txt')
 links.append(f'<a class="btn" href="downloads/{name}" download>512 清晰包 {i} · {group[0].stem}–{group[-1].stem} ↓</a>')
p=D/'index.html';s=p.read_text();s=s.replace('https://github.com/diwer/ai-biaoqingbao/raw/refs/heads/master/downloads/dafeiyu-240.zip','downloads/dafeiyu-240.zip').replace('https://github.com/diwer/ai-biaoqingbao/raw/refs/heads/master/downloads/dafeiyu-512.zip','#downloads')
s=s.replace('<footer>','<section id="downloads"><span class="eyebrow">DOWNLOAD THE COLLECTION</span><h2>把这份心情，带回聊天里。</h2><p>轻量包包含全部100个GIF；512清晰版分包提供，每一包都是独立ZIP，解压后放在一起即可。</p><div class="hero-actions" style="flex-wrap:wrap"><a class="btn" href="downloads/dafeiyu-240.zip" download>100个手机轻量包 ↓</a>'+''.join(links)+'</div><p><a href="https://github.com/diwer/ai-biaoqingbao">GitHub 代码与完整下载</a> · Gitee 国内镜像</p></section><footer>',1)
s=s.replace('<a href="https://github.com/diwer/ai-biaoqingbao" target="_blank" rel="noopener">GitHub ↗</a>', '<a href="https://gitee.com/wmmhdhy/ai-biaoqingbao" target="_blank" rel="noopener">Gitee ↗</a><a href="https://github.com/diwer/ai-biaoqingbao" target="_blank" rel="noopener">GitHub ↗</a>')
s=s.replace('Gitee 国内镜像', '<a href="https://gitee.com/wmmhdhy/ai-biaoqingbao">Gitee 国内镜像</a>')
p.write_text(s)
assets=list(f for f in D.rglob('*') if f.is_file());assert len(assets)<=1000;assert all(f.stat().st_size<=25*1024*1024 for f in assets)
with zipfile.ZipFile(R/'output/edgeone-static-upload.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in assets:z.write(f,f.relative_to(D))
print(json.dumps({'assets':len(assets),'largest_asset_bytes':max(f.stat().st_size for f in assets),'clear_parts':len(groups),'archive':str(R/'output/edgeone-static-upload.zip')},ensure_ascii=False))
