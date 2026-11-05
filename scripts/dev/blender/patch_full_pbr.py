"""把剩余的纯色建筑构件全部接到 ambientCG 真实扫描 PBR。

【浏览器实测基线】127.0.0.1:8899/template.html?debug
  1494 个材质槽里 855 个是纯色（map/normalMap/roughnessMap 全空）：
    FLAT wallface  277   ← 墙体盒的端面/底面（用 e = L("#f3f1ec") 纯色）
    FLAT cap        78   ← 墙顶（承重/隔墙/新砌 状态色，纯色）
    FLAT -         471   ← 窗框铝材 / 开关面板 / 插座孔 / 结构柱 / 下照灯 …
    TEX wallface   114   ← 房间两侧大面（j7 走 __WALL_PBR，已经是扫描 PBR）
    TEX -          283   ← 门 / 踢脚 / 吊顶（已是扫描 PBR）
  也就是说：看得见的大面墙、地、顶、门已经是真贴图，
  剩下的是【端面 / 顶面 / 五金 / 面板】还在纯色。

【做法】
  1) 扩充模块级 __ARCH_MAT：新增 墙漆 / 混凝土 / 钢 / 黑铁 / 陶瓷 / 开关面板 等
  2) sx()：e(墙基色) i(铝窗框) s(木门扇) o(入户门) t(墙顶状态色) 改用 __ARCH_MAT
  3) fx()：结构柱 / 管井 / 地漏 / 化粪池 / 开关面板 / 插座孔 / 下照灯 改用 __ARCH_MAT
  4) sx() 门窗五金：窗执手 / 淋浴杆 / 车库门 / 折叠门扇 改用 __ARCH_MAT
  5) L7()：主题系统原本会把墙面的 map 置空（r.map=null）→ 改成保留扫描贴图只调色，
     免得用户一换风格，墙又退回纯色
  6) __applyPBR()：legacy __PBR_ROLES 路径补上 aoMap（AO 已补齐到 39/39 套）

【安全】所有锚点必须【唯一】命中，否则脚本拒绝写入。
用法：python patch_full_pbr.py [--check|--apply]
"""
import os
import shutil
import sys

ROOT = r"D:\house planner\house-plan-designer-main"
TP = os.path.join(ROOT, "assets", "template.html")
BAK = TP + ".bak_full_pbr"

OPS = []


def op(desc, old, new):
    OPS.append((desc, old, new))


# ---------------------------------------------------------------------------
# 1) 扩充 __ARCH_MAT
# ---------------------------------------------------------------------------
op(
    "扩充 __ARCH_MAT（墙漆/混凝土/钢/黑铁/陶瓷/面板/灯罩）",
    '  ceilTrim:__archMat("ceiling_white",{rough:.92,color:"#f4f2ee",normalScale:.35,rep:2}),\n};',
    '  ceilTrim:__archMat("ceiling_white",{rough:.92,color:"#f4f2ee",normalScale:.35,rep:2}),\n'
    '  /* --- 大面积墙面：墙面盒的端面/底面 + 主题降级兜底 --- */\n'
    '  wallPlaster:__archMat("wall_plaster_white",{rough:.9,color:"#f3f1ec",normalScale:.8,rep:3}),\n'
    '  /* --- 墙顶（承重/隔墙/新砌 状态色，保留语义色但带真实法线）--- */\n'
    '  capBearing:__archMat("wall_concrete",{rough:.86,color:"#3a3f47",normalScale:.6,rep:2}),\n'
    '  capPart:__archMat("wall_concrete",{rough:.86,color:"#9aa3ad",normalScale:.6,rep:2}),\n'
    '  capNew:__archMat("wall_concrete",{rough:.86,color:"#e8590c",normalScale:.6,rep:2}),\n'
    '  /* --- 金属件 --- */\n'
    '  metalSteel:__archMat("role_metal_steel",{rough:.42,metal:.9,color:"#9aa2ab",normalScale:.45,rep:1.8}),\n'
    '  metalBlack:__archMat("role_metal_black",{rough:.4,metal:.82,color:"#5b626c",normalScale:.42,rep:1.8}),\n'
    '  /* --- 结构（柱/管井/地台/楼板）--- */\n'
    '  concrete:__archMat("wall_concrete",{rough:.9,color:"#f1efea",normalScale:.7,rep:2.4}),\n'
    '  /* --- 面板 / 陶瓷小件 --- */\n'
    '  switchPlate:__archMat("door_paint",{rough:.42,color:"#fbfbfa",normalScale:.3,rep:3}),\n'
    '  ceramic:__archMat("role_ceramic_white",{rough:.2,metal:0,color:"#f2f2f0",normalScale:.3,rep:3}),\n'
    '  socketDark:__archMat("role_metal_black",{rough:.52,metal:.25,color:"#3a3d42",normalScale:.35,rep:3}),\n'
    '  /* --- 灯具本体 --- */\n'
    '  lampBody:__archMat("ceiling_white",{rough:.35,metal:0,color:"#e9e7e2",normalScale:.25,rep:3}),\n'
    '};',
)

