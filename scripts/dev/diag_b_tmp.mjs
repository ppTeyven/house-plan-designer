import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'] });
const page = await b.newPage();
const errs = [];
page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message.slice(0, 400)));
page.on('console', m => { if (m.type() === 'error' && !/favicon|404/.test(m.text())) errs.push('CONSOLE: ' + m.text().slice(0, 300)); });
await page.goto('http://127.0.0.1:8899/template.html?debug', { waitUntil: 'load' });
await page.waitForFunction(() => window.__designer, { timeout: 60000 });
const sleep = ms => new Promise(r => setTimeout(r, ms));
await sleep(7000);
const ev = (f, ...a) => page.evaluate(f, ...a);
const out = {};
out.keys = await ev(() => Object.keys(window.__designer || {}));
out.s3keys = await ev(() => { try { return Object.keys(window.__designer.S3 || {}).slice(0, 80); } catch (e) { return ['ERR ' + e.message]; } });
// 1. smart 中控点击
try {
  await page.click('#smartBtn');
  await sleep(4000);
  out.smart = await ev(() => ({ on: document.body.classList.contains('smart-mode'), show: !!document.querySelector('.smart-ui.show'), smartBtnOn: document.querySelector('#smartBtn')?.className }));
} catch (e) { out.smart = { clickFail: e.message.slice(0, 200) }; }
// 2. 管线/风格按钮选中态
try {
  await ev(() => document.querySelector('#smartBtn') && (location.hash = ''));
  await page.click('#mepBtn');
  await sleep(800);
  out.mep = await ev(() => ({ cls: document.querySelector('#mepBtn')?.className, on: document.querySelector('#mepBtn')?.classList.contains('on') }));
  await page.click('#lookBtn');
  await sleep(800);
  out.look = await ev(() => ({ popOpen: document.querySelector('#lookPop')?.classList.contains('open'), cls: document.querySelector('#lookBtn')?.className }));
} catch (e) { out.mepLookFail = e.message.slice(0, 200); }
// 3. 3D 平移拖拽：记录相机 target 变化
await ev(() => window.__designer.setView('3d'));
await sleep(2500);
out.v3d = await ev(() => { const d = window.__designer; return { view: d.app?.view, stage: document.getElementById('stage')?.dataset.view }; });
const cam0 = await ev(() => { try { const S = window.__designer.S3; S.renderNow(); return { ok: true }; } catch (e) { return { ok: false, err: String(e).slice(0, 200) }; } });
out.cam0 = cam0;
// puppeteer 真实拖拽 c3d 中心
try {
  const r = await ev(() => { const c = document.querySelector('#c3d').getBoundingClientRect(); return { x: c.x + c.width / 2, y: c.y + c.height / 2 }; });
  const tgt0 = await ev(() => window.__smart ? 'has-smart' : 'no-smart');
  await page.mouse.move(r.x, r.y);
  await page.mouse.down();
  await page.mouse.move(r.x + 120, r.y + 60, { steps: 12 });
  await page.mouse.up();
  await sleep(1200);
  out.drag3d = { from: r, tgt0 };
} catch (e) { out.drag3d = { fail: e.message.slice(0, 200) }; }
// 4. 分屏 2D/3D 几何 + 平移
await ev(() => window.__designer.setView('split'));
await sleep(2500);
out.split = await ev(() => {
  const p2 = document.getElementById('pane2d').getBoundingClientRect(), p3 = document.getElementById('pane3d').getBoundingClientRect();
  const c2 = document.querySelector('#c2d'), c3 = document.querySelector('#c3d');
  const r2 = c2.getBoundingClientRect(), r3 = c3.getBoundingClientRect();
  const v = window.__designer.view || {};
  return { p2: [Math.round(p2.width), Math.round(p2.height)], p3: [Math.round(p3.width), Math.round(p3.height)], c2css: [Math.round(r2.width), Math.round(r2.height)], c3css: [Math.round(r3.width), Math.round(r3.height)], c2px: [c2.width, c2.height], c3px: [c3.width, c3.height], Se: { s: v.s, ox: Math.round(v.ox), oy: Math.round(v.oy), W: Math.round(v.W), H: Math.round(v.H) } };
});
// 分屏拖 2D 看是否动
try {
  const r = await ev(() => { const c = document.querySelector('#c2d').getBoundingClientRect(); return { x: c.x + c.width / 2, y: c.y + c.height / 2 }; });
  const se0 = await ev(() => { const v = window.__designer.view; return { ox: v.ox, oy: v.oy }; });
  await page.mouse.move(r.x, r.y);
  await page.mouse.down();
  await page.mouse.move(r.x + 80, r.y + 40, { steps: 10 });
  await page.mouse.up();
  await sleep(1000);
  const se1 = await ev(() => { const v = window.__designer.view; return { ox: v.ox, oy: v.oy }; });
  out.drag2dSplit = { se0, se1, moved: Math.hypot(se1.ox - se0.ox, se1.oy - se0.oy) };
} catch (e) { out.drag2dSplit = { fail: e.message.slice(0, 200) }; }
// 5. 漫游进入
try {
  await ev(() => window.__designer.setView('3d'));
  await sleep(2000);
  await page.click('#camSeg [data-cam="fp"]');
  await sleep(4500);
  out.fp = await ev(() => { const d = window.__designer; return { active: !!d.S3?.fp?.active, view: d.app?.view }; });
} catch (e) { out.fp = { fail: e.message.slice(0, 300) }; }
// 6. 全景/实景按钮存在性
out.btns = await ev(() => ({ pano: !!document.querySelector('#panoBtn'), xr: !!document.querySelector('#xr-btn'), walkCtl: !!document.querySelector('#walkCtl.show'), camFp: !!document.querySelector('#camSeg [data-cam="fp"]') }));
out.errs = [...new Set(errs)].slice(0, 12);
console.log(JSON.stringify(out, null, 1));
await b.close();
