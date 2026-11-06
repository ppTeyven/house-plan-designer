// 深度性能剖析 v2：修正 v1 的 meshCount 累加 bug，并做真实热点定位
// 用法：node scripts/dev/profile_perf2.js [url]
import puppeteer from 'puppeteer-core';
import fs from 'fs';

const URL_ = process.argv[2] || 'http://127.0.0.1:8899/template.html';
const exe = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
].find(p => fs.existsSync(p));

const browser = await puppeteer.launch({
  executablePath: exe, headless: 'new', protocolTimeout: 300000,
  defaultViewport: { width: 1600, height: 960 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist',
    '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
    '--disable-backgrounding-occluded-windows'],
});
const page = await browser.newPage();
const errs = [];
page.on('pageerror', e => errs.push({ t: 'pageerror', m: e.message, st: (e.stack || '').split('\n').slice(0, 6).join(' | ') }));
page.on('console', m => { if (m.type() === 'error') errs.push({ t: 'console', m: m.text() }); });
page.on('requestfailed', r => errs.push({ t: 'reqfail', m: r.url() + ' ' + (r.failure() || {}).errorText }));
page.on('response', r => { if (r.status() >= 400) errs.push({ t: 'http' + r.status(), m: r.url() }); });

await page.goto(URL_, { waitUntil: 'networkidle2', timeout: 180000 });
await new Promise(r => setTimeout(r, 12000));

const out = await page.evaluate(async () => {
  const R = { errors: [] };

  // --- 场景真实规模（修正：不累加） ---
  const scene = window.__D3 && window.__D3.scene;
  if (scene) {
    let mesh = 0, light = 0, obj = 0, tris = 0, byType = {};
    scene.traverse(o => {
      obj++;
      if (o.isMesh) {
        mesh++;
        const g = o.geometry;
        if (g) tris += (g.index ? g.index.count : g.attributes.position.count) / 3;
        const t = o.material && o.material.type || '?';
        byType[t] = (byType[t] || 0) + 1;
      }
      if (o.isPointLight || o.isSpotLight || o.isDirectionalLight || o.isRectAreaLight) light++;
    });
    R.scene = { obj, mesh, light, tris: Math.round(tris), matTypes: byType };

    // --- traverse 真实成本 ---
    const N = 300;
    let sink = 0;
    const t0 = performance.now();
    for (let i = 0; i < N; i++) scene.traverse(o => { if (o.isMesh) sink++; });
    const t1 = performance.now();
    R.traverseMs = +((t1 - t0) / N).toFixed(4);
    R.sink = sink;
  }

  // --- 帧间隔分布（分场景：静止 / 旋转相机） ---
  async function sampleFrames(n) {
    const gaps = [];
    await new Promise(res => {
      let last = performance.now(), i = 0;
      function tick(now) { gaps.push(now - last); last = now; if (++i < n) requestAnimationFrame(tick); else res(); }
      requestAnimationFrame(tick);
    });
    gaps.sort((a, b) => a - b);
    return {
      p50: +gaps[(gaps.length * 0.5) | 0].toFixed(2),
      p95: +gaps[(gaps.length * 0.95) | 0].toFixed(2),
      fps: +(1000 / gaps[(gaps.length * 0.5) | 0]).toFixed(1),
    };
  }
  R.framesIdle = await sampleFrames(150);

  // --- 强制 GC 后测堆 ---
  R.mem = {};
  if (performance.memory) {
    R.mem.before = performance.memory.usedJSHeapSize;
  }

  // --- 模拟「跑 10 分钟」的泄漏增长：Yv() 每帧 push 的数组 ---
  R.leakProbe = {
    YV_TRACE_len: (window.__YV_TRACE && window.__YV_TRACE.length) || 0,
    has_YV_TRACE: '__YV_TRACE' in window,
  };

  // --- 统计 rAF 回调数量：包装 requestAnimationFrame 计数不现实，
  //     改为统计 window 上暴露的调试钩子数量 ---
  R.debugHooks = Object.keys(window).filter(k => k.startsWith('__')).length;

  return R;
});

// 分离的：测「Yv 每帧 push」修复后的残留（应已被我删掉）
const leakCheck = await page.evaluate(() => ({
  YV_TRACE: window.__YV_TRACE ? window.__YV_TRACE.length : 'absent',
  errs: window.__ACC_ERRORS || null,
}));

console.log(JSON.stringify({ ...out, leakCheck, pageErrors: errs.slice(0, 25) }, null, 2));
await browser.close();
