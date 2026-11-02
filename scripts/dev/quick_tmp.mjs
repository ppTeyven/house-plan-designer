import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const page = await b.newPage();
page.on('pageerror', e => console.log('PAGEERROR::', e.message.slice(0, 800)));
page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE::', m.text().slice(0, 400)); });
await page.goto('http://127.0.0.1:8899/template.html?debug', { waitUntil: 'load', timeout: 30000 }).catch(e => console.log('GOTO FAIL', e.message.slice(0,200)));
await new Promise(r => setTimeout(r, 12000));
const st = await page.evaluate(() => ({ href: location.href, hasD: !!window.__designer, ready: document.readyState, body: document.body ? document.body.innerHTML.slice(0, 200) : 'no-body' }));
console.log('STATE', JSON.stringify(st));
await b.close();
