@echo off
chcp 65001 >nul
title ターニャ先生のロシア語学習アプリ

cd /d "%~dp0"

powershell -NoProfile -Command "try { $r = [System.Net.WebRequest]::Create('http://localhost:8085/api/state').GetResponse(); if ($r.StatusCode -eq 200) { exit 0 } } catch { exit 1 }"
if %errorlevel% equ 0 goto OPEN_BROWSER

start "Tanya Russian Server" /min "C:\Users\ymura\AppData\Local\Python\pythoncore-3.14-64\python.exe" server.py

for /L %%i in (1,1,16) do (
    timeout /t 1 /nobreak >nul 2>&1
    powershell -NoProfile -Command "try { $r = [System.Net.WebRequest]::Create('http://localhost:8085/api/state').GetResponse(); if ($r.StatusCode -eq 200) { exit 0 } } catch { exit 1 }"
    if not errorlevel 1 goto OPEN_BROWSER
)

:OPEN_BROWSER
start http://localhost:8085/
exit