# ---------------------------------------------------------------------------
# 2) sx()：墙体 / 门窗 五金 的基材改用 __ARCH_MAT
# ---------------------------------------------------------------------------
op(
    "sx(): 墙基色 e / 铝窗框 i / 木门扇 s / 入户门 o / 墙顶状态色 t 改扫描 PBR",
    'const n=E.plan.height,e=L("#f3f1ec",.92),t={bear:L("#3a3f47",.8),part:L("#9aa3ad",.8),new:L("#e8590c",.8)},i=L("#5b626c",.5,.3),s=L("#c9a57c",.6),o=L("#474c55",.5),a=[];',
    'const n=E.plan.height,e=__ARCH_MAT.wallPlaster,t={bear:__ARCH_MAT.capBearing,part:__ARCH_MAT.capPart,new:__ARCH_MAT.capNew},i=__ARCH_MAT.metalSteel,s=__ARCH_MAT.doorWood,o=__ARCH_MAT.doorMetal,a=[];',
)

# 窗执手
op(
    "窗执手改扫描钢",
    'const be=new Me(new ot(.015,.12,.03),L("#c7ccd2",.3,.8));',
    'const be=new Me(new ot(.015,.12,.03),__ARCH_MAT.metalSteel);',
)

# 淋浴房 杆 / 软管
op(
    "淋浴房五金改扫描钢",
    'const __rs=new Me(new Bn(.032,.032,.01,20),L("#c8ced4",.3,.7));',
    'const __rs=new Me(new Bn(.032,.032,.01,20),__ARCH_MAT.metalSteel);',
)
op(
    "淋浴房软管改扫描钢",
    'const ie=new Me(new Go(.025,10,8),L("#b9bec6",.3,.8));',
    'const ie=new Me(new Go(.025,10,8),__ARCH_MAT.metalSteel);',
)

# 推拉门边框
op(
    "推拉门边框改扫描钢",
    'const W=new ht,B=new Me(new ot(O,G-.01,.04),s);',
    'const W=new ht,B=new Me(new ot(O,G-.01,.04),__ARCH_MAT.metalSteel);',
)
op(
    "推拉门把手改扫描钢",
    'const K=new Me(new ot(.02,.18,.05),L("#9aa1a8",.3,.8));',
    'const K=new Me(new ot(.02,.18,.05),__ARCH_MAT.metalSteel);',
)

# 折叠门扇
op(
    "折叠门扇改扫描木纹",
    'const j=new Me(new ot(K,G-.03,.025),Q%2?s:L("#d9bf9c",.6));',
    'const j=new Me(new ot(K,G-.03,.025),Q%2?s:__ARCH_MAT.doorWood);',
)

