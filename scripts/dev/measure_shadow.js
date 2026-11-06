// 实测阴影贴图的开销：影子灯每盏 = 一整轮额外的场景渲染
import puppeteer from 'puppeteer-core';
import fs from 'fs';

const URL_ = process.argv[2] || 'http://127.0.0.1:8899/template.html';
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

const info = await page.evaluate(() => {
  const scene = window.__D3 && window.__D3.scene;
  const out = { lights: [] };
  if (!scene) return { error: 'no scene' };
  scene.traverse(o => {
    if (o.isLight) {
      out.lights.push({
        type: o.type,
        castShadow: !!o.castShadow,
        visible: o.visible,
        intensity: +(o.intensity || 0).toFixed(2),
        shadowMapSize: o.shadow && o.shadow.mapSize ? o.shadow.mapSize.x : null,
      });
    }
  });
  out.shadowCasters = out.lights.filter(l => l.castShadow && l.visible).length;

  // renderer.info 里的 draw call
  try {
    const r = window.__D3.renderer;
    if (r && r.info) {
      out.render = {
        calls: r.info.render.calls,
        triangles: r.info.render.triangles,
        programs: r.info.programs ? r.info.programs.length : null,
        geometries: r.info.memory.geometries,
        textures: r.info.memory.textures,
      };
    }
  } catch (e) { out.renderErr = String(e); }
  return out;
});

// 测：关掉阴影 vs 开着阴影 的帧率差
async function fps(n = 100) {
  return await page.evaluate(async (n) => {
    const gaps = [];
    await new Promise(res => {
      let last = performance.now(), i = 0;
      function tick(now) { gaps.push(now - last); last = now; if (++i < n) requestAnimationFrame(tick); else res(); }
      requestAnimationFrame(tick);
    });
    gaps.sort((a, b) => a - b);
    return +(1000 / gaps[(gaps.length * 0.5) | 0]).toFixed(1);
  }, n);
}

const fpsOn = await fps();

// 关掉所有投影灯
await page.evaluate(() => {
  window.__D3.scene.traverse(o => { if (o.isLight && o.castShadow) o.castShadow = false; });
});
await new Promise(r => setTimeout(r, 2500));
const fpsNoShadow = await fps();

// 恢复
await page.evaluate(() => {
  window.__D3.scene.traverse(o => { if (o.isLight && o.type === 'DirectionalLight') o.castShadow = true; });
});
await new Promise(r => setTimeout(r, 2000));

console.log(JSON.stringify({ ...info, fpsWithShadow: fpsOn, fpsNoShadow }, null, 2));
await browser.close();
