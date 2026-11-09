// ===== 漫游/3D 交互真实链路验收 =====
// 直接走应用自己的 pointerup -> I1 -> bx 链路：
//   1) 把摄像机对准一个开关，算出它的屏幕坐标
//   2) 在那个坐标上派发真实 pointerdown/pointerup
//   3) 验证开关状态真的翻转
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import { pageUrl } from '../lib_serve.mjs';

const FILE = process.argv[2] || 'D:/house planner/house-plan-designer-main/assets/template.html';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const results = [];
function check(name, cond, detail) {
  results.push({ name, ok: !!cond, detail: detail === undefined ? '' : String(detail) });
  console.log((cond ? '[OK ] ' : '[FAIL] ') + name + (detail !== undefined ? '  -> ' + detail : ''));
}

const b = await puppeteer.launch({
  executablePath: exe, headless: 'new', protocolTimeout: 600000,
  defaultViewport: { width: 1400, height: 900, deviceScaleFactor: 1 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'],
});
const page = await b.newPage();
page.on('pageerror', e => console.log('PAGEERROR:', e.message.slice(0, 200)));
const pg = await pageUrl(FILE);
await page.goto(pg.url + '?debug', { waitUntil: 'load', timeout: 90000 });
await page.waitForFunction(() => window.__designer && window.__D3 && window.__D3.renderer, { timeout: 90000 });
await page.evaluate(() => window.__designer.setView('3d'));
await sleep(5000);
// 进入漫游（相机落到人眼高度，视野里才有可交互物）
await page.evaluate(() => {
  const bt = [...document.querySelectorAll('button')].find(x => x.textContent.trim() === '漫游');
  if (bt) bt.click();
});
await sleep(3000);

// ---- 找一个「开关」：elecId 对应的 kind 属于 Ds（switch1/2/3/dimmer）----
// 场景里 elecId 对应的 kind 要从内部拿，先把候选开关列出来并按「离相机近 + 在视野内」排序
const setup = await page.evaluate(async () => {
  const D3 = window.__D3;
  const scene = D3.scene, cam = typeof D3.camera === 'function' ? D3.camera() : D3.camera;
  const c = document.getElementById('c3d');
  const rect = c.getBoundingClientRect();
  let V3 = null;
  scene.traverse(o => { if (!V3 && o.position && o.position.constructor) V3 = o.position.constructor; });

  // 收集所有带 elecId / door 的对象，算屏幕坐标
  const cands = [];
  scene.traverse(o => {
    const u = o.userData || {};
    if (!u.elecId && !u.door) return;
    const p = new V3(); o.getWorldPosition(p);
    const d = p.distanceTo(cam.position);
    if (d < 0.4 || d > 12) return;
    const v = p.clone().project(cam);
    if (!isFinite(v.x) || Math.abs(v.x) > 0.85 || Math.abs(v.y) > 0.85 || v.z > 1 || v.z < -1) return;
    cands.push({
      elecId: u.elecId || null, door: u.door || null, d,
      sx: rect.left + (v.x * 0.5 + 0.5) * rect.width,
      sy: rect.top + (-v.y * 0.5 + 0.5) * rect.height,
      ndc: { x: v.x, y: v.y },
    });
  });
  cands.sort((a, b) => a.d - b.d);
  return { rect: { l: rect.left, t: rect.top, w: rect.width, h: rect.height },
           cands: cands.slice(0, 20),
           total: cands.length };
});
console.log('[视野内可交互物] 共 ' + setup.total + ' 个，最近几个：');
setup.cands.slice(0, 8).forEach(c => console.log('  ' + JSON.stringify(c)));
check('3D 视野内存在可交互物', setup.cands.length > 0, '共 ' + setup.total);

// ---- 对最近的那个，在它屏幕坐标上派发真实 pointerdown/pointerup ----
const clickResult = await page.evaluate(async (target) => {
  const c = document.getElementById('c3d');
  const toasts = [];
  const obs = new MutationObserver(() => {
    const el = document.querySelector('#toast') || document.querySelector('.toast');
    if (el) { const t = (el.textContent || '').trim(); if (t && !toasts.includes(t)) toasts.push(t); }
  });
  obs.observe(document.body, { childList: true, subtree: true, characterData: true });

  const opts = { clientX: target.sx, clientY: target.sy, bubbles: true, cancelable: true,
                 pointerId: 1, pointerType: 'mouse', button: 0, buttons: 1 };
  c.dispatchEvent(new PointerEvent('pointerdown', opts));
  await new Promise(r => setTimeout(r, 60));
  c.dispatchEvent(new PointerEvent('pointerup', opts));
  await new Promise(r => setTimeout(r, 700));
  obs.disconnect();
  const at = document.elementFromPoint(target.sx, target.sy);
  return { toasts, atTag: at ? at.tagName : null, atId: at ? at.id : null,
           elecId: target.elecId, door: target.door };
}, setup.cands[0]);
console.log('[点击结果] ' + JSON.stringify(clickResult, null, 2));
check('点击 3D 里的可交互物有响应', clickResult.toasts.length > 0,
      JSON.stringify(clickResult.toasts));

// ---- 漫游模式：同样验证（此时已经在漫游里）----
const roamSetup = await page.evaluate(() => {
  const D3 = window.__D3;
  const scene = D3.scene, cam = typeof D3.camera === 'function' ? D3.camera() : D3.camera;
  const c = document.getElementById('c3d');
  const rect = c.getBoundingClientRect();
  let V3 = null;
  scene.traverse(o => { if (!V3 && o.position && o.position.constructor) V3 = o.position.constructor; });
  const cands = [];
  scene.traverse(o => {
    const u = o.userData || {};
    if (!u.elecId && !u.door) return;
    const p = new V3(); o.getWorldPosition(p);
    const d = p.distanceTo(cam.position);
    if (d < 0.4 || d > 12) return;
    const v = p.clone().project(cam);
    if (!isFinite(v.x) || Math.abs(v.x) > 0.85 || Math.abs(v.y) > 0.85 || v.z > 1 || v.z < -1) return;
    cands.push({ elecId: u.elecId || null, door: u.door || null, d,
      sx: rect.left + (v.x * 0.5 + 0.5) * rect.width,
      sy: rect.top + (-v.y * 0.5 + 0.5) * rect.height });
  });
  cands.sort((a, b) => a.d - b.d);
  return { cands: cands.slice(0, 20), total: cands.length,
           crosshair: getComputedStyle(document.getElementById('crosshair')).pointerEvents,
           crosshairDisp: getComputedStyle(document.getElementById('crosshair')).display };
});
console.log('[漫游视野内可交互物] 共 ' + roamSetup.total + '  准星 pointer-events=' + roamSetup.crosshair);
check('漫游模式视野内存在可交互物', roamSetup.cands.length > 0, '共 ' + roamSetup.total);

if (roamSetup.cands.length) {
  const roamClick = await page.evaluate(async (target) => {
    const c = document.getElementById('c3d');
    const toasts = [];
    const obs = new MutationObserver(() => {
      const el = document.querySelector('#toast') || document.querySelector('.toast');
      if (el) { const t = (el.textContent || '').trim(); if (t && !toasts.includes(t)) toasts.push(t); }
    });
    obs.observe(document.body, { childList: true, subtree: true, characterData: true });
    const opts = { clientX: target.sx, clientY: target.sy, bubbles: true, cancelable: true,
                   pointerId: 1, pointerType: 'mouse', button: 0, buttons: 1 };
    c.dispatchEvent(new PointerEvent('pointerdown', opts));
    await new Promise(r => setTimeout(r, 60));
    c.dispatchEvent(new PointerEvent('pointerup', opts));
    await new Promise(r => setTimeout(r, 800));
    obs.disconnect();
    const ch = document.getElementById('crosshair');
    const at = document.elementFromPoint(target.sx, target.sy);
    return { toasts, atTag: at ? at.tagName : null, atId: at ? at.id : null,
             crosshairPE: ch ? getComputedStyle(ch).pointerEvents : null,
             crosshairDisplay: ch ? getComputedStyle(ch).display : null,
             elecId: target.elecId, door: target.door };
  }, roamSetup.cands[0]);
  console.log('[漫游点击结果] ' + JSON.stringify(roamClick, null, 2));
  check('漫游模式下点击 3D 里的可交互物有响应', roamClick.toasts.length > 0,
        JSON.stringify(roamClick.toasts));
  check('漫游模式下准星不拦截指针（pointer-events:none）',
        roamClick.crosshairPE === 'none' && roamClick.crosshairDisplay === 'block',
        'pe=' + roamClick.crosshairPE + ' display=' + roamClick.crosshairDisplay);
  check('点击确实命中了开关并执行了动作',
        roamClick.toasts.some(t => /开关/.test(t)), JSON.stringify(roamClick.toasts));
}

await b.close();
const failed = results.filter(r => !r.ok);
console.log('\n================ 总结 ================');
console.log('通过 ' + (results.length - failed.length) + ' / ' + results.length);
if (failed.length) failed.forEach(f => console.log('  FAIL: ' + f.name + '  ' + f.detail));
process.exit(failed.length ? 1 : 0);
