import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'] });
const page = await b.newPage();
const errs = [];
page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message.slice(0, 300)));
await page.goto('http://127.0.0.1:8899/template.html?debug', { waitUntil: 'load' });
await page.waitForFunction(() => window.__designer, { timeout: 60000 });
const sleep = ms => new Promise(r => setTimeout(r, ms));
await sleep(7000);
const ev = (f, ...a) => page.evaluate(f, ...a);
const out = {};
// 1. smart open via real click
await ev(() => window.__designer.setView('3d'));
await sleep(2500);
try { await page.click('#smartBtn'); await sleep(3500); } catch (e) { out.smartClick = 'FAIL ' + e.message.slice(0, 150); }
out.smart = await ev(() => ({ body: document.body.classList.contains('smart-mode'), show: !!document.querySelector('.smart-ui.show'), cls: document.querySelector('#smartBtn').className }));
await ev(() => window.__designer.setView('2d'));
await sleep(1500);
// 2. mep/look via evaluate (overlay may block real click)
out.btn = await ev(() => { const o = {}; document.querySelector('#mepBtn').click(); o.mep = document.querySelector('#mepBtn').className; document.querySelector('#lookBtn').click(); o.look = document.querySelector('#lookBtn').className; o.pop = document.querySelector('#lookPop').classList.contains('open'); document.querySelector('#lookBtn').click(); return o; });
// 3. 3d left-drag pans (target moves) ; right-drag also pans
await ev(() => window.__designer.setView('3d'));
await sleep(2500);
const r = await ev(() => { const c = document.querySelector('#c3d').getBoundingClientRect(); return { x: c.x + c.width / 2, y: c.y + c.height / 2 }; });
const t0 = await ev(() => { const s = window.__designer.S3.sceneRefs(); return [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x => +x.toFixed(3)); });
await page.mouse.move(r.x, r.y); await page.mouse.down(); await page.mouse.move(r.x + 120, r.y + 40, { steps: 12 }); await page.mouse.up(); await sleep(1500);
const t1 = await ev(() => { const s = window.__designer.S3.sceneRefs(); return { tgt: [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x => +x.toFixed(3)), left: s.controls.mouseButtons.LEFT }; });
await page.mouse.move(r.x, r.y); await page.mouse.down({ button: 'right' }); await page.mouse.move(r.x + 100, r.y + 30, { steps: 10 }); await page.mouse.up({ button: 'right' }); await sleep(1200);
const t2 = await ev(() => { const s = window.__designer.S3.sceneRefs(); return [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x => +x.toFixed(3)); });
out.drag3 = { t0, t1, t2 };
// 4. walk via direct call
out.fp = await ev(() => { try { window.__designer.S3.enterFP(); return { ok: true }; } catch (e) { return { ok: false, err: String(e).slice(0, 200) }; } });
await sleep(4500);
out.fpAfter = await ev(() => ({ active: !!window.__designer.S3.fp.active, walkShow: !!document.querySelector('#walkCtl.show'), hint: !!document.querySelector('.fphint.show'), view: window.__designer.app.view }));
await ev(() => window.__designer.S3.exitFP());
await sleep(2500);
// 5. split: geometry + sync + pan-only + walk hidden
await ev(() => window.__designer.setView('split'));
await sleep(2500);
out.split = await ev(() => {
  const d = window.__designer, v = d.view;
  const p2 = document.getElementById('pane2d').getBoundingClientRect(), p3 = document.getElementById('pane3d').getBoundingClientRect();
  const b = d.app.geo.bounds;
  let proj = null;
  try {
    const cs = [[b.x, b.y], [b.x + b.w, b.y], [b.x, b.y + b.h], [b.x + b.w, b.y + b.h]].map(([x, y]) => [x * v.s + v.ox, y * v.s + v.oy]);
    proj = { minX: Math.round(Math.min(...cs.map(p => p[0]))), maxX: Math.round(Math.max(...cs.map(p => p[0]))), minY: Math.round(Math.min(...cs.map(p => p[1]))), maxY: Math.round(Math.max(...cs.map(p => p[1]))) };
  } catch (e) { proj = { err: String(e).slice(0, 100) }; }
  let cam = null, ctl = null;
  try { const s = d.S3.sceneRefs(); cam = [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x => +x.toFixed(3)); ctl = { rot: s.controls.enableRotate, left: s.controls.mouseButtons.LEFT, en: s.controls.enabled }; } catch (e) {}
  return { W: Math.round(v.W), Se: { s: v.s, ox: Math.round(v.ox), oy: Math.round(v.oy) }, p2: [Math.round(p2.width), Math.round(p2.height)], p3: [Math.round(p3.width), Math.round(p3.height)], proj, cam, ctl,
    fpGone: !document.querySelector('#camSeg [data-cam="fp"]')?.offsetParent, walkGone: !document.querySelector('#walkCtl.show'),
    panoGone: !document.querySelector('#panoBtn'), xrGone: !document.querySelector('#xr-btn') };
});
// split 3d->2d sync: drag 3d, check Se moved
try {
  const rr = await ev(() => { const c = document.querySelector('#c3d').getBoundingClientRect(); return { x: c.x + c.width / 2, y: c.y + c.height / 2 }; });
  const s0 = await ev(() => ({ ox: window.__designer.view.ox, oy: window.__designer.view.oy }));
  await page.mouse.move(rr.x, rr.y); await page.mouse.down(); await page.mouse.move(rr.x + 90, rr.y + 25, { steps: 10 }); await page.mouse.up(); await sleep(1200);
  const s1 = await ev(() => ({ ox: window.__designer.view.ox, oy: window.__designer.view.oy }));
  const c1 = await ev(() => { const s = window.__designer.S3.sceneRefs(); return [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x => +x.toFixed(3)); });
  out.splitSync32 = { s0, s1, cam: c1, moved2d: Math.hypot(s1.ox - s0.ox, s1.oy - s0.oy) };
} catch (e) { out.splitSync32 = { fail: e.message.slice(0, 150) }; }
// split 2d->3d sync: wheel on 2d? use emit view via drag 2d
try {
  const rr = await ev(() => { const c = document.querySelector('#c2d').getBoundingClientRect(); return { x: c.x + c.width / 2, y: c.y + c.height / 2 }; });
  const c0 = await ev(() => { const s = window.__designer.S3.sceneRefs(); return [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x => +x.toFixed(3)); });
  await page.mouse.move(rr.x, rr.y); await page.mouse.down(); await page.mouse.move(rr.x + 60, rr.y + 20, { steps: 8 }); await page.mouse.up(); await sleep(1200);
  const c1 = await ev(() => { const s = window.__designer.S3.sceneRefs(); return [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x => +x.toFixed(3)); });
  out.splitSync23 = { c0, c1, moved3d: c0.join() !== c1.join() };
} catch (e) { out.splitSync23 = { fail: e.message.slice(0, 150) }; }
out.errs = [...new Set(errs)].slice(0, 10);
console.log(JSON.stringify(out, null, 1));
await b.close();
