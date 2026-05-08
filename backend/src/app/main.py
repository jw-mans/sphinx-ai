from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
import logging

from prometheus_fastapi_instrumentator import Instrumentator

from src.app.api.routers import router as interview_router
from src.app.db.base import Base
from src.app.db.session import engine
from src.app.exceptions import NotFoundError, ConflictError, LLMServiceError, DatabaseError
from src.app.config import settings
import src.app.metrics  # noqa: F401 — registers custom metrics on import


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    bot = None
    polling_task = None
    if settings.BOT_TOKEN and settings.WEBAPP_URL:
        import asyncio
        from aiogram import Bot
        from src.app.bot import build_dispatcher
        bot = Bot(token=settings.BOT_TOKEN)
        dp = build_dispatcher(settings.WEBAPP_URL)
        await bot.delete_webhook(drop_pending_updates=True)
        polling_task = asyncio.create_task(dp.start_polling(bot))
        logger.info("Telegram bot started")
    else:
        logger.info("BOT_TOKEN or WEBAPP_URL not set — Telegram bot disabled")

    yield

    if bot and polling_task:
        polling_task.cancel()
        await bot.session.close()
        logger.info("Telegram bot stopped")

    logger.info("Application shutting down")


app = FastAPI(
    title="Sphinx - AI Interview Simulator",
    description="API для симулятора технических интервью с ИИ",
    version="1.0.0",
    lifespan=lifespan
)

# Prometheus HTTP metrics (latency, request counts, status codes)
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

_cors_origins = [settings.FRONTEND_URL] if settings.FRONTEND_URL else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": exc.message})


@app.exception_handler(LLMServiceError)
async def llm_error_handler(request: Request, exc: LLMServiceError):
    logger.error(f"LLM service error: {exc.message}")
    return JSONResponse(status_code=503, content={"detail": exc.message})


@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    logger.error(f"Database error: {exc.message}")
    return JSONResponse(status_code=500, content={"detail": "Database error"})


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Unhandled SQLAlchemy error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Database error"})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(interview_router)


@app.get("/")
async def root():
    return {"message": "AI Interview Simulator API"}


@app.get("/health")
async def health():
    return {"status": "ok"}
