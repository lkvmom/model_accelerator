from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as matching_router
import os

app = FastAPI(
    title="Согласование пучка в ускорителе",
    description="Веб-интерфейс для расчёта согласующей секции пучка частиц",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роуты
app.include_router(matching_router)

# Статика и шаблоны
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/")
async def root(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/docs")
async def swagger_docs():
    """Swagger документация"""
    pass

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "accelerator-matching"}

