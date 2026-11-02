import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'] });
const page = await b.newPage();
const errs = [];
page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message.slice(0, 400)));
page.on('console', m => { if (m.type() === 'error' && !/favicon|404|JSHandle/.test(m.text())) errs.push('CONSOLE: ' + m.text().slice(0, 200)); });
await page.goto('http://127.0.0.1:8899/template.html?debug', { waitUntil: 'load' });
await page.waitForFunction(() => window.__designer, { timeout: 60000 });
const sleep = ms => new Promise(r => setTimeout(r, ms));
await sleep(7000);
const ev = (f, ...a) => page.evaluate(f, ...a);
const out = {};
const poll = () => ev(() => { const d = window.__designer; let anim = null, en = null; try { anim = d.S3.isAnimating(); } catch (e) { anim = 'err'; } try { en = d.S3.sceneRefs().controls.enabled; } catch (e) { en = 'err'; } return { view: d.app.view, tr: d.app.transitioning, anim, en, fp: !!d.S3.fp.active }; });
out.t0_2d = await poll();
// 2d->3d: poll tween state
await ev(() => window.__designer.setView('3d'));
out.poll3d = [];
for (let i = 0; i < 6; i++) { await sleep(500); out.poll3d.push(await poll()); }
// 3d drag
try {
  const r = await ev(() => { const c = document.querySelector('#c3d').getBoundingClientRect(); return { x: c.x + c.width / 2, y: c.y + c.height / 2 }; });
  const t0 = await ev(() => { const s = window.__designer.S3.sceneRefs(); return [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x => +x.toFixed(3)); });
  await page.mouse.move(r.x, r.y); await page.mouse.down(); await page.mouse.move(r.x + 120, r.y + 40, { steps: 12 }); await page.mouse.up(); await sleep(1500);
  const t1 = await ev(() => { const s = window.__designer.S3.sceneRefs(); return [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x => +x.toFixed(3)); });
  out.drag3 = { t0, t1, moved: t0.join() !== t1.join() };
} catch (e) { out.drag3 = { fail: e.message.slice(0, 150) }; }
// smart direct call with stack
out.smartCall = await ev(async () => { try { await window.__smart.setSmart(true); return { ok: true }; } catch (e) { return { ok: false, err: String(e).slice(0, 300), stack: (e.stack || '').slice(0, 800) }; } });
await sleep(2500);
out.smartUI = await ev(() => ({ body: document.body.classList.contains('smart-mode'), show: !!document.querySelector('.smart-ui.show') }));
out.smartOff = await ev(async () => { try { await window.__smart.setSmart(false); return { ok: true }; } catch (e) { return { ok: false, err: String(e).slice(0, 200) }; } });
await sleep(1200);
// look/mep via evaluate click (avoid overlay issues; smart now off)
out.btnClick = await ev(() => {
  const r = {};
  try { document.querySelector('#mepBtn').click(); r.mep = document.querySelector('#mepBtn').className; } catch (e) { r.mep = 'ERR'; }
  try { document.querySelector('#lookBtn').click(); r.lookPop = document.querySelector('#lookPop')?.classList.contains('open'); r.look = document.querySelector('#lookBtn').className; document.querySelector('#lookBtn').click(); } catch (e) { r.look = 'ERR'; }
  return r;
});
// split geometry
await ev(() => window.__designer.setView('split'));
await sleep(2500);
out.split = await ev(() => { const d = window.__designer, v = d.view; const p2 = document.getElementById('pane2d').getBoundingClientRect();
  let cam = null; try { const s = d.S3.sceneRefs(); cam = { tgt: [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x => +x.toFixed(3)), pos: [s.camera.position.x, s.camera.position.y, s.camera.position.z].map(x => +x.toFixed(2)) }; } catch (e) {}
  return { Se: { s: v.s, ox: Math.round(v.ox * 10) / 10, oy: Math.round(v.oy * 10) / 10, W: Math.round(v.W), H: Math.round(v.H) }, p2: [Math.round(p2.width), Math.round(p2.height)], cam, poll: null }; });
out.split.poll = await poll();
// enterFP direct
out.fpCall = await ev(() => { try { window.__designer.S3.enterFP(); return { ok: true }; } catch (e) { return { ok: false, err: String(e).slice(0, 300), stack: (e.stack || '').slice(0, 600) }; } });
await sleep(4000);
out.fpAfter = await poll();
out.errs = [...new Set(errs)].slice(0, 12);
console.log(JSON.stringify(out, null, 1));
await b.close();
