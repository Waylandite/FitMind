from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fitmind_agent.api.routes import analytics, auth, chat, memory, meta, profile, workouts
from fitmind_agent.api.routes import llm
from fitmind_agent.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.environment != "local" and (
        len(settings.auth_secret_key) < 32
        or settings.auth_secret_key == "local-development-only-change-me"
    ):
        raise RuntimeError("FITMIND_AUTH_SECRET_KEY must be a non-default value of at least 32 characters")
    if settings.environment != "local" and not settings.auth_cookie_secure:
        raise RuntimeError("FITMIND_AUTH_COOKIE_SECURE must be true outside local development")
    web_origins = {
        settings.web_origin,
        settings.web_origin.replace("localhost", "127.0.0.1"),
        settings.web_origin.replace("127.0.0.1", "localhost"),
    }

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(web_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(meta.router, prefix=settings.api_prefix)
    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(chat.router, prefix=settings.api_prefix)
    app.include_router(llm.router, prefix=settings.api_prefix)
    app.include_router(memory.router, prefix=settings.api_prefix)
    app.include_router(profile.router, prefix=settings.api_prefix)
    app.include_router(workouts.router, prefix=settings.api_prefix)
    app.include_router(analytics.router, prefix=settings.api_prefix)

    @app.get("/healthz", tags=["system"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app
