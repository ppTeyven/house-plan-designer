# 户型装修设计器 · 系统化交接文档

> 用途：新会话的 AI 在动手前必须通读本文档。它描述了项目结构、修改操作规程、压缩变量字典、
> 全部已实施改动（含精确定位锚点）、设计决策与禁令、调试经验、验收基线与需求回应指南。
> 配套深度笔记：`C:\Users\zzkkg\AppData\Local\Cursor\User\memories\memory.md`（前几轮会话的细节与验证记录）。

---

## 1. TL;DR（30 秒上下文）

- 项目是一个**单文件前端应用**：2D 平面绘图 + 3D 户型渲染 + 第一人称漫游 + 水电管线 + 智能家居控制。
- **唯一修改对象**：`D:\house planner\house-plan-designer-main\assets\template.html`（约 2MB，内联压缩 ES module + 巨型 `<style>`）。
- 本地服务：同目录 `serve.py`（强制 no-store）→ `http://127.0.0.1:8899/template.html`。
- 代码是**压缩产物**（短变量名如 `jt/pt/S0`）：只能锚点定位 + 字符串精确替换，禁止整体格式化。
- 每次改动后：`node --check` 语法校验 → HTTP 拉取确认新版 → 刷新页面 → 运行时探针验证。
- 用户机器 1920×1080 @ DPR=1；高画质**必须保留 1.25× 超采样**；一切以"不闪、平滑、清晰"为验收标准。

---

## 2. 运行与基础设施

| 项 | 说明 |
|---|---|
| 服务器 | `python serve.py`（监听 8899，响应头 `Cache-Control: no-store`，读取 script 同目录） |
| 自启 | `serve.bat`：netstat 检查 8899 → 无则 `pythonw serve.py`（放启动项） |
| HTML 防缓存 | `template.html` `<head>` 内含 no-store/no-cache/pragma 三个 meta |
| 访问 | Cursor 内置浏览器打开 `http://127.0.0.1:8899/template.html`；CDP 可控制（viewId 会变，先 browser_tabs 确认） |
| 历史坑 | 曾因旧 python http.server 无缓存头 + Chrome 启发式缓存造成"改了什么都没生效/回退"的假象，用户对此非常敏感——永远先确认服务器返回的是新字节 |

---

## 3. 文件解剖

`template.html` 自上而下：
1. `<head>`：title、禁缓存 meta、**巨大的内联 `<script type="module">`**（全部引擎+UI 逻辑，文件末尾 user 新增的补丁 IIFE 也在这里）、`<style>`（全部 CSS，最后一块是历次追加的覆盖样式）。
2. `<body>`：应用骨架（header 工具栏、左侧面板、`.stage` 含 `#pane2d/#pane3d`、右侧 inspector、footer）。
3. 注意：文件里 `</script>` 只出现一次（模块包结束处）；CSS 在其后的一个 `<style rel="stylesheet">` 里。

---

## 4. 修改操作规程（SOP，必须遵守）

> **2026-11-06 起强烈建议用工具代替手工**：
> `python scripts/dev/patch_template.py --pairs-file <json>` —— 它会自动做
> 锚点唯一性校验（不唯一直接拒绝写入）、`node --check` 语法校验、
> **行尾符守卫**（防止把 LF 写成 CRLF 导致整个文件在 git 里被重写）、写回后回读校验。
> 手工改 2MB 压缩产物极易把行尾符/编码改坏。

