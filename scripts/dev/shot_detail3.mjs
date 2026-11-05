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
// use birdPose / dioramaPose to frame; then zoom via wheel on canvas
const info = await p.evaluate(async () => {
  const S3 = window.__designer.S3;
  const out = {};
  try { S3.birdPose && S3.birdPose(); } catch(e) { out.birdErr = String(e); }
  await new Promise(r => setTimeout(r, 1200));
  try { S3.renderNow && S3.renderNow(); } catch(e) {}
  return out;
});
console.log('INFO', JSON.stringify(info));
await p.screenshot({ path: `C:/Temp/detail_${tag}/bird.png` });
// zoom in with wheel events over the 3D canvas
const box = await p.evaluate(() => { const c = document.querySelector('#c3d'); const r = c.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; });
for (let i = 0; i < 6; i++) {
  await p.mouse.move(box.x, box.y);
  await p.mouse.wheel({ deltaY: -300 });
  await new Promise(r => setTimeout(r, 500));
}
await new Promise(r => setTimeout(r, 2500));
await p.evaluate(() => { try { window.__designer.S3.renderNow(); } catch(e){} });
await p.screenshot({ path: `C:/Temp/detail_${tag}/zoom.png` });
console.log('ERR:', errs.slice(0,5).join(' | ') || 'NONE');
await b.close();
