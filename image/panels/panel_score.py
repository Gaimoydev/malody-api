import math
from datetime import datetime

from PIL import Image, ImageDraw, ImageFilter

from ..colors import TEXT_WHITE, TEXT_GRAY, TEXT_MUTED, get_rank_color
from ..components.avatar import render_avatar
from ..fonts import torus_semibold, torus_bold, poppins_bold, get_text_font
from ..renderer import (
    export_jpeg, export_png,
    draw_gradient_rect, draw_horizontal_gradient_rect,
    draw_text, get_text_width,
    fetch_web_background, fetch_image, fit_cover,
    load_null_cover, )

W, H = 1920, 1080

PANEL_BG = (28, 23, 25, 255)
CARD_DARK = (28, 23, 25, 200)
CARD_MAIN = (42, 34, 38, 230)
CARD_LIGHT = (60, 50, 55, 255)

JUDGE_COLORS = {"best": (141, 207, 244), "cool": (254, 246, 104), "good": (121, 196, 113), "miss": (237, 108, 158)}
JUDGE_LEVEL = {0: "A(EASY)", 1: "B(EASY+)", 2: "C(NORMAL)", 3: "D(NORMAL+)", 4: "E(HARD)"}
GRADE_COLORS = {
    "M5": (255, 215, 0), "M4": (192, 210, 255), "M3": (102, 204, 102),
    "M2": (180, 130, 255), "M1": (255, 170, 100), "M0": (255, 100, 100),
}
STAT_COLORS = {
    "BPM": (168, 100, 168), "Length": (240, 110, 169), "KEY": (0, 191, 243),
    "Notes": (124, 197, 118), "Level": (255, 244, 103), "Combo": (242, 108, 79),
}
AREA_MAP = {
    0: "???", 1: "Asia", 2: "Africa", 3: "N.America", 4: "S.America",
    5: "Europe", 6: "Australia", 7: "Japan", 8: "China", 9: "USA",
    10: "Taiwan", 11: "Korea", 12: "Germany", 13: "Russia", 14: "Poland",
    15: "France", 16: "Hong Kong", 17: "Canada", 18: "Chile", 19: "Indonesia",
    20: "Brazil", 21: "Thailand", 22: "Italy", 23: "UK", 24: "Argentina",
    25: "Philippines", 26: "Finland", 27: "Netherlands", 28: "Malaysia",
    29: "Spain", 30: "Mexico", 31: "Sweden", 32: "Singapore", 33: "New Zealand",
    34: "Vietnam", 35: "Belgium", 36: "Switzerland", 37: "Austria",
    38: "Bulgaria", 39: "Macau",
}


def _calc_grade(acc, miss, best, cool, good):
    total = best + cool + good + miss
    if total > 0 and best == total and acc >= 99.99:
        return "M5"
    if miss == 0 and acc >= 95:
        return "M4"
    if acc >= 90:
        return "M3"
    if acc >= 80:
        return "M2"
    if acc >= 70:
        return "M1"
    return "M0"


def _fmt_score(s):
    t = str(s)
    p = []
    while t:
        p.append(t[-4:])
        t = t[:-4]
    return ",".join(reversed(p))


