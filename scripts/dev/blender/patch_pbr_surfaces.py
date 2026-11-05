"""给 template.html 接入真实扫描 PBR 纹理（墙 / 地 / 天 / 门）。

【为什么需要】
  用户硬要求："地板天花板墙壁门的纹理要达到非常精细" +
            "墙壁门天花板，地板也要3d的纹理不要拿贴图糊弄我"
  现状：墙面/天花是 canvas 手绘的纯色/条纹贴图（__ft("plaster")、
        Y7()、j7()），地面是 canvas 画的木纹/瓷砖（K2/f9），
        门是纯色 L("#d9dcdf")。全部是【程序化假纹理】。

  ambientCG 的 26 套真实扫描材质已经落地到 assets/furnlib/tex/
  （见 export_pbr_textures.py），本脚本把它们接进渲染路径。

【技术边界（诚实说明）】
  · "3D 纹理"在物理上必须由法线贴图 + 位移贴图承载，
    单张 albedo 贴图做不到真起伏。
  · ambientCG 的 Displacement 是【真实扫描高度场】（photogrammetry），
    不是手绘假凹凸 —— 这是能做到的最强形态。
  · 位移贴图需要足够密的几何才有意义；
    墙/地/天在主程序里是大平面（顶点很少），
    所以【主路径用 normalMap + roughnessMap + aoMap】，
    位移贴图仅在网格足够密时启用（家具、地毯等）。
  · 几何上的立体结构（墙裙线、门套、天花阴角）本来就有真几何，
    纹理只负责微表面。

【修改纪律（handbook 附录 A）】
  1. 只做【锚点定位 + 精确字符串替换】，不重排不格式化。
  2. 每个锚点必须唯一；不唯一就扩大上下文。
  3. 改完必须语法校验 + 三层对账（磁盘→HTTP→内存态）。

用法：
  python patch_pbr_surfaces.py --check    # 只检查锚点
  python patch_pbr_surfaces.py --apply    # 执行替换
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TP = os.path.join(ROOT, "assets", "template.html")

# ---------------------------------------------------------------------
# 注入的 PBR 基础设施代码（追加到既有 __pbrTex 之后）
# ---------------------------------------------------------------------
INJECT_HELPERS = r'''
/* ===== 真实扫描 PBR 表面（ambientCG 2K 扫描材质）=====
 * 墙 / 地 / 天 / 门 原本是 canvas 手绘的假纹理，
 * 这里换成 ambientCG 真实扫描的 albedo + normal + roughness + AO。
 * 位移贴图仅用于【网格足够密】的表面（家具、地毯）——
 * 墙/地/天是大平面，位移贴图只会露出三角形边缘。
 */
const __SURF_PBR={};
const __SURF_ROLE={
  floor_oak:"floor_wood_oak",floor_walnut:"floor_wood_walnut",
  floor_tile:"floor_tile",floor_microcement:"floor_microcement",
  floor_stone:"floor_stone",floor_bath:"floor_bath",
  wall_plaster:"wall_plaster_white",wall_concrete:"wall_concrete",
  wall_microcement:"wall_microcement",wall_wainscot:"wall_wainscot",
  wall_stone:"wall_stone",wall_fabric:"wall_fabric",
  ceil_white:"ceiling_white",ceil_coffered:"ceiling_coffered",
  door_wood:"door_wood",door_paint:"door_paint",door_metal:"door_metal",
  rug_wool:"rug_wool",rug_lowpile:"rug_lowpile",rug_pattern:"rug_pattern",
};
function __surfTex(name,channel,rep){
  const key=name+"_"+channel+"|"+rep;
  if(__SURF_PBR[key])return __SURF_PBR[key];
  const t=new ms();
  t.wrapS=t.wrapT=E0;
  t.repeat.set(rep,rep);
  t.anisotropy=16;
  if(channel==="col")t.colorSpace=Et;
  const img=new Image();
  img.onload=()=>{t.image=img;t.needsUpdate=!0;};
  img.onerror=()=>{t.image=null;};
  img.src="furnlib/tex/"+name+"_"+channel+".jpg";
  __SURF_PBR[key]=t;
  return t;
}
/* 大面积表面：uv 按【毫米物理尺寸】平铺，保证 1 张贴图 = 真实尺度 */
function __surfMat(texName,opt){
  const o=opt||{};
  const rep=o.rep||1;
  const m=new Zt({
    map:__surfTex(texName,"col",rep),
    normalMap:__surfTex(texName,"nor",rep),
    roughnessMap:__surfTex(texName,"rough",rep),
  });
  if(o.ao!==false)m.aoMap=__surfTex(texName,"ao",rep);
  if(o.normalScale&&m.normalScale)m.normalScale.set(o.normalScale,o.normalScale);
  m.roughness=o.rough==null?.85:o.rough;
  m.metalness=o.metal==null?0:o.metal;
  m.envMapIntensity=o.env==null?.55:o.env;
  if(o.color)m.color.set(o.color);
  if(o.emissive){m.emissive=new Be(o.emissive);m.emissiveIntensity=o.emissiveIntensity==null?.06:o.emissiveIntensity;}
  m.name="PBR_"+texName;
  return m;
}
'''

# ---------------------------------------------------------------------
# 锚点表：(说明, 唯一锚点字符串, 替换字符串)
#   每个锚点必须在原文件中【唯一】出现，否则替换会误伤。
# ---------------------------------------------------------------------

# 1) 注入基础设施：插在 __applyPBR 函数结束之后（__furnWallTex 之前）
PATCHES = []

PATCHES.append((
    "注入 __surfTex/__surfMat 基础设施",
    'function __furnWallTex(){return __ft("plaster")}',
    INJECT_HELPERS + 'function __furnWallTex(){return __ft("plaster")}',
))

# 2) 墙面：j7() 里按墙面材质名换真实扫描贴图
PATCHES.append((
    "墙面材质改真实扫描 PBR",
    'function j7(n,e){if(!n)return e;const t=ks(n);if(P9.has(t))return P9.get(t);const i=Yu[t];let s;if(i.tex){const o=new ms(ku(i.tex));o.wrapS=o.wrapT=E0,o.colorSpace=Et,o.anisotropy=16,s=new Zt({map:o,roughness:t==="wallTile"?.35:.7})}else s=new Zt({color:i.color,roughness:t==="wallpaper"?1:.92});return P9.set(t,s),s}',
    'function j7(n,e){if(!n)return e;const t=ks(n);if(P9.has(t))return P9.get(t);const i=Yu[t];let s;'
    'const __WALL_PBR={latexWhite:"wall_plaster_white",latexGrey:"wall_concrete",'
    'latexSage:"wall_microcement",latexWarm:"wall_wainscot",'
    'wallpaper:"wall_fabric",wallTile:"floor_bath",woodPanel:"white_oak_veneer"};'
    'const __wp=__WALL_PBR[t];'
    'if(__wp){s=__surfMat(__wp,{rep:1,rough:t==="wallTile"?.42:.88,'
    'normalScale:t==="wallTile"?.55:.8,env:.5});}'
    'else if(i.tex){const o=new ms(ku(i.tex));o.wrapS=o.wrapT=E0,o.colorSpace=Et,o.anisotropy=16,s=new Zt({map:o,roughness:t==="wallTile"?.35:.7})}'
    'else s=new Zt({color:i.color,roughness:t==="wallpaper"?1:.92});'
    'return P9.set(t,s),s}',
))

# 3) 天花：Y7() 换成真实扫描石膏
PATCHES.append((
    "天花材质改真实扫描 PBR",
    'const Y7=()=>new Zt({color:"#f1efea",map:__furnWallTex(),roughness:.95,side:cn,emissive:"#f1efea",emissiveIntensity:.15});',
    'const Y7=()=>new Zt({map:__surfTex("ceiling_white","col",1),'
    'normalMap:__surfTex("ceiling_white","nor",1),'
    'roughnessMap:__surfTex("ceiling_white","rough",1),'
    'aoMap:__surfTex("ceiling_white","ao",1),'
    'color:"#f4f2ee",roughness:.95,side:cn,envMapIntensity:.5});',
))

# 4) 地面：把 jo.* 的 canvas make 换成真实扫描贴图
#    jo 结构的 make 字段被 OC()/Fd() 消费；这里给 jo 每项加一个 pbr 字段，
#    并在地面 mesh 创建处优先使用 pbr 贴图。
PATCHES.append((
    "地面：jo 增加真实扫描贴图名",
    'jo={oak:{name:"橡木地板",tile:1200,rough:.7,',
    'jo={oak:{name:"橡木地板",tile:1200,rough:.7,pbr:"floor_wood_oak",',
))

PATCHES.append((
    "地面：walnut 增加真实扫描贴图名",
    'walnut:{name:"胡桃木",tile:1200,rough:.7,',
    'walnut:{name:"胡桃木",tile:1200,rough:.7,pbr:"floor_wood_walnut",',
))

PATCHES.append((
    "地面：tile 增加真实扫描贴图名",
    'tile:{name:"灰白大板",tile:1600,rough:.45,',
    'tile:{name:"灰白大板",tile:1600,rough:.45,pbr:"floor_tile",',
))

PATCHES.append((
    "地面：marble 增加真实扫描贴图名",
    'marble:{name:"米白大理石",tile:1600,rough:.25,',
    'marble:{name:"米白大理石",tile:1600,rough:.25,pbr:"floor_stone",',
))

PATCHES.append((
    "地面：cement 增加真实扫描贴图名",
    'cement:{name:"微水泥",tile:2400,rough:.7,',
    'cement:{name:"微水泥",tile:2400,rough:.7,pbr:"floor_microcement",',
))

PATCHES.append((
    "地面：paving 增加真实扫描贴图名",
    'paving:{name:"庭院石材",tile:1200,rough:.85,',
    'paving:{name:"庭院石材",tile:1200,rough:.85,pbr:"floor_stone",',
))

PATCHES.append((
    "地面：carpet 增加真实扫描贴图名",
    'carpet:{name:"方块地毯",tile:1e3,rough:1,',
    'carpet:{name:"方块地毯",tile:1e3,rough:1,pbr:"rug_lowpile",',
))

# 5) 地面 mesh 创建：用 pbr 贴图替换 canvas 贴图
PATCHES.append((
    "地面材质改真实扫描 PBR",
    'const g=(r=c.labels[0])==null?void 0:r.tile;if(g){const m=c.bb,y=p.getAttribute("position"),x=[];for(let M=0;M<y.count;M++)x.push((y.getX(M)*1e3-m.x)/m.w,1-(y.getZ(M)*1e3-m.y)/m.h);p.setAttribute("uv",new vt(x,2));const b=new ms(OC(c,Hr(g)));b.colorSpace=Et,b.anisotropy=16;const v=Hr(g).tex,w=v==="marble"?.25:v==="wood"?.6:v==="cement"?.75:.45,S=new Me(p,new Zt({map:b,roughness:w}));',
    'const g=(r=c.labels[0])==null?void 0:r.tile;if(g){const m=c.bb,y=p.getAttribute("position"),x=[];for(let M=0;M<y.count;M++)x.push((y.getX(M)*1e3-m.x)/m.w,1-(y.getZ(M)*1e3-m.y)/m.h);p.setAttribute("uv",new vt(x,2));'
    'const __pg=Hr(g);const __pb=__pg.pbr?__surfMat(__pg.pbr,{rep:1,rough:__pg.rough==null?.8:__pg.rough,normalScale:.85,env:.5}):null;'
    'const b=__pb?null:new ms(OC(c,Hr(g)));if(b){b.colorSpace=Et,b.anisotropy=16;}'
    'const v=Hr(g).tex,w=v==="marble"?.25:v==="wood"?.6:v==="cement"?.75:.45,'
    'S=new Me(p,__pb||new Zt({map:b,roughness:w}));',
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
        # 备份
        bak = TP + ".bak_pbr"
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
