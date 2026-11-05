"""第二轮 PBR 补齐：可见纯色收尾 + 墙面物理尺度 UV。

【第一轮实测结果】127.0.0.1:8899/template.html?debug
  1494 材质槽 → 纯色 855 → 121（8.1%）
  剩 121 槽的构成：
    bcd8ea 玻璃 27 + fcfbfa/fdfdfd 家具玻璃 10  ← 玻璃，本来就无贴图（正确）
    cove ffe1b3 灯槽发光条 26                        ← 发光灯带（正确）
    roofShadow / ground / 天空球 / city              ← 背景（正确）
    1c7ed6 / e03131 / d9480f 冷热水燃气标记 21       ← 语义色（正确）
    ffffff 面板底板 + LED 指示灯 22                  ← 不可见底板 / 指示灯（正确）
    e8e4dc 门套下压条 12                            ← ★ 可见，要改
    #222 化粪池内胆 2 / #8a6a4d 烟道压顶 1           ← ★ 可见，要改
    #3a3f47 / #5c7080 柱与管井压边 3                 ← ★ 可见，要改

【墙面 UV 的问题】
  墙是 BoxGeometry，UV 默认 0..1 → 一张 2048 贴图被拉到 6.8m 宽的整面墙上，
  纹理被拉扁、失去"精细"感。
  这里按【毫米物理尺寸】重算每个面的 UV：1 张贴图 = 2.4m（与地面铺装同一套物理尺度逻辑）。

用法：python patch_full_pbr2.py [--check|--apply]
"""
import os
import shutil
import sys

ROOT = r"D:\house planner\house-plan-designer-main"
TP = os.path.join(ROOT, "assets", "template.html")
BAK = TP + ".bak_full_pbr2"

OPS = []


def op(desc, old, new):
    OPS.append((desc, old, new))


# ---------------------------------------------------------------------------
# 1) 新增 __boxUVmm：按物理尺寸重算 BoxGeometry 的 UV
# ---------------------------------------------------------------------------
op(
    "新增 __boxUVmm（按毫米物理尺寸重算盒子 UV）",
    '/* ===== 高清家具模型库 furnlib: 加载 + 按角色高清材质 ===== */',
    """/* 盒子按【毫米物理尺寸】重算 UV：1 张贴图 = __WALL_TILE_MM 毫米。
   BoxGeometry 默认 UV 是 0..1 → 一张 2048 贴图被拉到 6.8m 宽的整面墙，
   纹理被拉扁、看起来像"糊上去的"。这里改成真实尺度，墙面才有细腻的质感。
   面序（每面 4 顶点）：0=+X 1=-X 2=+Y 3=-Y 4=+Z 5=-Z
   dims  : 每个面的 (水平跨度, 垂直跨度) 毫米
   tP/tN : +Z / -Z 两个房间侧的铺装规格（mm，0 = 该侧不是砖，用扫描贴图） */
const __WALL_TILE_MM=2400;
function __boxUVmm(g,W,H,D,tP,tN){
  const V=g.getAttribute&&g.getAttribute("uv");
  if(!V)return;
  const dims=[[D,H],[D,H],[W,D],[W,D],[W,H],[W,H]];
  for(let f=0;f<6;f++){
    const tiled=(f===4&&tP>0)||(f===5&&tN>0);
    if(tiled)continue;                       // 砖的 UV 已由原逻辑按绝对毫米算好
    const tile=__WALL_TILE_MM;
    const fw=dims[f][0],fh=dims[f][1];
    for(let i=0;i<4;i++){
      const k=f*4+i;
      V.setXY(k,V.getX(k)*fw/tile,V.getY(k)*fh/tile);
    }
  }
}
/* ===== 高清家具模型库 furnlib: 加载 + 按角色高清材质 ===== */""",
)

# ---------------------------------------------------------------------------
# 2) sx() 的 w()：建墙盒后按物理尺寸重算 UV
# ---------------------------------------------------------------------------
op(
    "sx(): 墙盒 UV 改成毫米物理尺度",
    '}}const O=new Me(P,v);if(O.userData.roles=["wallface","wallface","cap","wallface","wallface","wallface"]',
    '}}__boxUVmm(P,D-k,H-I,u*1e3,x,b);const O=new Me(P,v);'
    'if(O.userData.roles=["wallface","wallface","cap","wallface","wallface","wallface"]',
)

# ---------------------------------------------------------------------------
# 3) __ARCH_MAT 的 rep 改成 1（UV 已经按物理尺度算过，不再叠乘）
# ---------------------------------------------------------------------------
op(
    "__ARCH_MAT: wallPlaster / cap* / concrete 的 rep 改成 1（UV 已按物理尺度算）",
    '  wallPlaster:__archMat("wall_plaster_white",{rough:.9,color:"#f3f1ec",normalScale:.8,rep:3}),',
    '  wallPlaster:__archMat("wall_plaster_white",{rough:.9,color:"#f3f1ec",normalScale:.8,rep:1}),',
)
op(
    "__ARCH_MAT: capBearing rep 1",
    'capBearing:__archMat("wall_concrete",{rough:.86,color:"#3a3f47",normalScale:.6,rep:2}),',
    'capBearing:__archMat("wall_concrete",{rough:.86,color:"#3a3f47",normalScale:.6,rep:1}),',
)
op(
    "__ARCH_MAT: capPart rep 1",
    'capPart:__archMat("wall_concrete",{rough:.86,color:"#9aa3ad",normalScale:.6,rep:2}),',
    'capPart:__archMat("wall_concrete",{rough:.86,color:"#9aa3ad",normalScale:.6,rep:1}),',
)
op(
    "__ARCH_MAT: capNew rep 1",
    'capNew:__archMat("wall_concrete",{rough:.86,color:"#e8590c",normalScale:.6,rep:2}),',
    'capNew:__archMat("wall_concrete",{rough:.86,color:"#e8590c",normalScale:.6,rep:1}),',
)
op(
    "__ARCH_MAT: concrete rep 1",
    'concrete:__archMat("wall_concrete",{rough:.9,color:"#f1efea",normalScale:.7,rep:2.4}),',
    'concrete:__archMat("wall_concrete",{rough:.9,color:"#f1efea",normalScale:.7,rep:1}),',
)

# ---------------------------------------------------------------------------
# 4) 剩下的可见纯色
# ---------------------------------------------------------------------------
op(
    "门套下压条改扫描木纹",
    'const __sa=new Me(new ot(O+.02,.05,.015),L("#e8e4dc",.5));',
    'const __sa=new Me(new ot(O+.02,.05,.015),__ARCH_MAT.doorWood);',
)
op(
    "化粪池内胆改扫描黑铁",
    'ue(o,a/2-.015,a/2-.015,.032,0,0,0,"#222",20)',
    'ue(o,a/2-.015,a/2-.015,.032,0,0,0,__ARCH_MAT.socketDark,20)',
)
op(
    "烟道压顶改扫描黑铁",
    's.kind==="flue"?"#8a6a4d":"#5c7080",!1)',
    's.kind==="flue"?__ARCH_MAT.metalBlack:__ARCH_MAT.metalSteel,!1)',
)
op(
    "结构柱压边改扫描黑铁",
    'N(o,a+.002,.004,r+.002,0,n-.002,0,"#3a3f47",!1))',
    'N(o,a+.002,.004,r+.002,0,n-.002,0,__ARCH_MAT.metalBlack,!1))',
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
