from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth

app = FastAPI(title="izanagi API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

# Integrate business API routes from src/web
from src.web.app import create_router as create_business_router
from src.web import db as web_db
from src.config import Config as BusinessConfig

web_db_path = web_db.DEFAULT_DB_PATH
web_db.init_db(web_db_path)
business_router = create_business_router(web_db_path, BusinessConfig())
app.include_router(business_router)


@app.get("/health")
def health():
    return {"status": "ok"}
