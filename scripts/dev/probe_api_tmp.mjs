import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const page = await b.newPage();
await page.goto('http://127.0.0.1:8899/template.html?debug', { waitUntil: 'load' });
await page.waitForFunction(() => window.__designer, { timeout: 60000 });
await new Promise(r => setTimeout(r, 7000));
const out = await page.evaluate(() => {
  const d = window.__designer;
  const rd = { src: String(d.requestDraw).slice(0, 300) };
  try { d.requestDraw(); rd.called = true; } catch (e) { rd.called = 'ERR ' + String(e).slice(0, 100); }
  return {
    rd,
    emitSrc: String(d.emit).slice(0, 200),
    fitSrc: String(d.fit2D).slice(0, 200),
    topPoseSrc: String(d.S3.topPoseFrom2D).slice(0, 200),
    setPoseSrc: String(d.S3.setPose).slice(0, 200),
    viewLive: !!(d.view && typeof d.view.s === 'number'),
  };
});
console.log(JSON.stringify(out, null, 1));
await b.close();
