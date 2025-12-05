# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from api import routes

app = FastAPI(
    title="DataHub Backend",
    description="ИИ-помощник для выбора вузов Казахстана",
    version="1.0.1"
)

# CORS - разрешить ВСЁ для разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)

@app.get("/")
async def root():
    return {
        "message": "Добро пожаловать в DataHub Backend!",
        "version": "1.0.1",
        "algorithm": "updated",
        "docs": "/docs",
        "redoc": "/redoc"
    }
