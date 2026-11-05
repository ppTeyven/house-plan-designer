"""把主程序的高清家具库从【按 type 取模型】改成【按款式 key 取模型】。

【为什么必须改 —— 这是"比例崩坏"的真正根源】
  主程序 assets/template.html 的 kv() 里：
      const __m = __FURN.get(n.type);
      __g.scale.set(i/__m.w, o/__m.h, s/__m.d);
  __FURN 的键是【type】。但 251 个款式里有 27 个 type 存在多个款式，
  且同 type 内尺寸差异巨大（实测）：
      cabinet   11 项，尺寸比 max/min = 6.50
      diningTable 6 项，3.00
      roundTable  5 项，3.00
      plant      3 项，3.60
      free      25 项，100.00
      sofa       5 项，2.80
      floorLamp  2 项，3.25
  也就是说：一个 sofa 模型会被拉伸去当 2.8 倍大的 theaterSofa，
  一个 free 模型会被拿去当 100 倍大的墙体 —— 这就是用户说的
  "不准有任何比例崩坏"被系统性违反。

  改法：
    · furnlib/index.json 的键改为【款式 key】（如 sofa / theaterSofa / freeBox）
    · kv() 优先用 n.key 取，取不到再退回 n.type（向后兼容）
    · 每个 key 都有自己精确尺寸的 GLB → 缩放比恒为 1.0 → 永不崩坏

【尺寸与朝向】
  GLB 全部是 Y-up（y=高），主程序读取 sz.x/sz.y/sz.z 作为 w/h/d ——
  与验收站口径一致（fit_item.py:228 用的是 (x范围, z范围, y范围) 的 w/d/h）。
  每个 GLB 已落地（min y = 0）且水平居中，摆放时直接放在地面即可。

用法：
  python patch_furnlib_keying.py --check
  python patch_furnlib_keying.py --apply
"""
import os
import sys

ROOT = r'D:\house planner\house-plan-designer-main'
TP = os.path.join(ROOT, "assets", "template.html")

# ---------------------------------------------------------------------
# 锚点 1：loader —— index.json 的键语义从 type 改为 key
# ---------------------------------------------------------------------
OLD_LOADER = '''(async()=>{
  try{
    const r=await fetch("furnlib/index.json");if(!r.ok)return;
    const idx=await r.json();
    const tasks=Object.entries(idx).map(([t,meta])=>
      fetch("furnlib/"+meta.file).then(x=>x.arrayBuffer()).then(b=>sv(b)).then(g=>{
        const sz=new z0().setFromObject(g).getSize(new z);
        __FURN.set(t,{g,w:Math.max(.01,sz.x),h:Math.max(.01,sz.y),d:Math.max(.01,sz.z)});
        __furnInvalidate();
      }).catch(()=>null)
    );
    await Promise.all(tasks);
  }catch(e){}
})();'''

NEW_LOADER = '''(async()=>{
  try{
    const r=await fetch("furnlib/index.json");if(!r.ok)return;
    const idx=await r.json();
    /* 【v2】index.json 的键是【款式 key】而不是 type。
       原因：27 个 type 下有多个款式且尺寸差异巨大（cabinet 11 项差 6.5 倍、
       free 25 项差 100 倍）。按 type 取模型 → 一个模型被拉伸去当别的款式 →
       系统性的"比例崩坏"。按 key 取 → 每件家具用自己的精确尺寸模型，
       缩放比恒为 1.0。
       兼容：若某 key 未命中，kv() 会退回按 type 查找。 */
    const tasks=Object.entries(idx).map(([k,meta])=>
      fetch("furnlib/"+meta.file).then(x=>x.arrayBuffer()).then(b=>sv(b)).then(g=>{
        const sz=new z0().setFromObject(g).getSize(new z);
        /* 落地 + 居中：GLB 已由构建流水线落地居中，
           这里再兜一次底，保证任何来源的模型都贴在 y=0 地面上。 */
        g.traverse(o=>{if(o.isMesh){o.castShadow=!0;o.receiveShadow=!0;}});
        const bb=new z0().setFromObject(g);
        if(bb.min.y!==0)g.position.y-=bb.min.y;
        const sz2=new z0().setFromObject(g).getSize(new z);
        __FURN.set(k,{g,w:Math.max(.01,sz2.x),h:Math.max(.01,sz2.y),d:Math.max(.01,sz2.z)});
        __furnInvalidate();
      }).catch(()=>null)
    );
    await Promise.all(tasks);
  }catch(e){}
})();'''

# ---------------------------------------------------------------------
# 锚点 2：kv() —— 优先按 key 取模型，退回 type
# ---------------------------------------------------------------------
OLD_LOOKUP = 'if(window.__FURN&&__FURN.size){const __m=__FURN.get(n.type);if(__m){const __g=__m.g.clone(!0);__g.scale.set(i/__m.w,o/__m.h,s/__m.d);'
NEW_LOOKUP = ('if(window.__FURN&&__FURN.size){'
              # 优先 key（款式级，尺寸精确）
              'const __m=(n.key&&__FURN.get(n.key))||__FURN.get(n.type);'
              'if(__m){const __g=__m.g.clone(!0);__g.scale.set(i/__m.w,o/__m.h,s/__m.d);')

PATCHES = [
    ("loader 改按款式 key 建索引", OLD_LOADER, NEW_LOADER),
    ("kv() 优先按 key 取模型", OLD_LOOKUP, NEW_LOOKUP),
]


def main():
    mode = "--apply" if "--apply" in sys.argv else "--check"
    src = open(TP, encoding="utf-8").read()
    orig = src

    print("模板: %s  (%.2f MB)" % (TP, len(src) / 1048576))
    print("模式: %s\n" % mode)

    ok = True
    for title, anchor, repl in PATCHES:
        n = src.count(anchor)
        if n != 1:
            print("  [锚点不唯一 %d 次] %s" % (n, title))
            ok = False
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
        bak = TP + ".bak_keying"
        if not os.path.exists(bak):
            with open(bak, "w", encoding="utf-8") as f:
                f.write(orig)
            print("\n备份 -> %s" % bak)
        with open(TP, "w", encoding="utf-8") as f:
            f.write(src)
        print("已写入 %s" % TP)
    return 0


if __name__ == "__main__":
    sys.exit(main())