# 车库门
op(
    "车库门扇板改扫描金属",
    'B=G/W,K=L("#d9dcdf",.45,.35),Q=L("#b9bec4",.5,.3);',
    'B=G/W,K=__ARCH_MAT.metalSteel,Q=__ARCH_MAT.metalSteel;',
)
op(
    "车库门导轨罩改扫描金属",
    'te=new Me(new ot(O+.1,.3,.3),L("#cfd3d7",.5,.3));',
    'te=new Me(new ot(O+.1,.3,.3),__ARCH_MAT.metalSteel);',
)
op(
    "窗下装饰板改扫描顶面白",
    'B=new Me(new ot(O+.1,.02,u/2+.03),L("#ece8e1",.3));',
    'B=new Me(new ot(O+.1,.02,u/2+.03),__ARCH_MAT.ceilTrim);',
)
op(
    "飘窗侧板改扫描顶面白",
    'Q=new Me(new ot(O+.12,Y,B),L("#e8e4dc",.5));',
    'Q=new Me(new ot(O+.12,Y,B),__ARCH_MAT.ceilTrim);',
)

# ---------------------------------------------------------------------------
# 3) fx()：结构件 / 电气面板 / 灯具
# ---------------------------------------------------------------------------
op(
    "结构柱改扫描混凝土",
    's.kind==="column"?(N(o,a,n,r,0,0,0,L("#f1efea",.9)),',
    's.kind==="column"?(N(o,a,n,r,0,0,0,__ARCH_MAT.concrete),',
)
op(
    "管井/烟道改扫描混凝土",
    's.kind==="shaft"||s.kind==="flue"?(N(o,a,n,r,0,0,0,L("#ebe8e2",.9)),',
    's.kind==="shaft"||s.kind==="flue"?(N(o,a,n,r,0,0,0,__ARCH_MAT.concrete),',
)
op(
    "地漏改扫描金属",
    's.kind==="drain"?ue(o,a/2,a/2,.006,0,0,0,L("#aeb6bd",.3,.8),20)',
    's.kind==="drain"?ue(o,a/2,a/2,.006,0,0,0,__ARCH_MAT.metalSteel,20)',
)
op(
    "化粪池改扫描黑铁",
    'ue(o,a/2,a/2,.03,0,0,0,L("#6b4a32",.6),20)',
    'ue(o,a/2,a/2,.03,0,0,0,__ARCH_MAT.metalBlack,20)',
)
op(
    "开关/插座面板改扫描漆面",
    'if(N(a,p?.4:.086,p?.3:.086,.012,0,l-(p?.15:.043),r,L("#fbfbfa",.4),!1),g)',
    'if(N(a,p?.4:.086,p?.3:.086,.012,0,l-(p?.15:.043),r,__ARCH_MAT.switchPlate,!1),g)',
)
op(
    "调光面板按钮改扫描陶瓷",
    'const b=ue(a,.02,.02,.012,0,0,0,L("#d9d9d6",.3,.4));',
    'const b=ue(a,.02,.02,.012,0,0,0,__ARCH_MAT.ceramic);',
)
op(
    "开关按键改扫描陶瓷",
    'N(a,.066/m-.003,.062,.006,(b-(m-1)/2)*(.066/m),l-.033,r+.009,L("#f4f4f2",.35),!1);',
    'N(a,.066/m-.003,.062,.006,(b-(m-1)/2)*(.066/m),l-.033,r+.009,__ARCH_MAT.ceramic,!1);',
)
op(
    "插座孔改扫描黑铁",
    'const m=L("#3a3d42",.8);',
    'const m=__ARCH_MAT.socketDark;',
)
op(
    "空调孔盖改扫描陶瓷",
    'const p=new Me(new js(.045,.012,8,24),L("#f1f1ef",.5));',
    'const p=new Me(new js(.045,.012,8,24),__ARCH_MAT.ceramic);',
)
op(
    "下照灯/筒灯灯体改扫描材质",
    'i=()=>new Zt({color:"#e9e7e2",emissive:"#ffe9c4",emissiveIntensity:.02,roughness:.5});',
    'i=()=>{const __lm=__ARCH_MAT.lampBody.clone();__lm.emissive=new Be("#ffe9c4");__lm.emissiveIntensity=.02;return __lm};',
)