1. **定位**：先 Grep/锚点注释找到目标代码，读足上下文，理解压缩变量语义（见 §5 字典）。
2. **替换**：用"精确且唯一"的字符串做替换；每次替换后立刻确认替换点前后结构完好（读回该区域）。
3. **语法检查**（必须 exit 0）：
```powershell
$f='D:\house planner\house-plan-designer-main\assets\template.html'; $txt=[System.IO.File]::ReadAllText($f); $s=$txt.IndexOf('<script type="module"'); $s=$txt.IndexOf('>',$s)+1; $e=$txt.IndexOf('</script>',$s); [System.IO.File]::WriteAllText("$env:TEMP\bundle_check.mjs",$txt.Substring($s,$e-$s)); node --check "$env:TEMP\bundle_check.mjs"
```
4. **服务校验**：`Invoke-WebRequest http://127.0.0.1:8899/template.html` 确认 200 且内容含新增锚点字符串。
5. **页面刷新 + 运行时探针**：`location.reload()` 后等 14–15s（含 1.8s 预热），用 CDP `Runtime.evaluate` 检查 DOM/画布几何/样式计算值。
6. **交互验证**：合成 PointerEvent 可以测试，但 `bubbles:true` 可能触发应用的全局处理（曾导致视图被误切换）——风险场景改用临时 `window.__xx` 钩子验证后删除。
7. 模块内变量（jt/pt/Se…）在全局作用域**不可访问**；需要探针时临时在 bundle 里加钩子，验证后移除。

---

## 5. 压缩变量字典（Grep 可验证）

**渲染核心**：`jt`=WebGLRenderer | `pt`=Scene | `Ze`=Camera | `Tt`=OrbitControls | `S0`=EffectComposer | `eh`=后期参数集合(composer/ao/bloom/SSRZ/grade/tilt)
**尺寸/像素**：`Cp()`=像素比策略 | `bi`=画质档(hd-quality) | `Gh()`=3D 画布尺寸同步 | 每帧守护=`tick()`(锚点注释"分辨率跟随") | `tc`=2D 画布设备比
**视图状态**：`E.view`/`W2.dataset.view` | `E.transitioning`=切换动画中（**Gh/_x/tick 防闪都依赖它**）| `Ua(view)`=视图切换 | `Ns()`=退出漫游 | `re`=漫游状态(re.active)
**2D**：`Se`={s,ox,oy,W,H} 视图 | `_x()`=2D 画布尺寸 | `ri()`=适应窗口 | `Je()`=重绘 | `J0`=#c2d | `M4`=#pane2d
**3D 结构**：`An`=家具组 | `F0`=墙组 | `On`=门窗组 | `C0`=吊顶组(仅漫游可见) | `Iu/Nu/Ou`=天空穹顶/日/月精灵 | `Bo`=其他楼层 | `b8`=#pane3d | `O0`=#c3d canvas | `os`=3D 容器
**拾取/几何**：`Nr`=Raycaster | `au(e)`=指针→NDC | `I1(n,e)`=通用拾取 | `z0`=Box3 | `z`=Vector3 | `Kk`=LineSegments | `Q4`=LineBasicMaterial | `Ut`=BufferGeometry | `vt`=BufferAttribute
**渲染/场景操作**：`gs()`=3D 场景重建 | `Is()`=家具同步 | `Zc()`=立即渲染一帧 | `dx(n)`=主渲染帧 | `ja()`=光照/天气重算 | `SL()`=已清空(见禁令) | `Yv()`/`U5`=合成器按模式重建 | `Xv()`=切画质 | `Aw()`=3D 渲染器初始化/预热
**相机**：`L1(Se,w,h)`=2D视图→3D俯视相机参数 | `P1(state,bounds,w,h,pad)`=适配 | `ao(state)`=立即设置相机 | `wi(state,ms,cb)`=相机缓动 | `uo()`=默认斜角视角
**用户数据/选项**：`E.plan.look`(Dn())={style,palette,glow,labels,round,tilt,grade,ssr} | `E.opts.lock3d`(hd-lock3d) | `Z`/`E.plan`=户型数据
**本次新增辅助**（全部在 bundle 末尾或 Ua 内）：`__fade/__walkSwitch/__walkPre/__walkFinish`(黑场过渡) | `__x2snap`(2D切换快照) | watcher(transitioning 翻转后一次性重建) | 悬停虚线框 IIFE | ripple IIFE
> 2026-11-06 清理：`skyDim/skyFade/__riSmooth/__riToFull/__syncCam3d` 已删除（声明后从未被调用，见 §7 死代码清单）。

