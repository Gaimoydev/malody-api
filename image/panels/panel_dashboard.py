import re
from datetime import datetime
from typing import List, Optional

from PIL import ImageDraw

from ..colors import TEXT_WHITE, TEXT_GRAY, TEXT_MUTED, MODE_COLORS, MODE_NAMES
from ..components.avatar import render_avatar
from ..components.text import draw_stat_label, draw_mode_badge
from ..fonts import torus_semibold, torus_bold, get_text_font
from ..renderer import (
    export_jpeg, export_png, draw_rounded_rect, draw_text, get_text_width,
    fetch_web_background,
)

W, H = 1920, 1080
CARD = (40, 38, 52, 210)


def _clean_wiki(raw: str) -> str:
    if not raw:
        return ""
    txt = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', raw)
    txt = re.sub(r'[#*_~`>]', '', txt)
    txt = re.sub(r'\n{2,}', '\n', txt)
    return txt.strip()


def _wrap_text(text: str, font, max_width: int) -> list:
    words = text.replace('\n', ' ').split(' ')
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


async def render_dashboard(
    player: dict, history: Optional[List[dict]] = None,
    mode: int = 0, output_format: str = "jpeg",
) -> bytes:
    mode_name = MODE_NAMES.get(mode, "ALL")
    mode_color = MODE_COLORS.get(mode, (180, 180, 180))
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    canvas = await fetch_web_background(W, H)
    canvas = canvas.convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    hdr = torus_semibold(18)
    draw_text(draw, (40, 16), f"powered by MalodyBot // {player.get('name', '?')}", hdr, TEXT_MUTED, anchor="lt")
    draw_text(draw, (W - 40, 16), ts, hdr, TEXT_MUTED, anchor="rt")

    avatar_size = 100
    avatar_x = 50
    name = player.get("name", "Unknown")
    name_font = get_text_font(name, 36, bold=True)
    name_h = name_font.getbbox("Ay")[3]
    info_font = get_text_font("A", 18)
    info_h = info_font.getbbox("Ay")[3]
    text_total_h = name_h + 8 + info_h
    block_h = max(avatar_size, text_total_h)
    block_y = 55
    avatar_y = block_y + (block_h - avatar_size) // 2
    text_base_y = block_y + (block_h - text_total_h) // 2

    avatar_img = await render_avatar(player.get("avatar_url", ""), avatar_size)
    canvas.alpha_composite(avatar_img, (avatar_x, avatar_y))
    draw = ImageDraw.Draw(canvas)
    draw.ellipse(
        (avatar_x - 3, avatar_y - 3, avatar_x + avatar_size + 3, avatar_y + avatar_size + 3),
        outline=(*mode_color, 255), width=3,
    )

    tx = avatar_x + avatar_size + 20
    draw_text(draw, (tx, text_base_y), name, name_font, TEXT_WHITE, anchor="lt")
    name_w = get_text_width(name, name_font)
    draw_mode_badge(draw, (tx + name_w + 12, text_base_y + 6), mode_name, mode_color, 15)

    info_parts = []
    if player.get("gold"):
        info_parts.append(f"Gold: {player['gold']:,}")
    if player.get("play_time"):
        info_parts.append(f"Play Time: {player['play_time']}")
    if info_parts:
        draw_text(draw, (tx, text_base_y + name_h + 8), "  |  ".join(info_parts), info_font, TEXT_GRAY, anchor="lt")

    stats_y = 175
    rank_val = player.get("rank") or 0
    level_val = player.get("level") or 0
    acc_val = player.get("accuracy") or 0
    combo_val = player.get("combo") or 0
    pc_val = player.get("play_count") or 0

    stat_cards = [
        ("RANK", f"#{rank_val:,}" if isinstance(rank_val, int) and rank_val > 0 else "#?"),
        ("LEVEL", str(level_val)),
        ("ACCURACY", f"{acc_val:.2f}%"),
        ("MAX COMBO", f"{combo_val:,}"),
        ("PLAY COUNT", f"{pc_val:,}"),
    ]

    card_count = len(stat_cards)
    card_gap = 16
    total_w = W - 80
    card_w = (total_w - card_gap * (card_count - 1)) // card_count
    card_h = 90

    for i, (label, value) in enumerate(stat_cards):
        cx = 40 + i * (card_w + card_gap)
        draw_rounded_rect(draw, (cx, stats_y, cx + card_w, stats_y + card_h), radius=14, fill=CARD)
        draw.rounded_rectangle((cx + 8, stats_y, cx + card_w - 8, stats_y + 3), radius=2, fill=(*mode_color, 180))
        draw_stat_label(draw, (cx + 14, stats_y + 14), label=label, value=value, label_size=13, value_size=28)

    wiki_raw = player.get("wiki", "")
    wiki_text = _clean_wiki(wiki_raw)
    cursor_y = stats_y + card_h + 16

    if wiki_text:
        wf = get_text_font(wiki_text, 16)
        max_line_w = W - 140
        lines = _wrap_text(wiki_text, wf, max_line_w)
        max_lines = min(len(lines), 5)
        line_h = 22
        wiki_card_h = 36 + max_lines * line_h + 10

        draw_rounded_rect(draw, (40, cursor_y, W - 40, cursor_y + wiki_card_h), radius=14, fill=CARD)
        draw_text(draw, (58, cursor_y + 10), "Wiki", torus_bold(17), TEXT_WHITE, anchor="lt")
        ly = cursor_y + 34
        for i in range(max_lines):
            draw_text(draw, (58, ly + i * line_h), lines[i], wf, TEXT_MUTED, anchor="lt", max_width=max_line_w)
        cursor_y += wiki_card_h + 12

    activities = player.get("activities", [])
    act_y = cursor_y
    act_h = H - act_y - 46

    draw_rounded_rect(draw, (40, act_y, W - 40, act_y + act_h), radius=16, fill=CARD)
    draw_text(draw, (58, act_y + 14), "Recent Activity", torus_bold(22), TEXT_WHITE)
    draw_text(draw, (W - 58, act_y + 18), f"{len(activities)} records", torus_semibold(16), TEXT_MUTED, anchor="rt")

    if activities:
        avail_h = act_h - 52
        row_h = min(40, max(avail_h // max(len(activities), 1), 24))
        max_rows = min(len(activities), avail_h // row_h)
        _draw_activity_list(draw, activities[:max_rows], 58, act_y + 46, W - 116, avail_h, row_h, mode_color)
    else:
        draw_text(draw, (W // 2, act_y + act_h // 2), "No activity data", torus_semibold(20), TEXT_MUTED, anchor="mm")

    ff = torus_semibold(16)
    draw_text(draw, (40, H - 24), "Malody Dashboard  //  Powered by MalodyBot", ff, TEXT_MUTED, anchor="lt")
    draw_text(draw, (W - 40, H - 24), ts, ff, TEXT_MUTED, anchor="rt")

    return export_png(canvas) if output_format == "png" else export_jpeg(canvas)


def _draw_activity_list(draw, activities, x, y, w, h, row_h, mode_color):
    msg_font = get_text_font("A", 17)
    time_font = torus_semibold(15)
    for i, act in enumerate(activities):
        ry = y + i * row_h
        draw.rounded_rectangle((x, ry + 2, x + 3, ry + row_h - 4), radius=2, fill=(*mode_color[:3], 180))
        draw_text(draw, (x + 12, ry + (row_h - 17) // 2), act.get("message", ""),
                  msg_font, TEXT_WHITE, anchor="lt", max_width=w - 200)
        draw_text(draw, (x + w, ry + (row_h - 15) // 2), act.get("time_str", ""),
                  time_font, TEXT_MUTED, anchor="rt")