async def render_score_panel(
        score: dict, player_name="", avatar_url="", chart_title="",
        chart_level=0, cover_url="", chart_meta=None, player_data=None,
        output_format="jpeg",
) -> bytes:
    chart_meta = chart_meta or {}
    player_data = player_data or {}

    acc = score.get("accuracy") or 0
    combo = score.get("combo") or 0
    score_val = score.get("score") or 0
    ranking = score.get("ranking") or 0
    fc = score.get("fc", False)
    miss = score.get("miss") or 0
    best = score.get("best") or 0
    cool = score.get("cool") or 0
    good = score.get("good") or 0
    judge = score.get("judge", 0)
    pro = score.get("pro", False)

    chart_data = score.get("chart", {})
    lvl = chart_level or chart_data.get("level", 0)
    max_combo = chart_data.get("max_combo", 0)
    time_str = score.get("time_str", "")
    cid = chart_data.get("cid", 0)

    chart_data["creator"] = chart_meta.get("creator", "")
    chart_data["length"] = chart_meta.get("length", 0)
    chart_data["bpm"] = chart_meta.get("bpm", 0)
    chart_data["hot"] = chart_meta.get("hot", 0)

    area = player_data.get("area", 0)
    modes = player_data.get("modes", [])
    p_mode = modes[0] if modes else {}

    grade = _calc_grade(acc, miss, best, cool, good)
    gc = GRADE_COLORS.get(grade, (180, 180, 180))

    canvas = Image.new("RGBA", (W, H), PANEL_BG)
    draw = ImageDraw.Draw(canvas)

    bg_img = await fetch_image(cover_url, W, H) if cover_url else None
    if bg_img is None:
        bg_img = await fetch_web_background(W, H)
    else:
        bg_img = bg_img.convert("RGBA").filter(ImageFilter.GaussianBlur(radius=25))
        dark_all = Image.new("RGBA", (W, H), (15, 10, 15, 150))
        bg_img = Image.alpha_composite(bg_img, dark_all)
    canvas.alpha_composite(bg_img, (0, 0))

    bg_card = Image.new("RGBA", (W, H - 290), (0, 0, 0, 0))
    mask = Image.new("L", (W, H - 290), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W, H - 290), radius=30, fill=180)
    bg_card.putalpha(mask)
    canvas.alpha_composite(bg_card, (0, 290))
    draw = ImageDraw.Draw(canvas)

    hdr = torus_semibold(18)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw_text(draw, (40, 16), "powered by MalodyApi // Score", hdr, (200, 200, 200, 200), anchor="lt")
    draw_text(draw, (W - 40, 16), f"score: {time_str}  //  req: {now}", hdr, (200, 200, 200, 200), anchor="rt")

    idx_w, idx_h = 240, 56
    idx_x = (W - idx_w) // 2
    draw.rounded_rectangle((idx_x, 35, idx_x + idx_w, 35 + idx_h), radius=28, fill=CARD_DARK)
    draw_text(draw, (W // 2, 63), f"GRADE {grade}", torus_bold(26), (*gc, 255), anchor="mm")

    await _player_card(canvas, draw, 40, 50, 480, 220, player_name, avatar_url, gc, judge, pro, area, p_mode)

    j_str = JUDGE_LEVEL.get(judge, f"J{judge}")
    draw_text(draw, (W - 40, 70), j_str, torus_bold(28), (*gc, 255), anchor="rt")
    if pro:
        draw_text(draw, (W - 40, 106), "PRO", torus_bold(20), (255, 100, 100, 255), anchor="rt")

    _draw_ranking_text(draw, ranking, gc)

    LX, W_LEFT = 40, 400
    RX, W_RIGHT = 900, 980
    Y_START = 330
    GAP = 20

    h_star = 150
    _star_rating_card(draw, canvas, LX, Y_START, W_LEFT, h_star, lvl, gc)

    y_stats = Y_START + h_star + GAP
    h_stats = 450
    _statistics_card(draw, canvas, LX, y_stats, W_LEFT, h_stats, chart_data, max_combo, gc)

    h_top_right = 270
    _right_top_card(draw, RX, Y_START, W_RIGHT, h_top_right, score_val, acc, combo, max_combo, fc, gc)

    y_judge = Y_START + h_top_right + GAP
    h_judge = 350
    _right_judgment(draw, canvas, RX, y_judge, W_RIGHT, h_judge, best, cool, good, miss, gc)

    hex_cx, hex_cy, hex_r = 670, 645, 175
    await _draw_hex_cover(canvas, draw, hex_cx, hex_cy, hex_r, cover_url, gc)
    grade_font = poppins_bold(160)
    draw_text(draw, (hex_cx + 5, hex_cy + 5), grade, grade_font, (0, 0, 0, 150), anchor="mm")
    draw_text(draw, (hex_cx, hex_cy), grade, grade_font, (*gc, 255), anchor="mm")

    _bottom_bar(draw, canvas, chart_title, cid, lvl, player_name)

    return export_png(canvas) if output_format == "png" else export_jpeg(canvas)


async def _player_card(canvas, draw, x, y, w, h, name, avatar_url, gc, judge, pro, area, mode_stats):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=20, fill=CARD_MAIN)
    av = 120
    img = await render_avatar(avatar_url, av)
    ax, ay = x + 25, y + (h - av) // 2
    canvas.alpha_composite(img, (ax, ay))
    draw = ImageDraw.Draw(canvas)
    nx = ax + av + 20

    nf = get_text_font(name or "?", 34, bold=True)
    draw_text(draw, (nx, y + 18), name or "?", nf, TEXT_WHITE, anchor="lt", max_width=w - av - 80)

    area_str = AREA_MAP.get(area, f"Area:{area}") if area else ""
    tag_y = y + 58
    if area_str:
        af = get_text_font(area_str, 16, bold=True)
        aw = get_text_width(area_str, af)
        draw.rounded_rectangle((nx, tag_y, nx + aw + 16, tag_y + 24), radius=6, fill=(0, 120, 200, 180))
        draw_text(draw, (nx + 8, tag_y + 12), area_str, af, TEXT_WHITE, anchor="lm")

    g_rank = mode_stats.get("rank", 0)
    g_grade_rank = mode_stats.get("grade_rank", 0)
    g_level = mode_stats.get("level", 0)
    g_acc = mode_stats.get("accuracy", 0)
    g_combo = mode_stats.get("combo", 0)
    g_grade = mode_stats.get("grade", 0)

    info_y = tag_y + 32
    sf = torus_semibold(16)
    lf = torus_bold(16)
    col1_x, col2_x = nx, nx + 160

    draw_text(draw, (col1_x, info_y), "Rank", sf, TEXT_MUTED, anchor="lt")
    draw_text(draw, (col1_x + 50, info_y), f"#{g_rank:,}" if g_rank else "-", lf, TEXT_WHITE, anchor="lt")
    draw_text(draw, (col2_x, info_y), "GRank", sf, TEXT_MUTED, anchor="lt")
    draw_text(draw, (col2_x + 58, info_y), f"#{g_grade_rank:,}" if g_grade_rank else "-", lf, TEXT_WHITE, anchor="lt")

    info_y += 26
    draw_text(draw, (col1_x, info_y), "Lv", sf, TEXT_MUTED, anchor="lt")
    draw_text(draw, (col1_x + 50, info_y), str(g_level), lf, (*gc, 255), anchor="lt")
    draw_text(draw, (col2_x, info_y), "Acc", sf, TEXT_MUTED, anchor="lt")
    draw_text(draw, (col2_x + 58, info_y), f"{g_acc:.2f}%", lf, TEXT_WHITE, anchor="lt")

    info_y += 26
    draw_text(draw, (col1_x, info_y), "Cmb", sf, TEXT_MUTED, anchor="lt")
    draw_text(draw, (col1_x + 50, info_y), f"{g_combo:,}", lf, TEXT_WHITE, anchor="lt")
    draw_text(draw, (col2_x, info_y), "MM", sf, TEXT_MUTED, anchor="lt")
    draw_text(draw, (col2_x + 58, info_y), f"{g_grade:,}", lf, TEXT_WHITE, anchor="lt")

    draw_horizontal_gradient_rect(
        canvas, (x + 25, y + h - 12, x + w - 25, y + h - 6),
        left_color=(*gc, 255), right_color=(*gc, 50), radius=3
    )


def _draw_ranking_text(draw, ranking, gc):
    if not ranking:
        return
    rx, ry = W - 40, 130
    if ranking > 1000:
        draw_text(draw, (rx, ry), "Rank >1000", torus_semibold(18), TEXT_MUTED, anchor="rt")
    else:
        draw_text(draw, (rx, ry), f"#{ranking}", poppins_bold(40), get_rank_color(ranking), anchor="rt")


def _star_rating_card(draw, canvas, x, y, w, h, level, gc):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=20, fill=CARD_MAIN)
    draw.rounded_rectangle((x, y, x + 8, y + h), radius=8, fill=(*gc, 220))
    draw_text(draw, (x + 35, y + 25), "Star Rating", torus_bold(22), TEXT_WHITE, anchor="lt")

    if level == 0:
        draw_text(draw, (x + 40, y + 75), "铺面未评级", get_text_font("铺面未评级", 36, bold=True), TEXT_MUTED, anchor="lt")
    else:
        lvl_big = poppins_bold(64)
        draw_text(draw, (x + 40, y + 60), str(level), lvl_big, TEXT_WHITE, anchor="lt")
        pw = get_text_width(str(level), lvl_big)
        draw_text(draw, (x + 40 + pw + 6, y + 86), "/ LV", torus_bold(26), TEXT_GRAY, anchor="lt")


