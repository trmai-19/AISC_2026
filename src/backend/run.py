import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"==================================================")
    print(f" Khởi động {settings.APP_NAME}")
    print(f" Swagger UI: http://localhost:{settings.APP_PORT}/docs")
    print(f" API Base:   http://localhost:{settings.APP_PORT}/api/v1")
    print(f"==================================================")
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=(settings.APP_ENV == "development")
    )
