/* 验收站：家具建模验收台
 * - 每件家具一个独立预览空间（棚拍灯光/转盘/线框/截图）
 * - 加载 models/<type>.glb，本地 PBR 材质
 * - 读 models/manifest.json 里的真实几何体检数据（面数/顶点/尺寸）
 * - 右侧显示参考素材图，用于与原版建模对照
 */
import * as THREE from './vendor/three.module.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';
import { OrbitControls } from './vendor/OrbitControls.js';
import { RoomEnvironment } from './vendor/RoomEnvironment.js';

const V = document.getElementById('viewport');
const $ = (id) => document.getElementById(id);

/* ---------------- 渲染器 ---------------- */
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
V.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0c0e10);
scene.environment = new THREE.PMREMGenerator(renderer)
  .fromScene(new RoomEnvironment(), 0.04).texture;

const camera = new THREE.PerspectiveCamera(38, 1, 0.05, 200);
camera.position.set(2.6, 1.9, 3.2);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.075;
controls.minDistance = 0.6;
controls.maxDistance = 14;
controls.maxPolarAngle = Math.PI * 0.495;
controls.target.set(0, 0.45, 0);

/* ---------------- 棚拍布光 ---------------- */
const key = new THREE.DirectionalLight(0xfff2e2, 2.5);
key.position.set(3.2, 5.0, 3.4);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.near = 0.5;
key.shadow.camera.far = 18;
key.shadow.camera.left = -4; key.shadow.camera.right = 4;
key.shadow.camera.top = 4; key.shadow.camera.bottom = -4;
key.shadow.bias = -0.0006;
key.shadow.normalBias = 0.018;
scene.add(key);

const fill = new THREE.DirectionalLight(0xcfe0ff, 0.55);
fill.position.set(-4, 2.6, -2.2);
scene.add(fill);

const rim = new THREE.DirectionalLight(0xffffff, 0.9);
rim.position.set(-1.6, 3.2, -4.2);
scene.add(rim);

scene.add(new THREE.HemisphereLight(0xdfe8f2, 0x1b1f24, 0.35));

/* 地面 + 接影（棚拍台）
 * 【关键】地面不能与家具底面共面（都在 y=0），否则深度冲突会把家具实体吃掉，
 * 只剩高出底面 1~2mm 的滚边/针脚可见（实测：沙发只显示为一条窄带）。
 * 做法：地面下沉 GROUND_DROP，让家具真正"落"在地面之上。
 */
const GROUND_DROP = 0.006;
const groundMat = new THREE.MeshStandardMaterial({ color: 0x1a1e22, roughness: 0.94, metalness: 0 });
const ground = new THREE.Mesh(new THREE.CircleGeometry(9, 64), groundMat);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -GROUND_DROP;
ground.receiveShadow = true;
scene.add(ground);

const contact = new THREE.Mesh(
  new THREE.PlaneGeometry(9, 9),
  new THREE.ShadowMaterial({ opacity: 0.42 })
);
contact.rotation.x = -Math.PI / 2;
contact.position.y = -GROUND_DROP * 0.5;
contact.receiveShadow = true;
scene.add(contact);

/* 尺寸标尺（放在模型前方地面） */
const rulerGroup = new THREE.Group();
const rulerMat = new THREE.LineBasicMaterial({ color: 0x4c9aff, transparent: true, opacity: 0.75 });
scene.add(rulerGroup);

function buildRuler(w, d) {
  rulerGroup.clear();
  const y = 0.004;
  const hw = w / 2, hd = d / 2;
  const pts = [
    new THREE.Vector3(-hw, y, hd + 0.14), new THREE.Vector3(hw, y, hd + 0.14),
    new THREE.Vector3(hw, y, hd + 0.14), new THREE.Vector3(hw, y, -hd - 0.14),
    new THREE.Vector3(hw, y, -hd - 0.14), new THREE.Vector3(-hw, y, -hd - 0.14),
    new THREE.Vector3(-hw, y, -hd - 0.14), new THREE.Vector3(-hw, y, hd + 0.14),
  ];
  const g = new THREE.BufferGeometry().setFromPoints(pts);
  rulerGroup.add(new THREE.LineSegments(g, rulerMat));
  // 刻度端点
  for (const sx of [-1, 1]) {
    const p = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(sx * hw, y, hd + 0.08), new THREE.Vector3(sx * hw, y, hd + 0.20),
    ]);
    rulerGroup.add(new THREE.LineSegments(p, rulerMat));
  }
}

