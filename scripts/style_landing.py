"""Presentation layer shared by the tracked page and the publication builder."""
import re

def apply_design(page):
 if 'class="hero"' in page:return page
 page=re.sub(r'<style>.*?</style>','<link rel="stylesheet" href="site.css">',page,flags=re.S)
 page=re.sub(r'<section id="support">.*?</section>','',page,flags=re.S)
 header='''<div class="topbar"><a class="brand" href="#"><span class="brand-symbol">𓆝</span> 大肥鱼 <small>EXPRESSION STUDIO</small></a><nav><a href="#collection">表情图鉴</a><a href="#import">使用指南</a><a href="https://github.com/diwer/ai-biaoqingbao" target="_blank" rel="noopener">GitHub ↗</a></nav></div><header class="hero"><div class="hero-copy"><div class="eyebrow"><i></i> A LITTLE BLUE. A LOT OF FEELINGS.</div><h1>有些心情，<br>让<span>大肥鱼</span>说。</h1><p class="intro">不想上班的早晨，绷不住的瞬间，<br>还有那些想认真说的「晚安」。<br>一百种小情绪，总有一张懂你。</p><div class="hero-actions"><a class="btn" href="https://github.com/diwer/ai-biaoqingbao/raw/refs/heads/master/downloads/dafeiyu-240.zip">收藏整套表情 <span>↓</span></a><a class="text-link" href="#collection">先逛一逛 ↗</a></div><div class="hero-meta"><span><b>100</b> 个中文动图</span><span><b>02</b> 种清晰度 · <a href="https://github.com/diwer/ai-biaoqingbao/raw/refs/heads/master/downloads/dafeiyu-512.zip">512 高清 ↗</a></span><span class="live">持续更新中</span></div></div><div class="showcase" aria-label="大肥鱼精选表情展示"><div class="orbit"></div><span class="scene-caption">THE MOOD OF TODAY</span><div class="sticker s1"><img src="media/031.gif" alt="绷不住了的大肥鱼"><span>忍住，忍不住了。</span></div><div class="sticker s2"><img src="media/064.gif" alt="正在摸鱼的大肥鱼"><span>今天也要适当摸鱼。</span></div><div class="sticker s3"><img src="media/054.gif" alt="想你了的大肥鱼"><span>这张，留给特别的人。</span></div><div class="edition">VOL. 01 <span>／</span> DAILY MOODS</div></div></header><div class="section-heading" id="collection"><div><span class="eyebrow">THE COLLECTION</span><h2>今天，想让她说什么？</h2></div><p>从热点表达，到日常陪伴。<br>点开看看，找到此刻的心情。</p></div>'''
 page=re.sub(r'<header>.*?</header><h2>热点含义与常用表情</h2><p>.*?</p>',header,page,flags=re.S)
 page=page.replace('oninput="document.querySelectorAll(\'article\').forEach(e=>e.hidden=!e.dataset.q.includes(this.value.trim()))"','oninput="filterCards()"')
 chips='<div class="filters" aria-label="按场景筛选">'+''.join(f'<button type="button" class="'+('selected' if c=='全部' else '')+f'" onclick="chooseCategory(this)" data-category="{c}">{c}</button>' for c in ['全部','抽象反应','日常回应','打工摸鱼','亲密陪伴','情绪状态','祝福庆祝'])+'</div>'
 page=page.replace('<div class="grid">',chips+'<div class="grid">',1)
 page=page.replace('<section><h2 id="import">','<section class="guide"><span class="eyebrow">TAKE HER WITH YOU</span><h2 id="import">',1)
 page=page.replace('<footer>持续更新', '<footer><span class="footer-brand">大肥鱼 · EXPRESSION STUDIO</span><p>非商业二创整理 · 基础角色：上善无形 · 女仆二次设计：ZipZipPipe · AI辅助改绘与整理：ming</p>持续更新')
 js="""<script>let selectedCategory='全部';function filterCards(){const q=document.getElementById('query').value.trim();let count=0;document.querySelectorAll('article').forEach(e=>{const match=e.dataset.q.includes(q)&&(selectedCategory==='全部'||e.dataset.q.includes(selectedCategory));e.hidden=!match;if(match)count++});let note=document.getElementById('empty-state');if(!note){note=document.createElement('p');note.id='empty-state';document.querySelector('.grid').after(note)}note.textContent=count?'':'没有找到这个心情，试试其他关键词。'}function chooseCategory(b){selectedCategory=b.dataset.category;document.querySelectorAll('.filters button').forEach(x=>x.classList.toggle('selected',x===b));filterCards()}</script>"""
 page=page.replace('</body>',js+'</body>')
 return page

if __name__=='__main__':
 from pathlib import Path
 p=Path(__file__).resolve().parents[1]/'docs/index.html';p.write_text(apply_design(p.read_text()))
