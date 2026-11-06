// CPU Profiler v2：带列号 + 自底向上调用树，定位真正的热点
// 用法：node scripts/dev/cpu_profile2.js [url] [seconds]

import puppeteer from 'puppeteer-core';
import fs from 'fs';

const URL_ = process.argv[2] || 'http://127.0.0.1:8899/template.html';
const SECS = parseFloat(process.argv[3] || '8');

const exe = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
].find(p => fs.existsSync(p));

const browser = await puppeteer.launch({
  executablePath: exe, headless: 'new', protocolTimeout: 300000,
  defaultViewport: { width: 1600, height: 960 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist',
    '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
    '--disable-backgrounding-occluded-windows'],
});
const page = await browser.newPage();
await page.goto(URL_, { waitUntil: 'networkidle2', timeout: 180000 });
await new Promise(r => setTimeout(r, 12000));

const client = await page.createCDPSession();
await client.send('Profiler.enable');
await client.send('Profiler.setSamplingInterval', { interval: 80 });
await client.send('Profiler.start');
await new Promise(r => setTimeout(r, SECS * 1000));
const { profile } = await client.send('Profiler.stop');

// 建树
const byId = new Map();
for (const n of profile.nodes) byId.set(n.id, n);
const parent = new Map();
for (const n of profile.nodes) for (const c of (n.children || [])) parent.set(c, n.id);

const selfCount = new Map();
for (const s of profile.samples) selfCount.set(s, (selfCount.get(s) || 0) + 1);
const total = profile.samples.length;

// 对每个热点叶子，回溯调用链，输出「谁在调它」
function chainOf(id) {
  const out = [];
  let cur = id;
  for (let d = 0; d < 12; d++) {
    const n = byId.get(cur);
    if (!n) break;
    const f = n.callFrame;
    out.push((f.functionName || '(anon)') + ':' + (f.lineNumber + 1) + ':' + (f.columnNumber + 1));
    const p = parent.get(cur);
    if (p === undefined) break;
    cur = p;
  }
  return out;
}

// 按 self time 排热点
const leaves = [...selfCount.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12);
console.log('=== 采样 %d 个，热点叶子及其调用链 ===', total);
for (const [id, c] of leaves) {
  const n = byId.get(id);
  const f = n.callFrame;
  console.log('\n--- %s  (self %d = %s%%) ---', f.functionName || '(anon)', c, (c / total * 100).toFixed(2));
  console.log('  位置: %s:%d:%d', (f.url || '').split('/').pop(), f.lineNumber + 1, f.columnNumber + 1);
  console.log('  链: ' + chainOf(id).join(' <- '));
}

// 整棵树的 total time（谁占大头，含子调用）
const totalTime = new Map();
function totalOf(id) {
  if (totalTime.has(id)) return totalTime.get(id);
  const n = byId.get(id);
  let t = selfCount.get(id) || 0;
  for (const c of (n.children || [])) t += totalOf(c);
  totalTime.set(id, t);
  return t;
}
for (const n of profile.nodes) totalOf(n.id);

const agg = new Map();
for (const n of profile.nodes) {
  const f = n.callFrame;
  const key = (f.functionName || '(anon)') + ':' + (f.lineNumber + 1) + ':' + (f.columnNumber + 1);
  agg.set(key, (agg.get(key) || 0) + totalTime.get(n.id));
}
console.log('\n=== total time 排行（含子调用）===');
for (const [k, v] of [...agg.entries()].sort((a, b) => b[1] - a[1]).slice(0, 25)) {
  console.log('  %-46s %6.2f%%', k.slice(0, 46), (v / total * 100).toFixed(2));
}

await browser.close();
