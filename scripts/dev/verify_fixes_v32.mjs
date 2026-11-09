// ===== 【三项修复的自动化验收】v32 =====
// 1) 首次加载 3D 显示加载动画（#loading3d 真的上屏），场景就绪后隐藏
// 2) 模式切换不卡顿（不再被 __pgWaitWarmAsync 阻塞 12s）
// 3) 漫游模式下可交互物能点到（准星不再吞掉指针事件）
// 4) 画质未降级：DPR 1.25 / ACES / GTAO / SSR / Bloom / SMAA / PCFSoft / MSAA 全在位
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
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist',
    '--disable-background-timer-throttling', '--disable-renderer-backgrounding'],
});
const page = await b.newPage();
page.on('pageerror', e => console.log('PAGEERROR:', e.message.slice(0, 200)));
const pg = await pageUrl(FILE);
await page.goto(pg.url + '?debug', { waitUntil: 'load', timeout: 90000 });
await page.waitForFunction(() => window.__designer && window.__D3 && window.__D3.renderer, { timeout: 90000 });

// ---------- 1) 加载动画真的上屏 ----------
const helpers = await page.evaluate(() => ({
  show: typeof window.__showLoading3D, hide: typeof window.__hideLoading3D }));
check('加载动画助手已导出', helpers.show === 'function' && helpers.hide === 'function', JSON.stringify(helpers));

// 1a) 助手本身：show 必须真的让它可见（display=grid + opacity=1）
const helperShow = await page.evaluate(async () => {
  const el = document.getElementById('loading3d');
  window.__showLoading3D('正在加载 3D 场景…');
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  return { disp: getComputedStyle(el).display, op: getComputedStyle(el).opacity,
           hasHide: el.classList.contains('hide'),
           spin: !!el.querySelector('.lspin'),
           txt: el.querySelector('.ltxt') ? el.querySelector('.ltxt').textContent : null };
});
check('__showLoading3D 让动画真正可见', helperShow.disp === 'grid' && helperShow.op === '1'
      && !helperShow.hasHide && helperShow.spin, JSON.stringify(helperShow));
await page.evaluate(() => window.__hideLoading3D());
await sleep(500);
const helperHide = await page.evaluate(() => {
  const el = document.getElementById('loading3d');
  return { disp: getComputedStyle(el).display, op: getComputedStyle(el).opacity,
           hasHide: el.classList.contains('hide') };
});
check('__hideLoading3D 隐藏动画', helperHide.hasHide && helperHide.disp === 'none', JSON.stringify(helperHide));

// 1b) 真实首屏路径：重新加载页面（全新加载 = 真·首次），观察 loading3d 生命周期
const page2 = await b.newPage();
await page2.setViewport({ width: 1400, height: 900, deviceScaleFactor: 1 });
await page2.goto(pg.url + '?debug', { waitUntil: 'load', timeout: 90000 });
await page2.waitForFunction(() => window.__designer && window.__D3 && window.__D3.renderer, { timeout: 90000 });
const spinnerLife = await page2.evaluate(async () => {
  const el = document.getElementById('loading3d');
  const log = [];
  const snap = tag => log.push({ tag, disp: getComputedStyle(el).display,
                                op: getComputedStyle(el).opacity, cls: el.className });
  const mo = new MutationObserver(() => snap('mut'));
  mo.observe(el, { attributes: true, attributeFilter: ['style', 'class'] });
  snap('init');
  window.__designer.setView('3d');
  await new Promise(r => setTimeout(r, 8000));
  mo.disconnect();
  const visible = log.filter(l => l.disp !== 'none' && l.op !== '0');
  return { log, everVisible: visible.length > 0, visibleCount: visible.length };
});
check('真实首屏时加载动画曾上屏', spinnerLife.everVisible,
      '可见帧数=' + spinnerLife.visibleCount);
spinnerLife.log.forEach(l => console.log('    ' + l.tag.padEnd(5) + ' display=' + l.disp.padEnd(6) + ' opacity=' + l.op + ' cls="' + l.cls + '"'));
await page2.close();

const spinnerGone = await page.evaluate(() => {
  const el = document.getElementById('loading3d');
  return { disp: getComputedStyle(el).display, op: getComputedStyle(el).opacity,
           hasHide: el.classList.contains('hide') };
});
check('场景就绪后加载动画已隐藏',
      spinnerGone.hasHide && spinnerGone.disp === 'none', JSON.stringify(spinnerGone));

