"""实时可视化 —— 让建模过程可被【实时观测】，且 Blender 窗口全程不卡死。

【需求】
  用户要求："我需要能实时观测你建模的过程，你看到的我也要看到"

【踩坑 · v18 首版】
  用 time.sleep() 做阶段停顿 → 【阻塞 Blender 的主消息循环】→
  Windows 判定"未响应"，窗口变灰、无法交互、脚本还得等。
  根因：Blender 的 UI 与脚本跑在同一个线程里，sleep 期间没人处理窗口消息。

【正确做法 · bpy.app.timers】
  Blender 4.x 提供 bpy.app.timers.register()：注册一个回调，
  Blender 会在【空闲时】调用它。用它把"建模步骤"拆成若干帧：
    · 每帧只做一小步建模
    · 帧与帧之间 Blender 照常处理 UI（重绘、鼠标、快捷键）
  → 窗口全程可交互，实时看到模型一点点长出来。

【架构】
  build.py 里不用改结构，只需把建模过程包成：
      live.run(steps)
  其中 steps 是 [(标签, 函数), ...]，每帧执行一个函数。
  若某个函数返回剩余待执行列表，则继续拆分（支持一步内再分帧）。
"""
import bpy
import math
import os
import mathutils

# ---- 全局状态 ----
_queue = []          # 待执行的 [(label, fn), ...]
_running = False
_frame = 0
_total = 0
_pause_frames = 0    # 每步之间额外停留的帧数
_on_done = None


def _redraw():
    for area in getattr(bpy.context.screen, 'areas', []):
        try:
            area.tag_redraw()
        except Exception:
            pass


def _setup_world():
    """工作环境：三点布光 + 环境光（视口用 MATERIAL 预览时需要真实灯光）

    【为什么不用默认 HDRI】
    默认 HDRI 的方向不可控 —— 实时建模时经常出现整片背光，
    模型看起来一片黑，几何完全看不清（实测 v18 多次误判）。
    这里用【可控的三点光】：主光 + 补光 + 轮廓光 + 柔和环境光，
    保证任何角度都能看清形体，且与 render_preview.py 的布光思路一致。
    """
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("live_world")
        bpy.context.scene.world = world
    world.use_nodes = True
    try:
        bg = world.node_tree.nodes.get("Background")
        bg.inputs[0].default_value = (0.16, 0.17, 0.19, 1.0)
        bg.inputs[1].default_value = 1.0
    except Exception:
        pass

    if "live_key" in bpy.data.objects:
        return

    def _area(name, loc, rot, size, energy, color=(1, 1, 1), aim=None):
        ld = bpy.data.lights.new(name, type='AREA')
        ld.shape = 'RECTANGLE'
        ld.size = size[0]
        ld.size_y = size[1]
        ld.energy = energy
        ld.color = color
        ob = bpy.data.objects.new(name, ld)
        bpy.context.collection.objects.link(ob)
        ob.location = loc
        if aim is not None:
            # 【关键】面光默认沿【自身 -Z】照射。手写 rotation_euler 极难
            # 算对（实测 v18 多次把灯照向别处 → 部件全在背光里 →
            # 渲染图上"部件消失"，被误判成几何/法线问题，白查半天）。
            # 现在统一用 to_track_quat 让灯【明确指向目标】。
            d = mathutils.Vector(aim) - mathutils.Vector(loc)
            ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        else:
            ob.rotation_euler = rot
        return ob

    aim = (0.0, 0.0, 0.45)
    # 主光：右前上方，柔和大面光
    _area("live_key", (2.8, 2.6, 3.2), None, (3.4, 2.6), 1400.0,
          (1.0, 0.98, 0.95), aim)
    # 补光：左前方弱一点，压暗部
    _area("live_fill", (-3.0, 2.2, 1.8), None, (3.2, 2.8), 520.0,
          (0.92, 0.95, 1.0), aim)
    # 轮廓光：后上方，勾出软包边缘
    _area("live_rim", (-1.4, -3.2, 2.8), None, (2.6, 2.2), 700.0,
          (1.0, 0.96, 0.90), aim)


def _bbox():
    import mathutils
    lo = mathutils.Vector((1e9, 1e9, 1e9))
    hi = mathutils.Vector((-1e9, -1e9, -1e9))
    found = False
    for o in bpy.context.scene.objects:
        if o.type not in ('MESH', 'CURVE'):
            continue
        if o.name in ('live_cam', 'live_key', 'live_fill'):
            continue
        try:
            ws = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        except Exception:
            continue
        if not ws:
            continue
        found = True
        for w in ws:
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    if not found:
        return None
    return lo, hi


