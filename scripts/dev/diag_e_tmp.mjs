import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'] });
const page = await b.newPage();
page.on('pageerror', e => console.log('PAGEERROR ' + e.message.slice(0,300)));
await page.goto('http://127.0.0.1:8899/template.html?debug', { waitUntil: 'load' });
await page.waitForFunction(() => window.__designer, { timeout: 60000 });
const sleep = ms => new Promise(r => setTimeout(r, ms));
await sleep(7000);
const ev = (f, ...a) => page.evaluate(f, ...a);
// 3d left-drag: check camera pos change (rotate) vs target (pan)
await ev(() => window.__designer.setView('3d'));
await sleep(2500);
const c0 = await ev(() => { const s = window.__designer.S3.sceneRefs(); return { tgt: [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x=>+x.toFixed(3)), pos: [s.camera.position.x, s.camera.position.y, s.camera.position.z].map(x=>+x.toFixed(3)), en: s.controls.enabled, lr: s.controls.mouseButtons.LEFT, rot: s.controls.enableRotate, pan: s.controls.enablePan }; });
const r = await ev(() => { const c = document.querySelector('#c3d').getBoundingClientRect(); return { x: c.x + c.width/2, y: c.y + c.height/2 }; });
await page.mouse.move(r.x, r.y); await page.mouse.down(); await page.mouse.move(r.x+120, r.y+40, {steps:12}); await page.mouse.up(); await sleep(1500);
const c1 = await ev(() => { const s = window.__designer.S3.sceneRefs(); return { tgt: [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x=>+x.toFixed(3)), pos: [s.camera.position.x, s.camera.position.y, s.camera.position.z].map(x=>+x.toFixed(3)), en: s.controls.enabled }; });
console.log(JSON.stringify({c0, c1}, null, 1));
// right-drag pan check
await page.mouse.move(r.x, r.y); await page.mouse.click(r.x, r.y, {button: 'right'});
await page.mouse.move(r.x, r.y); await page.mouse.down({button:'right'}); await page.mouse.move(r.x+100, r.y+30, {steps:10}); await page.mouse.up({button:'right'}); await sleep(1200);
const c2 = await ev(() => { const s = window.__designer.S3.sceneRefs(); return { tgt: [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x=>+x.toFixed(3)) }; });
console.log(JSON.stringify({rightPan: c2}, null, 1));
// split: Bi age trace
await ev(() => window.__designer.setView('split'));
for (let i=0;i<5;i++){ await sleep(800);
  const p = await ev(() => { const d = window.__designer; let anim=null,en=null,biAge=null; try{anim=d.S3.isAnimating();}catch(e){} try{en=d.S3.sceneRefs().controls.enabled;}catch(e){} return {view:d.app.view,tr:d.app.transitioning,anim,en}; });
  console.log('split poll', i, JSON.stringify(p));
}
await b.close();
