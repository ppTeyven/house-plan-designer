"""修补 assets/template.html 的四处 PBR / 家具缺口。

【调查结论（本脚本要修的四个真因，全部有运行时证据）】
  ① 家具从 3D 场景里整体消失（最严重）
     __furnInvalidate() 在 251 个模型各自加载完成时被调用，
     每次都 An.remove(o.g) 把【已建好的家具实例】从场景摘掉并 Qs.clear()，
     但【没有重建】—— 251 个模型到齐后，3D 视图里一件家具都没有。
     证据：浏览器 CDP 探测 furnG.children.length === 0，而 plan.furniture.length === 50；
           手动调用 commit() 后 furnG.children.length 恢复为 50。
     修法：加载完毕后【显式重建一次】家具（走 Is()，与 commit 同一条路径）。

  ② 家具 GLB 的 14 种 U_* 材质角色没有对应 PBR 贴图
     kv() 把 U_<role> 交给 __furnMat(role)，
     而 __furnMat 只认 __FURN_ROLE 里的【程序化角色名】（wood / panel / fabric / …），
     对不上 GLB 的角色名（wood_oak / fabric_oat / metal_black / …），
     14 种角色全部落到 fallback → 纯色、无贴图。
     证据：浏览器探测显示 F_fabric_oat / F_wood_oak / F_metal_black … 全部 NO-MAP。
     修法：新增 __GLB_PBR_ROLE 表（role → furnlib/tex 里的纹理集名）。

  ③ 地面默认分支仍走 canvas 假贴图
     ux() 里只有"房间有 tile 标签"时才用 __surfMat，
     没标签的房间走 else 分支 → jL(u) 程序化 canvas 贴图。
     而 ps(c) 默认返回 "oak"（即 jo.oak，【已配 pbr:"floor_wood_oak"】），
     所以绝大多数房间其实都该有 PBR，却没接上。
     修法：else 分支也查 jo[u].pbr。

  ④ GLB 角色名与 __FURN_ROLE 的程序化角色同名冲突时会互相覆盖
     __applyPBR 会把 wood / wooddk / panel / stone 这些角色强行换成固定贴图，
     与新增的 GLB 角色分支冲突。
     修法：__applyPBR 遇到 GLB 角色直接返回。

【修改纪律（handbook 附录 A）】
  1. 只做【锚点定位 + 精确字符串替换】，不重排不格式化。
  2. 每个锚点必须唯一；不唯一就扩大上下文。
  3. 改完必须 node --check 语法校验 + 三层对账（磁盘→HTTP→内存态）。

用法：
  python patch_pbr_furniture.py --check    # 只检查锚点
  python patch_pbr_furniture.py --apply    # 执行替换
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TP = os.path.join(ROOT, "assets", "template.html")

# ---------------------------------------------------------------------
# 注入代码：GLB 材质角色 → 真实扫描 PBR 纹理
#   纹理集名对应 assets/furnlib/tex/<name>_{col,nor,rough,ao}.jpg
#   由 export_pbr_textures.py 从 ambientCG 2K 扫描材质导出。
#   选型依据是【实测平均色 + ambientCG 标签】，不是按名字猜的：
#     role_wood_oak     (179,157,132) 浅白橡
#     role_wood_walnut  ( 55, 30, 14) 深胡桃
#     role_fabric_oat   (197,191,182) 燕麦米
#     role_fabric_cream (195,192,188) 米白
#     role_metal_brass  (254,226,156) 黄铜
#     role_leaf         ( 38, 48, 14) 叶绿
# ---------------------------------------------------------------------
INJECT_ROLES = r'''
/* ===== GLB 家具材质角色 → 真实扫描 PBR =====
 * 251 个 GLB 的材质名是 U_<role>（geo_gen.py 里 mat="U_wood_oak" 等），
 * kv() 会把它们交给 __furnMat(role)。下面这张表把角色名对上
 * assets/furnlib/tex/ 里由 ambientCG 2K 扫描导出的真实贴图。
 */
const __GLB_PBR_ROLE={
  wood_oak:"role_wood_oak",wood_walnut:"role_wood_walnut",
  fabric_oat:"role_fabric_oat",fabric_oat_d:"role_fabric_oat_dark",
  fabric_cream:"role_fabric_cream",fabric_grey:"role_fabric_grey",
  metal_black:"role_metal_black",metal_steel:"role_metal_steel",
  metal_brass:"role_metal_brass",ceramic_white:"role_ceramic_white",
  stone_light:"role_stone_light",stone_dark:"role_stone_dark",
  leaf:"role_leaf",leaf_dark:"role_leaf",
};
/* 角色 → 物理参数（roughness / metalness / 法线强度 / 平铺 / 色调） */
const __GLB_PBR_OPT={
  wood_oak:{rough:.6,rep:1.6,ns:.75,color:"#e8d8c2"},
  wood_walnut:{rough:.58,rep:1.6,ns:.75,color:"#c9a888"},
  fabric_oat:{rough:.95,rep:2.4,ns:1.05,color:"#f0e6d6"},
  fabric_oat_d:{rough:.95,rep:2.4,ns:1.05,color:"#a89478"},
  fabric_cream:{rough:.96,rep:2.4,ns:1.05,color:"#f4efe6"},
  fabric_grey:{rough:.96,rep:2.4,ns:1.05,color:"#b9b6b0"},
  metal_black:{rough:.55,metal:.75,rep:2.2,ns:.6,color:"#d2d2d2"},
  metal_steel:{rough:.42,metal:.9,rep:2.2,ns:.55,color:"#e8eaec"},
  metal_brass:{rough:.34,metal:.95,rep:2.2,ns:.5,color:"#f0d9a8"},
  ceramic_white:{rough:.18,metal:0,rep:2.4,ns:.35,color:"#ffffff"},
  stone_light:{rough:.28,metal:0,rep:1.8,ns:.5,color:"#f2efe8"},
  stone_dark:{rough:.3,metal:0,rep:1.8,ns:.5,color:"#8e8e8e"},
  leaf:{rough:.78,metal:0,rep:3,ns:.9,color:"#9fc06a"},
  leaf_dark:{rough:.8,metal:0,rep:3,ns:.9,color:"#7ba24e"},
};
'''

# ---------------------------------------------------------------------
# 锚点表：(说明, 唯一锚点字符串, 替换字符串)
# ---------------------------------------------------------------------
PATCHES = []

# ===== ① 注入 GLB 角色表 =====
# 插在 __PBR_ROLES 之后 —— 必须早于 __applyPBR（1952009）与 __furnMat（1955424），
# 这样两者在模块求值完成时都已初始化（const 有 TDZ，位置错了会 ReferenceError）。
PATCHES.append((
    "注入 GLB 材质角色 PBR 表",
    'const __PBR_ROLES={wood:"white_oak_veneer",wooddk:"american_walnut_veneer",panel:"white_oak_veneer",stone:"marble_01"};',
    'const __PBR_ROLES={wood:"white_oak_veneer",wooddk:"american_walnut_veneer",panel:"white_oak_veneer",stone:"marble_01"};\n'
    + INJECT_ROLES,
))

# ===== ② __pbrTex 加载失败时兜底 =====
# 原来没有 onerror：某通道 404 时 texture.image 为空，
# 三方会告警甚至整段 shader 出问题。__surfTex 已经有这个兜底，这里对齐。
PATCHES.append((
    "__pbrTex 加载失败兜底（避免缺通道时整张材质失效）",
    '  const img=new Image();img.onload=()=>{t.image=img;t.needsUpdate=!0;};\n'
    '  img.src="furnlib/tex/"+file+".jpg";',
    '  const img=new Image();img.onload=()=>{t.image=img;t.needsUpdate=!0;};\n'
    '  img.onerror=()=>{t.image=null;};\n'
    '  img.src="furnlib/tex/"+file+".jpg";',
))

# ===== ③ __furnMat 支持 GLB 角色 =====
# 原实现里 GLB 角色两个条件都不满足 → 纯色无贴图：
#   if(cfg.tex && __FURN_ROLE[role] && !__PBR_ROLES[role]) params.map = __ft(cfg.tex)
#   __FURN_ROLE["wood_oak"] 是 undefined → 不给贴图。
# 新实现：命中 __GLB_PBR_ROLE 就接真实扫描 PBR（albedo + normal + roughness + AO）。
PATCHES.append((
    "家具材质支持 GLB U_* 角色的真实 PBR",
    'function __furnMat(role,colHex){\n'
    '  const key=role+"|"+(colHex||"#bbbbbb");\n'
    '  if(__furnMatCache.has(key))return __furnMatCache.get(key);\n'
    '  const cfg=__FURN_ROLE[role]||{tint:.5,rough:.7,tex:role};\n'
    '  let base;\n'
    '  try{base=new Be(colHex||"#cccccc")}catch(e){base=new Be("#cccccc")}\n'
    '  const params={roughness:cfg.rough,metalness:cfg.metal||0};\n'
    '  if(cfg.tex&&__FURN_ROLE[role]&&!__PBR_ROLES[role])params.map=__ft(cfg.tex);\n'
    '  const m=new Zt(params);\n'
    '  if(cfg.color)m.color.set(cfg.color);\n'
    '  else{m.color.set("#ffffff");if(cfg.tint>0)m.color.lerp(base,cfg.tint)}\n'
    '  if(cfg.glass){m.transparent=!0;m.opacity=.32;m.depthWrite=!1;m.side=Qt}\n'
    '  if(cfg.emissive){m.emissive=new Be(colHex||"#fff3dd");m.emissiveIntensity=cfg.emissive;m.emissive.multiplyScalar(.6).add(new Be(.25,.22,.18))}\n'
    '  m.name="F_"+role;__applyPBR(m,role);\n'
    '  __furnMatCache.set(key,m);return m;\n'
    '}',
    'function __furnMat(role,colHex){\n'
    '  const key=role+"|"+(colHex||"#bbbbbb");\n'
    '  if(__furnMatCache.has(key))return __furnMatCache.get(key);\n'
    '  const cfg=__FURN_ROLE[role]||{tint:.5,rough:.7,tex:role};\n'
    '  let base;\n'
    '  try{base=new Be(colHex||"#cccccc")}catch(e){base=new Be("#cccccc")}\n'
    '  const params={roughness:cfg.rough,metalness:cfg.metal||0};\n'
    '  if(cfg.tex&&__FURN_ROLE[role]&&!__PBR_ROLES[role])params.map=__ft(cfg.tex);\n'
    '  const m=new Zt(params);\n'
    '  if(cfg.color)m.color.set(cfg.color);\n'
    '  else{m.color.set("#ffffff");if(cfg.tint>0)m.color.lerp(base,cfg.tint)}\n'
    '  if(cfg.glass){m.transparent=!0;m.opacity=.32;m.depthWrite=!1;m.side=Qt}\n'
    '  if(cfg.emissive){m.emissive=new Be(colHex||"#fff3dd");m.emissiveIntensity=cfg.emissive;m.emissive.multiplyScalar(.6).add(new Be(.25,.22,.18))}\n'
    '  m.name="F_"+role;__applyPBR(m,role);\n'
    '  /* ---- GLB 角色（U_wood_oak 等）：接 ambientCG 真实扫描 PBR ---- */\n'
    '  try{\n'
    '    const __gx=__GLB_PBR_ROLE[role];\n'
    '    if(__gx){\n'
    '      const __go=__GLB_PBR_OPT[role]||{};\n'
    '      const __rep=__go.rep||1.8;\n'
    '      m.map=__pbrTex(__gx+"_col",!0,__rep);\n'
    '      m.normalMap=__pbrTex(__gx+"_nor",!1,__rep);\n'
    '      m.roughnessMap=__pbrTex(__gx+"_rough",!1,__rep);\n'
    '      m.aoMap=__pbrTex(__gx+"_ao",!1,__rep);\n'
    '      if(m.normalScale)m.normalScale.set(__go.ns==null?.75:__go.ns,__go.ns==null?.75:__go.ns);\n'
    '      if(__go.rough!=null)m.roughness=__go.rough;\n'
    '      if(__go.metal!=null)m.metalness=__go.metal;\n'
    '      if(__go.color)m.color.set(__go.color);\n'
    '      m.envMapIntensity=__go.metal!=null&&__go.metal>.5?1.05:.55;\n'
    '      m.needsUpdate=!0;\n'
    '    }\n'
    '  }catch(e){}\n'
    '  __furnMatCache.set(key,m);return m;\n'
    '}',
))

# ===== ④ __applyPBR 跳过 GLB 角色 =====
PATCHES.append((
    "__applyPBR 跳过 GLB 角色（避免覆盖新贴图）",
    'function __applyPBR(m,role){\n'
    '  try{\n'
    '    const w=__PBR_ROLES[role];',
    'function __applyPBR(m,role){\n'
    '  try{\n'
    '    if(__GLB_PBR_ROLE[role])return;\n'
    '    const w=__PBR_ROLES[role];',
))

# ===== ⑤ 玻璃角色（U_glass_clear）走透明玻璃参数 =====
# U_glass_clear 在 23 个模型里出现（如玻璃隔断 / 玻璃门），
# 原来不在 __FURN_ROLE 里 → 落到 fallback → 不透明灰白板。
PATCHES.append((
    "U_glass_clear 走透明玻璃参数",
    'mirror:{tint:0,rough:.05,metal:1,color:"#cfd4da"}\n'
    '};',
    'mirror:{tint:0,rough:.05,metal:1,color:"#cfd4da"},\n'
    'glass_clear:{tint:.18,rough:.06,metal:.05,glass:!0}\n'
    '};',
))

# ===== ⑥ 地面默认分支也用 PBR =====
PATCHES.append((
    "地面无 tile 标签时也接真实扫描 PBR",
    'else{const m=new Me(p,new Zt({map:jL(u),roughness:((l=jo[u])==null?void 0:l.rough)??.7}));'
    'm.receiveShadow=!0,m.userData.role="floor",m.userData.mat=u,an.add(m)}',
    'else{const __jf=(l=jo[u])==null?void 0:l.pbr;'
    'const __jm=__jf?__surfMat(__jf,{rep:1,rough:(l=jo[u])==null?.7:(l.rough??.7),normalScale:.85,env:.5}):null;'
    'const m=new Me(p,__jm||new Zt({map:jL(u),roughness:((l=jo[u])==null?void 0:l.rough)??.7}));'
    'm.receiveShadow=!0,m.userData.role="floor",m.userData.mat=u;'
    'if(__jm)m.userData.noTheme=!0;'
    'an.add(m)}',
))

# ===== ⑦ 环氧地坪也接 PBR =====
PATCHES.append((
    "环氧地坪接真实扫描 PBR",
    'epoxy:{name:"环氧地坪",tile:2400,rough:.35,',
    'epoxy:{name:"环氧地坪",tile:2400,rough:.35,pbr:"floor_microcement",',
))

# ===== ⑧ 加载完毕后重建家具（修 3D 里家具消失）=====
# __furnInvalidate 只负责"清缓存 + 让下次重建能用上新模型"；
# 真正的重建必须显式触发 —— 否则家具被摘掉后就再也回不来。
PATCHES.append((
    "__furnInvalidate 清缓存并标脏（不再直接 Je）",
    'function __furnInvalidate(){\n'
    '  try{\n'
    '    Qs.forEach(o=>{try{An.remove(o.g);o.g.traverse(c=>{const u=c.geometry;u&&!u.userData.shared&&u.dispose()})}catch(e){}});\n'
    '    Qs.clear();Je();\n'
    '  }catch(e){}\n'
    '}',
    'function __furnInvalidate(){\n'
    '  try{\n'
    '    Qs.forEach(o=>{try{An.remove(o.g);o.g.traverse(c=>{const u=c.geometry;u&&!u.userData.shared&&u.dispose()})}catch(e){}});\n'
    '    Qs.clear();\n'
    '    /* 清掉旧材质缓存：重建时会按新的 __GLB_PBR_ROLE 重新造带 PBR 的材质 */\n'
    '    try{__furnMatCache.clear();}catch(e){}\n'
    '    try{Je();}catch(e){}\n'
    '  }catch(e){}\n'
    '}\n'
    '/* 【关键修复】家具重建入口。\n'
    '   原实现：__furnInvalidate() 把家具从场景摘掉后【从不重建】→\n'
    '           251 个模型加载完，3D 视图里一件家具都没有（furnG.children.length === 0）。\n'
    '   现在：加载完毕后显式调用 Is() 重建，走与 commit 事件完全相同的路径。 */\n'
    'function __furnRebuild(){\n'
    '  try{\n'
    '    if(typeof Is==="function"){Is();return;}\n'
    '  }catch(e){}\n'
    '  try{Je();}catch(e){}\n'
    '}',
))

# ===== ⑨ 加载循环结束后重建一次 =====
PATCHES.append((
    "251 个模型加载完毕后重建家具",
    '    await Promise.all(tasks);\n'
    '  }catch(e){}\n'
    '})();',
    '    await Promise.all(tasks);\n'
    '    /* 全部模型到齐 → 用 GLB 模型 + 真实 PBR 重建家具 */\n'
    '    __furnRebuild();\n'
    '  }catch(e){}\n'
    '})();',
))


def main():
    mode = "--apply" if "--apply" in sys.argv else "--check"
    src = open(TP, encoding="utf-8").read()
    orig = src

    print("模板: %s  (%.2f MB)" % (TP, len(src) / 1048576))
    print("模式: %s" % mode)
    print()

    ok = True
    for title, anchor, repl in PATCHES:
        n = src.count(anchor)
        if n != 1:
            print("  [锚点不唯一 %d 次] %s" % (n, title))
            ok = False
            continue
        if anchor == repl:
            print("  [已应用] %s" % title)
            continue
        if mode == "--apply":
            src = src.replace(anchor, repl, 1)
            print("  [已替换] %s" % title)
        else:
            print("  [可替换] %s" % title)

    if not ok:
        print("\n有锚点不唯一 —— 未执行替换（避免误伤）。")
        return 1

    if mode == "--apply":
        if src == orig:
            print("\n无变化。")
            return 0
        bak = TP + ".bak_pbr_furn"
        if not os.path.exists(bak):
            with open(bak, "w", encoding="utf-8") as f:
                f.write(orig)
            print("\n备份 -> %s" % bak)
        with open(TP, "w", encoding="utf-8") as f:
            f.write(src)
        print("已写入 %s  (%.2f MB)" % (TP, len(src) / 1048576))
        print("\n下一步：node --check 语法校验 + 起服浏览器实测")
    return 0


if __name__ == "__main__":
    sys.exit(main())
