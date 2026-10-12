@echo off
chcp 65001 > nul
echo =======================================================
echo   AISC 2026 - DIGITAL CULTURAL INTERPRETER (DCI)
echo   Khoi dong tu dong Backend Server (Team Asteria - UIT)
echo =======================================================
echo.

cd /d "%~dp0"

REM Kiem tra xem da co thu muc venv chua
if not exist "venv" (
    echo [1/3] Chua co moi truong ao. Dang tu dong tao 'venv'...
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo [LOI] Khong tim thay Python tren he thong.
        echo Vui long cai dat Python (khuyen nghi 3.11 hoac 3.12) va tich chon "Add Python to PATH"!
        echo.
        pause
        exit /b 1
    )
    echo [2/3] Dang tu dong cai dat thu vien tu requirements.txt...
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r src\backend\requirements.txt
    if errorlevel 1 (
        echo [CANH BAO] Co loi khi cai dat thu vien. Vui long kiem tra lai ket noi Internet!
        pause
        exit /b 1
    )
    echo [THANH CONG] Da cai dat xong moi truong!
) else (
    echo [1/2] Da tim thay moi truong ao 'venv' san co.
    call venv\Scripts\activate.bat
)

echo.
echo [OK] Dang khoi dong FastAPI Backend tai http://localhost:8000 ...
echo Bam Ctrl+C de dung server.
echo.

python src\backend\run.py

pause
