"""解析 CDP CPU profile，输出 self time 占比 Top-N 函数。

用途：定位"帧数降低"的真正 CPU 瓶颈（不是 GPU）。
"""
import collections
import io
import json
import sys

path = sys.argv[1]
top = int(sys.argv[2]) if len(sys.argv) > 2 else 30

d = json.load(io.open(path, encoding='utf-8'))
if 'profile' in d:
    d = d['profile']
nodes = {n['id']: n for n in d['nodes']}
samples = d.get('samples', [])
deltas = d.get('timeDeltas', [])

self_us = collections.Counter()
for i, sid in enumerate(samples):
    dt = deltas[i] if i < len(deltas) else 0
    self_us[sid] += max(0, dt)

total = sum(self_us.values()) or 1

# 把 id 归并到 (functionName, url:line)
agg = collections.Counter()
for nid, us in self_us.items():
    n = nodes.get(nid)
    if not n:
        continue
    cf = n.get('callFrame', {})
    fn = cf.get('functionName') or '(anonymous)'
    url = cf.get('url') or ''
    line = cf.get('lineNumber', -1)
    short = url.split('/')[-1].split('?')[0] if url else 'native'
    agg['%s @%s:%s' % (fn, short, line + 1)] += us

print('采样总时长: %.1f ms' % (total / 1000))
print('样本数: %d' % len(samples))
print()
print('%-58s %8s %7s' % ('function', 'self ms', 'share'))
print('-' * 78)
for k, v in agg.most_common(top):
    print('%-58s %8.1f %6.1f%%' % (k[:58], v / 1000, 100 * v / total))
