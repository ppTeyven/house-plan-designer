import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const page = await b.newPage();
const errs = [];
page.on('pageerror', e => errs.push('PAGEERROR::' + e.message.slice(0, 200) + ' | ' + (e.stack||'').split('\n')[1]));
page.on('console', m => { if (m.type()==='error' && !/404|Failed to load resource/.test(m.text())) errs.push('CONSOLE::' + m.text().slice(0,200)); });
await page.goto('http://127.0.0.1:8899/template.html?debug', { waitUntil: 'load', timeout: 30000 });
await new Promise(r => setTimeout(r, 8000));
async function clickView(v, wait=6000) {
  await page.evaluate(vv => { const el=[...document.querySelectorAll('[data-view]')].find(b=>b.dataset.view===vv); el && el.click(); }, v);
  await new Promise(r => setTimeout(r, wait));
  const st = await page.evaluate(() => ({ view: window.__designer?.state?.view ?? window.__designer?.app?.state?.view ?? null }));
  console.log('VIEW', v, JSON.stringify(st));
}
await clickView('3d', 9000);
await page.screenshot({ path: 'C:/Temp/verify_3d.png' });
await clickView('split', 7000);
await page.screenshot({ path: 'C:/Temp/verify_split.png' });
await clickView('2d', 4000);
console.log('ERRORS:\n' + (errs.join('\n') || 'NONE'));
await b.close();