/* ---------------- 状态 ---------------- */
const state = {
  manifest: null,
  items: [],
  current: null,
  wire: false,
  spin: false,
  model: null,
  box: new THREE.Box3(),
  size: new THREE.Vector3(),
  groups: [],
  query: '',
  roadmap: null,
  batch: '',        // 当前批次筛选（'' = 全部）
};

/* ---------------- 建模批次（roadmap.json） ----------------
 * 251 款不是一次做完的 —— roadmap.json 把它们排成 P0~P4 五个批次，
 * 每批说明目标与款式 key。验收站左侧的 chip 显示每批实时进度，
 * 点一下就只看该批款式，方便按批次推进与验收。
 */
async function loadRoadmap() {
  const rm = await loadJSON('models/roadmap.json').catch(() => null);
  if (!rm) return null;
  // 建立 key → batch 映射
  const key2batch = new Map();
  for (const b of rm.batches || []) {
    for (const k of b.items || []) key2batch.set(k, b.id);
  }
  rm._key2batch = key2batch;
  return rm;
}

function batchProgress(b) {
  const keys = new Set(b.items || []);
  let ok = 0, total = 0;
  for (const it of state.items) {
    if (!keys.has(it.key)) continue;
    total++;
    if (it.status === 'ok') ok++;
  }
  return { ok, total };
}

function renderBatches() {
  const box = $('batches');
  if (!box) return;
  if (!state.roadmap) { box.innerHTML = ''; return; }
  const chips = [];
  // 全部
  const allOk = state.items.filter((i) => i.status === 'ok').length;
  chips.push(
    `<button class="bchip${state.batch === '' ? ' on' : ''}" data-b="">` +
    `全部<span class="bp">${allOk}/${state.items.length}</span></button>`);

  for (const b of state.roadmap.batches || []) {
    const { ok, total } = batchProgress(b);
    const pct = total ? Math.round((ok / total) * 100) : 0;
    const cls = ['bchip'];
    if (state.batch === b.id) cls.push('on');
    if (b.status === 'done') cls.push('done');
    chips.push(
      `<button class="${cls.join(' ')}" data-b="${b.id}" title="${b.name} — ${b.goal}">` +
      `${b.id}<span class="bp">${ok}/${total}</span>` +
      `<span class="bar"><i style="width:${pct}%"></i></span></button>`);
  }
  box.innerHTML = chips.join('');
  box.querySelectorAll('.bchip').forEach((c) => {
    c.onclick = () => {
      state.batch = c.dataset.b;
      renderBatches();
      renderList();
    };
  });
}

/* ---------------- 加载清单 ----------------
 * catalog.json  = 全屋完整目录（251 款，按组分类，含建模状态）
 * manifest.json = 已建模款式的几何体检数据
 */
