// 最终视觉验证：切换 2D/3D/分屏/漫游，确认画面正常、无报错、无 NaN
// 用法：node scripts/dev/final_visual_check.js [设计器.html] [输出目录]
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { pageUrl } from '../lib_serve.mjs';

const FILE = process.argv[2] || 'assets/template.html';
const OUT = process.argv[3] || 'scripts/dev/_final_shots';
fs.mkdirSync(OUT, { recursive: true });

const exe = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
].find(p => fs.existsSync(p));

const browser = await puppeteer.launch({
  executablePath: exe, headless: 'new', protocolTimeout: 600000,
  defaultViewport: { width: 1600, height: 960 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist',
    '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
    '--disable-backgrounding-occluded-windows'],
});
const page = await browser.newPage();
const errs = [];
page.on('pageerror', e => errs.push('pageerror: ' + e.message));
page.on('console', m => { if (m.type() === 'error' && !/favicon/.test(m.text())) errs.push('console: ' + m.text()); });

const pg = await pageUrl(FILE);
await page.goto(pg.url + '?debug', { waitUntil: 'networkidle2', timeout: 180000 });
await page.waitForFunction(() => window.__designer, { timeout: 60000 });
await new Promise(r => setTimeout(r, 12000));

const sleep = ms => new Promise(r => setTimeout(r, ms));
async function shot(name) {
  await page.screenshot({ path: path.join(OUT, `${name}.png`) });
  console.log('  截图', name);
}

const results = {};
for (const v of ['2d', '3d', 'split']) {
  const ok = await page.evaluate(async (vv) => { await window.__designer.setView(vv); return true; }, v);
  if (!ok) { results[v] = '切换失败'; continue; }
  await sleep(5000);
  await shot('view_' + v);
  results[v] = await page.evaluate(() => {
    const D = window.__designer;
    const scene = D.S3.sceneRefs().scene;
    let nan = 0, meshes = 0;
    scene.traverse(o => {
      if (o.isMesh) {
        meshes++;
        const p = o.geometry && o.geometry.attributes && o.geometry.attributes.position;
        if (p && p.array) for (let i = 0; i < Math.min(p.array.length, 300); i++) if (!Number.isFinite(p.array[i])) { nan++; break; }
      }
    });
    const txt = document.body.innerText;
    const c = document.querySelector('#c3d');
    return { meshes, nanMeshes: nan, hasNaNText: /NaN|undefined/.test(txt), canvasSize: c ? c.width + 'x' + c.height : 'n/a' };
  });
}

// 漫游
await page.evaluate(async () => { await window.__designer.setView('3d'); });
await sleep(4000);
await page.evaluate(() => window.__designer.S3.enterFP({ x: 2900, y: 6425 }));
for (let i = 0; i < 300; i++) { await sleep(250); if (await page.evaluate(() => window.__designer.S3.fp.active)) break; }
await sleep(3000);
await shot('view_walk');
results.walk = await page.evaluate(() => ({ fp: window.__designer.S3.fp.active, marks: document.querySelectorAll('.pt-hud .pt').length }));

console.log('\n=== 各视图状态 ===');
console.log(JSON.stringify(results, null, 2));
console.log('\n=== 页面错误 ===');
console.log(errs.length ? errs.slice(0, 15).join('\n') : '(无)');

await browser.close();
await pg.close();
