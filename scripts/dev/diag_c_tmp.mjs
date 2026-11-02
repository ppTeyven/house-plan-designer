import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'] });
const page = await b.newPage();
const errs = [];
page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message.slice(0, 500)));
page.on('console', m => { if (m.type() === 'error' && !/favicon|404|JSHandle/.test(m.text())) errs.push('CONSOLE: ' + m.text().slice(0, 200)); });
await page.goto('http://127.0.0.1:8899/template.html?debug', { waitUntil: 'load' });
await page.waitForFunction(() => window.__designer, { timeout: 60000 });
const sleep = ms => new Promise(r => setTimeout(r, ms));
await sleep(7000);
const ev = (f, ...a) => page.evaluate(f, ...a);
const out = {};
// 基线: 2d fit
out.d2 = await ev(() => { const v = window.__designer.view, g = window.__designer.app?.geo?.bounds || window.__designer.bld?.bounds || null;
  const p2 = document.getElementById('pane2d').getBoundingClientRect();
  return { Se: { s: v.s, ox: Math.round(v.ox), oy: Math.round(v.oy), W: Math.round(v.W), H: Math.round(v.H) }, pane: [Math.round(p2.width), Math.round(p2.height)], bounds: g ? [g.x, g.y, g.w, g.h] : null }; });
// 切 3d, 再点 smart/mep/look(此时 pane3d 可点)
await ev(() => window.__designer.setView('3d'));
await sleep(2500);
out.v3 = await ev(() => ({ view: window.__designer.app.view, stage: document.getElementById('stage').dataset.view }));
try { await page.click('#smartBtn'); await sleep(3500); } catch (e) { out.smartClick = 'FAIL ' + e.message.slice(0, 150); }
out.smart = await ev(() => { const d = window.__designer; let info = 'no-smart';
  try { info = JSON.stringify({ on: d.S3.smartUI ? 'has' : 'no' }); } catch (e) {}
  return { bodySmart: document.body.classList.contains('smart-mode'), uiShow: !!document.querySelector('.smart-ui.show'), smartInfo: info,
    smErr: (window.__smErr || null) }; });