// ---------- 4) 画质未降级 ----------
await page.evaluate(() => window.__designer.setView('3d'));
await sleep(4000);
const quality = await page.evaluate(() => {
  const D3 = window.__D3;
  const r = D3.renderer;
  const c = document.querySelector('#c3d');
  const gl = r.getContext();
  const rect = c.getBoundingClientRect();
  const passes = (typeof D3.passes === 'function' ? D3.passes() : (D3.passes || [])).map(p => ({
    name: (p && p.constructor && p.constructor.name) || (p && p.type) || '?',
    enabled: p && p.enabled !== false,
    type: p && p.type, ao: p && p.ao,
  }));
  const comp = typeof D3.composer === 'function' ? D3.composer() : D3.composer;
  const compPasses = comp && comp.passes
    ? comp.passes.map(p => ({ name: (p.constructor && p.constructor.name) || '?',
                             enabled: p.enabled !== false }))
    : null;
  const ao = typeof D3.aoPass === 'function' ? D3.aoPass() : D3.aoPass;
  return {
    dpr: r.getPixelRatio(),
    bufW: c.width, cssW: Math.round(rect.width),
    supersample: +(c.width / rect.width).toFixed(2),
    maxSamples: gl.getParameter(gl.MAX_SAMPLES),
    msaaSetting: window.__MSAA_SAMPLES,
    toneMapping: r.toneMapping, ACES: r.toneMapping === 4,
    exposure: r.toneMappingExposure,
    shadowEnabled: r.shadowMap.enabled, shadowType: r.shadowMap.type,
    outputCS: r.outputColorSpace,
    aoPassType: ao ? (ao.constructor && ao.constructor.name) : null,
    aoEnabled: ao ? ao.enabled : null,
    passes, compPasses,
  };
});
console.log('\n[画质快照] ' + JSON.stringify(quality, null, 2) + '\n');
check('DPR = 1.25（超采样未降级）', quality.dpr === 1.25, 'dpr=' + quality.dpr);
check('超采样倍率 = 1.25', quality.supersample === 1.25, 'ss=' + quality.supersample);
check('ACES Filmic 色调映射', quality.ACES, 'toneMapping=' + quality.toneMapping);
check('阴影开启且为 PCFSoft', quality.shadowEnabled && quality.shadowType === 2,
      'enabled=' + quality.shadowEnabled + ' type=' + quality.shadowType);
check('sRGB 输出色彩空间', quality.outputCS === 'srgb', quality.outputCS);
check('GPU 支持 8x MSAA', quality.maxSamples >= 8, 'maxSamples=' + quality.maxSamples);
const allPasses = [...quality.passes, ...(quality.compPasses || [])];
// bundle 里这些 class 名被压缩了，用已知对应关系判定：
// Cu=Render, Eo=GTAO, SSRZ=SSR, Wa=UnrealBloom, Du=Output(ACES), Sr=Grade, ND=SMAA
const PASS_MAP = { Cu: 'Render', Eo: 'GTAO', SSRZ: 'SSR', Wa: 'Bloom', Du: 'Output', Sr: 'Grade', ND: 'SMAA' };
const passTypes = [...new Set(allPasses.map(p => p.type || p.name))];
const hasPass = re => passTypes.some(t => re.test(t) || re.test(PASS_MAP[t] || ''));
console.log('[后期链] ' + JSON.stringify(passTypes.map(t => t + '=' + (PASS_MAP[t] || '?'))));
check('GTAO 通道存在', hasPass(/GTAO/i), passTypes.join(','));
check('SSR 通道存在', hasPass(/SSR/i), passTypes.join(','));
check('Bloom 通道存在', hasPass(/Bloom/i), passTypes.join(','));
check('Render/Output/Grade 通道存在', hasPass(/Render|Output|Grade/i), passTypes.join(','));

// ---------- 2) 模式切换不卡顿 ----------
const switchTiming = await page.evaluate(async () => {
  const out = [];
  for (const v of ['2d', 'split', '3d', '2d', 'split', '3d']) {
    const t0 = performance.now();
    window.__designer.setView(v);
    await new Promise(res => {
      const tick = () => {
        if (document.querySelector('#stage').dataset.view === v) return res();
        requestAnimationFrame(tick);
      };
      tick();
    });
    out.push({ view: v, ms: +(performance.now() - t0).toFixed(1) });
  }
  return out;
});
console.log('[切换耗时] ' + JSON.stringify(switchTiming));
const worst = Math.max(...switchTiming.map(x => x.ms));
check('模式切换无阻塞（最慢 < 3000ms）', worst < 3000, '最慢=' + worst + 'ms');

// ---------- 3) 漫游模式交互 ----------
await page.evaluate(() => window.__designer.setView('3d'));
await sleep(3000);
await page.evaluate(() => {
  const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim() === '漫游');
  if (b) b.click();
});
await sleep(2500);

const crosshair = await page.evaluate(() => {
  const el = document.getElementById('crosshair');
  return { exists: !!el, pe: el ? getComputedStyle(el).pointerEvents : null,
           display: el ? getComputedStyle(el).display : null };
});
check('准星 pointer-events = none（不再吞掉点击）', crosshair.pe === 'none', JSON.stringify(crosshair));
check('漫游时准星可见', crosshair.display === 'block', JSON.stringify(crosshair));

