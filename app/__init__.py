from fastapi import FastAPI

from app.api import routes
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Research App API",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(routes.router, prefix="/api", tags=["api"])

    @app.get("/")
    def root():
        return {"message": "Research App API", "docs": "/docs", "api": "/api"}

    return app


app = create_app()