---

## 6. 已实施改动登记册（全部已完成并验证，禁止无意回退）

### 6.1 分辨率体系
- `Cp()`：fast=1；balanced=min(max(DPR,1.25),1.5)；high=min(max(DPR,1.25),2)。**1.25 下限是画质关键**（用户屏幕 DPR=1，纯 1:1 会被骂"糊"）。
- 合成链（创建/复用/Gh/AO/Bloom/景深/SSRZ/SMAA）全部按 CSS×Cp 设备像素；SMAA 创建**不要**再乘 pixelRatio。
- 每帧守护 `tick()`：canvas 物理 = 面板 CSS×Cp；`E.transitioning` 时只做便宜的 jt.setSize，**不**重建 composer；resize 后立即 `Zc()` 同步渲染（防清空帧闪屏）。
- SSRZ `setSize` 全分辨率（rt2 不再半分辨率）。漫游关 SSR/关全景兜底；相机光 distance=0 防光圈；全景 6 面幂4混合；点位标签 DOM 不放大 12px；楼层名精灵 1024×320；漫游 HUD（视高/视距/视角）；60fps 锁帧(hiIv)；整屋静态阴影。

### 6.2 切换防闪（用户核心痛点，已根治不要遮罩）
- 视图切换不用遮罩；根治方案：动画期间冻结合成器重建 + 画布等比例同步 + resize 后同步 `Zc()` 渲染 + `E.transitioning` 翻转后 watcher 一次性 `Gh()+_x()+Je()` 重建。
- 加载 1.8s 后 `Aw()` 预热 3D 渲染器（锚点"预热 3D 渲染器"）。

### 6.3 漫游过渡
- `#modeFade` 黑场层（锚点"按钮统一美化"前的 `#modeFade` 规则）。
- 进入漫游：`__walkPre(1300)` 在落地前 ~180ms 开始遮黑；落地回调 `__walkFinish` 重建后 280ms 快速淡出。退出用 `__walkSwitch`。
> 2026-11-06：`skyDim()/skyFade(1)` 已删除（声明后从未被调用）——天空渐显现在由 `__walkFinish` 链路直接处理，不要恢复这两个函数。
- `SL()` 已改成空函数（锚点 `function SL(){/*`）：**切换不再重算光影**，鸟瞰渲染好的直接用。不要恢复。

### 6.4 2D 缩放与相机一致性
- 2D↔分屏都平滑：分屏切换的 380ms 缓入缓出镜头已内联进 `Ua`/`watcher`；分屏→2D 等面板滑完再推镜（原 `__riToFull()`）。
> 2026-11-06：`__riSmooth()/__riToFull()/__syncCam3d()` 已删除（声明后从未被调用，逻辑已被内联过渡取代）。
- 切换中 2D 用快照平移裁切（`__x2snap`，`_x` 的 transitioning 分支），结束后丢弃快照做满分辨率重绘；2D 画布切换中与面板按比例同步（不拉伸）。
- 2D→3D/分屏保持**正俯视**（已删 `wi(uo(),1000)` 斜角 tween）；分屏时 3D 与 2D 等大，且对齐过程有 400ms 相机缓动。
- 3D→2D 收尾防顿挫（v2026-11-02）：`Ua` 的 3d→2d `setTimeout(...,640)` 分支内，在翻面瞬间（pane2d 未显形时）就地撤销 ox/oy 对齐补偿并 `Se.W/H=t.width/height`、`J0` 按最终尺寸重建、清 `__x2snap` 后 `Je()`——2D 画布从淡化第一帧起就是 1:1 最终分辨率（仅被 CSS scale .97→1 均匀缩放），watcher 在 `transitioning` 翻转后新增 `skip2d` 判定（`Y5` rect×`tc` 与 `J0` 尺寸一致且 `Se.W/H` 吻合时）跳过 `_x()/Je()`，消除"淡化将结束瞬间画布跳尺寸 + 清屏 + 双重重绘"的那一帧顿挫。改动仅两处锚点：`Ua` 内 `setTimeout(()=>{W2.dataset.view="2d"...` 与 watcher `else if (was) {`。
- 分屏→3D 填满构图（v2026-11-02）：`Ua` 收尾 `else` 分支内，`n==="3d"&&e==="split"` 时 `P1(i9,E.geo.bounds,stage.w,stage.h,60)` 适配整屏（四周留 60px）+ `wi(L1(...),800)` 平滑推近（替代原来相机停留在分屏半屏构图导致 3D 模型偏小）。锚点：`else W2.dataset.view=n,...`。正俯视不变，2d→3d/3d→2d 路径未动。

