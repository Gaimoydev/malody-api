import io
from typing import Optional

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .colors import *
from .fonts import ASSETS_DIR

IMAGES_DIR = ASSETS_DIR / "images"
IMG_URL = "https://img.catcdn.cn/ba/"
NULL_AVATAR_PATH = IMAGES_DIR / "null_p.png"
NULL_COVER_PATH = IMAGES_DIR / "null_c.png"

_image_cache: dict[str, bytes] = {}
_avatar_cache: dict[str, bytes] = {}
_FETCH_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def create_canvas(width: int, height: int, color: tuple = BG_PRIMARY) -> Image.Image:
    return Image.new("RGBA", (width, height), color)


def draw_rounded_rect(draw: ImageDraw.ImageDraw, xy: tuple, radius: int = 20,
                      fill=None, outline=None, width: int = 0):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_gradient_rect(img: Image.Image, xy: tuple, top_color: tuple, bottom_color: tuple, radius: int = 0):
    x1, y1, x2, y2 = xy
    w, h = x2 - x1, y2 - y1
    if w < 1 or h < 1:
        return
    gradient = Image.new("RGBA", (w, h))
    gd = ImageDraw.Draw(gradient)
    for y in range(h):
        ratio = y / max(h - 1, 1)
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        a = int(top_color[3] + (bottom_color[3] - top_color[3]) * ratio) if len(top_color) > 3 and len(bottom_color) > 3 else 255
        gd.line([(0, y), (w, y)], fill=(r, g, b, a))
    if radius > 0:
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
        gradient.putalpha(mask)
    img.alpha_composite(gradient, (x1, y1))


def draw_horizontal_gradient_rect(img: Image.Image, xy: tuple, left_color: tuple, right_color: tuple, radius: int = 0):
    x1, y1, x2, y2 = xy
    w, h = x2 - x1, y2 - y1
    if w < 1 or h < 1:
        return
    gradient = Image.new("RGBA", (w, h))
    gd = ImageDraw.Draw(gradient)
    for x in range(w):
        ratio = x / max(w - 1, 1)
        r = int(left_color[0] + (right_color[0] - left_color[0]) * ratio)
        g = int(left_color[1] + (right_color[1] - left_color[1]) * ratio)
        b = int(left_color[2] + (right_color[2] - left_color[2]) * ratio)
        a = int(left_color[3] + (right_color[3] - left_color[3]) * ratio) if len(left_color) > 3 and len(right_color) > 3 else 255
        gd.line([(x, 0), (x, h)], fill=(r, g, b, a))
    if radius > 0:
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
        gradient.putalpha(mask)
    img.alpha_composite(gradient, (x1, y1))


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple, text: str, font: ImageFont.FreeTypeFont,
              fill: tuple = TEXT_WHITE, anchor: str = "lt", max_width: int = 0):
    if max_width > 0:
        text = truncate_text(text, font, max_width)
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)


def truncate_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    bbox = font.getbbox(text)
    if bbox[2] - bbox[0] <= max_width:
        return text
    while len(text) > 0:
        text = text[:-1]
        bbox = font.getbbox(text + "...")
        if bbox[2] - bbox[0] <= max_width:
            return text + "..."
    return "..."


def get_text_width(text: str, font: ImageFont.FreeTypeFont) -> int:
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0]


def circle_crop(img: Image.Image, size: int) -> Image.Image:
    img = img.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(img, (0, 0), mask)
    return output


def fit_cover(img: Image.Image, width: int, height: int) -> Image.Image:
    img_ratio = img.width / img.height
    target_ratio = width / height
    if img_ratio > target_ratio:
        new_h, new_w = height, int(height * img_ratio)
    else:
        new_w, new_h = width, int(width / img_ratio)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left, top = (new_w - width) // 2, (new_h - height) // 2
    return img.crop((left, top, left + width, top + height))


def rounded_crop(img: Image.Image, radius: int = 20) -> Image.Image:
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    output = img.copy().convert("RGBA")
    output.putalpha(mask)
    return output


async def fetch_web_background(width: int = 1920, height: int = 1080) -> Image.Image:
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=_FETCH_HEADERS) as c:
            resp = await c.get(IMG_URL, follow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 1000:
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                img = fit_cover(img, width, height).filter(ImageFilter.GaussianBlur(radius=16))
                dark = Image.new("RGBA", (width, height), (0, 0, 0, 140))
                return Image.alpha_composite(img, dark)
    except Exception:
        pass
    return Image.new("RGBA", (width, height), BG_PRIMARY)


async def fetch_image(url: str, width: int = 0, height: int = 0) -> Optional[Image.Image]:
    if url in _image_cache:
        img = Image.open(io.BytesIO(_image_cache[url])).convert("RGBA")
        if width and height:
            img = fit_cover(img, width, height)
        return img
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=_FETCH_HEADERS) as c:
            resp = await c.get(url, follow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 100:
                _image_cache[url] = resp.content
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                if width and height:
                    img = fit_cover(img, width, height)
                return img
    except Exception:
        pass
    return None


def load_null_avatar(size: int = 100) -> Image.Image:
    if NULL_AVATAR_PATH.exists():
        return Image.open(NULL_AVATAR_PATH).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    return _default_avatar(size)


def load_null_cover(width: int = 400, height: int = 400) -> Image.Image:
    if NULL_COVER_PATH.exists():
        return fit_cover(Image.open(NULL_COVER_PATH).convert("RGBA"), width, height)
    return Image.new("RGBA", (width, height), (55, 50, 65, 255))


async def fetch_avatar(url: str, size: int = 80) -> Image.Image:
    if url in _avatar_cache:
        img = Image.open(io.BytesIO(_avatar_cache[url])).convert("RGBA")
        return circle_crop(img, size)
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=_FETCH_HEADERS) as c:
            resp = await c.get(url, follow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 100:
                _avatar_cache[url] = resp.content
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                return circle_crop(img, size)
    except Exception:
        pass
    return circle_crop(load_null_avatar(size), size)


def _default_avatar(size: int = 80) -> Image.Image:
    img = Image.new("RGBA", (size, size), (80, 80, 100, 255))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img


def draw_progress_bar(draw: ImageDraw.ImageDraw, img: Image.Image, xy: tuple,
                      progress: float, bar_color=(102, 204, 255, 255),
                      bg_color=(60, 60, 80, 200), radius: int = 6):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=bg_color)
    bar_width = int((x2 - x1) * min(max(progress, 0), 1))
    if bar_width > 0:
        draw.rounded_rectangle((x1, y1, x1 + bar_width, y2), radius=radius, fill=bar_color)


def _as_rgb_for_export(img: Image.Image) -> Image.Image:
    if img.mode == "RGB":
        return img
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, BG_PRIMARY[:3])
        bg.paste(img, mask=img.getchannel("A"))
        return bg
    return img.convert("RGB")


def export_jpeg(img: Image.Image, quality: int = 98) -> bytes:
    rgb = _as_rgb_for_export(img)
    buf = io.BytesIO()
    rgb.save(
        buf,
        format="JPEG",
        quality=quality,
        subsampling=0,
        optimize=True,
    )
    return buf.getvalue()


def export_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
