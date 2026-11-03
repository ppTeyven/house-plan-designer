"""把参考 PDF 图纸转成 PNG，便于在验收站里直接对照查看。"""
import sys, pathlib, warnings
warnings.filterwarnings("ignore")
import pymupdf

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".png")
zoom = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0

doc = pymupdf.open(src)
page = doc[0]
pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
pix.save(dst)
print(f"OK {dst.name} {pix.width}x{pix.height} {dst.stat().st_size} bytes")