### 6.5 UI
- 按钮淡灰蓝底 `#f2f5fa`/边框 `#d3dae4`/文字 `#28303c`；选中态一律品牌蓝实底白字（`.seg button.on`/`.tbtn.on`/`.ibtn.on`），选中悬停深蓝 `#2458c8` 防变白；`.btn.primary` 悬停深蓝 `#255fd6` 白字（导出图纸曾被迫切成全白，已修，禁止回退）。
- 动效：涟漪（委托，480ms 自清）、悬停上浮、按下回弹、焦点环、prefers-reduced-motion 支持；全部只动 transform/opacity。
- **`.pane{will-change:auto}` 覆盖**（锚点"取消 .pane 的 will-change"）：曾在 .pane 上 will-change:left,width,opacity,transform 导致合成层关闭 ClearType 亚像素渲染，覆盖层文字发糊。**不要加回 will-change**。

### 6.6 3D 悬停虚线框
- 锚点"悬停可编辑家具"。非锁定（`!E.opts.lock3d`）、非漫游、非纯 2D 时，pointermove(50ms 节流) 对 `An.children` 射线检测，命中家具在其包围盒外围画蓝色虚线框（1px LineSegments 手工虚线，depthTest:false，renderOrder 999）；pointerleave 消失。
- 因 O0 在初始化后才存在，绑定用 setInterval 等 O0 就绪后执行（锚点 `__bindHover`）。

---

## 7. 设计决策与禁令（新 AI 不得推翻，除非用户明确要求）

1. 高画质保留 1.25 超采样；画质档策略见 `Cp()`。
2. 视图切换**不许用遮罩**；只许根治（冻结 composer + 等比例同步 + 同步渲染）。
3. 切换期间画布尺寸必须与面板**等比例**同步（用户嫌拉伸诡异）。
4. 2D→3D/分屏保持正俯视；分屏 3D 与 2D 等大。
5. 漫游黑屏在落地前开始、280ms 快速淡出；天空渐显。
6. `SL()` 保持空函数；光影鸟瞰渲染好直接沿用。
7. `.pane` 不加 will-change。
8. 按钮/选中/主按钮 hover 配色规则见 §6.5（选中或主按钮悬停绝不出现白底白字）。
9. 不要给浏览器页面加长期 debug 钩子；临时钩子用完删除。
10. 不改动文件结构、不格式化压缩代码；所有修改必须通过 §4 SOP。

---

## 8. 调试经验与已知坑