async function loadJSON(p) {
  const r = await fetch(p, { cache: 'no-store' });
  if (!r.ok) throw new Error(p + ' ' + r.status);
  return await r.json();
}
async function loadManifest() {
  const [cat, man] = await Promise.all([
    loadJSON('models/catalog.json').catch(() => null),
    loadJSON('models/manifest.json').catch(() => ({ items: [] })),
  ]);
  if (!cat) return man;                       // 兜底：只有 manifest
  // 把体检数据按【cat 绑定】合并进目录条目。
  // 【关键】manifest.key 是模型类型（sofa/bed/...），catalog.key 是款式
  // （三人沙发/双人沙发/...）。必须用 manifest 显式声明的 cat 字段做唯一绑定，
  // 不能用 byType[it.type] 兜底 —— 那会让 1 件模型广播到该 type 的所有款式上
  // （实测 bug：8 件模型被标成 26 款达标，双人沙发显示三人沙发的尺寸）。
  const byCat = {};
  for (const it of man.items || []) {
    if (it.cat) byCat[it.cat] = it;
  }
  for (const g of cat.groups) {
    for (const it of g.items) {
      const m = byCat[it.key];
      if (m) {
        it.file = m.file || it.file;
        it.status = m.status || 'none';
        it.tris = m.tris || 0;
        it.checks = m.checks || [];
        it.ref = m.ref || null;
        it.refTitle = m.refTitle || null;
        it.refNote = m.refNote || it.refNote || '';
      }
    }
  }
  return { items: cat.groups.flatMap((g) => g.items), groups: cat.groups, total: cat.total };
}
/* ---------------- 渲染清单（分组 + 搜索 + 批次 + 状态徽章） ---------------- */
function renderList() {
  const box = $('list');
  box.innerHTML = '';
  const q = (state.query || '').trim().toLowerCase();
  const rm = state.roadmap;
  const k2b = rm ? rm._key2batch : null;

  for (const g of state.groups) {
    const items = g.items.filter((it) => {
      if (q && !(it.name.toLowerCase().includes(q) || it.type.toLowerCase().includes(q)))
        return false;
      // 批次筛选：只显示属于当前批次的款式
      if (state.batch && k2b) {
        if (k2b.get(it.key) !== state.batch) return false;
      }
      return true;
    });
    if (!items.length) continue;

    const hd = document.createElement('div');
    hd.className = 'grp';
    const done = items.filter((i) => i.status === 'ok').length;
    hd.innerHTML = `<span>${g.name}</span><em>${done}/${items.length}</em>`;
    box.appendChild(hd);

    for (const it of items) {
      const d = document.createElement('div');
      d.className = 'item' + (state.current === it.key ? ' sel' : '');
      const st = it.status || 'none';
      d.innerHTML =
        `<i class="st dot ${st}"></i>` +
        `<span class="nm">${it.name}</span>` +
        `<span class="mt">${it.tris ? it.tris.toLocaleString() + ' tri' : '待建模'}</span>`;
      d.onclick = () => select(it.key);
      box.appendChild(d);
    }
  }
  if (!box.children.length) {
    box.innerHTML = '<div class="refempty" style="padding:20px">没有匹配的款式</div>';
  }

  const c = { ok: 0, warn: 0, bad: 0, none: 0 };
  for (const it of state.items) c[it.status || 'none'] = (c[it.status || 'none'] || 0) + 1;
  $('topstats').innerHTML =
    `<span>共 <b>${state.items.length}</b> 款</span>` +
    `<span class="s-ok">达标 <b>${c.ok}</b></span>` +
    `<span class="s-warn">偏差 <b>${c.warn}</b></span>` +
    `<span class="s-bad">未达标 <b>${c.bad}</b></span>` +
    `<span>待建模 <b>${c.none}</b></span>`;
}

/* ---------------- 载入模型 ---------------- */
const loader = new GLTFLoader();

function clearModel() {
  if (state.model) {
    scene.remove(state.model);
    state.model.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) {
        const ms = Array.isArray(o.material) ? o.material : [o.material];
        for (const m of ms) m.dispose();
      }
    });
  }
  state.model = null;
}

function applyWire(root) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    const ms = Array.isArray(o.material) ? o.material : [o.material];
    for (const m of ms) {
      if (!m) continue;
      if (!m.userData.__wireSaved) {
        m.userData.__wireSaved = { wireframe: m.wireframe, transparent: m.transparent, opacity: m.opacity };
      }
      m.wireframe = state.wire;
      if (state.wire) { m.transparent = true; m.opacity = 0.75; }
      else { m.transparent = m.userData.__wireSaved.transparent; m.opacity = m.userData.__wireSaved.opacity; }
      m.needsUpdate = true;
    }
  });
}

