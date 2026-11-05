import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const target = process.argv[2] || 'template.html';
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1700, height: 1000 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const p = await b.newPage();
const errs = [];
p.on('pageerror', e => errs.push(e.message.slice(0,150)));
await p.goto(`http://127.0.0.1:8899/${target}?debug`, { waitUntil: 'load', timeout: 30000 });
await p.waitForFunction(() => window.__designer && window.shot, { timeout: 30000 });
await new Promise(r => setTimeout(r, 4000));
fs.mkdirSync('C:/Temp/detail', { recursive: true });
// bird's eye + a few interior angles
const shots = [
  { name: 'bird', x: 6, y: 6, yaw: 0.8, pitch: -0.85, t: 14 },
  { name: 'in1', x: 2.5, y: 3.2, yaw: 1.2, pitch: -0.05, t: 16 },
  { name: 'in2', x: 5.5, y: 4.0, yaw: 2.4, pitch: -0.08, t: 16 }
];
for (const s of shots) {
  const r = await p.evaluate(async s => {
    const st = await shot(s.x, s.y, s.yaw, s.pitch, s.t);
    await pump(400);
    window.__designer.S3.renderNow();
    return { st, url: document.querySelector('#c3d').toDataURL('image/jpeg', .92) };
  }, s);
  fs.writeFileSync(`C:/Temp/detail/${s.name}.jpg`, Buffer.from(r.url.split(',')[1], 'base64'));
  console.log(s.name, JSON.stringify(r.st));
}
console.log('ERR:', errs.slice(0,5).join(' | ') || 'NONE');
await b.close();
