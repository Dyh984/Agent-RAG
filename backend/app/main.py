from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.knowledge_bases import router as knowledge_bases_router
from app.core.config import PROJECT_ROOT

app = FastAPI(title="Agent RAG API", version="0.1.0")
app.include_router(health_router, prefix="/api")
app.include_router(knowledge_bases_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.mount(
    "/",
    StaticFiles(directory=PROJECT_ROOT / "frontend", html=True),
    name="frontend",
)
