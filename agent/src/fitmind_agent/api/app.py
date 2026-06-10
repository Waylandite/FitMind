from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fitmind_agent.api.routes import chat, memory, meta
from fitmind_agent.api.routes import llm
from fitmind_agent.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
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
    app.include_router(chat.router, prefix=settings.api_prefix)
    app.include_router(llm.router, prefix=settings.api_prefix)
    app.include_router(memory.router, prefix=settings.api_prefix)

    @app.get("/healthz", tags=["system"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app
