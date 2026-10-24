@echo off
title KMB Apps - WhatsApp Silent Gateway (Port 5005)
cd /d "%~dp0wa_gateway"
echo ========================================================
echo    KMB APPS POS - WHATSAPP SILENT BACKGROUND GATEWAY
echo ========================================================
echo Starting local WhatsApp gateway on port 5005...
echo Once connected, receipts will send silently in background!
echo.
node server.js
pause
