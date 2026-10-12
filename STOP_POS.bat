@echo off
title Stop Smart Grocery POS
color 0C

echo ===================================================
echo     STOPPING SMART GROCERY POS & GATEWAY
echo ===================================================
echo.

echo Terminating running Python servers on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Terminating running WhatsApp Gateway servers on port 5005...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5005') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo All POS background services have been stopped.
timeout /t 3 >nul
