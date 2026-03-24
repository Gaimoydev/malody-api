"""颜色常量"""

MODE_NAMES = {
    0: "KEY", 1: "STEP", 2: "DJ", 3: "CATCH", 4: "PAD",
    5: "TAIKO", 6: "RING", 7: "SLIDE", 8: "LIVE", 9: "CUBE",
}

BG_PRIMARY = (30, 30, 40, 255)
BG_SECONDARY = (40, 40, 55, 255)
BG_CARD = (50, 50, 68, 230)
BG_CARD_HOVER = (60, 60, 80, 240)

TEXT_WHITE = (255, 255, 255, 255)
TEXT_GRAY = (180, 180, 190, 255)
TEXT_MUTED = (120, 120, 135, 255)
TEXT_ACCENT = (255, 204, 34, 255)
TEXT_RANK_TOP = (255, 215, 0, 255)

MODE_COLORS = {
    0: (102, 204, 255), 1: (255, 153, 102), 2: (178, 102, 255),
    3: (102, 255, 178), 4: (255, 102, 153), 5: (255, 204, 0),
    6: (0, 204, 204), 7: (204, 102, 255), 8: (255, 128, 128), 9: (128, 200, 255),
}

GRADIENT_BANNER_TOP = (60, 20, 80)
GRADIENT_BANNER_BOTTOM = (20, 20, 60)
GRADIENT_OVERLAY = (0, 0, 0, 160)

BORDER_SUBTLE = (70, 70, 90, 180)
SEPARATOR = (80, 80, 100, 100)

RANK_COLORS = {1: (255, 215, 0), 2: (192, 192, 192), 3: (205, 127, 50)}


def get_mode_color(mode: int, alpha: int = 255) -> tuple:
    return (*MODE_COLORS.get(mode, (180, 180, 180)), alpha)


def get_rank_color(rank) -> tuple:
    if not isinstance(rank, (int, float)) or rank is None:
        return TEXT_GRAY
    rank = int(rank)
    if rank <= 0:
        return TEXT_GRAY
    if rank <= 3:
        return (*RANK_COLORS.get(rank, (255, 255, 255)), 255)
    if rank <= 10:
        return TEXT_ACCENT
    if rank <= 50:
        return TEXT_WHITE
    return TEXT_GRAY
