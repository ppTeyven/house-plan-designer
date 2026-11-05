"""多源现成资源获取器（3d.shep.bot 聚合 API）。

【为什么是它】
3d.shep.bot 一个接口聚合 PolyHaven / Kenney / Quaternius / BlenderKit /
Sketchfab / ShareTextures / 3DAssets / PolyFork / Grab3D 等多家源，
统一返回：
  · license{name, commercialUse, attributionRequired}
  · price{free}
  · downloadable（能否直下）
  · formats / resolutions / polyCount
并提供 GET /v1/assets/{id}/download 直链（单文件 302，多文件打包 zip）。

【为什么不能只靠 Poly Haven】
实测 Poly Haven 521 个模型只能覆盖目录 158 个 type 中的 62 个：
卫浴（马桶/浴缸/淋浴）、厨电（冰箱/洗碗机）、软装（地毯/窗帘）、
建筑构件（地板/墙/门）基本缺失。多源才能补齐。

【硬性纪律】
  ① 只接受 price.free == true 且 downloadable == true
  ② license.commercialUse != false
  ③ 每个资产记录 provider/nativeId/license/source-url（可追溯、可回溯）
  ④ 下载后一律走 Blender 侧【尺寸校验 + 统一重着色 + 落地导出】

用法：
  python fetch_multi.py --search "curtain,rug,toilet" --list
  python fetch_multi.py --download-id "threedassets:cozy-home-interiors-toilet-a3169629"
"""
import argparse
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RAW = os.path.join(ROOT, "assets", "external", "raw")
UA = "HousePlannerAssetFetcher/1.0"
BASE = "https://3d.shep.bot/v1"


def _get_json(url, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _get_json_retry(url, timeout=90, retries=5, base_delay=1.6):
    """带指数退避的 JSON 请求。

    【为什么必须加重试】
    聚合 API 3d.shep.bot 在高频并发下会持续返回 503
    （实测 12 线程连打 ~250 个查询词，约 1/4 的请求直接 503 失败）。
    裸重试不够，必须指数退避 + 抖动，否则重试仍然撞在同一波限流上。
    """
    import random
    last = None
    for i in range(retries):
        try:
            return _get_json(url, timeout=timeout)
        except urllib.error.HTTPError as e:
            last = e
            # 4xx（除 429）不是限流，重试无意义
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except Exception as e:
            last = e
        delay = base_delay * (2 ** i) + random.uniform(0, 0.8)
        time.sleep(delay)
    raise last if last else RuntimeError("request failed: %s" % url)


def _download(url, dest, timeout=900):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as f:
        while True:
            c = r.read(1 << 16)
            if not c:
                break
            f.write(c)
    os.replace(tmp, dest)
    return os.path.getsize(dest)


# --------------------------------------------------------------------
def search(q, kind="model", limit=30, free_only=True):
    params = {"q": q, "type": kind, "limit": str(limit)}
    if free_only:
        params["free"] = "true"
    url = "%s/search?%s" % (BASE, urllib.parse.urlencode(params))
    try:
        r = _get_json_retry(url)
    except Exception as e:
        print("  [search fail] %s: %s" % (q, e))
        return []
    res = r.get("results") or r.get("items") or []
    out = []
    for it in res:
        lic = it.get("license") or {}
        price = it.get("price") or {}
        if not it.get("downloadable"):
            continue
        if free_only and not price.get("free", False):
            continue
        if lic.get("commercialUse") is False:
            continue
        out.append({
            "id": it.get("id"),
            "provider": it.get("provider"),
            "nativeId": it.get("nativeId"),
            "title": it.get("title"),
            "url": it.get("url"),
            "license": lic.get("name"),
            "commercialUse": lic.get("commercialUse"),
            "formats": it.get("formats") or [],
            "polyCount": it.get("polyCount"),
            "tags": it.get("tags") or [],
        })
    return out


def asset_detail(aid):
    url = "%s/assets/%s" % (BASE, urllib.parse.quote(aid, safe=""))
    try:
        return _get_json_retry(url)
    except Exception:
        return None


def download_asset(aid, fmt="glb", resolution="2k", dest_root=None):
    """下载资产到本地目录，返回 (dir, files[]) 或 (None, reason)。

    优先走 files[] 里的直链（更可控），拿不到再退回 /download 端点。
    """
    dest_root = dest_root or os.path.join(RAW, aid.replace(":", "__"))
    d = asset_detail(aid)
    if not d:
        return None, "no_detail"

    files = d.get("files") or []
    picked = []
    for f in files:
        if f.get("requiresAuth"):
            continue
        if f.get("format") == fmt:
            picked.append(f)
    if not picked:
        # 退化：接受 gltf / blend / fbx 里的任意一种（后续用 Blender 导入）
        for alt in ("gltf", "glb", "blend", "fbx", "obj", "usd"):
            picked = [f for f in files if f.get("format") == alt
                      and not f.get("requiresAuth")]
            if picked:
                fmt = alt
                break
    if not picked:
        return None, "no_file:%s" % ",".join(
            sorted({f.get("format", "?") for f in files}))

    os.makedirs(dest_root, exist_ok=True)
    got = []
    for f in picked:
        url = f.get("url")
        if not url:
            continue
        fn = f.get("filename") or os.path.basename(
            urllib.parse.urlparse(url).path) or "asset.bin"
        dest = os.path.join(dest_root, fn)
        try:
            if os.path.exists(dest) and os.path.getsize(dest) == f.get("sizeBytes", -1):
                got.append(dest)
                continue
            _download(url, dest)
            got.append(dest)
        except Exception as e:
            print("    [dl fail] %s: %s" % (fn, e))

    # .gltf 需要配套 .bin / 贴图
    for f in files:
        inc = f.get("includes") or []
        for c in inc:
            if c.get("requiresAuth"):
                continue
            cu, cf = c.get("url"), c.get("filename")
            if not cu or not cf:
                continue
            dest = os.path.join(dest_root, cf)
            if os.path.exists(dest):
                continue
            try:
                _download(cu, dest)
                got.append(dest)
            except Exception as e:
                print("    [inc fail] %s: %s" % (cf, e))

    if not got:
        return None, "download_failed"
    return dest_root, got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", default="")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--download-id", default="")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.download_id:
        d, files = download_asset(args.download_id, dest_root=args.out)
        if d is None:
            print("FAIL:", files)
            return
        print("OK", d)
        for f in files:
            print("   ", f)
        return

    if not args.search:
        ap.print_help()
        return

    queries = [q.strip() for q in args.search.split(",") if q.strip()]
    bundle = {}
    for q in queries:
        res = search(q)
        bundle[q] = res
        print("\n=== %s === (%d)" % (q, len(res)))
        for r in res[:10]:
            print("  [%-13s] %-48s %-14s %s"
                  % (r["provider"], (r["title"] or "")[:48],
                     r["license"], ",".join(r["formats"])[:24]))

    if args.list:
        out = os.path.join(ROOT, "assets", "external", "multi_search.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, indent=1)
        print("\n->", out)


if __name__ == "__main__":
    main()
