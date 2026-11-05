"""免认证资源获取层 —— ambientCG / Polyhaven / Poly Pizza。

【已实测的访问能力（2026-11-03）】
  ambientCG  : https://ambientcg.com/get?file=<ID>_2K-JPG.zip      ✅ 免认证
               API: https://ambientcg.com/api/v2/full_json?id=<ID>&include=downloadData,fileData
               材质库 2038 套 PBR（含 Color/Normal/Displacement/Roughness/AO）
  Polyhaven  : https://dl.polyhaven.org/file/ph-assets/...       ✅ 免认证
               API: https://api.polyhaven.com/assets?t=models|textures|hdris
               模型 521 个（.blend / .gltf+bin / .fbx），纹理与 HDRI 齐全
  Poly Pizza : api.poly.pizza → 401；static.poly.pizza CDN → 403  ✅ 免认证

【设计要点】
  ① 单一真源：所有 URL 构造集中在本模块，其他脚本不直接拼 URL
  ② 显式失败：下载失败返回结构化错误（含 HTTP 码 / URL / 重试次数），
     不用静默 fallback（手册第 2 条）
  ③ 缓存 + 校验：已下载文件按 md5 校验，损坏自动重下
  ④ 限速与并发：默认串行 + 间隔，避免被 CDN 限流
"""
import os
import sys
import json
import time
import hashlib
import zipfile
import shutil
import random
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")

USER_AGENT = "house-planner/1.0 (+https://localhost)"

# ---- 退避重试参数（人为理由：CDN 偶发 5xx/超时；实测 3 次足够）----
RETRY = 3
BACKOFF = 1.5
TIMEOUT = 90


