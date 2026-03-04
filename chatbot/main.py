import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.exceptions import ChatbotException, chatbot_exception_handler
from app.services.memory import init_db
from app.services.sheets import sheets_service
from app.api.v1 import chat, knowledge, health, sheets


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("app.startup", name=settings.APP_NAME, env=settings.APP_ENV)

    # 1. Khoi tao SQLite (tao bang neu chua co)
    await init_db()

    # 2. Sync du lieu Google Sheets -> Chroma lan dau
    asyncio.create_task(sheets_service.start_auto_sync())

    yield
    logger.info("app.shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(ChatbotException, chatbot_exception_handler)

# API Routers
app.include_router(health.router)
app.include_router(chat.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(sheets.router, prefix="/api/v1")

# Serve static files (Web UI)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_ui():
        return FileResponse(os.path.join(static_dir, "index.html"))
