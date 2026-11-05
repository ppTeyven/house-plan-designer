import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const page = await b.newPage();
const errs = [];
page.on('pageerror', e => errs.push('PAGEERROR::' + e.message.slice(0, 300) + '\nSTACK::' + (e.stack||'').split('\n').slice(0,6).join('\n')));
await page.goto('http://127.0.0.1:8899/template.html?debug', { waitUntil: 'load', timeout: 30000 });
await new Promise(r => setTimeout(r, 9000));
console.log('ERRORS:\n' + (errs.join('\n---\n') || 'NONE'));
await b.close();
