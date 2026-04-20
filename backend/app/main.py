from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import run_migrations


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        run_migrations(settings.db_path)
        yield

    application = FastAPI(title="NYC Dining", lifespan=lifespan)
    frontend_dir: Path = settings.frontend_dir

    @application.get("/healthz")
    def healthz() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return {"status": "ok"}

    @application.get("/")
    def root() -> FileResponse:  # pyright: ignore[reportUnusedFunction]
        return FileResponse(frontend_dir / "index.html", media_type="text/html")

    application.mount("/css", StaticFiles(directory=frontend_dir / "css"), name="css")
    application.mount("/js", StaticFiles(directory=frontend_dir / "js"), name="js")

    return application


app = create_app()
