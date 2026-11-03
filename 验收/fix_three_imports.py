"""修正 vendor 里 three examples 模块的裸模块导入（'three' → 相对路径）。
浏览器无法解析裸模块名 'three'，必须改成相对路径。
用法: python fix_three_imports.py <vendor_dir> <utils_dir>
"""
import os, re, sys

vendor = sys.argv[1] if len(sys.argv) > 1 else "vendor"
utils = sys.argv[2] if len(sys.argv) > 2 else "utils"

for f in os.listdir(vendor):
    if not f.endswith(".js"):
        continue
    p = os.path.join(vendor, f)
    s = open(p, encoding="utf-8").read()
    n0 = len(re.findall(r"from\s*['\"]three['\"]", s))
    s2 = re.sub(r"(from\s*['\"])three(['\"])", r"\1./three.module.js\2", s)
    n1 = len(re.findall(r"from\s*['\"]three['\"]", s2))
    if n0:
        open(p, "w", encoding="utf-8").write(s2)
    print(f"{p}: bare-three {n0} -> {n1}")

if os.path.isdir(utils):
    for f in os.listdir(utils):
        if not f.endswith(".js"):
            continue
        p = os.path.join(utils, f)
        s = open(p, encoding="utf-8").read()
        n0 = len(re.findall(r"from\s*['\"]three['\"]", s))
        s2 = re.sub(r"(from\s*['\"])three(['\"])", r"\1../vendor/three.module.js\2", s)
        n1 = len(re.findall(r"from\s*['\"]three['\"]", s2))
        if n0:
            open(p, "w", encoding="utf-8").write(s2)
        print(f"{p}: bare-three {n0} -> {n1}")