- "改动没生效" ⇒ 先查服务与缓存（8899 进程是否 serve.py、no-store 头、HTTP 字节含锚点），再怀疑代码。
- 替换文本时必须核对结果区段完整；该文件曾在替换中吞掉括号，全靠 `node --check` 兜底。
- CDP 合成 PointerEvent `bubbles:true` 可能触发应用全局逻辑（曾导致视图被切到 2D）；交互验证优先用真实坐标 + 短暂观察，必要时加钩子。
- `#c3d` 物理尺寸 = CSS×1.25（高画质）= 正确；`#c2d` 物理 = CSS×1（`tc`）。
- 页面刷新后需等 ~15s（含预热的初始化）。
- 截图工具输出是降采样图，判读小字号/细线要谨慎，用"像素计数"等程序化手段辅助。
- window 尺寸变化/分屏时画布等一切尺寸逻辑都走 Gh/_x/tick 三处，改动任何尺寸逻辑时要同步检查这三处与 watcher。

---

## 9. 验收基线（每次改动后对照）

- `node --check` exit 0；HTTP 200 且含新锚点。
- 控制台无报错；`main>aside` 存在（应用已启动）。
- 3D 高画质 canvas = CSS×1.25；分屏/2D/切回尺寸精确落位。
- 2D↔分屏↔3D 切换不闪、等比例、3D 正俯视、分屏等大;进入漫游黑屏时机正确、天空渐显；漫游进出正常。
- 悬停家具出现蓝虚线框；按钮悬停不变白。

---

## 10. 常见需求回应指南

| 用户说 | 先做什么 |
|---|---|
| "又闪了/糊了/回去了" | 先跑 §8 服务与缓存检查，再定位他说的具体场景（哪个视图、哪个阶段），拿数据说话 |
| "分辨率/清晰度…" | 检查 Cp()/canvas 物理尺寸/composer RT/超采样，不许降 1.25 下限 |
| "切换不顺畅" | 检查 Ua/transitioning 三处尺寸逻辑/watcher/Zc 同步渲染/分屏对齐缓动时序 |
| "漫游视角/黑屏" | 检查 __walkPre/__walkFinish 时序、wi 回调 |
| "UI 不好看/对比度" | 改追加的覆盖样式块（文件末尾 `<style>` 内），遵守 §6.5 配色规则，只动 transform/opacity |
| "3D 里…鼠标/选中/柜子" | 检查 An 射线、lock3d、悬停 IIFE；编辑逻辑在 c3d 的 pointerdown/up |
| 提新功能 | 先 Grep 找现有同类实现（引擎几乎全有基础设施），复用压缩类名（字典 §5），按 SOP 修改 |

---

## 11. 2026-11-06 代码审计与清理（本轮）

### 11.1 性能实测结论（先量后改，不要凭直觉改压缩产物）

在 1600×960 / d3d11 / 真 Chrome 下实测：

| 指标 | 实测值 | 结论 |
|---|---|---|
| 帧间隔 p50 / p95 | 11.5ms / 11.7ms | 87fps，**不卡** |
| `getBoundingClientRect` 占 CPU | **0.02%** | 5 条常驻 rAF 循环**不是**瓶颈，**不要合并** |
| `cL()` 场景 traverse | 0.027ms/次 | 微不足道，**不要**加脏标记改造 |
| CPU 热点 | `renderBufferDirect` 64%、`setupVertexAttributes` 23% | 全在 Three.js 渲染管线内部，是正常成本 |
| 阴影开关 | 64.5 → 64.9 fps | 阴影不是瓶颈 |

> **教训**：本轮最初假设「5 条 rAF 循环 + 每帧 traverse = 卡顿根因」，实测证明不成立。
> 任何对 2MB 压缩产物的性能改造，**先拿 profiler 数据**，否则是在拿风险换 0 收益。

### 11.2 真实修掉的问题

1. **`__YV_TRACE` 内存泄漏**（已删）：`Yv()` 每帧往 `window.__YV_TRACE` push 2–4 个字符串，
   数组只增不减。60fps 跑 1 小时 ≈ 65 万条。删除后 `__YV_TRACE` 已不存在于 bundle。
