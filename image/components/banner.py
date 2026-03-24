"""Banner 组件"""
from PIL import Image, ImageDraw

from ..renderer import draw_gradient_rect
from ..colors import GRADIENT_BANNER_TOP, GRADIENT_BANNER_BOTTOM
from ..fonts import get_text_font
from .text import draw_header_text


def render_banner(width: int = 1920, height: int = 320, title: str = "Malody Dashboard",
                  subtitle: str = "", version: str = "v1.0", timestamp: str = "") -> Image.Image:
    banner = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_gradient_rect(banner, (0, 0, width, height),
                       top_color=(*GRADIENT_BANNER_TOP, 160), bottom_color=(*GRADIENT_BANNER_BOTTOM, 200))
    draw = ImageDraw.Draw(banner)
    draw_header_text(draw, width, title, version, timestamp)

    title_font = get_text_font(title, 48, bold=True)
    draw.text((width // 2, height // 2 - 10), title, font=title_font, fill=(255, 255, 255, 255), anchor="mm")
    if subtitle:
        sub_font = get_text_font(subtitle, 28)
        draw.text((width // 2, height // 2 + 40), subtitle, font=sub_font, fill=(200, 200, 210, 255), anchor="mm")
    return banner
