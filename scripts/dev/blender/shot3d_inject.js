"""浏览器端 3D 场景截图助手（CDP 注入用）。

【为什么需要】
  browser_take_screenshot 对 WebGL 画布返回全白 —— 渲染缓冲没有
  preserveDrawingBuffer，截图拿不到 GPU 内容。
  这里改成：手动调 renderer.render() → 把 canvas 画到 2D canvas →
  toDataURL() 传回，再由本地脚本落盘成图片。

【用法】
  1) 在页面里调用 __shot3d({pos:[x,y,z], tgt:[x,y,z], w:1200, h:800, out:'a.jpg'})
  2) 返回 {dataURL, stats}
"""
window.__shot3d = function (opt) {
  opt = opt || {};
  const jt = window.__d && window.__d.jt;
  const sc = window.__scene;
  const cam = window.__cam || (window.__d && window.__d.Ze);
  if (!jt || !sc || !cam) return JSON.stringify({ err: 'missing renderer/scene/cam' });

  const W = opt.w || 1200, H = opt.h || 800;
  const pos = opt.pos, tgt = opt.tgt;
  if (pos && tgt) {
    cam.position.set(pos[0], pos[1], pos[2]);
    cam.lookAt(tgt[0], tgt[1], tgt[2]);
    if (cam.updateProjectionMatrix) cam.updateProjectionMatrix();
  }

  jt.render(sc, cam);

  const src = jt.domElement;
  const c2 = document.createElement('canvas');
  c2.width = W; c2.height = H;
  const g = c2.getContext('2d');
  g.drawImage(src, 0, 0, W, H);

  // 统计：取样像素，算非背景比例与平均亮度
  const d = g.getImageData(0, 0, W, H).data;
  let sum = 0, nonBg = 0, n = 0;
  for (let i = 0; i < d.length; i += 4 * 37) {
    const l = (d[i] * 0.299 + d[i + 1] * 0.587 + d[i + 2] * 0.114);
    sum += l; n++;
    if (l < 248) nonBg++;
  }
  return JSON.stringify({
    dataURL: c2.toDataURL('image/jpeg', 0.86),
    stats: { avgLum: +(sum / n).toFixed(1), nonBgPct: +((nonBg / n) * 100).toFixed(1) }
  });
};
'__shot3d_ready'