2. **数组材质崩溃**（已修）：`dx()` 里 `const a=o.material; a.userData._cached` —— 当 mesh 用
   **多材质数组**时 `o.material` 是数组，`a.userData` 抛 `TypeError: Cannot read properties
   of undefined (reading '_cached')`。这会让整条 `dx()` 帧渲染链中断。
   已改为 `Array.isArray(o.material) ? o.material : [o.material]` 逐个处理。
   **基线版本确实复现此崩溃，当前版本不再出现**（见 §11.4 对比报告）。

### 11.3 删除的死代码（9 函数 + 2 分支 + 1 实例）

全部经「全 bundle 出现次数 == 1（只有声明本身）」验证：

| 名字 | 位置 | 说明 |
|---|---|---|
| `G7` | ax() 附近 | 房间窗帘遮光系数计算，从未调用 |
| `OL` | 同上 | 房间日照小时数计算，从未调用 |
| `UL` | 同上 | 房间相邻关系查询，从未调用 |
| `__furnWallTex` | 家具材质区 | 墙面贴图 getter，从未调用 |
| `skyDim` / `skyFade` | bundle 末尾 | 被内联过渡取代的旧天空淡入淡出 |
| `__riSmooth` / `__syncCam3d` / `__riToFull` | bundle 末尾 | 被内联过渡取代的旧分屏相机动画 |

另有 2 处 `if(false){...}` 死分支（`ax()` 的 CONST-LIGHT 旧路径、画质 `apply()` 的 bloom 分支）
和 1 个孤立 `new Be;` 实例（`GL=new Be(...)` 后面的无用构造）。
> `if(false){A}else if(B){C}` 里的 `else` 是活代码 —— 只能删 `if` 那一支，不能整块删。

### 11.4 验证方式

```powershell
python scripts/dev/verify_template.py            # 语法 + 行尾符 + 死代码 + 泄漏 + 崩溃
python scripts/dev/check_scripts_syntax.py       # scripts/ 全量语法
node scripts/check.mjs assets/template.html <out> # 功能自检
python scripts/dev/compare_reports.py <基线report.json> <当前report.json>
```

基线（HEAD）与当前版对比结果：**房间/面积/开间进深/外围尺寸/问题清单 19 条完全一致**；
基线有的 `_cached` 崩溃当前**已消失**，无新增错误。
3D 截图差异 1.86% 属渲染非确定性 —— **同一版本跑两遍差异 1.834%**，即与本次改动无关；
2D 平面图截图差异 **0.000%**。

### 11.5 仓库清理

- 删除 `验收/`（验收站，用户明确要求）、`designer-autoqa/`（与 `scripts/` 完全重复；
  其中较新的 `record-transition.mjs` 已并入 `scripts/dev/`）、`.cursor/skills/`（41MB 陈旧副本，
  含 node_modules）、`_probe/`、`scripts/assets/`（已废弃 GLB 下载产物）
- 删除 11 个一次性 patch 脚本（`boost_ao/visual_boost/fix_overlay/fix_toolbar_bottom/
  patch_fphint/patch_fphint2/patch_light/check_banner/check_fphint/check_mat_light/list_toast`）——
  它们的修改早已落地在模板里，锚点 0 命中
- 60 个 `scripts/dev` 脚本的 `验收/xxx` 路径重映射到新落点（`assets/furnlib`、
  `scripts/dev/_previews|_logs|_refs`），避免删目录后这些脚本一跑就崩
- 新增维护工具：`patch_template.py`（安全改压缩产物：锚点唯一性校验 + node --check + 行尾符守卫）、
  `remove_fn.py`（删顶层函数）、`verify_template.py`、`check_scripts_syntax.py`、
  `audit_scripts.py`、`remap_accept_paths.py`、`compare_reports.py`、
  `profile_perf2.js` / `cpu_profile2.js` / `measure_shadow.js`

> **给后续接手的人**：`assets/template.html` 是压缩产物，**永远不要**用编辑器改。
> 用 `scripts/dev/patch_template.py --pairs-file <json>`（锚点必须唯一，否则工具拒绝写入）。
> 该工具用**二进制读写**并有行尾符守卫 —— 早期用 text 模式写回会把 15815 个 LF 变成 CRLF，
> 整个文件在 git 里被重写。