def _statistics_card(draw, canvas, x, y, w, h, chart, max_combo, gc):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=20, fill=CARD_MAIN)
    draw.rounded_rectangle((x, y, x + 8, y + h), radius=8, fill=(*gc, 220))
    draw_text(draw, (x + 35, y + 25), "Statistics", torus_bold(22), TEXT_WHITE, anchor="lt")

    length = chart.get("length", 0)
    length_str = f"{length // 60}:{length % 60:02d} / {length}s" if length else "Unknown"
    creator = chart.get("creator", "") or "Unknown"
    hot = chart.get("hot", 0)

    stats = [
        ("CRT", creator, STAT_COLORS["KEY"]),
        ("LEN", length_str, STAT_COLORS["Length"]),
        ("HOT", f"{hot:,}" if hot else "0", STAT_COLORS["Combo"]),
        ("MAX", f"{max_combo:,}" if max_combo else "?", STAT_COLORS["Notes"]),
    ]

    start_y = y + 85
    row_gap = 85
    for i, (label, val, clr) in enumerate(stats):
        cy = start_y + i * row_gap
        draw.rounded_rectangle((x + 35, cy, x + 85, cy + 28), radius=8, fill=(*clr, 220))
        draw_text(draw, (x + 60, cy + 14), label, torus_bold(14), (20, 20, 20, 255), anchor="mm")
        draw_text(draw, (x + 105, cy - 4), val, get_text_font(val, 34, bold=True), TEXT_WHITE, anchor="lt", max_width=260)
        if i < len(stats) - 1:
            draw.line([(x + 35, cy + 55), (x + w - 30, cy + 55)], fill=(80, 70, 75, 120), width=1)