def _frame_camera():
    """按当前包围盒自动取景 —— 模型在长大，固定机位会跑出画面"""
    import mathutils
    bb = _bbox()
    if bb is None:
        return
    lo, hi = bb
    cam = bpy.data.objects.get('live_cam')
    if cam is None:
        cd = bpy.data.cameras.new("live_cam")
        cd.lens = 50
        cam = bpy.data.objects.new("live_cam", cd)
        bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    center = (lo + hi) * 0.5
    radius = max(0.3, (hi - lo).length * 0.5)
    direction = mathutils.Vector((1.0, 1.30, 0.72)).normalized()
    dist = radius / math.tan(cam.data.angle * 0.5) * 1.15
    cam.location = center + direction * dist
    cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()


def _setup_view(do_frame=False, focus=None):
    """视口：3/4 视角 + 实体着色（材质色）

    【实测踩坑】用 bpy.ops.view3d.view_camera() + region_3d.view_perspective
    切相机视角，在实时建模里不可靠 —— 视口经常停在自由视角，
    看到的是模型背面（沙发正面是 +Y，模型背板在 -Y），
    表现为一整块深色，看不出任何形体（v18 实测）。
    改用【确定性的 view_axis + view_orbit】：
      view_axis(type='FRONT')  → 再绕 Z 转 -55° → 再俯视 26°
    这样每个模型都以固定的 3/4 视角呈现，不会跑到画面外。

    do_frame：是否重新取景。view_all() 会把灯光/相机也算进包围盒，
    所以只在最初几步调用，之后模型长大时靠用户视角保持不变。
    """
    try:
        win = bpy.context.window
    except Exception:
        return
    if win is None:
        return
    for area in win.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        sp = area.spaces.active
        # 【v18 决策】用 MATERIAL 预览着色 —— 与最终渲染完全一致。
        # 用户要求"你看到的我也要看到"，若视口用 SOLID 而我给渲染图，
        # 两边观感不一致会误导判断。
        # 代价：MATERIAL 预览比 SOLID 慢，但模型只有 52 个对象，实测流畅。
        sp.shading.type = 'MATERIAL'
        sp.shading.use_scene_lights = True
        sp.shading.use_scene_world = True
        sp.shading.studio_light = 'Default'
        sp.shading.show_shadows = True
        sp.shading.show_cavity = False
        sp.shading.background_type = 'VIEWPORT'
        sp.shading.background_color = (0.06, 0.065, 0.075)
        sp.overlay.show_overlays = False

        # ---- 【v23】跟随取景：对准当前正在建模的部位 ----
        # 用户要求："你得时刻把你正在操作的位置放大展示给我看，
        #            但是也别让整个物件的大小超过窗口"。
        if focus is not None:
            _focus_view(sp, focus[0], focus[1])
            break

        if not do_frame:
            break
        sp.region_3d.view_perspective = 'PERSP'
        for region in area.regions:
            if region.type == 'WINDOW':
                with bpy.context.temp_override(window=win, area=area,
                                             region=region):
                    try:
                        # 从【正前方 +Y】看（沙发正面），再绕 Z 转 -55°
                        # → 得到标准的右前 3/4 视角
                        bpy.ops.view3d.view_axis(type='FRONT')
                        # view_orbit 的 type 是方向枚举，不是轴名
                        bpy.ops.view3d.view_orbit(
                            angle=math.radians(-55.0), type='ORBITRIGHT')
                        bpy.ops.view3d.view_orbit(
                            angle=math.radians(26.0), type='ORBITDOWN')
                        bpy.ops.view3d.view_all()
                    except Exception as e:
                        print("[LIVE] view set warn:", e)
                break
        break


# =====================================================================
# 【v23】跟随取景 —— 始终对准当前正在建模的部位
# =====================================================================
# 用户要求：
#   "你得时刻把你正在操作的位置放大展示给我看，
#    但是也别让整个物件的大小超过窗口"
#
# 做法：
#   ① 每步建模后，检测【本步新建的对象】（名字在 step 前后的差集里）
#   ② 算它的包围盒中心与半径
#   ③ 相机对准该中心，距离取【刚好框住这个部位】的距离
#      —— 不是框住整个家具，这样"看细节"而不是"看全貌"
#
# 距离公式（球半径 r，视距 d，占画面高度比例 p）：
#     asin(r/d) = fov_v/2 * p   →   d = r / sin(fov_v/2 * p)
# p = 0.42 → 部位占画面 ~84% 高度，不会超出窗口。
_view_state = {'dist': None, 'known': set()}


