@echo off
chcp 65001 > nul
echo =======================================================
echo   AISC 2026 - DIGITAL CULTURAL INTERPRETER (DCI)
echo   Khoi dong toan bo he thong bang Docker Compose
echo =======================================================
echo.

cd /d "%~dp0"

echo [1/2] Dang kiem tra Docker Desktop va build cac container...
docker compose up -d --build

if errorlevel 1 (
    echo.
    echo [LOI] Khong the chay Docker! Vui long kiem tra Docker Desktop da mo chua.
    echo.
    pause
    exit /b 1
)

echo.
echo =======================================================
echo [THANH CONG] Toan bo he thong da san sang:
echo   - 🌐 Giao dien Web (Frontend):   http://localhost:3000
echo   - 🚀 API Backend (Swagger Docs): http://localhost:8000/docs
echo   - 🐘 Co so du lieu PostgreSQL:   localhost:5432
echo =======================================================
echo.
pause
