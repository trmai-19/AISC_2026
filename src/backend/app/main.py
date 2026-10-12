import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import (
    auth_router,
    chat_router,
    evidence_router,
    survey_router,
    admin_router,
    analytics_router
)

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("dci-backend")

app = FastAPI(
    title="DCI - Digital Cultural Interpreter API",
    description="""
    Hệ thống Backend & RAG Copilot hỗ trợ thích nghi văn hoá cho cộng đồng người Việt tại Nhật Bản, Hàn Quốc và Australia.
    
    * **Đề án**: AISC'26 (Advanced Information Systems Contest 2026)
    * **Đội thi**: Asteria - Trường ĐH Công nghệ Thông tin (UIT - ĐHQG TP.HCM)
    * **Chủ đề**: Data-Driven Business & Social Tech
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Cấu hình CORS cho phép Frontend truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn các routers theo chuẩn RESTful v1
app.include_router(auth_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(survey_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")

@app.get("/", tags=["Health Check"])
def root_endpoint():
    return {
        "project": "DCI - Digital Cultural Interpreter",
        "contest": "AISC'26 - Team Asteria (UIT)",
        "status": "online",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api_v1": "/api/v1"
    }

@app.get("/health", tags=["Health Check"])
def health_check():
    return {"status": "healthy"}