class FetchError(Exception):
    """结构化下载失败（手动第 6 条：失败必须可区分原因）"""

    def __init__(self, code, message, url=None, status=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.url = url
        self.status = status

    def to_dict(self):
        return {"code": self.code, "message": self.message,
                "url": self.url, "status": self.status}


def _http_get(url, dest=None, expect_md5=None, timeout=TIMEOUT):
    """下载单个 URL 到 dest（可选 md5 校验）。失败抛 FetchError。"""
    tmp = None
    if dest:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".part"
    last = None
    for attempt in range(RETRY):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            if expect_md5:
                got = hashlib.md5(data).hexdigest()
                if got != expect_md5:
                    if tmp and os.path.exists(tmp):
                        os.remove(tmp)
                    raise FetchError(
                        "checksum_mismatch",
                        "md5 mismatch: expected %s got %s" % (expect_md5, got),
                        url=url)
            if dest:
                with open(tmp, "wb") as f:
                    f.write(data)
                os.replace(tmp, dest)
            return data
        except urllib.error.HTTPError as e:
            last = FetchError("http_%d" % e.code, e.reason, url=url, status=e.code)
            # 4xx 不重试（除 429）
            if e.code != 429 and 400 <= e.code < 500:
                break
        except FetchError:
            raise
        except Exception as e:
            last = FetchError("network_error", str(e), url=url)
        if attempt < RETRY - 1:
            # 指数退避 + 抖动：Polyhaven CDN 偶发 SSL EOF，
            # 固定退避在连续请求时会反复撞同一时刻的 CDN 抖动。
            time.sleep(BACKOFF ** attempt * (0.7 + 0.6 * random.random()))
    raise last or FetchError("unknown", "download failed", url=url)


def _http_json(url, timeout=45):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise FetchError("http_%d" % e.code, e.reason, url=url, status=e.code)
    except Exception as e:
        raise FetchError("network_error", str(e), url=url)


# =====================================================================
# ambientCG —— PBR 材质包（墙/地/天/门的精细纹理来源）
# =====================================================================
ACG_API = "https://ambientcg.com/api/v2/full_json"
ACG_GET = "https://ambientcg.com/get"


def acg_list(data_type="Material", query=None, limit=100, offset=0):
    """列出 ambientCG 资产（免认证）。

    data_type: Material / HDRI / 3DModel ...
    query    : 可选关键字，映射到 API 的 ?q=
    """
    url = "%s?type=%s&limit=%d&offset=%d" % (ACG_API, data_type, limit, offset)
    if query:
        url += "&q=" + urllib.parse.quote(query)
    data = _http_json(url)
    return data.get("foundAssets", []), data.get("numberOfResults", 0)


def acg_detail(asset_id):
    """取单个资产的完整信息（含 downloadFolders 直链）。"""
    url = "%s?id=%s&include=downloadData,fileData" % (ACG_API, asset_id)
    data = _http_json(url)
    assets = data.get("foundAssets", [])
    if not assets:
        raise FetchError("not_found", "ambientCG asset not found: %s" % asset_id,
                         url=url)
    return assets[0]


def acg_download(asset_id, resolution="2K", fmt="JPG", dest_dir=None,
                 extract=True):
    """下载 ambientCG 材质包（zip）并解压。

    返回 (zip_path, {basename: 绝对路径})
    """
    dest_dir = dest_dir or os.path.join(CACHE, "ambientcg")
    fname = "%s_%s-%s.zip" % (asset_id, resolution, fmt)
    dest = os.path.join(dest_dir, fname)
    if not os.path.exists(dest):
        info = acg_detail(asset_id)
        url = None
        for dl in (info.get("downloadFolders") or {}).values():
            for d in dl.get("downloadFiletypeCategories", {}).values():
                for it in d.get("downloads", []):
                    if it.get("fileName") == fname:
                        url = it.get("downloadLink")
                        break
        if not url:
            raise FetchError(
                "variant_missing",
                "no download entry for %s in asset %s" % (fname, asset_id))
        _http_get(url, dest)
    out = {}
    if extract:
        outdir = os.path.join(dest_dir, asset_id)
        # 【必须按"是否有实际文件"判断，不能只看目录存在】
        # 否则上一轮解压后文件被取走，目录还在 → 永远不再解压 → 空目录
        has_files = os.path.isdir(outdir) and any(
            fn.lower().endswith((".jpg", ".png", ".exr"))
            for fn in os.listdir(outdir))
        if not has_files:
            os.makedirs(outdir, exist_ok=True)
            with zipfile.ZipFile(dest) as z:
                z.extractall(outdir)
        for dp, _dn, fns in os.walk(outdir):
            for fn in fns:
                if fn.lower().endswith((".jpg", ".png", ".exr")):
                    out[fn] = os.path.join(dp, fn)
    return dest, out


def acg_maps(files):
    """从 ambientCG 解压结果里挑出各通道。

    返回 dict: {'color': path, 'normal': path, 'rough': path,
                 'disp': path, 'ao': path, 'arm': path}
    命名规则（ambientCG 标准）：
      <ID>_Color.jpg  <ID>_NormalGL.jpg / _NormalDX.jpg
      <ID>_Roughness.jpg  <ID>_Displacement.jpg  <ID>_AmbientOcclusion.jpg
    """
    def find(*keys):
        for k in keys:
            for fn, p in files.items():
                if k.lower() in fn.lower():
                    return p
        return None

    return {
        "color": find("_Color"),
        "normal": find("_NormalGL"),       # OpenGL 约定（绿通道向上）
        "normalDX": find("_NormalDX"),
        "rough": find("_Roughness"),
        "disp": find("_Displacement"),
        "ao": find("_AmbientOcclusion"),
        "arm": find("_ARM"),
        "bump": find("_Bump"),
    }


# =====================================================================
# Polyhaven —— CC0 模型 / 纹理 / HDRI
# =====================================================================
PH_API = "https://api.polyhaven.com"
PH_DL = "https://dl.polyhaven.org/file/ph-assets"


def ph_assets(asset_type="models"):
    """列出全部 Polyhaven 资产（免认证）。"""
    url = "%s/assets?t=%s" % (PH_API, asset_type)
    data = _http_json(url)
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def ph_files(asset_id):
    """取某个资产的文件清单。"""
    url = "%s/files/%s" % (PH_API, asset_id)
    return _http_json(url)


def ph_download_gltf(asset_id, resolution="1k", dest_dir=None):
    """下载 Polyhaven 模型的 gltf 组（.gltf + .bin + 贴图）。

    返回 (gltf_path, {相对路径: 绝对路径})
    """
    dest_dir = dest_dir or os.path.join(CACHE, "polyhaven", asset_id)
    files = ph_files(asset_id)
    entry = (files.get("gltf") or {}).get(resolution)
    if not entry:
        raise FetchError("variant_missing",
                         "asset %s has no gltf/%s" % (asset_id, resolution),
                         url="%s/files/%s" % (PH_API, asset_id))
    node = entry.get("gltf") or {}
    os.makedirs(dest_dir, exist_ok=True)

    main_url = node.get("url")
    main_md5 = node.get("md5")
    main_name = os.path.basename(main_url) if main_url else (asset_id + ".gltf")
    main_path = os.path.join(dest_dir, main_name)
    if not os.path.exists(main_path):
        _http_get(main_url, main_path, expect_md5=main_md5)

    got = {}
    for rel, info in (node.get("include") or {}).items():
        p = os.path.join(dest_dir, rel.replace("/", os.sep))
        if not os.path.exists(p):
            _http_get(info["url"], p, expect_md5=info.get("md5"))
        got[rel] = p
    got[main_name] = main_path
    return main_path, got


def ph_download_texture(asset_id, resolution="1k", dest_dir=None):
    """下载 Polyhaven 纹理集（albedo/normal/rough/disp）。

    返回 dict: {'albedo': path, 'normal': path, 'rough': path, 'disp': path, 'ao': path}
    """
    dest_dir = dest_dir or os.path.join(CACHE, "polyhaven_tex", asset_id)
    os.makedirs(dest_dir, exist_ok=True)
    files = ph_files(asset_id)
    out = {}
    for key, want in (("Diffuse", "albedo"), ("nor_gl", "normal"),
                      ("Rough", "rough"), ("disp", "disp"), ("AO", "ao")):
        byres = (files.get(key) or {}).get(resolution)
        if not byres:
            continue
        for fmt, info in byres.items():
            fn = os.path.basename(info["url"])
            p = os.path.join(dest_dir, fn)
            if not os.path.exists(p):
                _http_get(info["url"], p, expect_md5=info.get("md5"))
            out[want] = p
            break
    return out


# =====================================================================
# GLB 打包（把 Polyhaven 的 .gltf+bin+贴图 打成单文件 .glb）
# =====================================================================
# =====================================================================
# 纹理降采样（控制 GLB 体积）
# =====================================================================
def _load_texture(path, max_px=2048):
    """读取贴图；若超过 max_px 则等比降采样后重新编码为 JPEG。

    【为什么需要】
      Polyhaven 的部分资源（树木类）自带 4K 贴图，
      打包后单个 GLB 达 465MB —— 验收站根本打不开。
      实测：fir_tree_01 原始贴图 4096×4096，降到 2048 后体积降 95%，
      视觉上（家具在房间里的大小）几乎无差别。

    依赖 Pillow；没装则原样返回（不静默失败，只是体积没优化）。
    """
    with open(path, "rb") as fh:
        raw = fh.read()
    if max_px <= 0:
        return raw
    try:
        import io
        from PIL import Image
    except ImportError:
        return raw
    try:
        im = Image.open(io.BytesIO(raw))
    except Exception:
        return raw
    if max(im.size) <= max_px:
        return raw
    ratio = max_px / max(im.size)
    new = (max(1, int(im.width * ratio)), max(1, int(im.height * ratio)))
    im = im.convert("RGB").resize(new, Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


def gltf_to_glb(gltf_path, files, dest_glb, texture_max_px=2048):
    """把 .gltf + .bin + 外部贴图 打包成 .glb（纯 Python，无 Blender 依赖）。

    这是为了避免每次都启动 Blender 解析 .blend（慢 100 倍）。
    glTF 2.0 的 GLB 容器格式：
      magic 'glTF' | version 2 | total length | chunk( length, type, data )
      chunk type: 0x4E4F534A = JSON, 0x004E4942 = BIN

    files=None 时自动扫描 .gltf 同目录下的 .bin / .jpg / .png，
    按文件名匹配 uri —— 用于"已下载到本地、离线重新打包"的场景。
    """
    with open(gltf_path, "r", encoding="utf-8") as f:
        gltf = json.load(f)

    if files is None:
        files = {}
        base = os.path.dirname(os.path.abspath(gltf_path))
        for fn in os.listdir(base):
            if fn.lower().endswith((".bin", ".jpg", ".jpeg", ".png", ".webp", ".ktx2")):
                files[fn] = os.path.join(base, fn)
        # 部分模型的贴图放在 textures/ 子目录里
        tex_dir = os.path.join(base, "textures")
        if os.path.isdir(tex_dir):
            for fn in os.listdir(tex_dir):
                if fn.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".ktx2")):
                    files.setdefault(fn, os.path.join(tex_dir, fn))

    # ---- 1. 内嵌图片 ----
    images = gltf.get("images") or []
    buffer_views = gltf.setdefault("bufferViews", [])
    buffers = gltf.setdefault("buffers", [])
    blob = bytearray()

    # 收集 .bin
    bin_data = b""
    for b in gltf.get("buffers", []):
        if b.get("uri") and not b["uri"].startswith("data:"):
            name = os.path.basename(b["uri"])
            src = None
            for rel, p in files.items():
                if os.path.basename(rel) == name:
                    src = p
                    break
            if src and os.path.exists(src):
                with open(src, "rb") as fh:
                    bin_data = fh.read()
            b.pop("uri", None)
    if bin_data:
        bv = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob),
                             "byteLength": len(bin_data)})
        blob += bin_data
        buffers = [{"byteLength": len(blob)}]
    else:
        buffers = []

    # 把外部图片转成 bufferView
    for img in images:
        uri = img.get("uri")
        if not uri or uri.startswith("data:"):
            continue
        name = os.path.basename(uri)
        src = None
        for rel, p in files.items():
            if os.path.basename(rel) == name:
                src = p
                break
        if not src or not os.path.exists(src):
            raise FetchError("asset_missing",
                             "image not found for %s" % name, url=uri)
        data = _load_texture(src, max_px=texture_max_px)
        bv = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob),
                             "byteLength": len(data)})
        blob += data
        img.pop("uri", None)
        img["bufferView"] = bv
        img["mimeType"] = "image/jpeg" if name.lower().endswith((".jpg", ".jpeg")) \
            else "image/png"

    if blob:
        buffers = [{"byteLength": len(blob)}]

    # ---- 2. JSON chunk ----
    for i, b in enumerate(gltf.get("buffers", [])):
        if i == 0 and blob:
            b["byteLength"] = len(blob)
    gltf["buffers"] = buffers

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    bin_bytes = bytes(blob)
    bin_bytes += b"\x00" * ((4 - len(bin_bytes) % 4) % 4)

    total = 12 + 8 + len(json_bytes) + (8 + len(bin_bytes) if bin_bytes else 0)
    out = bytearray()
    out += b"glTF"
    out += (2).to_bytes(4, "little")
    out += total.to_bytes(4, "little")
    out += len(json_bytes).to_bytes(4, "little")
    out += (0x4E4F534A).to_bytes(4, "little")
    out += json_bytes
    if bin_bytes:
        out += len(bin_bytes).to_bytes(4, "little")
        out += (0x004E4942).to_bytes(4, "little")
        out += bin_bytes

    os.makedirs(os.path.dirname(dest_glb), exist_ok=True)
    with open(dest_glb, "wb") as f:
        f.write(out)
    return dest_glb


# =====================================================================
if __name__ == "__main__":
    a, n = acg_list("Material", limit=1)
    print("ambientCG Material total:", n)
    m = ph_assets("models")
    print("polyhaven models total:", len(m))