function select(key) {
  const it = state.items.find((x) => x.key === key);
  if (!it) return;
  state.current = key;
  renderList();
  $('hName').textContent = it.name;
  $('refName').textContent = it.ref ? (it.refTitle || '参考图') : '无';
  $('refNote').textContent = it.refNote || '';
  const rb = $('refBox');

  // 渲染图（离线 Blender 出的棚拍图）+ 参考素材（外部实拍）双栏对照
  const shots = [];
  if (it.file) {
    const base = it.file.replace(/\.glb$/, '');
    for (const v of ['studio', 'front', 'detail']) {
      shots.push({ src: `models/preview_${base}_${v}.png`, label: v });
    }
  }
  const refs = it.ref ? [{ src: it.ref, label: it.refTitle || '参考' }] : [];

  const cards = [...shots, ...refs].map((s) =>
    `<figure class="shot"><img src="${s.src}" alt="${s.label}" loading="lazy"
       onerror="this.closest('.shot')?.remove()"><figcaption>${s.label}</figcaption></figure>`);
  rb.innerHTML = cards.length ? cards.join('') :
    '<div class="refempty">未选参考图</div>';

  if (!it.file) {
    clearModel();
    $('hDims').textContent = '—'; $('hTris').textContent = '—'; $('hVerts').textContent = '—';
    renderChecks(it);
    return;
  }

  clearModel();
  loader.load('models/' + it.file, (gltf) => {
    const root = gltf.scene;
    root.traverse((o) => {
      if (o.isMesh) {
        o.castShadow = true;
        o.receiveShadow = true;
        // 兜底：家具底面与地面共面时的深度冲突防护（polygonOffset 把模型往相机推）
        const ms = Array.isArray(o.material) ? o.material : [o.material];
        for (const m of ms) {
          if (!m) continue;
          m.polygonOffset = true;
          m.polygonOffsetFactor = -1;
          m.polygonOffsetUnits = -1;
        }
      }
    });
    state.model = root;
    scene.add(root);
    state.box.setFromObject(root);
    state.box.getSize(state.size);
    const c = state.box.getCenter(new THREE.Vector3());
    // 落地居中
    root.position.x -= c.x;
    root.position.z -= c.z;
    root.position.y -= state.box.min.y;
    state.box.setFromObject(root);
    state.box.getSize(state.size);
    applyWire(root);
    buildRuler(state.size.x, state.size.z);
    controls.target.set(0, state.size.y * 0.45, 0);
    camera.position.set(state.size.x * 1.25 + 1.4, state.size.y * 0.8 + 1.3, state.size.z * 1.5 + 1.9);
    fitCamera();
    $('hDims').textContent = `${Math.round(state.size.x * 1000)} × ${Math.round(state.size.z * 1000)} × ${Math.round(state.size.y * 1000)}`;
    $('hTris').textContent = (it.tris || 0).toLocaleString();
    $('hVerts').textContent = (it.verts || 0).toLocaleString();
    renderChecks(it);
  }, undefined, (err) => {
    console.error('GLB 加载失败', it.file, err);
    $('hDims').textContent = '加载失败';
  });
}

/* ---------------- 取景 ----------------
 * 【关键】不能用"包围球半径 / sin(fov)"估距：宽而扁的家具（沙发 2.24×0.9×0.87）
 * 在三分之四视角下，投影后的对角线远大于包围球半径，会左右溢出画布。
 * 正确做法：把包围盒 8 个角投影到【相机空间】（相对相机位置，不是相对 target），
 * 取最大横向/纵向张角，据此反算距离，并用多次迭代收敛（距离变化会改变投影深度）。
 */
const _corner = new THREE.Vector3();
function projectExtent(camPos, qInv) {
  const s = state.size;
  let maxH = 0.001, maxV = 0.001;
  for (let i = 0; i < 8; i++) {
    _corner.set(
      i & 1 ? s.x / 2 : -s.x / 2,
      i & 2 ? s.y : 0,
      i & 4 ? s.z / 2 : -s.z / 2
    ).sub(camPos).applyQuaternion(qInv);
    const z = Math.max(0.001, -_corner.z);   // 相机前方为 -z
    maxH = Math.max(maxH, Math.abs(_corner.x) / z);
    maxV = Math.max(maxV, Math.abs(_corner.y) / z);
  }
  return { maxH, maxV };
}

