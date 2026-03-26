from datetime import datetime

from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import Response, JSONResponse

from malody_client import MalodyClient, MODE_NAMES
from utils.temp_image import save_temp_image_url_payload
from image.panels.panel_card_list import render_card_list
from image.panels.panel_dashboard import render_dashboard
from image.panels.panel_score import render_score_panel
from image.panels.panel_trends import render_trends
from image.panels.panel_recent_scores import render_player_recent_scores_panel

router = APIRouter(prefix="/api", tags=["malody"])
client = MalodyClient()

MODE_NAME_TO_ID = {
    "key": 0, "catch": 3, "pad": 4, "taiko": 5,
    "ring": 6, "slide": 7, "live": 8, "cube": 9,
}


def _resolve_mode(s: str) -> int:
    return int(s) if s.isdigit() else MODE_NAME_TO_ID.get(s.lower(), 0)


def _ok(data, message: str = "ok"):
    return {"success": True, "data": data, "message": message, "timestamp": datetime.now().isoformat()}


def _err(message: str, code: int = 400):
    return JSONResponse(status_code=code, content={
        "success": False, "error": message, "timestamp": datetime.now().isoformat(),
    })


def _image_or_url(request: Request, img_bytes: bytes, fmt: str, is_url: bool, img_url_time: int):
    if not is_url:
        return Response(content=img_bytes, media_type=f"image/{fmt}")
    return _ok(save_temp_image_url_payload(request, img_bytes, fmt, img_url_time), "图片临时 URL")


def _parse_cid(cid_str: str) -> int:
    cleaned = cid_str.strip().lower().lstrip("c")
    try:
        return int(cleaned)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的谱面码: {cid_str}")


def _pick_mode(modes: list, mode_str: str = ""):
    if mode_str:
        mid = _resolve_mode(mode_str)
        for m in modes:
            if m.get("mode") == mid:
                return m
    return min(modes, key=lambda m: m.get("rank", 999999) or 999999) if modes else None


@router.get("/rankings")
async def get_rankings(mode: int = Query(0, ge=0, le=9), limit: int = Query(50, ge=1, le=200)):
    players = await client.get_rankings(mode)
    return _ok(players[:limit], f"{MODE_NAMES.get(mode, '?')} 排行榜 Top {min(limit, len(players))}")


@router.get("/rankings/image")
async def get_rankings_image(
    request: Request,
    mode: int = Query(0, ge=0, le=9), limit: int = Query(20, ge=1, le=50), fmt: str = Query("jpeg"),
    is_url: bool = Query(False), img_url_time: int = Query(300, ge=1, le=604800),
):
    players = await client.get_rankings(mode)
    img = await render_card_list(players=players[:limit], mode=mode, output_format=fmt)
    return _image_or_url(request, img, fmt, is_url, img_url_time)


@router.get("/ranking/global")
async def get_global_ranking(mode: str = Query("key"), mm: int = Query(1, ge=0, le=1), limit: int = Query(40, ge=1, le=100)):
    mode_id = _resolve_mode(mode)
    players = await client.get_global_rankings(mode=mode_id, mm=mm, limit=limit)
    rank_type = "MM" if mm else "EXP"
    return _ok(players, f"{MODE_NAMES.get(mode_id, '?')} {rank_type} 排行榜 Top {len(players)}")


@router.get("/ranking/global/image")
async def get_global_ranking_image(
    request: Request,
    mode: str = Query("key"), mm: int = Query(1, ge=0, le=1), limit: int = Query(40, ge=1, le=50), fmt: str = Query("jpeg"),
    is_url: bool = Query(False), img_url_time: int = Query(300, ge=1, le=604800),
):
    mode_id = _resolve_mode(mode)
    players = await client.get_global_rankings(mode=mode_id, mm=mm, limit=limit)
    rank_type = "MM" if mm else "EXP"
    title = f"Malody {MODE_NAMES.get(mode_id, '?')} Global Ranking ({rank_type})"
    img = await render_card_list(players=players, mode=mode_id, title=title, output_format=fmt)
    return _image_or_url(request, img, fmt, is_url, img_url_time)


