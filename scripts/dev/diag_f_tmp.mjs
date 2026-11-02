import puppeteer from 'puppeteer-core';
import fs from 'fs';
const exe = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
const b = await puppeteer.launch({ executablePath: exe, headless: 'new', defaultViewport: { width: 1400, height: 860 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'] });
const page = await b.newPage();
page.on('pageerror', e => console.log('PAGEERROR ' + e.message.slice(0,300)));
await page.goto('http://127.0.0.1:8899/template.html?debug', { waitUntil: 'load' });
await page.waitForFunction(() => window.__designer, { timeout: 60000 });
const sleep = ms => new Promise(r => setTimeout(r, ms));
await sleep(7000);
const ev = (f, ...a) => page.evaluate(f, ...a);
// install Bi spy: wrap wi to log calls
await ev(() => {
  window.__wiLog = [];
  const S = window.__designer.S3;
  // find wi via animatePose
  window.__anim0 = S.animatePose;
});
await ev(() => window.__designer.setView('split'));
for (let i = 0; i < 6; i++) {
  await sleep(700);
  const p = await ev(() => {
    const d = window.__designer;
    let bi = null;
    try {
      // Bi not exported; infer from isAnimating + controls
      const s = d.S3.sceneRefs();
      bi = { anim: d.S3.isAnimating(), en: s.controls.enabled };
    } catch (e) { bi = { err: String(e).slice(0,100) }; }
    return { view: d.app.view, tr: d.app.transitioning, ...bi, t: Math.round(performance.now()) };
  });
  console.log('poll', i, JSON.stringify(p));
}
// direct tween test in 3d
await ev(() => window.__designer.setView('3d'));
await sleep(1500);
const t0 = await ev(() => {
  const d = window.__designer;
  const s = d.S3.sceneRefs();
  const tgt0 = [s.controls.target.x, s.controls.target.y, s.controls.target.z];
  d.S3.animatePose({ target: s.controls.target.clone(), r: 20, p: .72, t: -.7 }, 800);
  return { tgt0, anim: d.S3.isAnimating(), t: Math.round(performance.now()) };
});
console.log('tween start', JSON.stringify(t0));
for (let i = 0; i < 5; i++) {
  await sleep(500);
  const p = await ev(() => ({ anim: window.__designer.S3.isAnimating(), en: window.__designer.S3.sceneRefs().controls.enabled }));
  console.log('tween poll', i, JSON.stringify(p));
}
await b.close();
