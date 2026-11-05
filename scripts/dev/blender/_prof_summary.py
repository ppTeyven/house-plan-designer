# -*- coding: utf-8 -*-
"""Summarize a CDP .cpuprofile: top self-time functions."""
import json, sys
from collections import defaultdict

path = sys.argv[1]
data = json.load(open(path, 'r', encoding='utf-8'))
if 'profile' in data:
    data = data['profile']
nodes = {n['id']: n for n in data['nodes']}
# self time from samples/timeDeltas
samples = data.get('samples', [])
deltas = data.get('timeDeltas', [])
self_us = defaultdict(float)
for i, sid in enumerate(samples):
    d = deltas[i] if i < len(deltas) else 0
    self_us[sid] += max(0, d)

agg = defaultdict(float)
for sid, us in self_us.items():
    n = nodes.get(sid)
    if not n:
        continue
    cf = n['callFrame']
    name = cf.get('functionName') or '(anonymous)'
    url = (cf.get('url') or '').split('/')[-1]
    line = cf.get('lineNumber', -1) + 1
    agg[f"{name}  @{url}:{line}"] += us

total = sum(agg.values()) or 1
print(f"total sampled: {total/1000:.1f} ms")
for k, v in sorted(agg.items(), key=lambda kv: -kv[1])[:25]:
    print(f"{v/1000:9.2f} ms  {100*v/total:5.1f}%  {k}")
