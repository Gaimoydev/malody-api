"""字体管理：优先加载含 CJK 字形的字体，避免中文等字符显示为乱码或方框。"""
import os
import sys
from pathlib import Path
from PIL import ImageFont

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

_font_cache: dict[str, ImageFont.FreeTypeFont] = {}
_ui_path_idx: dict[bool, tuple[str, int] | None] = {}


def _try_truetype(path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont | None:
    try:
        return ImageFont.truetype(path, size, index=index)
    except OSError:
        return None


def _cjk_candidates(bold: bool) -> list[tuple[Path, int]]:
    cands: list[tuple[Path, int]] = []
    env = os.environ.get("MALODY_CJK_FONT", "").strip()
    if env:
        cands.append((Path(env), 0))

    cands.append((FONTS_DIR / "AlibabaPuHuiTi3.0-75SemiBold-CJKTGv4.3.ttf", 0))

    if sys.platform == "win32":
        fd = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        if bold:
            cands.extend([
                (fd / "msyhbd.ttc", 0),
                (fd / "simhei.ttf", 0),
                (fd / "msyh.ttc", 1),
                (fd / "simsunb.ttf", 0),
            ])
        cands.extend([
            (fd / "msyh.ttc", 0),
            (fd / "simsun.ttc", 0),
            (fd / "simhei.ttf", 0),
        ])
    elif sys.platform == "darwin":
        cands.extend([
            (Path("/System/Library/Fonts/PingFang.ttc"), 0),
            (Path("/System/Library/Fonts/Hiragino Sans GB.ttc"), 0),
            (Path("/Library/Fonts/Arial Unicode.ttf"), 0),
        ])
    else:
        if bold:
            for p in (
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
                "/usr/share/fonts/opentype/nototc/NotoSansCJK-Bold.ttc",
                "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
                "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc",
            ):
                cands.append((Path(p), 0))
        for p in (
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/nototc/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        ):
            cands.append((Path(p), 0))

    return cands


def _resolve_ui_path_idx(bold: bool) -> tuple[str, int] | None:
    if bold in _ui_path_idx:
        return _ui_path_idx[bold]
    chosen = None
    for path, idx in _cjk_candidates(bold):
        if not path.is_file():
            continue
        if _try_truetype(str(path), 16, idx) is not None:
            chosen = (str(path), idx)
            break
    _ui_path_idx[bold] = chosen
    return chosen


def _ui_sans(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    cache_key = f"ui_{int(bold)}_{size}"
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    face = _resolve_ui_path_idx(bold)
    if face:
        path, idx = face
        f = _try_truetype(path, size, idx)
        if f is not None:
            _font_cache[cache_key] = f
            return f

    torus_name = "Torus-Bold.ttf" if bold else "Torus-SemiBold.ttf"
    tp = FONTS_DIR / torus_name
    if tp.is_file():
        f = _try_truetype(str(tp), size, 0)
        if f is not None:
            _font_cache[cache_key] = f
            return f

    fb = ImageFont.load_default()
    _font_cache[cache_key] = fb
    return fb


def torus_semibold(size: int = 24) -> ImageFont.FreeTypeFont:
    return _ui_sans(size, False)


def torus_regular(size: int = 24) -> ImageFont.FreeTypeFont:
    return _ui_sans(size, False)


def torus_bold(size: int = 24) -> ImageFont.FreeTypeFont:
    return _ui_sans(size, True)


def puhuiti(size: int = 24) -> ImageFont.FreeTypeFont:
    return _ui_sans(size, True)


def poppins_bold(size: int = 24) -> ImageFont.FreeTypeFont:
    key = f"poppins_bold_{size}"
    if key not in _font_cache:
        fp = FONTS_DIR / "Poppins-Bold.ttf"
        if fp.is_file():
            f = _try_truetype(str(fp), size, 0)
            _font_cache[key] = f if f is not None else _ui_sans(size, True)
        else:
            _font_cache[key] = _ui_sans(size, True)
    return _font_cache[key]


def get_text_font(text: str, size: int = 24, bold: bool = False) -> ImageFont.FreeTypeFont:
    return _ui_sans(size, bold)
