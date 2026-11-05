import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const target = process.argv[2] || 'template.html';
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const page = await b.newPage();
const errs = [];
page.on('pageerror', e => errs.push('PAGEERROR::' + e.message.slice(0, 160)));
await page.goto(`http://127.0.0.1:8899/${target}?debug`, { waitUntil: 'load', timeout: 30000 });
await new Promise(r => setTimeout(r, 8000));
for (const v of ['3d','split','2d']) {
  await page.evaluate(vv => { const el=[...document.querySelectorAll('[data-view]')].find(b=>b.dataset.view===vv); el && el.click(); }, v);
  await new Promise(r => setTimeout(r, 5000));
}
console.log(target, 'ERRORS:', errs.length ? errs.join(' | ') : 'NONE');
await b.close();
