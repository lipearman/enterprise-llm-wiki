from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.chat import router as chat_router
from app.api.sources import router as sources_router
from app.api.wiki import router as wiki_router
from app.api.jobs import router as jobs_router
from app.api.health import router as health_router

app = FastAPI(title=settings.APP_NAME, version="0.1.0")

origins = ["*"] if settings.ALLOW_ORIGINS == "*" else [x.strip() for x in settings.ALLOW_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(sources_router)
app.include_router(wiki_router)
app.include_router(jobs_router)

@app.get("/")
def root():
    return {"name": settings.APP_NAME, "docs": "/docs"}
