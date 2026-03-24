from datetime import datetime
from typing import List

from PIL import Image, ImageDraw, ImageFilter

from ..colors import TEXT_WHITE, TEXT_GRAY, MODE_NAMES
from ..components.player_card import render_player_card, CARD_WIDTH, CARD_HEIGHT
from ..fonts import torus_semibold, get_text_font
from ..renderer import create_canvas, export_jpeg, export_png, draw_text, fetch_web_background, fetch_image

PANEL_WIDTH = 1920
BANNER_HEIGHT = 280
CARD_PER_ROW = 2
CARD_SPACING_X = 40
CARD_SPACING_Y = 20
MARGIN_X = 40
MARGIN_TOP = 30
MARGIN_BOTTOM = 40


def _calc_panel_height(card_count: int) -> int:
    rows = (card_count + CARD_PER_ROW - 1) // CARD_PER_ROW if card_count > 0 else 0
    body_height = rows * (CARD_HEIGHT + CARD_SPACING_Y) - (CARD_SPACING_Y if rows > 0 else 0)
    return BANNER_HEIGHT + MARGIN_TOP + body_height + MARGIN_BOTTOM


async def render_card_list(players: List[dict], mode: int = 0, title: str = "",
                           cover_url: str = "", output_format: str = "jpeg") -> bytes:
    if not title:
        title = f"Malody {MODE_NAMES.get(mode, 'ALL')} Rankings"

    panel_height = _calc_panel_height(len(players))
    canvas = create_canvas(PANEL_WIDTH, panel_height)

    banner_img = await fetch_image(cover_url, PANEL_WIDTH, BANNER_HEIGHT) if cover_url else None
    if banner_img is None:
        banner_img = await fetch_web_background(PANEL_WIDTH, BANNER_HEIGHT)
    else:
        banner_img = banner_img.filter(ImageFilter.GaussianBlur(radius=20))
        dark = Image.new("RGBA", (PANEL_WIDTH, BANNER_HEIGHT), (0, 0, 0, 140))
        banner_img = Image.alpha_composite(banner_img, dark)
    canvas.alpha_composite(banner_img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hdr = torus_semibold(20)
    draw_text(draw, (20, 10), f"powered by MalodyApi // {title}", hdr, TEXT_GRAY, anchor="lt")
    draw_text(draw, (PANEL_WIDTH - 20, 10), ts, hdr, TEXT_GRAY, anchor="rt")

    tf = get_text_font(title, 42, bold=True)
    draw_text(draw, (PANEL_WIDTH // 2, BANNER_HEIGHT // 2 - 10), title, tf, TEXT_WHITE, anchor="mm", max_width=PANEL_WIDTH - 200)
    draw_text(draw, (PANEL_WIDTH // 2, BANNER_HEIGHT // 2 + 35),
              f"Top {len(players)} Players", get_text_font(f"Top {len(players)} Players", 24),
              (200, 200, 210, 255), anchor="mm")

    start_y = BANNER_HEIGHT + MARGIN_TOP
    for i, player in enumerate(players):
        col = i % CARD_PER_ROW
        row = i // CARD_PER_ROW
        cx = MARGIN_X + col * (CARD_WIDTH + CARD_SPACING_X)
        cy = start_y + row * (CARD_HEIGHT + CARD_SPACING_Y)
        card_img = await render_player_card(player, cx, cy)
        canvas.alpha_composite(card_img, (cx, cy))

    return export_png(canvas) if output_format == "png" else export_jpeg(canvas)