try { await page.click('#mepBtn'); await sleep(800); } catch (e) { out.mepClick = 'FAIL ' + e.message.slice(0, 150); }
out.mep = await ev(() => ({ cls: document.querySelector('#mepBtn')?.className, hasOn: document.querySelector('#mepBtn')?.classList.contains('on') }));
try { await page.click('#lookBtn'); await sleep(800); } catch (e) { out.lookClick = 'FAIL ' + e.message.slice(0, 150); }
out.look = await ev(() => ({ pop: document.querySelector('#lookPop')?.classList.contains('open'), cls: document.querySelector('#lookBtn')?.className, hasOn: document.querySelector('#lookBtn')?.classList.contains('on') }));
// 3d 拖拽: 读相机 target 变化
out.camA = await ev(() => { const t = window.__designer.S3.three?.controls?.target || window.__designer.S3.sceneRefs?.()?.camera?.position; return 'skip'; });
out.camT = await ev(() => { try { const s = window.__designer.S3.sceneRefs(); return { tgt: s.controls?.target ? [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(v => +v.toFixed(3)) : null, cam: s.camera?.position ? [s.camera.position.x, s.camera.position.y, s.camera.position.z].map(v => +v.toFixed(2)) : null, enabled: s.controls?.enabled ?? null, enablePan: s.controls?.enablePan ?? null, enableRotate: s.controls?.enableRotate ?? null, mouseL: s.controls?.mouseButtons?.LEFT ?? null }; } catch (e) { return { err: String(e).slice(0, 200) }; } });
try {
  const r = await ev(() => { const c = document.querySelector('#c3d').getBoundingClientRect(); return { x: c.x + c.width / 2, y: c.y + c.height / 2 }; });
  await page.mouse.move(r.x, r.y); await page.mouse.down(); await page.mouse.move(r.x + 120, r.y + 40, { steps: 12 }); await page.mouse.up(); await sleep(1500);
  out.camT2 = await ev(() => { try { const s = window.__designer.S3.sceneRefs(); return { tgt: [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(v => +v.toFixed(3)), cam: [s.camera.position.x, s.camera.position.y, s.camera.position.z].map(v => +v.toFixed(2)) }; } catch (e) { return { err: String(e).slice(0, 200) }; } });
} catch (e) { out.drag3 = 'FAIL ' + e.message.slice(0, 150); }
// 漫游进入(3d 下点 camSeg fp)
try { await page.click('#camSeg [data-cam="fp"]'); await sleep(5000); } catch (e) { out.fpClick = 'FAIL ' + e.message.slice(0, 150); }
out.fp = await ev(() => { const d = window.__designer; return { active: !!d.S3?.fp?.active, view: d.app?.view, walkShow: !!document.querySelector('#walkCtl.show'), hint: !!document.querySelector('.fphint.show') }; });
// 退出漫游 Esc
try { await page.keyboard.press('Escape'); await sleep(2500); } catch (e) {}
out.fpAfter = await ev(() => ({ active: !!window.__designer.S3?.fp?.active }));
// 分屏几何 + 2d 包络投影(是否全显/居中)
await ev(() => window.__designer.setView('split'));
await sleep(2500);
out.split = await ev(() => {
  const d = window.__designer, v = d.view;
  const p2 = document.getElementById('pane2d').getBoundingClientRect(), p3 = document.getElementById('pane3d').getBoundingClientRect();
  const b = d.app?.geo?.bounds;
  let proj = null;
  try {
    const s = v.s, ox = v.ox, oy = v.oy;
    const corners = [[b.x, b.y], [b.x + b.w, b.y], [b.x, b.y + b.h], [b.x + b.w, b.y + b.h]];
    const pts = corners.map(([x, y]) => [x * s + ox, y * s + oy]);
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
    proj = { minX: Math.round(Math.min(...xs)), maxX: Math.round(Math.max(...xs)), minY: Math.round(Math.min(...ys)), maxY: Math.round(Math.max(...ys)) };
  } catch (e) { proj = { err: String(e).slice(0, 150) }; }
  let cam = null;
  try { const s = d.S3.sceneRefs(); cam = { tgt: [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x => +x.toFixed(3)) }; } catch (e) {}
  return { Se: { s: v.s, ox: Math.round(v.ox), oy: Math.round(v.oy), W: Math.round(v.W), H: Math.round(v.H) }, p2: [Math.round(p2.width), Math.round(p2.height)], p3: [Math.round(p3.width), Math.round(p3.height)], bounds: b ? [b.x, b.y, b.w, b.h] : null, proj, cam,
    fpVisible: !!document.querySelector('#camSeg [data-cam="fp"]')?.offsetParent, walkHtml: !!document.querySelector('#walkCtl'), panoVisible: !!document.querySelector('#panoBtn')?.offsetParent };
});
// 分屏 3d 拖拽是否带动相机
try {
  const r = await ev(() => { const c = document.querySelector('#c3d').getBoundingClientRect(); return { x: c.x + c.width / 2, y: c.y + c.height / 2 }; });
  const t0 = await ev(() => { const s = window.__designer.S3.sceneRefs(); return [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x => +x.toFixed(3)); });
  await page.mouse.move(r.x, r.y); await page.mouse.down(); await page.mouse.move(r.x + 100, r.y + 30, { steps: 10 }); await page.mouse.up(); await sleep(1200);
  const t1 = await ev(() => { const s = window.__designer.S3.sceneRefs(); return [s.controls.target.x, s.controls.target.y, s.controls.target.z].map(x => +x.toFixed(3)); });
  out.splitDrag3 = { t0, t1 };
} catch (e) { out.splitDrag3 = { fail: e.message.slice(0, 150) }; }
out.errs = [...new Set(errs)].slice(0, 12);
console.log(JSON.stringify(out, null, 1));
await b.close();
