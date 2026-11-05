"""修复踢脚线材质作用域错误。

【问题】
  patch_arch_pbr.py 把踢脚线材质改成 sk / skm，
  但这两个 const 声明在 sx() 【函数体内】，
  而踢脚线几何是在另一个函数 qL() 里创建的 —— qL() 拿不到 sx() 的局部变量，
  于是 `new Me(geo, i)` 传进去的是字符串 "sk" 而不是材质对象。
  浏览器实测：138 个 role=skirt 的 mesh 的 material 是字符串，不是材质 → 踢脚线不渲染。

【修法】
  把建筑构件材质提升到【模块级】（与 __archMat 放在一起），
  sx() / qL() / KL() 都从模块级引用。
"""
import os
import shutil
import sys

ROOT = r"D:\house planner\house-plan-designer-main"
TP = os.path.join(ROOT, "assets", "template.html")
BAK = TP + ".bak_skirt_scope"

OPS = []


def op(desc, old, new):
    OPS.append((desc, old, new))


# 1) 在 __archMat 后面【追加】模块级材质常量
op(
    "把建筑构件材质提升到模块级",
    '  m.name="ARCH_"+texName;\n  return m;\n}',
    '  m.name="ARCH_"+texName;\n  return m;\n}\n'
    '/* 模块级建筑构件材质。\n'
    '   【必须放在模块级】——踢脚线在 qL() 里创建，而 qL() 拿不到 sx() 的局部变量，\n'
    '   之前把材质 const 放在 sx() 里导致 new Me(geo,"sk") 传了字符串 → 踢脚线不渲染。 */\n'
    'const __ARCH_MAT={\n'
    '  frame:__archMat("door_metal",{rough:.42,metal:.8,color:"#9aa2ab",normalScale:.45}),\n'
    '  skirtWood:__archMat("role_wood_oak",{rough:.6,color:"#e8d8c2",normalScale:.6,rep:2}),\n'
    '  skirtMetal:__archMat("role_metal_black",{rough:.38,metal:.85,color:"#8d939c",normalScale:.4,rep:2}),\n'
    '  doorWood:__archMat("door_wood",{rough:.52,color:"#d8b98e",normalScale:.7,rep:1.4}),\n'
    '  doorPaint:__archMat("door_paint",{rough:.55,color:"#f0ece4",normalScale:.55,rep:1.4}),\n'
    '  doorMetal:__archMat("door_metal",{rough:.36,metal:.88,color:"#b6bcc3",normalScale:.45,rep:1.4}),\n'
    '  ceilTrim:__archMat("ceiling_white",{rough:.92,color:"#f4f2ee",normalScale:.35,rep:2}),\n'
    '};',
)

# 2) sx() 里删掉局部 const，改为引用模块级
op(
    "sx() 改为引用模块级材质",
    '/* 建筑构件接真实扫描 PBR（原本全是纯色）：   i=窗框/门套铝材  s=木门/实木踢脚  o=入户门  i2=踢脚金属  sk=木踢脚  */'
    'const i2=__archMat("role_metal_black",{rough:.5,metal:.72,color:"#6a6f78",normalScale:.5});'
    'const iw=__archMat("door_metal",{rough:.42,metal:.8,color:"#9aa2ab",normalScale:.45});'
    'const sk=__archMat("role_wood_oak",{rough:.6,color:"#e8d8c2",normalScale:.6,rep:2});'
    'const skm=__archMat("role_metal_black",{rough:.38,metal:.85,color:"#8d939c",normalScale:.4,rep:2});'
    'const drw=__archMat("door_wood",{rough:.52,color:"#d8b98e",normalScale:.7,rep:1.4});'
    'const drp=__archMat("door_paint",{rough:.55,color:"#f0ece4",normalScale:.55,rep:1.4});'
    'const drm=__archMat("door_metal",{rough:.36,metal:.88,color:"#b6bcc3",normalScale:.45,rep:1.4});',
    '/* 建筑构件接真实扫描 PBR（原本全是纯色），材质见模块级 __ARCH_MAT */'
    'const iw=__ARCH_MAT.frame,sk=__ARCH_MAT.skirtWood,skm=__ARCH_MAT.skirtMetal,'
    'drw=__ARCH_MAT.doorWood,drp=__ARCH_MAT.doorPaint,drm=__ARCH_MAT.doorMetal;',
)

# 3) KL() 里删掉局部 __ct
op(
    "KL() 改为引用模块级顶面材质",
    'const __ct=__archMat("ceiling_white",{rough:.92,color:"#f4f2ee",normalScale:.35,rep:2});'
    'const r=new Zt({color:"#f3f1ec",roughness:.95,emissive:"#f3f1ec",emissiveIntensity:.15}),'
    '__ce=__ct,'
    'l=i.cove?new Zt({color:"#ffe1b3",emissive:"#ffcf8a",emissiveIntensity:.8}):__ct;',
    'const r=new Zt({color:"#f3f1ec",roughness:.95,emissive:"#f3f1ec",emissiveIntensity:.15}),'
    '__ce=__ARCH_MAT.ceilTrim,'
    'l=i.cove?new Zt({color:"#ffe1b3",emissive:"#ffcf8a",emissiveIntensity:.8}):__ARCH_MAT.ceilTrim;',
)

# 4) qL() 踢脚线：sk/skm 是 sx() 的局部变量，改成直接用模块级
op(
    "qL() 踢脚线材质改用模块级",
    'const t=e==="metal"?.04:.08,i=e==="metal"?skm:sk,',
    'const t=e==="metal"?.04:.08,i=e==="metal"?__ARCH_MAT.skirtMetal:__ARCH_MAT.skirtWood,',
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

    if mode == "--check":
        print("\n锚点全部唯一。")
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
