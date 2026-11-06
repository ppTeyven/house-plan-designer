// 切换动效录像：自动点 2D→3D→分屏→2D→分屏→3D，全程 CDP screencast 录帧，输出帧序列 + 可播放回放页
// 用法：node record-transition.mjs <设计器.html|httpURL> [输出目录]
//   例：node record-transition.mjs D:/xxx/客厅-装修设计器.html ./transition-rec
//       node record-transition.mjs http://127.0.0.1:8899/template.html ./transition-rec  （需先起 python serve.py）
// 输出：<out>/frames/frame-*.jpg、<out>/metrics.json、<out>/playback.html（浏览器打开按播放看动态）、<out>/summary.json
// 依赖：puppeteer-core（本目录 npm install）、Chrome。本地文件会自动起一个临时 http 静态服务（file:// 下 PBR 贴图会被 WebGL 拒绝）；http(s) 地址直接打开。
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { pathToFileURL } from 'url';
import { pageUrl } from '../lib_serve.mjs';

const args = process.argv.slice(2);
let TARGET = null, OUTARG = null;
for (const a of args) {
  if (!TARGET && (/^https?:\/\//.test(a) || /\.html?([?#].*)?$/.test(a))) { TARGET = a; continue; }
  if (!OUTARG) { OUTARG = a; continue; }
}
// 兼容老用法：只给一个目录（设计器仓库内跑，默认打开 serve.py 的 template.html）
let OUT;
if (TARGET && OUTARG) OUT = path.resolve(OUTARG);
else if (TARGET && !OUTARG && !/\.html?([?#].*)?$/.test(TARGET) && !/^https?:\/\//.test(TARGET)) { OUT = path.resolve(TARGET); TARGET = null; }
else if (TARGET && !OUTARG) { OUT = path.resolve('transition-rec'); }
else { OUT = path.resolve('transition-rec'); }
const FRAMES = path.join(OUT, 'frames');
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(FRAMES, { recursive: true });

const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
if (!exe) { console.error('ERR: 找不到 Chrome/Edge'); process.exit(1); }

// 解析目标地址：本地文件走 http://（file:// 下 WebGL 拒绝上传跨源贴图，PBR 材质全不生效），
// http(s) 直接用；都没给则回退到 8899 serve.py
let pageURL, closeServer = async () => {};
if (TARGET && /^https?:\/\//.test(TARGET)) pageURL = TARGET;
else if (TARGET) { const pg = await pageUrl(TARGET); pageURL = pg.url; closeServer = pg.close; }
else pageURL = 'http://127.0.0.1:8899/template.html';
// 只有没给目标文件时才要求 8899 在跑
if (!TARGET) {
  try {
    const r = await fetch(pageURL, { method: 'HEAD' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
  } catch (e) {
    console.error('ERR: 8899 服务没跑，先起 python serve.py → ' + e.message);
    process.exit(1);
  }
}

const b = await puppeteer.launch({
  executablePath: exe, headless: 'new',
  defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows']
});
const page = await b.newPage();
const errs = [];
page.on('pageerror', e => errs.push('pageerror: ' + e.message));
page.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 160)); });
page.on('dialog', d => d.dismiss());

await page.goto(pageURL + (pageURL.includes('?') ? '&' : '?') + 'debug', { waitUntil: 'load' });
await page.waitForFunction(() => window.__designer, { timeout: 60000 });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ev = (f, ...a) => page.evaluate(f, ...a);
// 等过 1.8s 预热 + 3D 就绪，复现“刷新后第一次切换”
await ev(() => new Promise(res => {
  const t0 = performance.now();
  (function w() {
    const ok = window.__designer && window.__designer.S3 && window.__designer.S3.ready;
    if ((ok && performance.now() - t0 > 2500) || performance.now() - t0 > 25000) res();
    else setTimeout(w, 300);
  })();
}));
await sleep(1500);

// 页内逐帧度量探针（和录像同一时钟）
await ev(() => {
  window.__tlog = []; window.__t0 = performance.now();
  window.__tsample = () => {
    try {
      const s = document.getElementById('stage');
      const p2 = document.getElementById('pane2d'), p3 = document.getElementById('pane3d');
      const c3 = document.getElementById('c3d');
      const r3 = p3.getBoundingClientRect(), r2 = p2.getBoundingClientRect();
      window.__tlog.push({
        t: Math.round(performance.now() - window.__t0),
        view: s ? s.dataset.view : '?',
        p2: [Math.round(r2.width), Math.round(r2.height)],
        p3: [Math.round(r3.width), Math.round(r3.height)],
        p3tr: getComputedStyle(p3).transform.slice(0, 44),
        p3op: getComputedStyle(p3).opacity.slice(0, 5),
        p2tr: getComputedStyle(p2).transform.slice(0, 44),
        c3: c3 ? [c3.width, c3.height, c3.clientWidth, c3.clientHeight] : null
      });
    } catch (e) { /* 忽略采样失败 */ }
  };
  window.__tTimer = setInterval(window.__tsample, 50);
});

// 开始 screencast 录制
const cdp = await page.createCDPSession();
const shots = [];
const t0 = Date.now();
cdp.on('Page.screencastFrame', async f => {
  shots.push({ t: Date.now() - t0, data: f.data });
  try { await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }); } catch { /* 断开后忽略 */ }
});
await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 70, maxWidth: 960, maxHeight: 600, everyNthFrame: 1 });

