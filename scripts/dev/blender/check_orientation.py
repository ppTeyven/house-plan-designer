"""源码级判定 geo builder 的"靠背/床头"朝向。

【主程序约定 -Z】assets/template.html 的 kv()：
    3D 位置 l.position.set(r.x/1e3, c/1e3, r.y/1e3)
      ⇒ 2D 平面图的 -Y（图纸上方）= 3D 的 -Z
    2D 床: 床头条 l(-o,-a,i,100,...) 在 -a 侧（图纸上方）
    3D 床: N(t,i+.04,p,.05,0,0,-l+.025,d) → 床头板 z=-l
    ⇒ 床头/靠背/背板/柜门 统一在 -Z，正面朝 +Z

【做法】扫描每个 builder 源码：
    找到含语义词的注释行 → 取其后最近的 add_box 的 center 的 z 分量 → 判符号
    z 分量表达式归一化后判断它是 "+d/2 系" 还是 "-d/2 系"
"""
import io
import os
import re

BL = os.path.dirname(os.path.abspath(__file__))
FILES = ['geo_models.py', 'geo_models_free.py', 'geo_models_extra.py',
         'geo_models_extra2.py', 'geo_models_extra3.py', 'geo_models_extra4.py']

# 语义词 → 应在的侧（-1 = -Z）
PART_Z = {
    '床头板': -1, '床头': -1, '靠背': -1, '背板': -1, '柜门': -1,
    '枕头': -1, '靠背板': -1, '柜体背板': -1,
}


def split_args(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def z_sign(expr):
    """center 的 z 分量靠近 +d/2 还是 -d/2。"""
    e = expr.replace(' ', '').replace('M(', 'M')
    e = e.replace('M(d)/2', 'H').replace('d/2', 'H')
    e = e.replace('M(d)', 'D').replace('d', 'D')
    m = re.search(r'H', e)
    if not m:
        return None
    prefix = e[:m.start()]
    ops = list(re.finditer(r'[-+]', prefix))
    if not ops:
        return None
    return -1 if ops[-1].group(0) == '-' else 1


def find_center_z(lines, i, limit=12):
    """从第 i 行起找下一个 add_box 的 center z 分量。"""
    for j in range(i, min(len(lines), i + limit)):
        if 'add_box' not in lines[j]:
            continue
        text = '\n'.join(lines[j:j + 10])
        m = re.search(r'add_box\s*\(', text)
        if not m:
            continue
        k, depth = m.end() - 1, 0
        st = k
        while k < len(text):
            if text[k] == '(':
                depth += 1
            elif text[k] == ')':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        args = split_args(text[st + 1:k])
        ctr = None
        for a in args:
            if a.startswith('center='):
                ctr = a.split('=', 1)[1]
        if ctr is None and len(args) >= 3:
            ctr = args[2]
        if ctr is None:
            continue
        cp = split_args(ctr.strip('()'))
        if len(cp) < 3:
            continue
        return cp[2].strip(), j
    return None, None


def main():
    print('=== 源码级朝向判定：靠背/床头 应在 -Z ===\n')
    rows = []
    for f in FILES:
        p = os.path.join(BL, f)
        if not os.path.exists(p):
            continue
        s = io.open(p, encoding='utf-8').read()
        for fm in re.finditer(r'def (build_\w+)\(', s):
            st = fm.start()
            nxt = s.find('\ndef ', st + 1)
            body = s[st:nxt if nxt > 0 else st + 5000]
            lines = body.split('\n')
            for i, ln in enumerate(lines):
                # 只认行内注释（# 开头）或含语义词的注释
                part = None
                for k in PART_Z:
                    if k in ln:
                        part = k
                        break
                if not part:
                    continue
                # 注释行本身要包含关键词
                zexpr, j = find_center_z(lines, i + 1)
                if zexpr is None:
                    continue
                sg = z_sign(zexpr)
                if sg is None:
                    continue
                rows.append((f, fm.group(1), part, sg, zexpr, i))
                break     # 每个 builder 只取第一处语义部件

    flip, ok = [], []
    for f, fn, part, sg, z, i in rows:
        want = PART_Z[part]
        good = (sg == want)
        (ok if good else flip).append((f, fn, part, z))
        print('  %s %-24s %-8s %sZ (应 %sZ)  z=%s'
              % ('OK ' if good else '反了', fn, part,
                 '+' if sg > 0 else '-', '+' if want > 0 else '-', z[:44]))

    print()
    print('需翻转 %d 个 / 共检测 %d 个' % (len(flip), len(rows)))
    print()
    for f, fn, part, z in flip:
        print('   %-22s %-24s %-8s z=%s' % (f, fn, part, z[:44]))
    return 2 if flip else 0


if __name__ == '__main__':
    raise SystemExit(main())
