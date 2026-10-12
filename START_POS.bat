@echo off
title Smart Grocery POS - System Launcher
color 0B

echo ===================================================
echo     SMART GROCERY POS - ONE-CLICK LAUNCHER
echo ===================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking environment & migrations...
python backend\manage.py migrate --noinput
if errorlevel 1 (
    echo [ERROR] Failed to run database migrations.
    pause
    exit /b %errorlevel%
)

echo [2/3] Starting WhatsApp Gateway (port 5005)...
if exist "wa_gateway\server.js" (
    start "Smart Grocery POS - WhatsApp Gateway" cmd /c "cd /d "%~dp0wa_gateway" && title WhatsApp Gateway && node server.js"
) else (
    echo [INFO] WhatsApp Gateway script not found. Skipping.
)

echo [3/3] Starting Django POS Server (port 8000)...
start "Smart Grocery POS - Server" cmd /c "cd /d "%~dp0backend" && title POS Server && python manage.py runserver 127.0.0.1:8000"

echo.
echo Waiting for servers to initialize...
timeout /t 3 /nobreak >nul

echo Opening POS Counter in your default browser...
start http://127.0.0.1:8000/

echo.
echo ===================================================
echo   Smart Grocery POS is running at:
echo   http://127.0.0.1:8000/
echo.
echo   Keep the server window open while using the POS.
echo ===================================================
echo.
timeout /t 5 >nul