---

## 12. 2026-11-06 下午：WebGL 报错溯源 + 漫游相机死锁 + 帧率节流器

> 本节只列**新修的、且必须记住的**三件事。§11 之前的全部内容依然有效。

### 12.1 `THREE.WebGLState: NaN` / SecurityError 的真凶：`file://` 协议，不是产品 bug

- Three.js 用 `new Image()` 加载 `furnlib/tex/*.jpg`。用 `file://` 打开时 Chromium 给文档一个
  opaque `null` origin，本地图片变成**跨源污染数据**，`texSubImage2D` 抛
  `SecurityError: The image element contains cross-origin data`，
  Three.js 在 `WebGLState` 里 catch 后 `console.error("THREE.WebGLState:", se)`。
- **走 HTTP 就完全干净**：170+ 张 PBR 贴图零报错、零 NaN。
- 处置：新增 `scripts/lib_serve.mjs` —— 进程内起一个 `http.Server`（`port: 0` 随机端口，
  `Cache-Control: no-store`），所有测试脚本改用它，**不再用 `pathToFileURL()`**。
- **教训**：以后任何自动化测试都**不要用 `file://`**；看到 `THREE.WebGLState` 报错先怀疑协议。

### 12.2 漫游相机的进入 / 退出去死锁（真 bug，已修）

- `Vp()`（进入漫游）在 `re.active || Bi` 时**静默 return**，请求被吞掉。
- `Ns()`（退出漫游）用 `__walkSwitch` 把 `re.active=false` 推迟到 `setTimeout` 140ms；
  GPU 忙时定时器被延迟，快速「退出→再进」会被永久吞掉。
- 已修三处：
  1. `Vp()`：改成 `if(re.active)return; if(Bi){__fpPending={p:n};return;}` —— 动画期间请求入队。
  2. `wi()` 的超时兜底与 `JL()` 动画结束处：**主动 flush `__fpPending`**。
  3. `Ns()`：`re.active=!1` 改为**同步**执行（不再等 140ms）。
- 工具栏「fp」按钮：动画期间也允许点击进入（原来被 `Xc()` 拦掉）。

### 12.3 自适应帧率节流器被「单帧巨耗时」毒化（真性能 bug，已修）

- `hx()` 里的 `hiWork` 滑动平均把**一次性事件**（切 3D / 进漫游时的 shader 编译，单帧阻塞
  3~7 秒）也算成帧率样本 → `hiT` 被抬到几百 ms → 之后每秒只渲染 1~2 帧，
  而 `hiWork` 又只能靠这 1~2 帧/秒慢慢衰减 → **画面看起来像卡死十几秒**。
  这正是「进漫游后点位标记要好几秒才消失」的直接原因。
- 已修（锚点：`【性能修复 v20】`）：
  1. 超过 50ms 的帧耗时视为一次性事件，**只记不采**（`Math.min(w,50)`）。
  2. `hiT` 上限 **100ms**（最差 10 FPS），绝不低于这个下限频率。
- 实测：修复前进漫游后 rAF 间隔最大 4020ms；修复后稳定 12~19ms（60fps）。

### 12.4 点位标记（HUD）按 T 立即清空

- 原实现只在**渲染循环**里清 DOM（`yB()` 开头）。被上面的节流器拖慢时，按 T 后要等好几秒。
- 已修：抽出 `__hudClear()`，`KeyT` 处理器在隐藏时**同步**调用（不依赖下一帧）。
- 附带：点位标记按钮加 `dataset.k`（= `"e<elecId>"` / `"f<furnId>"`），便于自动化按 id 定位。

—— 交接完毕。遇到任何不确定，先读 memory.md，再 Grep 代码验证，最后才动手。