function fitDistanceFor(dir, fill) {
  const target = controls.target.clone();
  const aspect = camera.aspect || 1;
  const tanH = Math.tan((camera.fov * Math.PI / 180) / 2);
  const tanV = tanH / aspect;

  let dist = Math.max(state.size.x, state.size.y, state.size.z) * 2.2;
  for (let iter = 0; iter < 5; iter++) {
    const camPos = target.clone().addScaledVector(dir, dist);
    const m = new THREE.Matrix4().lookAt(camPos, target, camera.up);
    const qInv = new THREE.Quaternion().setFromRotationMatrix(m).invert();
    const { maxH, maxV } = projectExtent(camPos, qInv);
    const need = Math.max(maxH / tanH, maxV / tanV) / fill;
    dist *= need;
  }
  return dist;
}
function fitCamera() {
  const dir = new THREE.Vector3(0.72, 0.46, 1).normalize();
  const d = fitDistanceFor(dir, 0.86);
  camera.position.copy(controls.target).addScaledVector(dir, d);
  controls.update();
}

/* ---------------- 自检清单 ---------------- */
function renderChecks(it) {
  const list = $('cList');
  list.innerHTML = '';
  const rows = it.checks || [];
  let pass = 0;
  for (const c of rows) {
    if (c.level === 'ok') pass++;
    const d = document.createElement('div');
    d.className = 'crow ' + c.level;
    const ico = c.level === 'ok' ? '✔' : c.level === 'warn' ? '!' : '✕';
    d.innerHTML = `<span class="ci">${ico}</span><span class="cx">${c.text}</span>` +
      (c.value ? `<span class="cv">${c.value}</span>` : '');
    list.appendChild(d);
  }
  const total = rows.length || 1;
  $('cScore').textContent = rows.length ? `${pass}/${rows.length} 通过` : '无记录';
  $('cScore').style.color = !rows.length ? 'var(--fg3)'
    : pass === total ? 'var(--ok)' : pass / total > 0.6 ? 'var(--warn)' : 'var(--bad)';
}

/* ---------------- 视图控制 ---------------- */
function buildTabs() {
  const g = $('spaceTabs');
  g.innerHTML = '';
  const defs = [
    ['棚拍', 'studio'], ['正视图', 'front'], ['俯视图', 'top'], ['侧视图', 'side']
  ];
  defs.forEach(([label, mode], i) => {
    const b = document.createElement('button');
    b.className = 'mini' + (i === 0 ? ' on' : '');
    b.textContent = label;
    b.onclick = () => {
      [...g.children].forEach((x) => x.classList.remove('on'));
      b.classList.add('on');
      setView(mode);
    };
    g.appendChild(b);
  });
}

function setView(mode) {
  const s = state.size;
  const t = new THREE.Vector3(0, s.y * 0.45, 0);
  controls.target.copy(t);
  camera.up.set(0, 1, 0);
  // 各视图的相机方向（统一走精确投影取景，保证不裁切）
  const dirs = {
    front: new THREE.Vector3(0, 0.10, 1),
    side: new THREE.Vector3(1, 0.10, 0),
    top: new THREE.Vector3(0.001, 1, 0.001),
    studio: new THREE.Vector3(0.72, 0.46, 1).normalize(),
  };
  const dir = (dirs[mode] || dirs.studio).clone().normalize();
  if (mode === 'top') camera.up.set(0, 0, -1);
  const d = fitDistanceFor(dir, 0.86);
  camera.position.copy(t).addScaledVector(dir, d);
  controls.update();
}

document.querySelectorAll('#viewbar [data-act]').forEach((b) => {
  b.onclick = () => {
    const act = b.dataset.act;
    if (act === 'wire') { state.wire = !state.wire; b.classList.toggle('on', state.wire); if (state.model) applyWire(state.model); }
    else if (act === 'spin') { state.spin = !state.spin; b.classList.toggle('on', state.spin); }
    else if (act === 'reset') { setView('studio'); fitCamera(); }
    else if (act === 'shot') {
      renderer.render(scene, camera);
      const a = document.createElement('a');
      a.download = (state.current || 'shot') + '.png';
      a.href = renderer.domElement.toDataURL('image/png');
      a.click();
    }
  };
});

