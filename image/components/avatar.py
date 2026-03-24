"""头像组件"""
from PIL import Image
from ..renderer import circle_crop, fetch_avatar, _default_avatar


async def render_avatar(url: str = "", size: int = 80) -> Image.Image:
    if url:
        return await fetch_avatar(url, size)
    return _default_avatar(size)
