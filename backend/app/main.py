from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.auth import SESSION_COOKIE, read_session
from app.config import get_settings
from app.db import run_migrations

PUBLIC_PREFIXES = ("/healthz", "/login", "/api/login/", "/css/", "/js/")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self'; "
        "script-src 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'; "
        "base-uri 'self'"
    ),
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        return response


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, signing_key_getter: Callable[[], str]) -> None:
        super().__init__(app)
        self._signing_key_getter = signing_key_getter

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        if path in {"/login", "/healthz"} or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        token = request.cookies.get(SESSION_COOKIE)
        key = self._signing_key_getter()
        session = read_session(token, key) if token else None
        if session is None:
            if path.startswith("/api/"):
                return JSONResponse({"detail": "unauthorized"}, status_code=401)
            return RedirectResponse("/login", status_code=303)
        request.state.user_id = session[0]
        request.state.display_name = session[1]
        return await call_next(request)


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        run_migrations(settings.db_path)
        yield

    application = FastAPI(title="NYC Dining", lifespan=lifespan)
    frontend_dir: Path = settings.frontend_dir

    application.add_middleware(
        AuthMiddleware, signing_key_getter=lambda: get_settings().cookie_signing_key
    )
    application.add_middleware(SecurityHeadersMiddleware)

    @application.get("/healthz")
    def healthz() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return {"status": "ok"}

    @application.get("/login")
    def login_page() -> FileResponse:  # pyright: ignore[reportUnusedFunction]
        return FileResponse(frontend_dir / "login.html", media_type="text/html")

    @application.get("/")
    def root() -> FileResponse:  # pyright: ignore[reportUnusedFunction]
        return FileResponse(frontend_dir / "index.html", media_type="text/html")

    @application.get("/api/whoami")
    def whoami(request: Request) -> dict[str, object]:  # pyright: ignore[reportUnusedFunction]
        user_id = getattr(request.state, "user_id", None)
        display_name = getattr(request.state, "display_name", None)
        if user_id is None:
            raise HTTPException(status_code=401, detail="unauthorized")
        return {"user_id": user_id, "display_name": display_name}

    application.mount("/css", StaticFiles(directory=frontend_dir / "css"), name="css")
    application.mount("/js", StaticFiles(directory=frontend_dir / "js"), name="js")

    from app.routes import auth as auth_routes
    from app.routes import availability as availability_routes
    from app.routes import search as search_routes

    application.include_router(auth_routes.router)
    application.include_router(search_routes.router)
    application.include_router(availability_routes.router)

    return application


app = create_app()
