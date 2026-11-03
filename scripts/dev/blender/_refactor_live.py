"""把 make_sofa_v18.py 的顶层建模代码，重构成【逐帧可执行】的步骤队列。

【为什么需要】
  旧结构：顶层顺序执行 + time.sleep() 停顿
  → 阻塞 Blender 主消息循环 → Windows 判定"未响应"、窗口灰掉、无法交互。
  新结构：每段建模代码包成一个函数，交给 live.run() 用 bpy.app.timers
  逐帧执行 → Blender 全程可交互，且能实时看到模型逐步长出来。

【转换规则】
  · 以 "# --- LIVE-STEPS-START ---" 开头、"# --- LIVE-STEPS-END ---" 结尾
    之间的顶层代码，按 live.step("...") 切成若干段；
  · 每段变成一个 def build_<n>_<slug>() 函数；
  · 原来跨段的全局变量（shell / seat_objs / backc_objs / arm_pad_objs ...）
    统一放进一个 namespace 字典，通过 ns['x'] 访问。
"""
import re
import io
import os
import sys

SRC = sys.argv[1]
DST = sys.argv[2]

src = open(SRC, encoding='utf-8').read()
START = "# --- LIVE-STEPS-START ---"
END = "# --- LIVE-STEPS-END ---"

i0 = src.index(START) + len(START)
i1 = src.index(END)
head = src[:i0]
body = src[i0:i1]
tail = src[i1 + len(END):]

# ---- 找出所有 live.step("...") 作为分段点 ----
STEP_RE = re.compile(r'^([ \t]*)live\.MARK\("([^"]+)"(.*?)\)\s*$', re.M)
marks = list(STEP_RE.finditer(body))
if not marks:
    print("no live.step found")
    sys.exit(1)

# 分段：每段 = 上一个 step 之后 到 当前 step 之前
segments = []
prev_end = 0
prev_label = "准备"
for m in marks:
    seg = body[prev_end:m.start()]
    segments.append((prev_label, seg))
    prev_label = m.group(2)
    prev_end = m.end()
segments.append((prev_label, body[prev_end:]))

# ---- 收集跨段使用的全局名 ----
ASSIGN_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*', re.M)
# 多目标赋值：a, b, c = f(...)  —— 也算共享变量
TUPLE_ASSIGN_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)+)\s*=\s*', re.M)
globals_used = set()
for _, seg in segments:
    for m in ASSIGN_RE.finditer(seg):
        globals_used.add(m.group(1))
    for m in TUPLE_ASSIGN_RE.finditer(seg):
        for nm in m.group(1).split(','):
            nm = nm.strip()
            if nm:
                globals_used.add(nm)
# 排除明显的局部/常量
ignore = {'os', 'sys', 'math', 'random', 'bpy', 'mathutils', 'B', 'SH',
          'live', 'PAL', 'ROLES', 'M_UP', 'M_UPDK', 'M_WELT', 'M_ALU',
          'M_THREAD'}
# objs 必须共享（各段都在往里 append），所以不排除它
shared = sorted(g for g in globals_used if g not in ignore)

out = io.StringIO()
out.write(head)
out.write("\n# =====================================================================\n")
out.write("# LIVE 步骤化：每段建模代码 = 一个函数，由 live.run() 逐帧执行\n")
out.write("# 跨段共享的变量放在 ns 字典里（避免闭包提前绑定问题）\n")
out.write("# =====================================================================\n")
out.write("NS = {}\n")
out.write("for _k in %r:\n    NS[_k] = None\n" % (shared,))
out.write("NS['objs'] = []          # 共享的对象列表，各段往里 append\n")
out.write("objs = NS['objs']\n\n")

slug_map = {}
for idx, (label, seg) in enumerate(segments):
    if not seg.strip():
        continue
    # 函数名
    slug = re.sub(r'[^0-9A-Za-z_]+', '_', label)[:28].strip('_')
    if not slug:
        slug = "step%d" % idx
    fn = "build_%02d_%s" % (idx, slug)
    slug_map[label] = fn

    # 把段内对 shared 名的赋值/引用改写为 NS['name']
    seg2 = seg
    # 先保护字符串字面量（避免把 'S_RIGHT' 这样的字符串内容也替换掉）
    literals = []

    def _stash(m):
        literals.append(m.group(0))
        return "\x00LIT%d\x00" % (len(literals) - 1)

    seg2 = re.sub(r'"[^"\n]*"|\'[^\'\n]*\'', _stash, seg2)
    for g in shared:
        if g == 'objs':
            # objs 是【共享的可变列表】：各段都往同一个列表 append，
            # 只要在函数内声明 global 即可，引用不用改写。
            continue
        seg2 = re.sub(r'(?<![\w\'\"])%s(?![\w\'\"])' % re.escape(g),
                      "NS['%s']" % g, seg2)
    # 修正：NS['NS'] 之类的嵌套
    seg2 = seg2.replace("NS['NS']", "NS")
    # 还原字符串字面量
    for i, lit in enumerate(literals):
        seg2 = seg2.replace("\x00LIT%d\x00" % i, lit)
    out.write("def %s():\n" % fn)
    out.write("    global objs\n")
    # 缩进 + 去掉 live.step 行
    lines = [l for l in seg2.split('\n')
             if not re.match(r'^\s*live\.MARK\(', l)]
    for l in lines:
        out.write(("    " + l).rstrip() + "\n")
    # 函数结束前，把本段新赋值的共享变量回写到 NS（跨段共享）
    out.write("    # --- 回写共享变量到 NS ---\n")
    for g in shared:
        if g == 'objs':
            continue
        out.write("    try:\n        NS['%s'] = %s\n    except NameError:\n        pass\n" % (g, g))
    out.write("\n\n")

# ---- 步骤清单 ----
out.write("STEPS = [\n")
for label, _ in segments:
    if label in slug_map:
        out.write("    (%r, %s),\n" % (label, slug_map[label]))
out.write("]\n\n")

out.write(tail)

# ---- 注入入口（转换后原文件里的入口会丢失，这里统一补上）----
if "live.run(STEPS)" not in out.getvalue():
    out.write("\n\n# =====================================================================\n")
    out.write("# 入口：把步骤队列交给 live.run()，由 bpy.app.timers 逐帧执行。\n")
    out.write("# Blender 主循环不阻塞 → 窗口全程可交互（不卡死、不\"未响应\"），\n")
    out.write("# 同时用户能实时看到模型一步步长出来。\n")
    out.write("# =====================================================================\n")
    out.write("live.run(STEPS)\n")
    out.write("print(\"[LIVE] queued %d steps\" % len(STEPS))\n")

open(DST, 'w', encoding='utf-8').write(out.getvalue())
print("wrote", DST, "steps:", len(slug_map))
for label, fn in slug_map.items():
    print("  ", fn, "<-", label)
