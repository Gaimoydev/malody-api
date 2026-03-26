from datetime import datetime

from PIL import Image, ImageDraw, ImageFilter

from .panel_score import _calc_grade, _fmt_score, GRADE_COLORS
from ..colors import TEXT_WHITE, TEXT_MUTED, TEXT_GRAY, get_rank_color
from ..components.avatar import render_avatar
from ..fonts import torus_bold, torus_semibold, poppins_bold, get_text_font
from ..renderer import (
    export_jpeg, export_png, draw_text, fetch_web_background,
    truncate_text
)

W = 1920
CARD_MAIN = (42, 34, 38, 230)
CARD_DARK = (28, 23, 25, 200)
CARD_LIGHT = (60, 50, 55, 200)


async def render_player_recent_scores_panel(player: dict, scores: list, output_format: str = "jpeg") -> bytes:
    n = max(len(scores), 1)

    card_y, card_h = 40, 200
    hdr_y = card_y + card_h + 30
    hdr_h = 50
    row_h, row_gap = 85, 12
    y0 = hdr_y + hdr_h + 15
    bottom_pad = 100

    total_content_h = y0 + n * (row_h + row_gap) + bottom_pad
    H = min(2800, max(1080, total_content_h))

    canvas = Image.new("RGBA", (W, H), (28, 23, 25, 255))
    bg_img = await fetch_web_background(W, H)
    if bg_img:
        bg_img = bg_img.convert("RGBA").filter(ImageFilter.GaussianBlur(radius=25))
        dark_all = Image.new("RGBA", (W, H), (15, 10, 15, 180))
        bg_img = Image.alpha_composite(bg_img, dark_all)
        canvas.alpha_composite(bg_img, (0, 0))

    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle((40, card_y, W - 40, card_y + card_h), radius=20, fill=CARD_MAIN)
    draw.rounded_rectangle((40, card_y, 48, card_y + card_h), radius=8, fill=(102, 204, 102, 220))

    av = 130
    ax, ay = 75, card_y + (card_h - av) // 2
    avatar_img = await render_avatar(player.get("avatar_url", ""), av)
    canvas.alpha_composite(avatar_img, (ax, ay))

    nx = ax + av + 30
    pname = player.get("name", "?")

    f_name = get_text_font(pname, 48, bold=True)
    draw_text(draw, (nx, card_y + 35), pname, f_name, TEXT_WHITE, anchor="lt")

    desc1 = "Malody — 最近上榜成绩"
    desc2 = f"共 {len(scores)} 条记录 (15条最新动态中获取榜位≤30的成绩)"
    f_desc1 = get_text_font(desc1, 22, bold=True)
    f_desc2 = get_text_font(desc2, 18)

    draw_text(draw, (nx, card_y + 110), desc1, f_desc1, (220, 220, 220, 255), anchor="lt")
    draw_text(draw, (nx, card_y + 145), desc2, f_desc2, TEXT_GRAY, anchor="lt")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw_text(draw, (W - 70, card_y + 35), f"req: {now}", torus_semibold(16), TEXT_MUTED, anchor="rt")
    draw.rounded_rectangle((40, hdr_y, W - 40, hdr_y + hdr_h), radius=12, fill=CARD_DARK)

    col = [70, 150, 750, 870, 980, 1100, 1320, 1460, 1600, 1720]
    labels = ["#", "谱面 / Chart", "CID", "榜位", "评级", "分数", "准确率", "Combo", "Mod", "动态时间"]

    f_hdr = get_text_font("测试", 18, bold=True)
    for x, lb in zip(col, labels):
        draw_text(draw, (x, hdr_y + 25), lb, f_hdr, TEXT_MUTED, anchor="lm")

    for i, s in enumerate(scores):
        y = y0 + i * (row_h + row_gap)

        draw.rounded_rectangle((40, y, W - 40, y + row_h), radius=16, fill=(42, 34, 38, 170))

        idx = s.get("index", i + 1)
        idx_color = get_rank_color(idx) if idx in (1, 2, 3) else TEXT_WHITE
        draw_text(draw, (col[0], y + row_h // 2), str(idx), poppins_bold(22), idx_color, anchor="lm")

        ch = s.get("chart", {})
        ttl = ch.get("title", "") or f"c{s.get('cid', 0)}"
        lv = ch.get("level", 0)
        if lv:
            ttl = f"{ttl} Lv.{lv}"

        f_ttl = get_text_font(ttl, 22)
        ttl_disp = truncate_text(ttl, f_ttl, 560)
        draw_text(draw, (col[1], y + row_h // 2), ttl_disp, f_ttl, TEXT_WHITE, anchor="lm")

        draw_text(draw, (col[2], y + row_h // 2), f"c{s.get('cid', 0)}", torus_semibold(18), TEXT_GRAY, anchor="lm")

        rk = s.get("ranking", 0)
        rk_str = f"#{rk}" if rk else "—"
        draw_text(draw, (col[3], y + row_h // 2), rk_str, torus_bold(20), TEXT_WHITE if rk else TEXT_GRAY, anchor="lm")

        g = _calc_grade(s.get("accuracy", 0), s.get("miss", 0), s.get("best", 0), s.get("cool", 0), s.get("good", 0))
        gc = GRADE_COLORS.get(g, TEXT_WHITE)
        draw_text(draw, (col[4], y + row_h // 2), g, poppins_bold(24), gc, anchor="lm")

        draw.rounded_rectangle((40, y, 46, y + row_h), radius=6, fill=(*gc, 180))

        score_str = _fmt_score(s.get("score", 0))
        draw_text(draw, (col[5], y + row_h // 2), score_str, poppins_bold(22), TEXT_WHITE, anchor="lm")

        acc_str = f"{s.get('accuracy', 0):.2f}%"
        draw_text(draw, (col[6], y + row_h // 2), acc_str, torus_bold(20), TEXT_WHITE, anchor="lm")

        cmb_str = f"{s.get('combo', 0):,}"
        draw_text(draw, (col[7], y + row_h // 2), cmb_str, torus_bold(20), TEXT_WHITE, anchor="lm")

        mod = s.get("mod") or "—"
        mod_str = str(mod)
        if len(mod_str) > 10:
            mod_str = mod_str[:8] + "…"
        mod_color = (130, 210, 255, 255) if mod != "—" else TEXT_GRAY
        draw_text(draw, (col[8], y + row_h // 2), mod_str, torus_semibold(18), mod_color, anchor="lm")

        time_str = s.get("activity_time_str", "")[:16]
        draw_text(draw, (col[9], y + row_h // 2), time_str, torus_semibold(16), TEXT_MUTED, anchor="lm")

    foot_y = H - 40
    f_foot = get_text_font("Malody", 16)
    draw_text(draw, (40, foot_y), "Malody Recent Scores  //  powered by MalodyBot", f_foot, TEXT_MUTED, anchor="lm")

    return export_jpeg(canvas) if output_format != "png" else export_png(canvas)