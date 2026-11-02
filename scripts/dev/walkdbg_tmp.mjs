import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const page = await b.newPage();
const errs = [];
page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message.slice(0, 500)));
page.on('console', m => { if (m.type() === 'error' && !/404|JSHandle/.test(m.text())) errs.push('CONSOLE: ' + m.text().slice(0, 300)); });
await page.goto('http://127.0.0.1:8899/template.html?debug', { waitUntil: 'load' });
await page.waitForFunction(() => window.__designer, { timeout: 60000 });
await new Promise(r => setTimeout(r, 7000));
const ev = (f, ...a) => page.evaluate(f, ...a);
await ev(() => window.__designer.setView('3d'));
await new Promise(r => setTimeout(r, 2500));
const pre = await ev(() => { const d = window.__designer; return { style: d.S3.look().style, anim: d.S3.isAnimating(), en: d.S3.sceneRefs().controls.enabled, fp: !!d.S3.fp.active }; });
console.log('PRE', JSON.stringify(pre));
const call = await ev(async () => { try { window.__designer.S3.enterFP(); return { ok: true }; } catch (e) { return { ok: false, err: String(e).slice(0, 400), stack: (e.stack || '').slice(0, 900) }; } });
console.log('CALL', JSON.stringify(call));
for (let i = 0; i < 8; i++) {
  await new Promise(r => setTimeout(r, 800));
  const p = await ev(() => { const d = window.__designer; return { anim: d.S3.isAnimating(), fp: !!d.S3.fp.active, en: d.S3.sceneRefs().controls.enabled }; });
  console.log('poll', i, JSON.stringify(p));
}
console.log('ERRS', JSON.stringify([...new Set(errs)].slice(0, 8)));
await b.close();
