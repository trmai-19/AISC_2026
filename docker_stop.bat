@echo off
chcp 65001 > nul
echo Dang dung cac container Docker DCI...
cd /d "%~dp0"
docker compose down
echo Da dung xong toan bo he thong.
pause
