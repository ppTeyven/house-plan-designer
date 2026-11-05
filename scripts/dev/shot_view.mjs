import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const target = process.argv[2] || 'template.html';
const out = process.argv[3] || 'C:/Temp/shot.png';
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1500, height: 900 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const page = await b.newPage();
await page.goto(`http://127.0.0.1:8899/${target}?debug`, { waitUntil: 'load', timeout: 30000 });
await new Promise(r => setTimeout(r, 9000));
await page.evaluate(() => { const el=[...document.querySelectorAll('[data-view]')].find(b=>b.dataset.view==='3d'); el && el.click(); });
await new Promise(r => setTimeout(r, 10000));
await page.screenshot({ path: out });
console.log('SHOT', out);
await b.close();