@router.get("/player/{identifier}")
async def get_player_info(identifier: str):
    try:
        data = await client.get_player_info(identifier)
    except Exception as e:
        return _err(str(e), 404)
    return _ok(data, f"玩家 {data.get('name', identifier)}")


@router.get("/player/{identifier}/image")
async def get_player_image(
    request: Request,
    identifier: str, mode: str = Query(""), fmt: str = Query("jpeg"),
    is_url: bool = Query(False), img_url_time: int = Query(300, ge=1, le=604800),
):
    try:
        data = await client.get_player_info(identifier)
        activities = await client.get_player_activity(identifier, 30)
    except Exception as e:
        return _err(str(e), 404)

    md = _pick_mode(data.get("modes", []), mode)
    mode_id = md.get("mode", 0) if md else 0
    img = await render_dashboard(player={
        "name": data.get("name", "?"), "uid": data.get("uid", 0),
        "avatar_url": data.get("avatar_url", ""),
        "rank": md.get("rank", 0) if md else 0,
        "level": md.get("level", 0) if md else 0,
        "accuracy": md.get("accuracy", 0) if md else 0,
        "combo": md.get("combo", 0) if md else 0,
        "play_count": md.get("play_count", 0) if md else 0,
        "gold": data.get("gold", 0), "play_time": data.get("play_time", ""),
        "wiki": data.get("wiki", ""), "activities": activities,
    }, mode=mode_id, output_format=fmt)
    return _image_or_url(request, img, fmt, is_url, img_url_time)


@router.get("/player/{identifier}/activity")
async def get_player_activity(identifier: str, limit: int = Query(15, ge=1, le=50)):
    try:
        activities = await client.get_player_activity(identifier, limit)
    except Exception as e:
        return _err(str(e), 404)
    return _ok(activities, f"最近 {len(activities)} 条活动记录")


@router.get("/player/{identifier}/recent-scores")
async def get_player_recent_scores(identifier: str):
    try:
        data = await client.get_player_recent_activity_scores(identifier)
    except Exception as e:
        return _err(str(e), 404)
    return _ok(data, f"玩家 {data['player'].get('name', identifier)} 最近上榜 {data['total']} 条")


@router.get("/player/{identifier}/recent-scores/image")
async def get_player_recent_scores_image(
    request: Request,
    identifier: str,
    fmt: str = Query("jpeg"),
    is_url: bool = Query(False), img_url_time: int = Query(300, ge=1, le=604800),
):
    try:
        data = await client.get_player_recent_activity_scores(identifier)
    except Exception as e:
        return _err(str(e), 404)
    scores = data.get("scores", [])
    if len(scores) <= 2:
        return _err("有效成绩不足 3 条（须大于 2 条），无法生成图片", 400)

    img = await render_player_recent_scores_panel(
        player={"name": data["player"].get("name", identifier), "avatar_url": data["player"].get("avatar_url", "")},
        scores=scores, output_format=fmt,
    )
    return _image_or_url(request, img, fmt, is_url, img_url_time)


@router.get("/player/search/{keyword}")
async def search_player(keyword: str, limit: int = Query(20, ge=1, le=50)):
    results = await client.search_player_list(keyword, limit)
    return _ok(results, f"搜索 '{keyword}' 共 {len(results)} 条结果")


@router.get("/chart/{cid_str}")
async def get_chart_scores(cid_str: str, limit: int = Query(30, ge=1, le=100)):
    cid = _parse_cid(cid_str)
    data = await client.get_chart_scores(cid, limit)
    return _ok(data, f"谱面 c{cid} 共 {data.get('total', 0)} 条成绩")


