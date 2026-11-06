/**
 * 测试用本地静态服务器。
 *
 * 为什么需要：设计器里的 PBR 贴图用 `new Image(); img.src="furnlib/tex/x.jpg"` 加载。
 * 用 file:// 打开页面时，每张图都是独立的不透明源，WebGL 会拒绝把它上传成贴图，
 * 报 `THREE.WebGLState: SecurityError ... contains cross-origin data`，
 * 结果是所有 PBR 贴图在测试里【全部没生效】——测试截图看着正常，其实材质是假的。
 * 所以所有跑页面的测试脚本都必须走 http://。
 *
 * 用法：
 *   import { pageUrl } from './lib_serve.mjs';
 *   const { url, close } = await pageUrl(file);
 *   await page.goto(url + '?debug');
 *   ... 测试 ...
 *   await close();
 *
 * 服务以 HTML 文件所在目录为根（页面里的相对路径 furnlib/tex/… 依赖这个根），
 * 端口用 0 让系统分配空闲端口，避免和 assets/serve.py 的 8899 冲突。
 */
import http from 'http';
import fs from 'fs';
import path from 'path';
import { pathToFileURL } from 'url';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.htm': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
  '.webp': 'image/webp', '.avif': 'image/avif', '.gif': 'image/gif',
  '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
  '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json', '.bin': 'application/octet-stream',
  '.wasm': 'application/wasm', '.ktx2': 'image/ktx2', '.basis': 'application/octet-stream',
  '.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf',
  '.mp4': 'video/mp4', '.pdf': 'application/pdf', '.txt': 'text/plain; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
};

/**
 * 起一个静态服务器。
 * @param {string} file 页面文件路径（用它的目录当服务根目录）
 */
export async function servePage(file) {
  const abs = path.resolve(file);
  const root = path.dirname(abs);
  const server = http.createServer((req, res) => {
    try {
      let p = decodeURIComponent((req.url || '/').split('?')[0].split('#')[0]);
      if (p.endsWith('/')) p += path.basename(abs);
      // 浏览器总会去要 /favicon.ico；回一个空的 204，免得控制台多一条 404 报错
      if (p === '/favicon.ico') { res.writeHead(204).end(); return; }
      const target = path.join(root, p);
      // 防目录穿越
      if (!path.resolve(target).startsWith(path.resolve(root))) {
        res.writeHead(403).end('forbidden');
        return;
      }
      fs.stat(target, (err, st) => {
        if (err || !st.isFile()) { res.writeHead(404).end('not found'); return; }
        const type = MIME[path.extname(target).toLowerCase()] || 'application/octet-stream';
        res.writeHead(200, {
          'Content-Type': type,
          'Content-Length': st.size,
          // 测试期间必须禁用缓存，否则改完代码重跑会看到旧版本
          'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        });
        fs.createReadStream(target).pipe(res);
      });
    } catch (e) {
      res.writeHead(500).end(String(e && e.message || e));
    }
  });
  await new Promise((r, j) => { server.once('error', j); server.listen(0, '127.0.0.1', r); });
  const port = server.address().port;
  return {
    port,
    url: (f) => f ? `http://127.0.0.1:${port}/${path.basename(path.resolve(f))}` : `http://127.0.0.1:${port}/`,
    close: () => new Promise(r => server.close(() => r())),
  };
}

/** 已经传了 http(s) 地址就直接用；否则起服务把本地文件变成 http 地址 */
export async function pageUrl(file) {
  if (/^https?:/i.test(file)) return { url: file, close: async () => {} };
  const srv = await servePage(file);
  return { url: srv.url(file), close: srv.close };
}

/** 保持旧行为：file:// 的绝对地址（只用于下载产物之类的场景，页面本体不要用） */
export { pathToFileURL };
