"""修复 __ARCH_MAT 的 TDZ（暂时性死区）崩溃。

【问题】
  fix_skirt_scope.py 把建筑构件材质提升到模块级，
  位置在 "window.__FURN=new Map" 附近（偏移 ~1950424）。
  但 __archMat() 内部会调用 __surfTex()，
  而 __surfTex() 读的是模块级 const __SURF_PBR={}（偏移 ~1956828，在后面）。

  const 有 TDZ：模块求值时，__ARCH_MAT 在 __SURF_PBR 初始化之前就执行
  __archMat() → __surfTex() → 读 __SURF_PBR → ReferenceError
  → 整个 module 挂掉 → window.__FURN / window.__d / window.__designer 全部不存在。

【证据】
  浏览器实测：页面加载后 window.__FURN === undefined、window.__d === undefined，
  但 window.__designer 存在（它在更早的位置赋值）。

【修法】
  把 __ARCH_MAT 这段【整块】从当前位置删除，
  挪到 __SURF_PBR / __surfTex 声明【之后】（紧跟 __surfMat 定义即可），
  保证求值顺序正确。
"""
import os
import shutil
import sys

ROOT = r"D:\house planner\house-plan-designer-main"
TP = os.path.join(ROOT, "assets", "template.html")
BAK = TP + ".bak_tdz_fix"

BLOCK_START = "/* 模块级建筑构件材质。"
BLOCK_END = "};\n"

OPS = []


def op(desc, old, new):
    OPS.append((desc, old, new))


# 1) 从当前位置删除 __ARCH_MAT 整块（连同上面的空行）
op(
    "从当前位置删除 __ARCH_MAT 块（TDZ 源）",
    """/* 模块级建筑构件材质。
   【必须放在模块级】——踢脚线在 qL() 里创建，而 qL() 拿不到 sx() 的局部变量，
   之前把材质 const 放在 sx() 里导致 new Me(geo,"sk") 传了字符串 → 踢脚线不渲染。 */
const __ARCH_MAT={
  frame:__archMat("door_metal",{rough:.42,metal:.8,color:"#9aa2ab",normalScale:.45}),
  skirtWood:__archMat("role_wood_oak",{rough:.6,color:"#e8d8c2",normalScale:.6,rep:2}),
  skirtMetal:__archMat("role_metal_black",{rough:.38,metal:.85,color:"#8d939c",normalScale:.4,rep:2}),
  doorWood:__archMat("door_wood",{rough:.52,color:"#d8b98e",normalScale:.7,rep:1.4}),
  doorPaint:__archMat("door_paint",{rough:.55,color:"#f0ece4",normalScale:.55,rep:1.4}),
  doorMetal:__archMat("door_metal",{rough:.36,metal:.88,color:"#b6bcc3",normalScale:.45,rep:1.4}),
  ceilTrim:__archMat("ceiling_white",{rough:.92,color:"#f4f2ee",normalScale:.35,rep:2}),
};
""",
    "",
)

# 2) 在 __surfMat 定义之后插入（__surfTex / __SURF_PBR 都已就绪）
op(
    "在 __surfMat 之后插入 __ARCH_MAT（TDZ 安全位置）",
    """  m.name="PBR_"+texName;
  return m;
}""",
    """  m.name="PBR_"+texName;
  return m;
}
/* 模块级建筑构件材质。
   【位置要求】必须在 __SURF_PBR / __surfTex 声明【之后】——
   const 有 TDZ，提前求值会 ReferenceError，整包 module 挂掉
   （window.__FURN / window.__d 全部消失）。
   【作用域要求】必须在模块级——踢脚线在 qL() 里创建，qL() 拿不到 sx() 的局部变量。 */
const __ARCH_MAT={
  frame:__archMat("door_metal",{rough:.42,metal:.8,color:"#9aa2ab",normalScale:.45}),
  skirtWood:__archMat("role_wood_oak",{rough:.6,color:"#e8d8c2",normalScale:.6,rep:2}),
  skirtMetal:__archMat("role_metal_black",{rough:.38,metal:.85,color:"#8d939c",normalScale:.4,rep:2}),
  doorWood:__archMat("door_wood",{rough:.52,color:"#d8b98e",normalScale:.7,rep:1.4}),
  doorPaint:__archMat("door_paint",{rough:.55,color:"#f0ece4",normalScale:.55,rep:1.4}),
  doorMetal:__archMat("door_metal",{rough:.36,metal:.88,color:"#b6bcc3",normalScale:.45,rep:1.4}),
  ceilTrim:__archMat("ceiling_white",{rough:.92,color:"#f4f2ee",normalScale:.35,rep:2}),
};""",
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
            print("  [锚点不唯一 %d 次] %s" % (cnt, desc))
            ok = False
        else:
            print("  [可替换] %s" % desc)
    if not ok:
        print("\n锚点校验失败，未做任何修改。")
        sys.exit(1)

    # 额外校验：插入点必须晚于 __SURF_PBR 声明
    i_surf = s.find("const __SURF_PBR={}")
    i_ins = s.find('  m.name="PBR_"+texName;')
    if i_ins < i_surf:
        print("  [插入点早于 __SURF_PBR 声明，仍会 TDZ]")
        ok = False
    if not ok:
        print("\n顺序校验失败，未做任何修改。")
        sys.exit(1)

    if mode == "--check":
        print("\n锚点唯一且顺序安全。")
        return

    for _desc, old, new in OPS:
        s = s.replace(old, new, 1)

    if os.path.exists(BAK):
        os.remove(BAK)
    shutil.copy2(TP, BAK)
    open(TP, "w", encoding="utf-8").write(s)
    print("\n备份 -> %s" % BAK)
    print("已写入 %s" % TP)


if __name__ == "__main__":
    main()