def _right_top_card(draw, x, y, w, h, score_val, acc, combo, max_combo, fc, gc):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=20, fill=CARD_MAIN)
    draw.rounded_rectangle((x, y, x + 8, y + h), radius=8, fill=(*gc, 220))

    draw_text(draw, (x + w - 30, y + 25), "Score", torus_semibold(18), TEXT_MUTED, anchor="rt")
    s = _fmt_score(score_val)
    parts = s.split(",", 1)
    if len(parts) == 2:
        draw_text(draw, (x + 40, y + 15), parts[0], poppins_bold(64), TEXT_WHITE, anchor="lt")
        pw = get_text_width(parts[0], poppins_bold(64))
        draw_text(draw, (x + 40 + pw, y + 30), "," + parts[1], poppins_bold(48), (200, 200, 210, 255), anchor="lt")
    else:
        draw_text(draw, (x + 40, y + 15), s, poppins_bold(64), TEXT_WHITE, anchor="lt")

    y_acc = y + 105
    draw.line([(x + 35, y_acc - 10), (x + w - 30, y_acc - 10)], fill=(80, 70, 75, 120), width=2)
    draw_text(draw, (x + w - 30, y_acc + 10), "Accuracy", torus_semibold(18), TEXT_MUTED, anchor="rt")
    a_int = f"{acc:.2f}"
    draw_text(draw, (x + 40, y_acc + 5), a_int, poppins_bold(52), TEXT_WHITE, anchor="lt")
    aw = get_text_width(a_int, poppins_bold(52))
    draw_text(draw, (x + 40 + aw + 4, y_acc + 22), "%", torus_bold(32), TEXT_GRAY, anchor="lt")

    y_combo = y + 195
    draw.line([(x + 35, y_combo - 10), (x + w - 30, y_combo - 10)], fill=(80, 70, 75, 120), width=2)
    draw_text(draw, (x + w - 30, y_combo + 10), "Combo", torus_semibold(18), TEXT_MUTED, anchor="rt")
    c_str = f"{combo:,}"
    draw_text(draw, (x + 40, y_combo + 5), c_str, poppins_bold(52), TEXT_WHITE, anchor="lt")
    cx = x + 40 + get_text_width(c_str, poppins_bold(52))

    if max_combo:
        max_str = f"/ {max_combo:,}"
        draw_text(draw, (cx + 10, y_combo + 22), max_str, torus_bold(32), TEXT_GRAY, anchor="lt")
        cx += 10 + get_text_width(max_str, torus_bold(32))

    if fc:
        bx, by, bw, bh = cx + 25, y_combo + 16, 125, 34
        draw.rounded_rectangle((bx, by, bx + bw, by + bh), radius=8, fill=(50, 220, 100, 220))
        draw_text(draw, (bx + bw // 2, by + bh // 2 - 1), "FULL COMBO", torus_bold(14), TEXT_WHITE, anchor="mm")


def _right_judgment(draw, canvas, x, y, w, h, best, cool, good, miss, gc):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=20, fill=CARD_MAIN)
    draw.rounded_rectangle((x, y, x + 8, y + h), radius=8, fill=(*gc, 220))
    draw_text(draw, (x + 35, y + 25), "Judgment", torus_bold(22), TEXT_WHITE, anchor="lt")

    total = best + cool + good + miss
    if total > 0 and cool > 0:
        r = f"BEST : COOL = {best / cool:.1f} : 1"
    elif total > 0 and best == total:
        r = "All BEST"
    else:
        r = ""
    if r:
        draw_text(draw, (x + w - 30, y + 28), r, torus_semibold(16), TEXT_MUTED, anchor="rt")

    judges = [
        ("BEST", best, JUDGE_COLORS["best"]), ("COOL", cool, JUDGE_COLORS["cool"]),
        ("GOOD", good, JUDGE_COLORS["good"]), ("MISS", miss, JUDGE_COLORS["miss"]),
    ]

    t = total or 1
    bx, bw, bh, gap, sy = x + 140, w - 260, 28, 45, y + 90

    for i, (lbl, cnt, clr) in enumerate(judges):
        by = sy + i * gap
        draw_text(draw, (x + 40, by + 1), lbl, torus_bold(22), (*clr, 255), anchor="lt")
        draw.rounded_rectangle((bx, by, bx + bw, by + bh), radius=bh // 2, fill=CARD_LIGHT)
        fw = max(int(bw * cnt / t), bh) if cnt > 0 else 0
        if fw > 0:
            draw_horizontal_gradient_rect(
                canvas, (bx, by, bx + fw, by + bh),
                left_color=(*clr, 200), right_color=(*clr, 255), radius=bh // 2
            )
        draw_text(draw, (x + w - 30, by + 1), str(cnt), torus_bold(26), TEXT_WHITE, anchor="rt")


async def _draw_hex_cover(canvas, draw, cx, cy, r, cover_url, gc):
    shadow_pts = [(cx + (r + 6) * math.cos(math.radians(60 * i - 90)),
                   cy + (r + 6) * math.sin(math.radians(60 * i - 90))) for i in range(6)]
    draw.polygon(shadow_pts, fill=(0, 0, 0, 100))

    cover = await fetch_image(cover_url, r * 2, r * 2) if cover_url else None
    if cover is None:
        cover = load_null_cover(r * 2, r * 2)

    mask = Image.new("L", (r * 2, r * 2), 0)
    md = ImageDraw.Draw(mask)
    pts = [(r + r * math.cos(math.radians(60 * i - 90)),
            r + r * math.sin(math.radians(60 * i - 90))) for i in range(6)]
    md.polygon(pts, fill=255)

    himg = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    cf = fit_cover(cover, r * 2, r * 2)
    himg.paste(cf, (0, 0), mask)

    overlay = Image.alpha_composite(
        Image.new("RGBA", (r * 2, r * 2), (*gc, 40)),
        Image.new("RGBA", (r * 2, r * 2), (10, 5, 10, 100)),
    )
    overlay.putalpha(mask)
    himg = Image.alpha_composite(himg, overlay)
    canvas.alpha_composite(himg, (cx - r, cy - r))

    hd = ImageDraw.Draw(canvas)
    bpts = [(cx + r * math.cos(math.radians(60 * i - 90)),
             cy + r * math.sin(math.radians(60 * i - 90))) for i in range(6)]
    bpts.append(bpts[0])
    hd.line(bpts, fill=(*gc, 255), width=6)


def _bottom_bar(draw, canvas, title, cid, level, player_name):
    draw_gradient_rect(canvas, (0, H - 140, W, H), top_color=(0, 0, 0, 0), bottom_color=(0, 0, 0, 220))
    if title:
        tf = get_text_font(title, 42, bold=True)
        draw_text(draw, (W // 2, H - 90), title, tf, TEXT_WHITE, anchor="mt", max_width=W - 300)
    sub = f"{player_name}  //  c{cid}  //  Lv.{level}"
    draw_text(draw, (W // 2, H - 35), sub, torus_semibold(20), (200, 200, 200, 255), anchor="mt")
