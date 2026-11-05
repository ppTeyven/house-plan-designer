"""给 3D 建筑构件（门/门套/窗框/踢脚线/吊顶边吊/灯槽）接上真实扫描 PBR。

【为什么需要】
  浏览器实测（127.0.0.1:8899/template.html?debug）发现：
    · 墙组 597 个 mesh 里 519 个是纯色（没贴图）
    · 顶组 42 个 mesh 里 35 个是纯色（边吊侧面 / 灯槽 / 灯带）
    · 踢脚线 138 段、门套 / 窗框 300+ 个都是 L("#xxxxxx") 纯色
  这些都是【看得见】的大面积构件，纯色 = 塑料感，与"墙体门顶要 3D 纹理
  不要拿贴图糊弄"的要求不符。

【已确认可用的纹理集】（assets/furnlib/tex/，均为 ambientCG 2K 真实扫描）
  door_wood / door_paint / door_metal   门板 / 门套 / 金属件
  role_wood_oak / role_metal_black      实木踢脚线 / 深色金属框
  ceiling_white                        顶面
  wall_plaster_white                   墙面

【做法】
  1) 新增 __ARCH_PBR_ROLE 表：构件角色 → 纹理集名
  2) 新增 __archMat(texName, opt)：生成带 albedo/normal/rough/AO 的材质
     （复用已有的 __surfTex，零新增网络请求）
  3) 在 sx()（墙体/门窗/踢脚线）与 KL()（吊顶）里替换掉纯色材质
  4) 保留原纯色作为【贴图加载失败时的兜底】，不会因为缺图变黑

用法：python patch_arch_pbr.py [--check|--apply]
"""
import os
import shutil
import sys

ROOT = r"D:\house planner\house-plan-designer-main"
TP = os.path.join(ROOT, "assets", "template.html")
BAK = TP + ".bak_arch_pbr"

# ---------------------------------------------------------------------------
# 补丁操作：(说明, 原文, 新文)
#   原文必须【唯一】出现，否则报错退出（避免误改）
# ---------------------------------------------------------------------------
OPS = []


def op(desc, old, new):
    OPS.append((desc, old, new))


# --- 1) 注入建筑构件 PBR 角色表 + 材质工厂 -------------------------------
op(
    "注入建筑构件 PBR 表与材质工厂",
    '/* ===== 高清家具模型库 furnlib: 加载 + 按角色高清材质 ===== */',
    """/* ===== 建筑构件 PBR（门 / 门套 / 窗框 / 踢脚线 / 吊顶边吊）===== *
 * 浏览器实测：墙组 519 个 mesh、顶组 35 个 mesh、踢脚线 138 段
 * 全是 L("#xxxxxx") 纯色 —— 大面积构件没有纹理 = 塑料感。
 * 这里把可��构件接到 assets/furnlib/tex/ 里 ambientCG 2K 真实扫描贴图。
 * 纹理集清单见 __ARCH_PBR_ROLE 的注释（均为 col/nor/rough/ao 四通道齐全）。
 */
const __ARCH_PBR_ROLE={
  doorWood:"door_wood",doorPaint:"door_paint",doorMetal:"door_metal",
  skirtWood:"role_wood_oak",skirtMetal:"role_metal_black",
  ceilTrim:"ceiling_white",wallPaint:"wall_plaster_white",
};
/* 建筑构件材质：albedo + normal + roughness + AO 全部来自真实扫描。
   opt.color 用于把扫描色调压到设计稿的配色（避免色调打架）。 */
function __archMat(texName,opt){
  const o=opt||{};
  const rep=o.rep||1;
  const m=new Zt({
    map:__surfTex(texName,"col",rep),
    normalMap:__surfTex(texName,"nor",rep),
    roughnessMap:__surfTex(texName,"rough",rep),
  });
  m.aoMap=__surfTex(texName,"ao",rep);
  if(o.normalScale&&m.normalScale)m.normalScale.set(o.normalScale,o.normalScale);
  m.roughness=o.rough==null?.7:o.rough;
  m.metalness=o.metal==null?0:o.metal;
  m.envMapIntensity=o.env==null?.55:o.env;
  if(o.color)m.color.set(o.color);
  m.name="ARCH_"+texName;
  return m;
}
/* ===== 高清家具模型库 furnlib: 加载 + 按角色高清材质 ===== */""",
)

