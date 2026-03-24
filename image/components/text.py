"""文字辅助组件"""
from PIL import ImageDraw

from ..fonts import torus_semibold, torus_bold, get_text_font
from ..colors import TEXT_WHITE, TEXT_GRAY, TEXT_MUTED
from ..renderer import draw_text, get_text_width


def draw_header_text(draw: ImageDraw.ImageDraw, width: int, title: str = "Malody Dashboard", timestamp: str = ""):
    font_sm = torus_semibold(22)
    draw_text(draw, (20, 8), f"powered by MalodyApi // {title}", font_sm, TEXT_GRAY, anchor="lt")
    if timestamp:
        draw_text(draw, (width - 20, 8), timestamp, font_sm, TEXT_GRAY, anchor="rt")


def draw_panel_title(draw: ImageDraw.ImageDraw, xy: tuple, text: str,
                     font_size: int = 48, color: tuple = TEXT_WHITE):
    draw_text(draw, xy, text, get_text_font(text, font_size, bold=True), color, anchor="lt")


def draw_stat_label(draw: ImageDraw.ImageDraw, xy: tuple, label: str, value: str,
                    label_color: tuple = TEXT_MUTED, value_color: tuple = TEXT_WHITE,
                    label_size: int = 18, value_size: int = 28):
    x, y = xy
    draw_text(draw, (x, y), label, torus_semibold(label_size), label_color, anchor="lt")
    draw_text(draw, (x, y + label_size + 4), value, torus_bold(value_size), value_color, anchor="lt")


def draw_mode_badge(draw: ImageDraw.ImageDraw, xy: tuple, mode_name: str, color: tuple, font_size: int = 16):
    font = torus_bold(font_size)
    tw = get_text_width(mode_name, font)
    x, y = xy
    pad_x, pad_y = 10, 4
    draw.rounded_rectangle(
        (x, y, x + tw + pad_x * 2, y + font_size + pad_y * 2),
        radius=8,
        fill=(*color[:3], 200) if len(color) >= 3 else color,
    )
    draw_text(draw, (x + pad_x, y + pad_y), mode_name, font, TEXT_WHITE, anchor="lt")
    return tw + pad_x * 2