@router.get("/chart/{cid_str}/image")
async def get_chart_scores_image(
    request: Request,
    cid_str: str, limit: int = Query(30, ge=1, le=50), fmt: str = Query("jpeg"),
    is_url: bool = Query(False), img_url_time: int = Query(300, ge=1, le=604800),
):
    cid = _parse_cid(cid_str)
    data = await client.get_chart_scores(cid, limit)
    scores, chart_info = data.get("scores", []), data.get("chart", {})
    chart_title = chart_info.get("title", "") or f"Chart c{cid}"
    level = chart_info.get("level", 0)

    players = [{
        "rank": s.get("ranking", 0),
        "name": s.get("player", {}).get("name", "?"),
        "uid": (uid := s.get("player", {}).get("uid", 0)),
        "avatar_url": f"https://cni.machart.top/avatar/{uid}" if uid else "",
        "level": 0, "accuracy": s.get("accuracy", 0) or 0,
        "combo": s.get("combo", 0) or 0,
        "play_count": s.get("score", 0) or 0, "mode": 0,
    } for s in scores]

    display_title = f"{chart_title} Lv.{level}" if level else chart_title
    img = await render_card_list(players=players, mode=0, title=display_title, cover_url=chart_info.get("cover_url", ""), output_format=fmt)
    return _image_or_url(request, img, fmt, is_url, img_url_time)


@router.get("/chart/{cid_str}/player/{identifier}")
async def get_player_chart_score(cid_str: str, identifier: str):
    cid = _parse_cid(cid_str)
    try:
        result = await client.get_player_chart_score(identifier, cid)
    except Exception as e:
        return _err(str(e), 404)
    if not result:
        return _err(f"玩家 {identifier} 在谱面 c{cid} 中没有成绩", 404)
    return _ok(result, f"玩家 {identifier} 在谱面 c{cid} 的成绩")


@router.get("/chart/{cid_str}/player/{identifier}/image")
async def get_player_chart_score_image(
    request: Request,
    cid_str: str, identifier: str, fmt: str = Query("jpeg"),
    is_url: bool = Query(False), img_url_time: int = Query(300, ge=1, le=604800),
):
    cid = _parse_cid(cid_str)
    try:
        player_data = await client.get_player_info(identifier)
        result = await client.get_player_chart_score(identifier, cid)
        chart_meta = await client.get_chart_meta(cid)
    except Exception as e:
        return _err(str(e), 404)
    if not result:
        return _err(f"玩家 {identifier} 在谱面 c{cid} 中没有成绩", 404)

    img = await render_score_panel(
        score=result, player_name=player_data.get("name", identifier),
        avatar_url=player_data.get("avatar_url", ""),
        chart_title=chart_meta.get("title", ""),
        chart_level=result.get("chart", {}).get("level", 0),
        cover_url=chart_meta.get("cover_url", ""),
        chart_meta=chart_meta, player_data=player_data, output_format=fmt,
    )
    return _image_or_url(request, img, fmt, is_url, img_url_time)


@router.get("/charts/search")
async def search_charts(word: str = Query(...), mode: int = Query(0, ge=0, le=9), limit: int = Query(20, ge=1, le=50)):
    results = await client.search_charts(word, mode, limit=limit)
    return _ok(results, f"搜索 '{word}' 共 {len(results)} 条结果")


@router.get("/analytics/player-trends/{identifier}")
async def get_player_trends(identifier: str, mode: str = Query("")):
    try:
        data = await client.get_player_info(identifier)
    except Exception as e:
        return _err(str(e), 404)
    modes = data.get("modes", [])
    if mode:
        mid = _resolve_mode(mode)
        modes = [m for m in modes if m.get("mode") == mid]
    return _ok({"name": data.get("name"), "uid": data.get("uid"), "modes": modes},
               f"玩家 {data.get('name', identifier)} 趋势数据")


@router.get("/analytics/player-trends/{identifier}/image")
async def get_player_trends_image(
    request: Request,
    identifier: str, mode: str = Query(""), fmt: str = Query("jpeg"),
    is_url: bool = Query(False), img_url_time: int = Query(300, ge=1, le=604800),
):
    try:
        data = await client.get_player_info(identifier)
    except Exception as e:
        return _err(str(e), 404)
    modes = data.get("modes", [])
    if mode:
        mid = _resolve_mode(mode)
        modes = [m for m in modes if m.get("mode") == mid]
    img = await render_trends(
        player={"name": data.get("name", "?"), "uid": data.get("uid", 0),
                "avatar_url": data.get("avatar_url", ""), "gold": data.get("gold", 0),
                "play_time": data.get("play_time", "")},
        modes=modes, output_format=fmt,
    )
    return _image_or_url(request, img, fmt, is_url, img_url_time)