$('btnReload').onclick = () => { if (state.current) select(state.current); };

/* ---------------- 主循环 ---------------- */
function resize() {
  const w = V.clientWidth, h = V.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(V);
resize();

let prev = performance.now();
function loop(now) {
  requestAnimationFrame(loop);
  const dt = now - prev; prev = now;
  if (state.spin && state.model) {
    state.model.rotation.y += dt * 0.00042;
  }
  controls.update();
  renderer.render(scene, camera);
}
requestAnimationFrame(loop);

/* ---------------- 启动 ---------------- */
window.__ACC_ERRORS = [];
window.addEventListener('error', (e) => {
  window.__ACC_ERRORS.push(String(e.message || e.error));
});

(async function init() {
  try {
    const man = await loadManifest();
    state.manifest = man;
    state.items = man.items || [];
    state.groups = man.groups || [{ name: '全部', items: state.items }];
    state.roadmap = await loadRoadmap();
    renderBatches();
    renderList();
    buildTabs();
    // 默认选中第一个「已建模」的款式（没建的就选第一个）
    const firstBuilt = state.items.find((i) => i.file) || state.items[0];
    if (firstBuilt) select(firstBuilt.key);

    // 搜索框
    const q = $('q');
    if (q) {
      q.oninput = () => { state.query = q.value; renderList(); };
    }
  } catch (e) {
    window.__ACC_ERRORS.push('init: ' + e.message);
    document.getElementById('list').innerHTML =
      '<div class="refempty" style="padding:20px">清单加载失败：' + e.message + '</div>';
  }
})();

window.__ACC = {
  state, select,
  list: () => state.items.map((i) => ({ key: i.key, name: i.name, status: i.status, tris: i.tris })),
  camera: () => ({ pos: camera.position.toArray(), target: controls.target.toArray() }),
  // 渲染探针：直接读回 renderer.info 与包围盒，用于排查"模型加载了但画不出来"
  probe: () => {
    const st = state;
    let meshes = 0, drawn = 0, tris = 0;
    const ndc = [];
    if (st.model) {
      st.model.traverse((o) => {
        if (!o.isMesh) return;
        meshes++;
        const g = o.geometry;
        tris += (g.index ? g.index.count : g.attributes.position.count) / 3;
        if (['base', 'arm_L', 'seat_0', 'backrest'].includes(o.name)) {
          const p = new THREE.Vector3();
          o.getWorldPosition(p);
          ndc.push({
            n: o.name,
            world: p.toArray().map((x) => +x.toFixed(3)),
            ndc: p.clone().project(camera).toArray().map((x) => +x.toFixed(3)),
            side: o.material.side, visible: o.visible,
          });
        }
      });
    }
    const b = new THREE.Box3();
    if (st.model) b.setFromObject(st.model);
    return {
      meshes, tris: Math.round(tris),
      renderCalls: renderer.info.render.calls,
      renderTris: renderer.info.render.triangles,
      boxMin: b.min.toArray(), boxMax: b.max.toArray(),
      camPos: camera.position.toArray(), camTarget: controls.target.toArray(),
      camNear: camera.near, camFar: camera.far,
      groundY: ground.position.y,
      ndc,
    };
  },
  diag: () => ({
    items: state.items.length,
    current: state.current,
    loaded: !!state.model,
    size: state.size.toArray(),
    checks: (state.items.find((i) => i.key === state.current) || {}).checks || [],
  }),
  errors: window.__ACC_ERRORS || [],
};

/* 诊断输出到 DOM，便于无 CDP 环境下排查（也方便用户自己看） */
function paintDiag() {
  const d = window.__ACC.diag();
  const el = document.getElementById('diag');
  if (!el) return;
  el.textContent =
    `items=${d.items} current=${d.current} loaded=${d.loaded} ` +
    `size=${d.size.map((v) => v.toFixed(3)).join('×')} ` +
    `errs=${JSON.stringify(window.__ACC.errors)}`;
}
setInterval(paintDiag, 800);
