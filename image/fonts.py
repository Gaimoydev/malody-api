"""字体管理"""
from pathlib import Path
from PIL import ImageFont

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

_font_cache: dict[str, ImageFont.FreeTypeFont] = {}


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    key = f"{name}_{size}"
    if key not in _font_cache:
        font_path = FONTS_DIR / name
        _font_cache[key] = ImageFont.truetype(str(font_path), size) if font_path.exists() else ImageFont.load_default()
    return _font_cache[key]


def torus_semibold(size: int = 24) -> ImageFont.FreeTypeFont:
    return _load_font("Torus-SemiBold.ttf", size)


def torus_regular(size: int = 24) -> ImageFont.FreeTypeFont:
    return _load_font("Torus-Regular.ttf", size)


def torus_bold(size: int = 24) -> ImageFont.FreeTypeFont:
    return _load_font("Torus-Bold.ttf", size)


def puhuiti(size: int = 24) -> ImageFont.FreeTypeFont:
    return _load_font("AlibabaPuHuiTi3.0-75SemiBold-CJKTGv4.3.ttf", size)


def poppins_bold(size: int = 24) -> ImageFont.FreeTypeFont:
    return _load_font("Poppins-Bold.ttf", size)


def get_text_font(text: str, size: int = 24, bold: bool = False) -> ImageFont.FreeTypeFont:
    for ch in text:
        if ord(ch) > 0x4E00:
            return puhuiti(size)
    return torus_bold(size) if bold else torus_semibold(size)