def _focus_view(sp, center, radius):
    """相机对准 center，距离刚好框住半径 radius。"""
    import math
    import mathutils

    r3d = sp.region_3d
    if r3d is None:
        return
    try:
        lens = sp.lens if hasattr(sp, 'lens') else 50.0
        sensor = sp.sensor_height if hasattr(sp, 'sensor_height') else 24.0
        fov_v = 2.0 * math.atan(sensor / (2.0 * lens))
    except Exception:
        fov_v = math.radians(39.6)

    p = 0.42
    d = radius / max(math.sin(fov_v * 0.5 * p), 1e-3)
    d = max(d, 0.10)

    dirv = mathutils.Vector((0.72, 0.46, 1.0)).normalized()
    target = mathutils.Vector(center)

    # 平滑跟随（每帧走 30%），避免视角跳变看晕
    k = 0.30
    if _view_state['dist'] is None:
        _view_state['dist'] = d
    else:
        _view_state['dist'] = _view_state['dist'] * (1 - k) + d * k

    r3d.view_location = target
    r3d.view_distance = _view_state['dist']
    r3d.view_rotation = dirv.to_track_quat('Z', 'Y')
    r3d.view_perspective = 'PERSP'
    try:
        r3d.update()
    except Exception:
        pass


def _new_objects_focus():
    """返回本步新建对象的 (中心, 半径)；没有则返回 None。

    判定方式：与上一步的已知对象集合做差集。
    """
    try:
        objs = set(o.name for o in bpy.context.scene.objects
                   if o.type in ('MESH', 'CURVE'))
    except Exception:
        return None
    new = objs - _view_state['known']
    _view_state['known'] = objs
    if not new:
        return None

    import mathutils
    mn = mathutils.Vector((1e9, 1e9, 1e9))
    mx = mathutils.Vector((-1e9, -1e9, -1e9))
    any_vert = False
    for o in bpy.context.scene.objects:
        if o.name not in new:
            continue
        try:
            bb = o.bound_box
        except Exception:
            continue
        for c in bb:
            w = o.matrix_world @ mathutils.Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
            any_vert = True
    if not any_vert:
        return None
    ctr = (mn + mx) * 0.5
    radius = max((mx - mn).length * 0.5, 0.03)
    return (ctr, radius)


def _tick():
    """定时器回调：执行一个建模步骤，然后返回下次调用间隔（秒）"""
    global _queue, _running, _frame, _total, _pause_frames, _on_done

    if _pause_frames > 0:
        _pause_frames -= 1
        _redraw()
        return 0.06          # 60fps 空转，让 UI 保持响应

    if not _queue:
        _running = False
        print("[LIVE] ===== done =====")
        if _on_done:
            try:
                _on_done()
            except Exception as e:
                print("[LIVE] on_done error:", e)
        return None            # 注销定时器

    label, fn = _queue.pop(0)
    _frame += 1
    try:
        fn()
    except Exception as e:
        import traceback
        print("[LIVE] step '%s' ERROR: %s" % (label, e))
        traceback.print_exc()
    try:
        bpy.context.view_layer.update()
        # 【v23】跟随取景：优先对准本步新建的部位
        focus = _new_objects_focus()
        if focus is not None:
            _setup_view(do_frame=False, focus=focus)
        else:
            _setup_view(do_frame=(_frame <= 3))
    except Exception:
        pass
    print("[LIVE] %2d/%-2d  %s" % (_frame, _total, label))
    _redraw()
    _pause_frames = int(PENDING_PAUSE / 0.06)
    return 0.02


# 每步之间停留秒数（可被环境变量覆盖）
import os
PENDING_PAUSE = float(os.environ.get("BL_LIVE_PAUSE", "1.0"))


def MARK(label):
    """仅作【分段标记】，供 _refactor_live.py 识别并切成步骤。

    实际的"实时可视化"由 make_sofa_v18_live.py（转换产物）用
    bpy.app.timers 逐帧执行；本文件（同步版）里它什么都不做，
    以便同一份几何代码既能后台跑、也能实时跑。
    """
    print("[MARK]", label)


def run(steps, on_done=None):
    """把建模步骤排入逐帧执行队列。

    steps : [(label, fn), ...]
    """
    global _queue, _running, _total, _on_done, _pause_frames
    if bpy.app.background:
        # 后台模式：直接同步跑完（没有 UI 可交互）
        for label, fn in steps:
            fn()
            print("[LIVE] (bg)", label)
        if on_done:
            on_done()
        return
    _queue = list(steps)
    _total = len(_queue)
    _pause_frames = 0
    _on_done = on_done
    _running = True
    _setup_world()
    _setup_view()
    bpy.app.timers.register(_tick, first_interval=0.05)


def run_sync(steps, on_done=None):
    """同步执行（不使用定时器）—— 供后台模式或最终导出阶段使用"""
    for label, fn in steps:
        fn()
        print("[LIVE]", label)
    if on_done:
        on_done()
