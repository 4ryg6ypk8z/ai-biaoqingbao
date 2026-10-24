from pathlib import Path
import json,shutil,html,zipfile
R=Path(__file__).resolve().parents[1]; S=R/'output/dafeiyu-100-v001';D=R/'docs';m=json.loads((S/'manifest.json').read_text()) if (S/'manifest.json').exists() else {'items':json.loads((D/'catalog.json').read_text())};items=m['items'];assert len(items)==100
for e in items if (S/'manifest.json').exists() else []:
 assert (S/e['gif']).exists() and (S/e['small']).exists()
 shutil.copy2(S/e['small'],D/'media'/f'{e["id"]}.gif');shutil.copy2(S/e['gif'],R/'stickers/512'/f'{e["id"]}.gif')
if (S/'manifest.json').exists(): shutil.copy2(S/'dafeiyu-personal-240.zip',R/'downloads/dafeiyu-240.zip')
if (S/'manifest.json').exists(): shutil.copy2(S/'dafeiyu-personal-512.zip',R/'downloads/dafeiyu-512.zip')
if (S/'来源与许可说明.txt').exists(): shutil.copy2(S/'来源与许可说明.txt',R/'NOTICE.txt')
public=[{k:e[k] for k in ['id','label','category','meaning']} for e in items];(D/'catalog.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n')
featured=['031','037','039','046','041','064','076','054','017','018','099','100'];order=sorted(items,key=lambda e:(0,featured.index(e['id'])) if e['id'] in featured else (1,int(e['id'])))
url='https://diwer.github.io/ai-biaoqingbao/'
cards=''.join(f'<article data-q="{html.escape(e["label"]+e["meaning"]+e["category"])}"><img src="media/{e["id"]}.gif" alt="大肥鱼表情包：{html.escape(e["label"])}，{html.escape(e["meaning"])}" loading="lazy" width="240" height="240"><h3>{e["label"]}</h3><p>{html.escape(e["meaning"])}</p><a href="media/{e["id"]}.gif" download="大肥鱼-{e["label"]}.gif">下载 GIF</a></article>' for e in order)
imports='''<h2 id="import">各 App 自用导入方法</h2><p>先下载轻量 ZIP，解压并保留 GIF 原文件。不要截图或转换成 JPG；若系统不能将 GIF 保存到相册，可保留在“文件”App 中再选取。以下为个人收藏/聊天使用，不是表情商店上架。</p><h3>微信</h3><ol><li>打开手机微信聊天，点表情按钮，进入爱心/自定义表情页。</li><li>若显示“+”，从相册选择 GIF 添加；也可到“我 → 表情 → 设置/齿轮 → 添加的单个表情”查找添加入口。</li><li>收到或发出可收藏的表情后，可长按查看是否有“添加”选项。没有该菜单时，先保存原 GIF 再从添加入口选择。</li></ol><h3>小红书</h3><p>当前未核实存在面向所有账号的整套本地 GIF 批量导入功能。可在私信的相册/图片入口尝试选择 GIF；若发送后长按菜单提供“添加表情/收藏”，再收藏使用。若被转成静态图或无添加入口，说明该版本/场景不支持，不承诺动图可导入。</p><h3>抖音</h3><p>进入手机端私信聊天 → 表情 → 收藏/爱心页，若有“+”入口则从相册选择；也可在聊天中长按已支持的表情，查看“添加到表情”等选项。评论区、私信与电脑端能力不同，实际以当前菜单为准，不能保证本地 GIF 在所有入口保留动画。</p><h3>Telegram</h3><p>官方 @Stickers 可创建整套安装链接。动态贴纸需将 GIF 转为符合规格的 VP9 WEBM；本项目下载包尚未提供该格式。<a href="https://core.telegram.org/stickers">官方说明</a>。</p><h3>Signal / WhatsApp</h3><p>Signal 桌面端提供 Create/Upload Sticker Pack，动图需 APNG，不能直接上传 GIF。WhatsApp 手机端支持创建与分享贴纸包，动图需满足其大小及格式要求；本项目暂无这两个 App 的直接安装包。<a href="https://support.signal.org/hc/en-us/articles/360031836512-Stickers">Signal 说明</a> · <a href="https://faq.whatsapp.com/1056840314992666">WhatsApp 说明</a>。</p><p>核查日期：2026-10-24。微信/小红书/抖音菜单会随系统、版本和账号变化；未在用户手机实测，不把条件性入口写成保证可用。</p>'''
faq=[('这是原创官方大肥鱼表情包吗？','不是。本项目为第三方角色的 AI 辅助二创整理，与 DeepSeek 官方无合作或背书关系。具体参考图权属仍在核实。'),('表情包免费吗？','提供免费下载，持续更新；非商业用途说明见 NOTICE。自愿赞助不构成购买或商用授权。'),('现在有多少个表情？','当前提供100个带中文配字的循环GIF，提供240像素轻量版和512像素清晰版。'),('可以一键导入微信、小红书、抖音吗？','目前没有跨App一键导入包。需解压GIF后在各App支持的个人表情入口添加，具体以手机版本为准。')]
ld={'@context':'https://schema.org','@type':'CollectionPage','name':'大肥鱼表情包：100个中文GIF，持续更新','description':'免费非商业二创表情整理，含热点含义、GIF下载和App自用导入指南。','url':url,'inLanguage':'zh-CN'}
page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>大肥鱼表情包下载｜100个中文GIF与导入指南 · 持续更新</title><meta name="description" content="大肥鱼中文GIF表情包，包含绷不住了、麻了、红温了、吃瓜、摸鱼中等常用表达。提供100个轻量及清晰动图下载，附微信、小红书、抖音自用导入说明，持续更新。"><link rel="canonical" href="URL"><meta property="og:title" content="大肥鱼表情包 · 100个中文GIF · 持续更新"><meta property="og:description" content="常用表达、动图下载和各App自用导入指南。"><meta property="og:image" content="URLmedia/031.gif"><meta property="og:url" content="URL"><meta name="robots" content="index,follow"><script type="application/ld+json">LD</script><style>*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f3f6fc;color:#23356c;font:16px/1.7 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:35px 22px}header{padding:30px;background:#e6edff;border-radius:22px}h1{font-size:38px;line-height:1.25;margin:10px 0}h2{margin-top:42px}a{color:#285bb0}nav{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}.btn{background:#243b80;color:white;padding:11px 18px;border-radius:12px;text-decoration:none}input{width:100%;padding:14px;border:1px solid #d7dfef;border-radius:12px;font:inherit}.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:15px;margin:22px 0}article{background:white;padding:10px;border-radius:16px;border:1px solid #e1e7f3}article img{display:block;width:100%;height:auto}article h3{margin:4px 0}article p{font-size:13px;color:#687797;margin:5px 0}section{background:white;padding:25px;border-radius:18px;margin-top:25px}aside{font-size:14px;color:#526685}footer{margin-top:35px;color:#72809a}details{margin:12px 0}summary{cursor:pointer;font-weight:bold}@media(max-width:700px){.grid{grid-template-columns:repeat(2,1fr)}h1{font-size:28px}main{padding:20px 12px}header{padding:20px}}[hidden]{display:none!important}</style></head><body><main><header><span>持续更新 · 100个中文循环GIF</span><h1>让大肥鱼，替你表达小情绪。</h1><p>绷不住了、麻了、红温了、摸鱼中……从日常回应到打工心情，找到此刻想发的那一张。</p><nav><a class="btn" href="https://github.com/diwer/ai-biaoqingbao/raw/refs/heads/master/downloads/dafeiyu-240.zip">下载手机轻量包</a><a class="btn" href="https://github.com/diwer/ai-biaoqingbao/raw/refs/heads/master/downloads/dafeiyu-512.zip">下载512清晰包</a><a href="#import">如何导入 App</a><a href="https://github.com/diwer/ai-biaoqingbao">GitHub</a></nav><aside>非商业二创整理。基础角色：上善无形；女仆二次设计：ZipZipPipe；AI辅助改绘与整理：ming。权属与使用边界见仓库 NOTICE。</aside></header><h2>热点含义与常用表情</h2><p>优先展示高互动题材衍生的常用表达；展示顺序为编辑选择，不是全网热度榜。</p><input id="query" aria-label="搜索表情含义" placeholder="搜索：摸鱼、安慰、早安……" oninput="document.querySelectorAll('article').forEach(e=>e.hidden=!e.dataset.q.includes(this.value.trim()))"><div class="grid">CARDS</div><section>IMPORTS</section><section><h2>常见问题</h2>FAQ</section><section id="support"><h2>自愿赞助 2 元 Token 费</h2><p>下载保持免费。若这些表情让你会心一笑，欢迎自愿支持制作所需的 Token 费用。微信赞赏码、支付宝收款码尚未提供，暂未开通收款入口。</p><p>赞助不是购买，不提供商业授权；在第三方角色许可范围未明确前不启用实际收款。</p></section><footer>持续更新 · 最近更新：2026-10-24 · <a href="https://github.com/diwer/ai-biaoqingbao/blob/master/NOTICE.txt">来源与许可</a></footer></main></body></html>'''
page=page.replace('URL',url).replace('LD',json.dumps(ld,ensure_ascii=False)).replace('CARDS',cards).replace('IMPORTS',imports).replace('FAQ',''.join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q,a in faq));(D/'index.html').write_text(__import__('style_landing').apply_design(page))
(D/'.nojekyll').touch();(D/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+url+'sitemap.xml\n');(D/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'+url+'</loc><lastmod>2026-10-24</lastmod></url></urlset>')
(D/'llms.txt').write_text('# 大肥鱼表情包\n\n100个中文GIF，持续更新。非商业二创，不是官方作品。\n\n- [宣传页]('+url+')\n- [表情目录]('+url+'catalog.json)\n- [来源与许可](https://github.com/diwer/ai-biaoqingbao/blob/master/NOTICE.txt)\n\n不保证任何搜索引擎或AI检索系统收录。\n')
readme='''# 大肥鱼表情包 · 100个中文 GIF

**持续更新**。大肥鱼（蓝发鲸鱼娘 / DeepSeek 社区拟人形象）中文表情二创整理，包含日常回应、抽象反应、打工摸鱼、陪伴与祝福。

[在线宣传页与动图预览](https://diwer.github.io/ai-biaoqingbao/) · [手机轻量包](downloads/dafeiyu-240.zip) · [512清晰包](downloads/dafeiyu-512.zip) · [来源与许可](NOTICE.txt)

## 热点含义与常用表达

热点题材仅作编辑选题参考，不是全网热度排名。画面为本项目 AI 辅助改绘，没有取用搜索帖中的其他角色图片。

'''
readme+='| 绷不住了 | 麻了 | 红温了 | 吃瓜 |\n|---|---|---|---|\n| ![大肥鱼绷不住了](docs/media/031.gif) | ![大肥鱼麻了](docs/media/037.gif) | ![大肥鱼红温了](docs/media/039.gif) | ![大肥鱼吃瓜](docs/media/046.gif) |\n\n'
readme+='''## 下载与自用导入

- 240×240 轻量 GIF：适合手机传输和个人收藏。
- 512×512 清晰 GIF：保留更清晰细节。
- ZIP 需要先解压，保留 GIF 原文件；不要截图后当作动图导入。
- 微信：手机聊天表情 → 爱心/自定义页 → 若有“+”则从相册添加；或查找“我 → 表情 → 设置 → 添加的单个表情”。版本入口可能不同。
- 小红书：未确认通用的整套 GIF 导入功能。可在私信图片入口尝试发送；仅当长按菜单出现收藏/添加时使用。部分入口可能转静态图。
- 抖音：手机私信表情收藏页若有“+”则尝试从相册添加；或长按已支持的表情查看添加选项。评论区、私信、电脑端能力不同。
- Telegram / Signal / WhatsApp：需要各平台专用格式及账号；当前 ZIP 不是一键安装包。[详见宣传页](https://diwer.github.io/ai-biaoqingbao/#import)。

以上说明于2026-10-24核查，未在用户手机逐项实测，不承诺所有版本保留动图。

## 持续更新

当前已制作100个，后续继续完善动作一致性、更多场景与平台适配。这里的“持续更新”是维护方向，不代表已设置定时生成任务。

## 自愿赞助 2 元 Token 费

下载保持免费。欢迎自愿支持制作所需 Token 费用。计划支持微信赞赏码和支付宝收款码；当前未提供二维码，尚未启用收款入口。

赞助不等于购买或商业授权。第三方角色许可范围未明确前不启用实际收款。

## 来源与使用边界

本项目是AI辅助二创，不是独立原创角色，也不是DeepSeek官方项目。

- 基础鲸鱼娘角色：上善无形。
- DeepSeek女仆二次设计：ZipZipPipe。
- 本套表情的AI辅助改绘、配字和GIF整理：ming。
- 直接参考网图的逐图作者及许可仍在核实；不因本仓库公开而自动取得授权。
- 不提供商业使用许可。[完整说明](NOTICE.txt)。

## 表情目录

|编号|表情|含义|分类|
|---|---|---|---|
'''
readme+='\n'.join(f'|{e["id"]}|[{e["label"]}](docs/media/{e["id"]}.gif)|{e["meaning"]}|{e["category"]}|' for e in items)
readme+='\n\n## English summary\n\nDafeiyu Chinese reaction GIF collection: 100 captioned whale-maid reaction stickers, including daily replies, work moods, affection and greetings. Continuously maintained. Non-commercial fan-made AI-assisted artwork, not an official DeepSeek product. No commercial license is granted. See NOTICE for attribution and unresolved reference-image provenance.\n'
(R/'README.md').write_text(readme)
print('Built README, 100 public GIFs in two sizes, landing page, catalog, metadata, sitemap, optional llms.txt')