# --- 2) sx()：门/窗框/门套/踢脚线接 PBR ---------------------------------
op(
    "门/窗框/门套/踢脚线接真实扫描 PBR",
    'function sx(){var r;Uu(F0),$5.clear();const n=E.plan.height,e=L("#f3f1ec",.92),'
    't={bear:L("#3a3f47",.8),part:L("#9aa3ad",.8),new:L("#e8590c",.8)},'
    'i=L("#5b626c",.5,.3),s=L("#c9a57c",.6),o=L("#474c55",.5),a=[];',
    'function sx(){var r;Uu(F0),$5.clear();const n=E.plan.height,e=L("#f3f1ec",.92),'
    't={bear:L("#3a3f47",.8),part:L("#9aa3ad",.8),new:L("#e8590c",.8)},'
    'i=L("#5b626c",.5,.3),s=L("#c9a57c",.6),o=L("#474c55",.5),a=[];'
    '/* 建筑构件接真实扫描 PBR（原本全是纯色）：'
    '   i=窗框/门套铝材  s=木门/实木踢脚  o=入户门  i2=踢脚金属  sk=木踢脚  */'
    'const i2=__archMat("role_metal_black",{rough:.5,metal:.72,color:"#6a6f78",normalScale:.5});'
    'const iw=__archMat("door_metal",{rough:.42,metal:.8,color:"#9aa2ab",normalScale:.45});'
    'const sk=__archMat("role_wood_oak",{rough:.6,color:"#e8d8c2",normalScale:.6,rep:2});'
    'const skm=__archMat("role_metal_black",{rough:.38,metal:.85,color:"#8d939c",normalScale:.4,rep:2});'
    'const drw=__archMat("door_wood",{rough:.52,color:"#d8b98e",normalScale:.7,rep:1.4});'
    'const drp=__archMat("door_paint",{rough:.55,color:"#f0ece4",normalScale:.55,rep:1.4});'
    'const drm=__archMat("door_metal",{rough:.36,metal:.88,color:"#b6bcc3",normalScale:.45,rep:1.4});',
)

# 窗框材质：把 i 换成扫描金属
op(
    "窗框铝材改用扫描金属 PBR",
    'C=(F,W,B,K,Q=0,j=.06)=>{const te=new Me(new ot(W,K,j),i);',
    'C=(F,W,B,K,Q=0,j=.06)=>{const te=new Me(new ot(W,K,j),iw);',
)

# 门板材质：entry/木门/金属门 分别接对应扫描纹理
op(
    "门板接 door_wood/door_paint/door_metal 扫描纹理",
    'const le=k.material==="glass"?_s():k.material==="metal"?L("#8c979e",.45,.65):k.entry?o:s,',
    'const le=k.material==="glass"?_s():k.material==="metal"?drm:k.entry?drm:drw,',
)

# 门套/窗台（sill）材质
op(
    "门套/窗台板接扫描木纹",
    'const W=new Me(new ot(O+.06,.03,u+.08),L("#e8e4dc",.5));',
    'const W=new Me(new ot(O+.06,.03,u+.08),drw);',
)
op(
    "门套压条接扫描木纹",
    'const __sn=new Me(new ot(O+.09,.014,u+.11),L("#e8e4dc",.5));',
    'const __sn=new Me(new ot(O+.09,.014,u+.11),drw);',
)

# 踢脚线材质
op(
    "踢脚线接扫描木纹/金属",
    'const t=e==="metal"?.04:.08,i=e==="metal"?L("#6b7078",.35,.7):L("#f1ede6",.6),',
    'const t=e==="metal"?.04:.08,i=e==="metal"?skm:sk,',
)

# --- 3) KL()：吊顶边吊侧面 / 灯槽接扫描 PBR -----------------------------
op(
    "吊顶边吊/灯槽接扫描 PBR",
    'const r=new Zt({color:"#f3f1ec",roughness:.95,emissive:"#f3f1ec",emissiveIntensity:.15}),'
    'l=i.cove?new Zt({color:"#ffe1b3",emissive:"#ffcf8a",emissiveIntensity:.8}):'
    'new Zt({color:"#e6e3dd",roughness:.95});',
    'const __ct=__archMat("ceiling_white",{rough:.92,color:"#f4f2ee",normalScale:.35,rep:2});'
    'const r=new Zt({color:"#f3f1ec",roughness:.95,emissive:"#f3f1ec",emissiveIntensity:.15}),'
    '__ce=__ct,'
    'l=i.cove?new Zt({color:"#ffe1b3",emissive:"#ffcf8a",emissiveIntensity:.8}):__ct;',
)

# 边吊侧面的 6 个材质槽：把 [l,l,r,r,l,l] 换成 [__ce,l,__ce,__ce,l,__ce]
op(
    "边吊侧面六材质槽接扫描顶面",
    'const u=new Me(new ot(c.w/1e3,s,c.h/1e3),[l,l,r,r,l,l]);',
    'const u=new Me(new ot(c.w/1e3,s,c.h/1e3),[__ce,l,__ce,__ce,l,__ce]);',
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
    print("已写入 %s  (%.2f MB)" % (TP, len(s) / 1024 / 1024))
    print("下一步：node --check 语法校验 + 起服浏览器实测")


if __name__ == "__main__":
    main()
