import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const target = process.argv[2] || 'template.html';
const tag = process.argv[3] || 'new';
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1700, height: 1000 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const p = await b.newPage();
const errs = [];
p.on('pageerror', e => errs.push(e.message.slice(0, 150)));
await p.goto(`http://127.0.0.1:8899/${target}?debug`, { waitUntil: 'load', timeout: 30000 });
await p.waitForFunction(() => window.__designer, { timeout: 30000 });
await new Promise(r => setTimeout(r, 7000));
await p.evaluate(() => { const el=[...document.querySelectorAll('[data-view]')].find(b=>b.dataset.view==='3d'); el && el.click(); });
await new Promise(r => setTimeout(r, 10000));
fs.mkdirSync(`C:/Temp/detail_${tag}`, { recursive: true });
// zoom the orbit camera in on the model to inspect micro-detail
const angles = [ { k: 'wide' }, { k: 'close', zoom: 0.42 }, { k: 'low', pitch: -0.02, zoom: 0.6 } ];
for (const a of angles) {
  const r = await p.evaluate(async a => {
    const S3 = window.__designer.S3;
    const c = S3.camera || S3.cam || null;
    return { hasCam: !!c, keys: S3 ? Object.keys(S3).slice(0,25) : [] };
  }, a);
  console.log('S3', JSON.stringify(r));
  break;
}
await p.screenshot({ path: `C:/Temp/detail_${tag}/view.png` });
console.log('ERR:', errs.slice(0,5).join(' | ') || 'NONE');
await b.close();