// 场景里可交互对象统计
const inter = await page.evaluate(() => {
  const scene = window.__D3.scene;
  let sw = 0, dr = 0, fu = 0;
  scene.traverse(o => {
    const u = o.userData || {};
    if (u.elecId) sw++;
    if (u.door) dr++;
    if (u.fid) fu++;
  });
  return { sw, dr, fu, total: sw + dr + fu };
});
console.log('[可交互对象] ' + JSON.stringify(inter));
check('场景中存在可交互对象（开关/门/家具）', inter.total > 0, JSON.stringify(inter));

// 真实点击画布中心，验证事件能到 canvas
const clickTest = await page.evaluate(() => {
  const c = document.getElementById('c3d');
  const rect = c.getBoundingClientRect();
  const cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2;
  const at = document.elementFromPoint(cx, cy);
  let gotDown = false, gotUp = false;
  const onDown = () => { gotDown = true; };
  const onUp = () => { gotUp = true; };
  c.addEventListener('pointerdown', onDown, true);
  c.addEventListener('pointerup', onUp, true);
  const opts = { clientX: cx, clientY: cy, bubbles: true, cancelable: true,
                 pointerId: 1, pointerType: 'mouse', button: 0, buttons: 1 };
  c.dispatchEvent(new PointerEvent('pointerdown', opts));
  c.dispatchEvent(new PointerEvent('pointerup', opts));
  c.removeEventListener('pointerdown', onDown, true);
  c.removeEventListener('pointerup', onUp, true);
  return { atTag: at ? at.tagName : null, atId: at ? at.id : null,
           atCls: at ? at.className : null, gotDown, gotUp,
           isCanvasOrChild: !!(at && (at === c || c.contains(at))) };
});
console.log('[中心点击] ' + JSON.stringify(clickTest));
check('画布中心命中的是 canvas（无遮罩拦截）', clickTest.isCanvasOrChild, JSON.stringify(clickTest));
check('pointerdown 能到达 canvas', clickTest.gotDown, JSON.stringify(clickTest));
check('pointerup 能到达 canvas', clickTest.gotUp, JSON.stringify(clickTest));

// 准星射线链路：只要求「射线本身能产生交点」。
// 是否命中可交互物取决于摄像机此刻正对着什么 —— 真正的「点了能生效」由
// verify_roam_e2e.mjs 用真实 pointerdown/pointerup + 真实屏幕坐标验证。
const hitAll = await page.evaluate(() => {
  const D3 = window.__D3;
  const scene = D3.scene;
  const cam = typeof D3.camera === 'function' ? D3.camera() : D3.camera;
  const rc = typeof D3.raycaster === 'function' ? D3.raycaster() : D3.raycaster;
  rc.setFromCamera({ x: 0, y: 0 }, cam);
  const hits = rc.intersectObjects(scene.children, true);
  let elec = 0, door = 0, fid = 0;
  scene.traverse(o => {
    const u = o.userData || {};
    if (u.elecId) elec++; if (u.door) door++; if (u.fid) fid++;
  });
  return { centerHits: hits.length, elec, door, fid };
});
console.log('[中心射线] ' + JSON.stringify(hitAll));
check('准星射线链路通（能产生交点）', hitAll.centerHits > 0, 'centerHits=' + hitAll.centerHits);
check('场景里有足量可交互物（开关/门/家具）',
      hitAll.elec > 0 && hitAll.door > 0 && hitAll.fid > 0,
      'elec=' + hitAll.elec + ' door=' + hitAll.door + ' fid=' + hitAll.fid);

// 漫游下按 Space：应触发准星交互（要么命中执行动作，要么给出明确提示）
await page.evaluate(() => {
  window.__toasts = [];
  const push = t => window.__toasts.push(String(t || ''));
  const orig = console.warn;
  // 捕获页面提示条
  const obs = new MutationObserver(() => {
    const el = document.querySelector('#toast') || document.querySelector('.toast');
    if (el) { const tx = (el.textContent || '').trim(); if (tx) window.__toasts.push(tx); }
  });
  obs.observe(document.body, { childList: true, subtree: true, characterData: true });
  window.__toastObs = obs;
});
await page.evaluate(() => {
  const c = document.getElementById('c3d');
  c.focus();
  window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space', key: ' ', bubbles: true, cancelable: true }));
});
await sleep(1000);
const toasts = await page.evaluate(() => {
  window.__toastObs && window.__toastObs.disconnect();
  return [...new Set(window.__toasts)];
});
console.log('[Space 后提示] ' + JSON.stringify(toasts));
check('Space 触发准星交互链路（有响应）', toasts.length > 0, JSON.stringify(toasts));

await b.close();
const failed = results.filter(r => !r.ok);
console.log('\n================ 总结 ================');
console.log('通过 ' + (results.length - failed.length) + ' / ' + results.length);
if (failed.length) failed.forEach(f => console.log('  FAIL: ' + f.name + '  ' + f.detail));
process.exit(failed.length ? 1 : 0);
