import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const target = process.argv[2] || 'template.html';
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const p = await b.newPage();
await p.goto(`http://127.0.0.1:8899/${target}?debug`, { waitUntil: 'load', timeout: 30000 });
await p.waitForFunction(() => window.__designer, { timeout: 30000 });
await new Promise(r => setTimeout(r, 8000));
const r = await p.evaluate(() => {
  // find scene via any object graph
  const S3 = window.__designer.S3;
  let scene = null;
  for (const k of Object.keys(S3)) {
    const v = S3[k];
    if (v && typeof v === 'object' && v.isScene) { scene = v; break; }
  }
  if (!scene) {
    // walk app state
    const seen = new Set(); const q = [window.__designer.app];
    while (q.length) {
      const o = q.pop();
      if (!o || typeof o !== 'object' || seen.has(o)) continue;
      seen.add(o);
      if (o.isScene) { scene = o; break; }
      for (const k of Object.keys(o)) { const v = o[k]; if (v && typeof v === 'object') q.push(v); }
    }
  }
  if (!scene) return { found: false };
  let total = 0, cast = 0, recv = 0, byRole = {};
  scene.traverse(o => {
    if (!o.isMesh) return;
    total++;
    if (o.castShadow) cast++;
    if (o.receiveShadow) recv++;
    const r = o.userData && o.userData.role || 'none';
    byRole[r] = (byRole[r] || 0) + 1;
  });
  return { found: true, total, cast, recv, byRole };
});
console.log(target, JSON.stringify(r, null, 1));
await b.close();
