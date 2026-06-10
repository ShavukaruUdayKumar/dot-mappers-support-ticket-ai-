"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.data.loader import data_loader
from app.core.config import get_settings
from app.core.exceptions import DataLoadError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data on startup, cleanup on shutdown."""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    try:
        data_loader.load_data(settings.data_path)
        logger.info(f"Data loaded: {len(data_loader.get_data())} tickets")
    except DataLoadError as e:
        logger.error(f"Failed to load data: {str(e)}")
        raise
    
    yield
    
    logger.info("Shutting down application")


app = FastAPI(
    title="Support Ticket AI System",
    description="""
AI-powered support ticket analysis with natural language querying and anomaly detection.

## Features
- **Natural Language Queries**: Ask questions in plain English
- **Hybrid Anomaly Detection**: Rule-based + Statistical (Z-score)
- **Structured Outputs**: Pydantic-validated responses
- **Dataset Stats & Schema**: Instant dataset insights

## Architecture
- LLM converts NL → Structured JSON Intent → Pandas executes → LLM narrates result
- Anomaly detection: rule-based business rules + Z-score statistical outliers
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, tags=["Support Tickets"])


@app.get("/ping", include_in_schema=False)
async def ping():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
