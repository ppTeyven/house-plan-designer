import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const page = await b.newPage();
const errs = [];
page.on('pageerror', e => errs.push('PAGEERROR::' + e.message.slice(0, 500)));
page.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE::' + m.text().slice(0, 300)); });
await page.goto('http://127.0.0.1:8899/template.html?debug', { waitUntil: 'load', timeout: 30000 }).catch(e => errs.push('GOTO FAIL ' + e.message.slice(0,200)));
await new Promise(r => setTimeout(r, 10000));
const st = await page.evaluate(() => {
  const d = window.__designer;
  return { hasD: !!d, ready: document.readyState, view: d && d.state ? d.state.view : null,
    keys: d ? Object.keys(d).slice(0, 20) : [] };
});
console.log('STATE', JSON.stringify(st));
// try switching to 3d
const res = await page.evaluate(async () => {
  const out = {};
  try {
    const btns = [...document.querySelectorAll('button,[data-view],[data-mode],.tab')].map(b => ({ t: (b.textContent||'').trim().slice(0,12), v: b.dataset.view||b.dataset.mode||'' })).filter(x=>x.t);
    out.buttons = btns.slice(0, 40);
  } catch (e) { out.err = String(e); }
  return out;
});
console.log('BTNS', JSON.stringify(res));
await new Promise(r => setTimeout(r, 1500));
await page.screenshot({ path: 'C:/Temp/verify_2d.png' });
console.log('ERRORS', errs.length ? errs.slice(0,12).join('\n') : 'NONE');
await b.close();
