"""Competitor Analysis API - FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, close_db
from app.api import routes, competitors, analysis, insights, export


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Competitor analysis tool: AskNews data, AI insights, PDF/CSV export",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(routes.router, prefix="/api", tags=["api"])
    app.include_router(competitors.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(insights.router, prefix="/api")
    app.include_router(export.router, prefix="/api")

    @app.get("/")
    def root():
        return {
            "message": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "api": "/api",
        }

    return app


app = create_app()
