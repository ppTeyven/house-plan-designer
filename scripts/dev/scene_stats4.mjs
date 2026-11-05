import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const p = await b.newPage();
await p.goto('http://127.0.0.1:8899/verify_tmp.html?debug', { waitUntil: 'load', timeout: 30000 });
await p.waitForFunction(() => window.__designer, { timeout: 30000 });
await new Promise(r => setTimeout(r, 8000));
await p.evaluate(() => { const el=[...document.querySelectorAll('[data-view]')].find(b=>b.dataset.view==='3d'); el && el.click(); });
await new Promise(r => setTimeout(r, 9000));
const r = await p.evaluate(() => {
  const scene = window.__SCENE;
  const bad = [];
  const bufNoCast = [];
  scene.traverse(o => {
    if (!o.isMesh) return;
    const role = o.userData?.role || 'none';
    const g = o.geometry?.type || '?';
    if (!o.castShadow) {
      // find nearest ancestor with fid / name
      let anc = o, label = 'scene';
      while (anc) { if (anc.userData && anc.userData.fid) { label = 'furn:' + anc.userData.fid; break; } if (anc.name) { label = 'name:' + anc.name; break; } anc = anc.parent; }
      if (g === 'BufferGeometry') bufNoCast.push({ role, label, mat: o.material?.type, col: o.material?.color?.getHexString?.() });
      else bad.push({ role, g, label, mat: o.material?.type });
    }
  });
  const agg = {};
  for (const b of bad) { const k = b.role + '/' + b.g + '/' + b.mat; agg[k] = (agg[k]||0)+1; }
  return { agg, bufNoCast: bufNoCast.slice(0, 20), total: bad.length };
});
console.log(JSON.stringify(r, null, 1));
await b.close();
