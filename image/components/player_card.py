"""玩家卡片组件"""
from PIL import Image, ImageDraw

from ..renderer import draw_rounded_rect, draw_horizontal_gradient_rect, draw_text, get_text_width, draw_progress_bar
from ..colors import BG_CARD, TEXT_WHITE, TEXT_GRAY, TEXT_MUTED, MODE_COLORS, MODE_NAMES, get_rank_color
from ..fonts import torus_semibold, torus_bold, poppins_bold, get_text_font
from .avatar import render_avatar
from .text import draw_mode_badge

CARD_WIDTH = 880
CARD_HEIGHT = 110
CARD_RADIUS = 16


async def render_player_card(player_data: dict, x: int = 0, y: int = 0) -> Image.Image:
    card = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    mode = player_data.get("mode", 0)
    mode_color = MODE_COLORS.get(mode, (180, 180, 180))

    draw_rounded_rect(draw, (0, 0, CARD_WIDTH, CARD_HEIGHT), radius=CARD_RADIUS, fill=BG_CARD)
    draw.rounded_rectangle((0, 0, 6, CARD_HEIGHT), radius=3, fill=(*mode_color, 220))

    avatar_size = 70
    avatar_x, avatar_y = 20, (CARD_HEIGHT - avatar_size) // 2
    avatar_img = await render_avatar(player_data.get("avatar_url", ""), avatar_size)
    card.alpha_composite(avatar_img, (avatar_x, avatar_y))

    rank = player_data.get("rank") or 0
    draw_text(draw, (100, 18), f"#{rank}", poppins_bold(28), get_rank_color(rank), anchor="lt")

    name = player_data.get("name") or "Unknown"
    draw_text(draw, (100, 52), name, get_text_font(name, 24, bold=True), TEXT_WHITE, anchor="lt", max_width=250)

    level = player_data.get("level") or 0
    if level > 0:
        draw_text(draw, (100, 82), f"Lv.{level}", torus_semibold(18), TEXT_MUTED, anchor="lt")

    accuracy = player_data.get("accuracy") or 0.0
    acc_str = f"{accuracy:.2f}%" if accuracy else "N/A"
    acc_label_font = torus_semibold(14)
    draw_text(draw, (380, 22), acc_str, torus_bold(24), TEXT_WHITE, anchor="lt")
    draw_text(draw, (380, 50), "ACCURACY", acc_label_font, TEXT_MUTED, anchor="lt")
    if accuracy:
        draw_progress_bar(draw, card, (380, 70, 500, 80), progress=accuracy / 100.0, bar_color=(*mode_color, 255))

    combo = player_data.get("combo") or 0
    draw_text(draw, (530, 22), f"{combo:,}", torus_bold(24), TEXT_WHITE, anchor="lt")
    draw_text(draw, (530, 50), "MAX COMBO", acc_label_font, TEXT_MUTED, anchor="lt")

    pc = player_data.get("play_count") or 0
    draw_text(draw, (680, 22), f"{pc:,}", torus_bold(24), TEXT_WHITE, anchor="lt")
    draw_text(draw, (680, 50), "PLAY COUNT", acc_label_font, TEXT_MUTED, anchor="lt")

    mode_name = MODE_NAMES.get(mode, "?")
    draw_mode_badge(draw, (CARD_WIDTH - 90, CARD_HEIGHT - 32), mode_name, mode_color, 14)

    return card