const seq = [
  ['3d', '#viewSeg [data-view="3d"]', 3000],
  ['split', '#viewSeg [data-view="split"]', 3000],
  ['2d', '#viewSeg [data-view="2d"]', 3000],
  ['split2', '#viewSeg [data-view="split"]', 2500],
  ['3d-final', '#viewSeg [data-view="3d"]', 3000]
];
for (const [name, sel, wait] of seq) {
  await page.click(sel);
  await sleep(wait);
  await ev(v => window.__tlog.push({ t: Math.round(performance.now() - window.__t0), mark: v }), 'after-click-' + name);
}
await cdp.send('Page.stopScreencast').catch(() => { });
await sleep(400);
await ev(() => clearInterval(window.__tTimer));
const metrics = await ev(() => window.__tlog);

// 落盘
shots.forEach((f, i) => fs.writeFileSync(path.join(FRAMES, 'frame-' + String(i + 1).padStart(4, '0') + '.jpg'), Buffer.from(f.data, 'base64')));
fs.writeFileSync(path.join(OUT, 'metrics.json'), JSON.stringify(metrics, null, 1));
const fps = shots.length / ((shots[shots.length - 1]?.t || 1) / 1000);
const summary = {
  frames: shots.length, seconds: Math.round((shots[shots.length - 1]?.t || 0) / 100) / 10,
  fps: Math.round(fps * 10) / 10, errors: [...new Set(errs)].slice(0, 8)
};
fs.writeFileSync(path.join(OUT, 'summary.json'), JSON.stringify(summary, null, 1));

// 回放页：按真实时间戳播放帧序列，可暂停/拖动/0.25x 慢放
const names = shots.map((_, i) => 'frames/frame-' + String(i + 1).padStart(4, '0') + '.jpg');
const times = shots.map(f => f.t);
const html = `<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>切换动效回放</title>
<style>body{margin:0;background:#111;color:#eee;font:13px system-ui;display:flex;flex-direction:column;align-items:center;gap:8px;padding:12px}
img{max-width:min(1200px,96vw);max-height:72vh;background:#000;border-radius:8px}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:center}
button{padding:6px 14px;border-radius:6px;border:0;background:#2f6fed;color:#fff;cursor:pointer}
input[type=range]{width:min(900px,90vw)}select{padding:5px;border-radius:6px}
#ts{font-variant-numeric:tabular-nums;color:#9cf}</style></head><body>
<img id="v" alt="replay"><div class="row"><button id="p">⏸ 暂停</button>
<input id="s" type="range" min="0" max="${names.length - 1}" value="0" step="1">
<select id="sp"><option value="1">1x</option><option value="0.5">0.5x</option><option value="0.25" selected>0.25x 慢放</option></select>
<span id="ts"></span></div>
<div class="row"><span>2D→3D→分屏→2D→分屏→3D，拖动滑杆逐帧看拉伸/顿挫那一帧</span></div>
<script>const F=${JSON.stringify(names)},T=${JSON.stringify(times)};
const v=document.getElementById('v'),s=document.getElementById('s'),p=document.getElementById('p'),ts=document.getElementById('ts');
let i=0,playing=true,timer=null,speed=()=>parseFloat(document.getElementById('sp').value);
function show(){v.src=F[i];s.value=i;ts.textContent='#'+(i+1)+'/'+F.length+'  t='+T[i]+'ms';}
function tick(){if(!playing)return;if(i<F.length-1){const dt=(T[i+1]-T[i])/speed();i++;show();timer=setTimeout(tick,Math.max(16,dt));}else{playing=false;p.textContent='▶ 播放';}}
p.onclick=()=>{playing=!playing;p.textContent=playing?'⏸ 暂停':'▶ 播放';if(playing)tick();else clearTimeout(timer);};
s.oninput=()=>{i=+s.value;show();};document.getElementById('sp').onchange=()=>{};
show();tick();</script></body></html>`;
fs.writeFileSync(path.join(OUT, 'playback.html'), html);

console.log(JSON.stringify(summary));
await b.close();
await closeServer();
