"""把 scripts/dev/_refs/ 下的所有官方 PDF 规格书转成 PNG，供验收站直接对照显示。

- 只转第 1 页（厂商规格书首页通常是尺寸图/产品图）
- 输出到 scripts/dev/_refs/<name>.png（同名不覆盖）
- 已经是图片的（png/jpg）跳过
"""
import pathlib, sys, warnings
warnings.filterwarnings("ignore")
import pymupdf

REFS = pathlib.Path(__file__).resolve().parents[3] / "验收" / "refs"
ZOOM = float(sys.argv[1]) if len(sys.argv) > 1 else 1.6


def main():
    pdfs = sorted(REFS.glob("*.pdf"))
    if not pdfs:
        print("no pdfs")
        return
    for src in pdfs:
        dst = src.with_suffix(".png")
        try:
            doc = pymupdf.open(src)
            if doc.page_count == 0:
                print(f"SKIP {src.name}: no page")
                continue
            page = doc[0]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM))
            pix.save(dst)
            print(f"OK {dst.name} {pix.width}x{pix.height} {dst.stat().st_size} bytes")
        except Exception as e:
            print(f"FAIL {src.name}: {e}")


if __name__ == "__main__":
    main()
