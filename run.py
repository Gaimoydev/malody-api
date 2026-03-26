#!/usr/bin/env python3
import os
import sys
from datetime import datetime

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles


def create_app() -> FastAPI:
    app = FastAPI(
        title="Malody API", version="2.0.0",
        description="malody",
        docs_url="/docs", redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_error(request, exc):
        return JSONResponse(status_code=500, content={
            "success": False, "error": str(exc), "timestamp": datetime.now().isoformat(),
        })

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "message": "Malody API running",
            "version": "2.0.0",
            "docs": "/docs",
            "endpoints": {
                "rankings": "/api/rankings",
                "global_ranking": "/api/ranking/global",
                "player": "/api/player/{name}",
                "player_image": "/api/player/{name}/image",
                "chart": "/api/chart/{cid}",
                "chart_image": "/api/chart/{cid}/image",
                "player_recent_scores": "/api/player/{name}/recent-scores",
                "player_recent_scores_image": "/api/player/{name}/recent-scores/image",
                "player_trends": "/api/analytics/player-trends/{name}/image",
            },
        }

    @app.get("/health", include_in_schema=False)
    async def health():
        return {"status": "ok"}

    return app


def _ensure_import_paths():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    for d in (parent_dir, current_dir):
        if d not in sys.path:
            sys.path.insert(0, d)


def register_routers(app: FastAPI):
    _ensure_import_paths()
    from routers.api import router as api_router
    app.include_router(api_router)


def mount_static(app: FastAPI):
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "temp")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


def main():
    _ensure_import_paths()
    app = create_app()
    register_routers(app)
    mount_static(app)
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    main()