# ---------------------------------------------------------------------------
# 4) ux()：楼板 slab 接扫描混凝土
# ---------------------------------------------------------------------------
op(
    "楼板 slab 接扫描混凝土",
    't),L("#8f969f",.9));i.receiveShadow=!0,i.castShadow=$e(),i.userData.role="slab",an.add(i);',
    't),__ARCH_MAT.concrete);i.receiveShadow=!0,i.castShadow=$e(),i.userData.role="slab",an.add(i);',
)

# ---------------------------------------------------------------------------
# 5) L7()：主题系统不要把墙面的扫描贴图置空
# ---------------------------------------------------------------------------
op(
    "L7(): 换风格时保留墙面扫描贴图（只调色，不再 r.map=null）",
    'case"wallface":t.mat==="wallTile"?c(E9(ku("wallTile"),"wt",i.tile)):t.mat==="woodPanel"?c(E9(ku("woodPanel"),"wp",i.wood)):(r.map=null,r.color.set(i.wall));break;',
    'case"wallface":t.mat==="wallTile"?c(E9(ku("wallTile"),"wt",i.tile)):t.mat==="woodPanel"?c(E9(ku("woodPanel"),"wp",i.wood)):(r.color.set(i.wall),r.map&&(r.map.needsUpdate=!0));break;',
)

# ---------------------------------------------------------------------------
# 6) __applyPBR()：legacy 路径补 AO
# ---------------------------------------------------------------------------
op(
    "__applyPBR(): legacy __PBR_ROLES 路径补 aoMap",
    '      m.roughnessMap=__pbrTex(w+"_rough",!1,rep);\n      if(m.normalScale)m.normalScale.set(.7,.7);',
    '      m.roughnessMap=__pbrTex(w+"_rough",!1,rep);\n      m.aoMap=__pbrTex(w+"_ao",!1,rep);\n      if(m.normalScale)m.normalScale.set(.7,.7);',
)
op(
    "__applyPBR(): legacy 布料路径补 aoMap",
    '      m.normalMap=__pbrTex("rough_linen_nor",!1,rep);\n      m.roughnessMap=__pbrTex("rough_linen_rough",!1,rep);',
    '      m.normalMap=__pbrTex("rough_linen_nor",!1,rep);\n      m.roughnessMap=__pbrTex("rough_linen_rough",!1,rep);\n      m.aoMap=__pbrTex("rough_linen_ao",!1,rep);',
)


def main():
    mode = "--apply" if "--apply" in sys.argv else "--check"
    s = open(TP, encoding="utf-8").read()
    print("模板: %s  (%.2f MB)" % (TP, len(s) / 1024 / 1024))
    print("模式: %s\n" % mode)

    ok = True
    for desc, old, new in OPS:
        cnt = s.count(old)
        if cnt != 1:
            print("  [锚点命中 %d 次] %s" % (cnt, desc))
            ok = False
        else:
            print("  [唯一] %s" % desc)
    if not ok:
        print("\n锚点校验失败，未做任何修改。")
        sys.exit(1)

    if mode == "--check":
        print("\n全部 %d 个锚点唯一。" % len(OPS))
        return

    for _desc, old, new in OPS:
        s = s.replace(old, new, 1)

    if os.path.exists(BAK):
        os.remove(BAK)
    shutil.copy2(TP, BAK)
    open(TP, "w", encoding="utf-8").write(s)
    print("\n备份 -> %s" % BAK)
    print("已写入 %s  (%.2f MB)" % (TP, len(s) / 1024 / 1024))
    print("下一步：python check_tpl_syntax.py")


if __name__ == "__main__":
    main()
