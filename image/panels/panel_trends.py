import math
from datetime import datetime
from typing import List

from PIL import Image, ImageDraw

from ..colors import TEXT_WHITE, TEXT_GRAY, TEXT_MUTED, MODE_COLORS, MODE_NAMES
from ..components.avatar import render_avatar
from ..components.text import draw_mode_badge
from ..fonts import torus_semibold, torus_bold, poppins_bold, get_text_font
from ..renderer import (
    export_jpeg, export_png, draw_rounded_rect, draw_text, get_text_width,
    draw_horizontal_gradient_rect, fetch_web_background,
)

W, H = 1920, 1080
CARD = (36, 32, 46, 220)

RANK_BENCHMARKS = {"rank": 5000, "level": 80, "accuracy": 100.0, "combo": 15000, "play_count": 5000}


async def render_trends(player: dict, modes: List[dict], output_format: str = "jpeg") -> bytes:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    canvas = await fetch_web_background(W, H)
    canvas = canvas.convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    hdr = torus_semibold(18)
    draw_text(draw, (40, 14), f"MalodyApi // Player Trends — {player.get('name', '?')}", hdr, TEXT_MUTED, anchor="lt")
    draw_text(draw, (W - 40, 14), ts, hdr, TEXT_MUTED, anchor="rt")

    avatar_size = 90
    avatar_img = await render_avatar(player.get("avatar_url", ""), avatar_size)
    canvas.alpha_composite(avatar_img, (50, 48))
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((47, 45, 143, 141), outline=TEXT_WHITE, width=2)

    name = player.get("name", "?")
    draw_text(draw, (160, 58), name, get_text_font(name, 34, bold=True), TEXT_WHITE, anchor="lt")

    sub_parts = []
    if player.get("gold"):
        sub_parts.append(f"Gold: {player['gold']:,}")
    if player.get("play_time"):
        sub_parts.append(f"Play Time: {player['play_time']}")
    if sub_parts:
        draw_text(draw, (160, 100), "  |  ".join(sub_parts), torus_semibold(18), TEXT_GRAY, anchor="lt")

    if not modes:
        draw_text(draw, (W // 2, H // 2), "No mode data available", torus_bold(32), TEXT_MUTED, anchor="mm")
        return export_jpeg(canvas) if output_format != "png" else export_png(canvas)

    best = min(modes, key=lambda m: m.get("rank", 999999) or 999999)
    best_color = MODE_COLORS.get(best.get("mode", 0), (180, 180, 180))
    draw_mode_badge(draw, (160, 125), f"BEST: {MODE_NAMES.get(best.get('mode', 0), '?')} #{best.get('rank', '?'):,}", best_color, 14)

    top_y = 160
    radar_size = 420
    left_w = radar_size + 20
    right_x = 40 + left_w + 20
    right_w = W - right_x - 40

    _draw_radar(canvas, draw, modes, 40, top_y, left_w, radar_size)

    stat_cards_h = radar_size
    _draw_stat_cards(canvas, draw, modes, right_x, top_y, right_w, stat_cards_h)

    table_y = top_y + radar_size + 20
    table_h = H - table_y - 50
    _draw_mode_table(canvas, draw, modes, 40, table_y, W - 80, table_h)

    ff = torus_semibold(16)
    draw_text(draw, (40, H - 24), "Malody Player Trends  //  MalodyApi", ff, TEXT_MUTED, anchor="lt")
    draw_text(draw, (W - 40, H - 24), ts, ff, TEXT_MUTED, anchor="rt")

    return export_jpeg(canvas) if output_format != "png" else export_png(canvas)


def _draw_radar(canvas, draw, modes, x, y, w, h):
    draw_rounded_rect(draw, (x, y, x + w, y + h), radius=20, fill=CARD)
    draw_text(draw, (x + 24, y + 18), "Ability Radar", torus_bold(20), TEXT_WHITE, anchor="lt")

    cx, cy = x + w // 2, y + h // 2 + 15
    r = min(w, h) // 2 - 60
    axes = ["Rank", "Level", "Accuracy", "Combo", "Plays"]
    n = len(axes)
    angle = lambda i: math.radians(360 / n * i - 90)

    for ring in range(1, 6):
        rr = r * ring / 5
        pts = [(cx + rr * math.cos(angle(i)), cy + rr * math.sin(angle(i))) for i in range(n)]
        pts.append(pts[0])
        draw.line(pts, fill=(80, 75, 90, 80 if ring < 5 else 140), width=1)

        if ring % 2 == 0:
            lbl = f"{ring * 20}%"
            draw_text(draw, (int(cx + rr + 4), int(cy - 6)), lbl, torus_semibold(9), (90, 85, 100, 120), anchor="lt")

    for i in range(n):
        ex = cx + r * math.cos(angle(i))
        ey = cy + r * math.sin(angle(i))
        draw.line([(cx, cy), (int(ex), int(ey))], fill=(70, 65, 80, 60), width=1)
        lx = cx + (r + 28) * math.cos(angle(i))
        ly = cy + (r + 28) * math.sin(angle(i))
        draw_text(draw, (int(lx), int(ly)), axes[i], torus_semibold(14), TEXT_MUTED, anchor="mm")

    for mode_data in modes:
        mc = MODE_COLORS.get(mode_data.get("mode", 0), (180, 180, 180))
        vals = _normalize_absolute(mode_data)
        pts = []
        for i, v in enumerate(vals):
            vr = r * max(v, 0.03)
            pts.append((int(cx + vr * math.cos(angle(i))), int(cy + vr * math.sin(angle(i)))))

        fill_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(fill_layer).polygon(pts, fill=(*mc, 45))
        canvas.alpha_composite(fill_layer)
        draw = ImageDraw.Draw(canvas)

        draw.line(pts + [pts[0]], fill=(*mc, 220), width=2)
        for px, py in pts:
            draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=(*mc, 255))

    if len(modes) > 1:
        legend_y = y + h - 30
        lx = x + 24
        for m in modes:
            mc = MODE_COLORS.get(m.get("mode", 0), (180, 180, 180))
            mn = MODE_NAMES.get(m.get("mode", 0), "?")
            draw.ellipse((lx, legend_y, lx + 10, legend_y + 10), fill=(*mc, 255))
            draw_text(draw, (lx + 14, legend_y - 1), mn, torus_semibold(12), TEXT_GRAY, anchor="lt")
            lx += get_text_width(mn, torus_semibold(12)) + 28


def _draw_stat_cards(canvas, draw, modes, x, y, w, h):
    draw_rounded_rect(draw, (x, y, x + w, y + h), radius=20, fill=CARD)
    draw_text(draw, (x + 24, y + 18), "Mode Comparison", torus_bold(20), TEXT_WHITE, anchor="lt")
    draw_text(draw, (x + w - 24, y + 20), f"{len(modes)} mode{'s' if len(modes) > 1 else ''}", torus_semibold(14), TEXT_MUTED, anchor="rt")

    metrics = [
        ("Rank", "rank", True), ("Level", "level", False),
        ("Accuracy", "accuracy", False), ("Combo", "combo", False),
        ("MM Grade", "grade", False), ("Play Count", "play_count", False),
    ]

    inner_x = x + 24
    n_modes = max(len(modes), 1)
    n_metrics = len(metrics)
    header_h = 50
    avail = h - header_h - 10
    block_h = max(avail // n_metrics, 24)

    label_area_h = 16
    seg_area = block_h - label_area_h - 4
    seg_h = max(seg_area // n_modes, 4)
    if seg_h > 18:
        seg_h = 18
    seg_gap = max((seg_area - seg_h * n_modes) // max(n_modes, 1), 1)
    seg_radius = max(min(seg_h // 2 - 1, 3), 1)

    label_w = 90
    val_col_w = 80
    bar_x = inner_x + label_w
    bar_w = max(w - 48 - label_w - val_col_w, 40)
    val_x = bar_x + bar_w + 6

    for mi, (label, key, inverse) in enumerate(metrics):
        by = y + header_h + mi * block_h
        draw_text(draw, (inner_x, by), label, torus_semibold(14), TEXT_MUTED, anchor="lt")

        seg_start = by + label_area_h

        for i, m in enumerate(modes):
            mc = MODE_COLORS.get(m.get("mode", 0), (180, 180, 180))
            mn = MODE_NAMES.get(m.get("mode", 0), "?")
            v = m.get(key, 0)
            bench = RANK_BENCHMARKS.get(key, 1000)

            if inverse:
                ratio = max(1.0 - v / bench, 0.01) if v > 0 else 0
            else:
                ratio = min(v / bench, 1.0) if bench > 0 else 0
            ratio = max(min(ratio, 1.0), 0)

            sby = seg_start + i * (seg_h + seg_gap)
            r = min(seg_radius, seg_h // 2)
            if seg_h >= 2:
                draw.rounded_rectangle((bar_x, sby, bar_x + bar_w, sby + seg_h), radius=r, fill=(45, 40, 55, 150))

            fill_w = int(bar_w * ratio) if ratio > 0 else 0
            min_fill = r * 2 + 2
            if fill_w > 0 and fill_w < min_fill:
                fill_w = min_fill
            if fill_w >= min_fill and seg_h >= 2:
                draw_horizontal_gradient_rect(canvas, (bar_x, sby, bar_x + fill_w, sby + seg_h),
                                              left_color=(*mc, 160), right_color=(*mc, 255), radius=r)
                draw = ImageDraw.Draw(canvas)

            vt = f"{v:.2f}%" if key == "accuracy" else f"{v:,}"
            font_sz = max(min(seg_h, 13), 8)
            txt_y = sby + seg_h // 2
            draw_text(draw, (val_x, txt_y), f"{mn} {vt}", torus_semibold(font_sz), (*mc, 220), anchor="lm")

        if mi < n_metrics - 1:
            sep_y = y + header_h + (mi + 1) * block_h - 2
            draw.line([(inner_x, sep_y), (x + w - 24, sep_y)], fill=(80, 75, 90, 140), width=2)


def _draw_mode_table(canvas, draw, modes, x, y, w, h):
    draw_rounded_rect(draw, (x, y, x + w, y + h), radius=20, fill=CARD)
    draw_text(draw, (x + 24, y + 18), "Detailed Stats", torus_bold(20), TEXT_WHITE, anchor="lt")

    cols = ["Mode", "Rank", "GRank", "Level", "Accuracy", "Combo", "MM", "Plays"]
    n_cols = len(cols)
    col_w = w // n_cols
    header_y = y + 52

    for ci, col in enumerate(cols):
        cx = x + ci * col_w + col_w // 2
        draw_text(draw, (cx, header_y), col, torus_bold(16), TEXT_MUTED, anchor="mt")

    draw.line([(x + 20, header_y + 24), (x + w - 20, header_y + 24)], fill=(70, 65, 80, 150), width=1)

    data_h = h - 90
    row_h = min(max(data_h // max(len(modes), 1), 28), 50)
    data_start = header_y + 32

    for ri, m in enumerate(modes):
        ry = data_start + ri * row_h
        mc = MODE_COLORS.get(m.get("mode", 0), (180, 180, 180))
        mn = MODE_NAMES.get(m.get("mode", 0), "?")

        draw.rounded_rectangle((x + 14, ry + 4, x + 18, ry + row_h - 4), radius=2, fill=(*mc, 220))

        vals = [
            mn,
            f"#{m.get('rank', 0):,}" if m.get("rank") else "-",
            f"#{m.get('grade_rank', 0):,}" if m.get("grade_rank") else "-",
            str(m.get("level", 0)),
            f"{m.get('accuracy', 0):.2f}%",
            f"{m.get('combo', 0):,}",
            f"{m.get('grade', 0):,}",
            f"{m.get('play_count', 0):,}",
        ]
        vf = torus_semibold(16)
        for ci, v in enumerate(vals):
            cx = x + ci * col_w + col_w // 2
            clr = (*mc, 255) if ci == 0 else TEXT_WHITE
            draw_text(draw, (cx, ry + row_h // 2), v, vf, clr, anchor="mm")

        if ri < len(modes) - 1:
            draw.line([(x + 20, ry + row_h), (x + w - 20, ry + row_h)], fill=(60, 55, 70, 60), width=1)

    if len(modes) == 1:
        summary_y = data_start + row_h + 20
        m = modes[0]
        mc = MODE_COLORS.get(m.get("mode", 0), (180, 180, 180))

        draw.line([(x + 40, summary_y), (x + w - 40, summary_y)], fill=(*mc, 80), width=1)
        summary_y += 16

        rank = m.get("rank", 0)
        grade = m.get("grade", 0)
        acc = m.get("accuracy", 0)
        combo = m.get("combo", 0)
        pc = m.get("play_count", 0)

        insights = []
        if rank > 0:
            if rank <= 100:
                insights.append(f"Top {rank} 世界排名，属于顶尖水平")
            elif rank <= 1000:
                insights.append(f"世界排名 #{rank:,}，进入前千名")
            elif rank <= 5000:
                insights.append(f"世界排名 #{rank:,}，中等偏上水平")
            else:
                insights.append(f"世界排名 #{rank:,}，还有很大提升空间")

        if acc >= 98:
            insights.append(f"准确率 {acc:.2f}% 非常优秀")
        elif acc >= 95:
            insights.append(f"准确率 {acc:.2f}% 良好")
        elif acc >= 90:
            insights.append(f"准确率 {acc:.2f}%，仍有提升空间")

        if combo >= 10000:
            insights.append(f"最高连击 {combo:,}，连击能力出色")
        elif combo >= 5000:
            insights.append(f"最高连击 {combo:,}，表现稳定")

        if grade > 0:
            insights.append(f"MM 值 {grade:,}")

        if pc > 0:
            insights.append(f"共游玩 {pc:,} 次")

        sf = torus_semibold(15)
        line_h = 26
        for i, text in enumerate(insights[:6]):
            ty = summary_y + i * line_h
            if ty + line_h > y + h - 10:
                break
            draw.ellipse((x + 40, ty + 7, x + 46, ty + 13), fill=(*mc, 180))
            draw_text(draw, (x + 56, ty), text, get_text_font(text, 15), TEXT_GRAY, anchor="lt")


def _normalize_absolute(m):
    rank = m.get("rank", 0)
    rank_norm = min(max(1.0 - rank / RANK_BENCHMARKS["rank"], 0), 1.0) if rank > 0 else 0
    return [
        rank_norm,
        min(m.get("level", 0) / RANK_BENCHMARKS["level"], 1.0),
        m.get("accuracy", 0) / RANK_BENCHMARKS["accuracy"],
        min(m.get("combo", 0) / RANK_BENCHMARKS["combo"], 1.0),
        min(m.get("play_count", 0) / RANK_BENCHMARKS["play_count"], 1.0),
    ]
