import asyncio
from contextlib import asynccontextmanager
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from routes import register_routes
from agents.services.agent_store import close_agent_store, configure_agent_store
from rag.services.chunk_store import configure_chunk_store
from auth.middleware import AuthMiddleware
from users.seed import seed_super_admin
from settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_agent_store(settings.mongo_uri, settings.mongo_database)
    configure_chunk_store(settings.qdrant_url, settings.qdrant_api_key or None)
    logger.info("Qdrant connecting to: %s", settings.qdrant_url)
    try:
        from rag.services.chunk_store import get_chunk_store_instance
        store = get_chunk_store_instance()
        collections = await asyncio.to_thread(store._client.get_collections)
        logger.info("Qdrant startup check OK — collections: %s", [c.name for c in collections.collections])
    except Exception as e:
        logger.error("Qdrant startup check FAILED: %s", e)
    seed_super_admin()
    logger.info("application startup complete")
    yield
    close_agent_store()
    logger.info("Shutting down application")

app = FastAPI(
    title="Maverick API",
    description="Backend API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "https://maverickai.in","https://maverick-psi.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)

register_routes(app)


@app.get("/health")
async def health():
    return {"status": "ok"}

handler = Mangum(app)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)
