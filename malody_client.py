"""Malody API 客户端 — api.mugzone.net"""
import re
import aiohttp
from typing import Optional, List, Dict, Any
from datetime import datetime

API_BASE = "https://api.mugzone.net"
HEADERS = {"User-Agent": "MalodyPythonWrapper/1.0"}
MODE_NAMES = {
    0: "Key", 1: "Step", 2: "DJ", 3: "Catch", 4: "Pad",
    5: "Taiko", 6: "Ring", 7: "Slide", 8: "Live", 9: "Cube",
}
STORE_TYPE_MAP = {"Key": 2, "Catch": 3, "Pad": 4, "Taiko": 5, "Ring": 6, "Slide": 7, "Live": 8, "Cube": 9}


class MalodyClient:

    async def _api(self, path: str, params: Optional[dict] = None) -> dict:
        if params is None:
            params = {}
        params.setdefault("uid", "1")
        url = f"{API_BASE}{path}"
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    raise Exception(f"API 请求失败: HTTP {resp.status} — {url}")
                data = await resp.json(content_type=None)
                if data.get("code", 0) != 0 and data.get("code") is not None:
                    if data.get("data") is None and "code" in data:
                        raise Exception(f"API 返回错误: code={data['code']}")
                return data

    # ── 玩家搜索 ──

    async def search_player(self, keyword: str) -> Optional[Dict[str, Any]]:
        data = await self._api("/api/player/search", {"keyword": keyword, "from": 0, "limit": 20})
        results = data.get("data", [])
        if len(results) == 1:
            return results[0]
        exact = [r for r in results if r.get("username", "").lower() == keyword.lower()]
        return exact[0] if len(exact) == 1 else None

    async def search_player_list(self, keyword: str, limit: int = 20) -> List[Dict]:
        data = await self._api("/api/player/search", {"keyword": keyword, "from": 0, "limit": limit})
        return data.get("data", [])

    # ── 玩家信息 ──

    async def resolve_player(self, identifier: str) -> int:
        if identifier.isdigit():
            return int(identifier)
        player = await self.search_player(identifier)
        if not player:
            raise Exception(f"找不到玩家: {identifier}")
        return player["uid"]

    async def get_player_info(self, identifier: str) -> Dict[str, Any]:
        touid = await self.resolve_player(identifier)
        info_data = await self._api("/api/player/info", {"touid": touid})
        rank_data = await self._api("/api/ranking/player/all", {"touid": touid})

        uid_val = info_data.get("uid", touid)
        modes = []
        for m in rank_data.get("data", []):
            modes.append({
                "mode": m.get("mode", 0),
                "mode_name": MODE_NAMES.get(m.get("mode", 0), "?"),
                "rank": m.get("rank", 0),
                "level": m.get("level", 0),
                "play_count": m.get("pc", 0),
                "accuracy": round(m.get("acc", 0), 2),
                "combo": m.get("combo", 0),
                "grade": m.get("grade", 0),
                "grade_rank": m.get("gradeRank", 0),
            })

        pts = info_data.get("playTime", 0)
        result = {
            "uid": touid,
            "name": info_data.get("username", f"Player_{touid}"),
            "avatar_url": f"https://cni.machart.top/avatar/{uid_val}",
            "gold": info_data.get("gold", 0),
            "play_time": f"{pts // 3600}h {(pts % 3600) // 60}m",
            "play_time_seconds": pts,
            "reg_time": info_data.get("regtime", 0),
            "last_play": info_data.get("lastPlay", 0),
            "stable_charts": info_data.get("stableCharts", 0),
            "area": info_data.get("area", 0),
            "active": info_data.get("active", 0),
            "modes": modes,
        }

        try:
            wiki_data = await self._api("/api/community/wiki", {"touid": touid, "lang": 0, "raw": 1})
            result["wiki"] = wiki_data.get("wiki", "")
        except Exception:
            result["wiki"] = ""

        return result

    async def get_player_activity(self, identifier: str, limit: int = 15) -> List[Dict]:
        touid = await self.resolve_player(identifier)
        data = await self._api("/api/player/activity", {"touid": touid})
        activities = []
        for a in data.get("data", [])[:limit]:
            activities.append({
                "time": a.get("time", 0),
                "time_str": datetime.fromtimestamp(a["time"]).strftime("%Y-%m-%d %H:%M") if a.get("time") else "",
                "message": a.get("msg", ""),
                "link": a.get("link", ""),
            })
        return activities

    # ── 全局排行榜 (API) ──

    async def get_global_rankings(self, mode: int = 0, mm: int = 1, limit: int = 40) -> List[Dict[str, Any]]:
        data = await self._api("/api/ranking/global", {"mm": mm, "mode": mode, "from": 0, "ver": 0})
        players = []
        for p in data.get("data", [])[:limit]:
            uid = p.get("uid", 0)
            players.append({
                "rank": p.get("rank", 0),
                "name": p.get("username", "?"),
                "uid": uid,
                "avatar_url": f"https://cni.machart.top/avatar/{uid}" if uid else "",
                "level": p.get("level", 0),
                "accuracy": round(p.get("acc", 0), 2),
                "combo": p.get("combo", 0),
                "play_count": p.get("playcount", 0),
                "grade": p.get("value", 0),
                "mode": mode,
            })
        return players

    # ── 排行榜 (网页抓取，备用) ──

    async def get_rankings(self, mode: int = 0, page: int = 0) -> List[Dict[str, Any]]:
        from bs4 import BeautifulSoup
        url = f"https://m.mugzone.net/page/all/player?from={page}&mode={mode}"
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception(f"排行榜页面请求失败: HTTP {resp.status}")
                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        players = []
        for item in soup.select("div.item-top"):
            p = self._parse_ranking_item_top(item, mode)
            if p:
                players.append(p)
        for item in soup.select("div.item"):
            p = self._parse_ranking_item(item, mode)
            if p:
                players.append(p)
        return players

    # ── 谱面 ──

    async def get_chart_meta(self, cid: int) -> Dict[str, Any]:
        try:
            url = f"https://m.mugzone.net/chart/{cid}"
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return {}
                    html = await resp.text()

            title_m = re.search(r'<title>Malody - (.+?)</title>', html)
            title = title_m.group(1).strip() if title_m else ""

            cover_m = re.search(r'og:image" content="([^"]+)"', html)
            cover_url = cover_m.group(1).strip() if cover_m else ""
            if cover_url.startswith("http://"):
                cover_url = cover_url.replace("http://", "https://", 1)

            creator_m = re.search(r'Created by:\s*</span>.*?alt="([^"]+)"', html, re.S)
            creator = creator_m.group(1).strip() if creator_m else ""

            length_m = re.search(r'<label>Length</label>:<span>(\d+)s</span>', html)
            length = int(length_m.group(1)) if length_m else 0

            bpm_m = re.search(r'<label>BPM</label>:<span>(\d+)</span>', html)
            bpm = int(bpm_m.group(1)) if bpm_m else 0

            hot_m = re.search(r'<span>Hot</span><span class="l">(\d+)</span>', html)
            hot = int(hot_m.group(1)) if hot_m else 0

            return {"title": title, "cover_url": cover_url, "creator": creator, "length": length, "bpm": bpm, "hot": hot}
        except Exception:
            return {}

    async def get_chart_scores(self, cid: int, limit: int = 30) -> Dict[str, Any]:
        data = await self._api("/api/ranking/list", {"cid": cid, "from": 0})
        meta = await self.get_chart_meta(cid)

        chart_info = {
            "cid": data.get("cid", cid),
            "sid": data.get("sid", 0),
            "level": data.get("meta", {}).get("level", 0),
            "title": meta.get("title", ""),
            "cover_url": meta.get("cover_url", ""),
        }

        scores = []
        for s in data.get("data", [])[:limit]:
            scores.append({
                "ranking": s.get("ranking", 0),
                "player": {"uid": s.get("uid", 0), "name": s.get("username", "?"), "avatar_url": ""},
                "score": s.get("score", 0),
                "combo": s.get("combo", 0),
                "accuracy": round(s.get("acc", 0), 2),
                "fc": s.get("fc", False),
                "rank_grade": s.get("rank", 0),
                "mod": s.get("mod", 0),
                "best": s.get("best", 0),
                "cool": s.get("cool", 0),
                "good": s.get("good", 0),
                "miss": s.get("miss", 0),
                "time": s.get("time", 0),
                "time_str": datetime.fromtimestamp(s["time"]).strftime("%Y-%m-%d %H:%M") if s.get("time") else "",
            })

        return {
            "chart": chart_info,
            "scores": scores,
            "total": len(scores),
            "fetched_at": datetime.now().isoformat(),
        }

    async def get_player_chart_score(self, identifier: str, cid: int) -> Optional[Dict]:
        touid = await self.resolve_player(identifier)
        data = await self._api("/api/ranking/list", {"cid": cid, "from": 0})
        all_scores = data.get("data", [])
        chart_max_combo = max((s.get("combo", 0) for s in all_scores), default=0)

        for s in all_scores:
            if s.get("uid") == touid:
                return {
                    "ranking": s.get("ranking", 0),
                    "player": {"uid": touid, "name": s.get("username", "?")},
                    "score": s.get("score", 0),
                    "combo": s.get("combo", 0),
                    "accuracy": round(s.get("acc", 0), 2),
                    "fc": s.get("fc", False),
                    "rank_grade": s.get("rank", 0),
                    "mod": s.get("mod", 0),
                    "judge": s.get("judge", 0),
                    "pro": s.get("pro", False),
                    "best": s.get("best", 0),
                    "cool": s.get("cool", 0),
                    "good": s.get("good", 0),
                    "miss": s.get("miss", 0),
                    "time": s.get("time", 0),
                    "time_str": datetime.fromtimestamp(s["time"]).strftime("%Y-%m-%d %H:%M") if s.get("time") else "",
                    "chart": {
                        "cid": data.get("cid", cid),
                        "sid": data.get("sid", 0),
                        "level": data.get("meta", {}).get("level", 0),
                        "max_combo": chart_max_combo,
                    },
                }
        return None

    # ── 谱面搜索 ──

    async def search_charts(self, word: str, mode: int = 0, sort: str = "time",
                            order: str = "desc", limit: int = 20) -> List[Dict]:
        type_val = mode + 2 if mode >= 0 else 2
        data = await self._api("/api/store/list2", {
            "mcver": 1, "from": 0, "sort": sort, "order": order,
            "org": 1, "mode": 0, "type": type_val, "word": word,
        })
        results = []
        for c in data.get("data", [])[:limit]:
            cover = c.get("cover", "")
            if cover and not cover.startswith("http"):
                cover = f"https://cni.machart.top{cover}"
            results.append({
                "sid": c.get("sid", 0),
                "title": c.get("title", ""),
                "artist": c.get("artist", ""),
                "cover_url": cover,
                "length": c.get("length", 0),
                "bpm": c.get("bpm", 0),
                "mode": c.get("mode", 0),
                "last_edit": c.get("lastedit", 0),
            })
        return results

    # ── 网页排行榜解析辅助 ──

    def _parse_ranking_item_top(self, item, mode: int) -> Optional[Dict]:
        label = item.select_one("i.label")
        rank = None
        if label and label.has_attr("class"):
            for c in label["class"]:
                if c.startswith("top-"):
                    try:
                        rank = int(c.replace("top-", ""))
                    except ValueError:
                        pass
        name_tag = item.select_one("span.name a")
        uid = self._extract_uid(name_tag)
        avatar = self._extract_avatar(item)
        lv, exp = self._parse_lv_exp(item.select_one("span.lv"))
        acc = self._safe_float(item.select_one("span.acc"), remove=["Acc:", "%"])
        combo = self._safe_int(item.select_one("span.combo"), remove=["Combo:"])
        pc = self._safe_int(item.select_one("span.pc"), digits_only=True)
        return {
            "rank": rank or 0, "name": name_tag.text.strip() if name_tag else "?",
            "uid": uid or 0, "avatar_url": avatar, "level": lv, "exp": exp,
            "accuracy": acc or 0, "combo": combo or 0, "play_count": pc or 0, "mode": mode,
        }

    def _parse_ranking_item(self, item, mode: int) -> Optional[Dict]:
        rank_tag = item.select_one("span.rank")
        rank = self._safe_int(rank_tag)
        if rank is None:
            return None
        name_tag = item.select_one("span.name a")
        uid = self._extract_uid(name_tag)
        avatar = self._extract_avatar(item)
        lv = self._safe_int(item.select_one("span.lv")) or 0
        exp = self._safe_int(item.select_one("span.exp")) or 0
        acc = self._safe_float(item.select_one("span.acc"), remove=["%"])
        combo = self._safe_int(item.select_one("span.combo"))
        pc = self._safe_int(item.select_one("span.pc"), digits_only=True)
        return {
            "rank": rank, "name": name_tag.text.strip() if name_tag else "?",
            "uid": uid or 0, "avatar_url": avatar, "level": lv, "exp": exp,
            "accuracy": acc or 0, "combo": combo or 0, "play_count": pc or 0, "mode": mode,
        }

    @staticmethod
    def _extract_uid(tag) -> Optional[int]:
        if not tag or not tag.has_attr("href"):
            return None
        m = re.search(r"/accounts/user/(\d+)", tag["href"])
        return int(m.group(1)) if m else None

    @staticmethod
    def _extract_avatar(item) -> str:
        img = item.select_one("img.avatar, span.rank img, img")
        return img["src"] if img and img.has_attr("src") else ""

    @staticmethod
    def _parse_lv_exp(tag):
        if not tag:
            return 0, 0
        txt = tag.text.strip()
        if "-" in txt:
            parts = txt.split("-")
            try:
                lv = int(parts[0].replace("Lv.", "").strip())
            except ValueError:
                lv = 0
            try:
                exp = int(parts[1].strip())
            except ValueError:
                exp = 0
            return lv, exp
        try:
            return int(txt.replace("Lv.", "").strip()), 0
        except ValueError:
            return 0, 0

    @staticmethod
    def _safe_int(tag, remove=None, digits_only=False):
        if not tag:
            return None
        txt = tag.text.strip()
        if remove:
            for r in remove:
                txt = txt.replace(r, "")
        if digits_only:
            txt = "".join(filter(str.isdigit, txt))
        try:
            return int(txt.strip().replace(",", ""))
        except ValueError:
            return None

    @staticmethod
    def _safe_float(tag, remove=None):
        if not tag:
            return None
        txt = tag.text.strip()
        if remove:
            for r in remove:
                txt = txt.replace(r, "")
        try:
            return float(txt.strip())
        except ValueError:
            return None
