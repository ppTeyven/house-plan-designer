import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const target = process.argv[2] || 'verify_tmp.html';
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const p = await b.newPage();
await p.goto(`http://127.0.0.1:8899/${target}?debug`, { waitUntil: 'load', timeout: 30000 });
await p.waitForFunction(() => window.__designer, { timeout: 30000 });
await new Promise(r => setTimeout(r, 8000));
await p.evaluate(() => { const el=[...document.querySelectorAll('[data-view]')].find(b=>b.dataset.view==='3d'); el && el.click(); });
await new Promise(r => setTimeout(r, 9000));
const r = await p.evaluate(() => {
  const scene = window.__SCENE;
  if (!scene) return { found: false };
  let total = 0, cast = 0, recv = 0, noCast = [], byRole = {};
  scene.traverse(o => {
    if (!o.isMesh) return;
    total++;
    if (o.castShadow) cast++; else if (noCast.length < 12) noCast.push(o.name || o.geometry?.type || '?');
    if (o.receiveShadow) recv++;
    const r = o.userData?.role || 'none';
    byRole[r] = (byRole[r] || 0) + 1;
  });
  return { found: true, total, cast, recv, noCast, byRole };
});
console.log(target, JSON.stringify(r, null, 1));
await b.close();
