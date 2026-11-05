# -*- coding: utf-8 -*-
"""Fix: restore contact shadows.

Root cause chain (verified at runtime):
  1. v3 lighting takeover's tick() forces `su[i].castShadow = false` every 500ms
     (a leftover CONST-LIGHT patch meant to keep light constant across
     bird-view / first-person, but it also killed every fill-light shadow).
  2. ax() (bird-view fill layout) also sets `f.castShadow = false`.
  3. renderer.shadowMap.autoUpdate = false AND each light shadow.autoUpdate = false
     -> shadow maps are never re-rendered.

Net effect: no fill-light shadows anywhere => furniture has no contact shadow,
wall corners have no occlusion => exactly what the user reported.

Fix:
  A. Keep the CONST-LIGHT intent (light levels stay constant) but STOP disabling
     castShadow. Shadows do not affect light levels, only the rendered shadow map.
  B. Let the fill-light pool actually cast shadows, with a bounded map size
     (1024) and a manual `needsUpdate` flag that the on-demand module refreshes.
  C. Make the shadow-on-demand module also dirty the shadow maps when the
     fill-light pool changes (positions/intensity) and when scene content changes.
"""
import io, sys, pathlib

P = pathlib.Path(r"D:\house planner\house-plan-designer-main\assets\template.html")
t = P.read_text(encoding='utf-8')
orig = len(t)
changed = []


def rep(name, old, new, expect=1):
    global t
    c = t.count(old)
    if c != expect:
        print('MISMATCH %-28s expect=%d got=%d' % (name, expect, c))
        print('  anchor: %r' % old[:160])
        sys.exit(1)
    t = t.replace(old, new)
    changed.append(name)


# ---------------------------------------------------------------- A
# v3 tick(): stop forcing castShadow off.
rep('A1_tick_no_kill_shadow',
    '''          for (var si2 = 0; si2 < su.length; si2++) {
            var cs = false; /* CONST-LIGHT */
            if (su[si2].castShadow !== cs) { su[si2].castShadow = cs; dirty = true; }
          }''',
    '''          for (var si2 = 0; si2 < su.length; si2++) {
            /* 【接触阴影修复】原 CONST-LIGHT 补丁每 500ms 强制 castShadow=false,
               把所有补光灯的阴影全部关掉 —— 家具底下和墙角因此没有任何阴影。
               CONST-LIGHT 的本意是"光照强度恒定"，与阴影无关；
               这里改为：保证补光灯保持 castShadow=true（阴影贴图由按需更新模块管理）。 */
            var cs = true;
            if (su[si2].castShadow !== cs) {
              su[si2].castShadow = cs;
              if (su[si2].shadow) {
                su[si2].shadow.mapSize.set(1024, 1024);
                su[si2].shadow.bias = -.006;
                su[si2].shadow.normalBias = .05;
                su[si2].shadow.radius = 3;
                su[si2].shadow.camera.near = .05;
                su[si2].shadow.camera.far = 9;
                su[si2].shadow.autoUpdate = false;
                su[si2].shadow.needsUpdate = true;
              }
              dirty = true;
            }
          }''')

# ---------------------------------------------------------------- B
# ax(): bird-view fill-light layout must not disable shadows either.
rep('B1_ax_castShadow',
    '''f.castShadow=!1;f.shadow.needsUpdate=!0;}}catch(e){}try{for(const h of Zh)__setLT(h,0);}catch(e){}}''',
    '''f.castShadow=!0;f.shadow.needsUpdate=!0;}}catch(e){}try{for(const h of Zh)__setLT(h,0);}catch(e){}}''')

rep('B2_ax_deadbranch_castShadow',
    '''su[0].castShadow=!1;su[0].shadow.needsUpdate=!0;''',
    '''su[0].castShadow=!0;su[0].shadow.needsUpdate=!0;''')

# ---------------------------------------------------------------- C
# initLights(): 2048 is too heavy for 5 point lights; 1024 is the sweet spot.
rep('C1_init_mapSize',
    '''        e.castShadow = true; e.shadow.mapSize.set(2048, 2048);''',
    '''        e.castShadow = true; e.shadow.mapSize.set(1024, 1024);''')

# ---------------------------------------------------------------- D
# shadow-on-demand module: also refresh when fill-light pool / scene changes.
rep('D1_ondemand_dirty',
    '''          /* 兜底: 每 600ms 重绘一次, 覆盖家具/开关门/落地灯等非光源类变化; 漫游中场景静态, 已有整屋预渲染, 跳过 */
          if (!(m0 && re.active) && now - last > 600) { last = now; nu = true; }''',
    '''          /* 【接触阴影修复】补光灯的位置/强度变化时也要重绘阴影贴图,
             否则移动补光灯后阴影仍是旧的。 */
          try {
            var ps = su || [];
            for (var si = 0; si < ps.length; si++) {
              var L = ps[si], p = L.position;
              var sig = p.x + "," + p.y + "," + p.z + "," + L.intensity;
              if (L.__shSig !== sig) {
                if (L.__shSig !== undefined) nu = true;
                L.__shSig = sig;
                if (L.shadow) L.shadow.needsUpdate = true;
              }
            }
          } catch (e) { }
          /* 兜底: 每 600ms 重绘一次, 覆盖家具/开关门/落地灯等非光源类变化;
             漫游中场景静态, 但补光灯阴影仍需在进屋时刷新一次 */
          if (!(m0 && re.active) && now - last > 600) { last = now; nu = true; }
          else if ((m0 && re.active) && !window.__SHADOW_ONCE) {
            window.__SHADOW_ONCE = true; nu = true;
          }''')

P.write_text(t, encoding='utf-8')
print('bytes %d -> %d' % (orig, len(t)))
print('patched:', ', '.join(changed))
