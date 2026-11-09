@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Notice Ledger - local server (port 8000)

echo.
echo   Notice Ledger / 校务·赛事通知可信问答助手
echo   URL : http://127.0.0.1:8000/
echo   Stop: press Ctrl+C in this window
echo.

netstat -ano | findstr /r /c:"LISTENING" | findstr ":8000 " >nul
if not errorlevel 1 (
  echo   [!] Port 8000 is already in use.
  echo       An older server process is probably still running - that is exactly the
  echo       situation that makes the panel show "接口不可用".
  echo       Close the old console window, or end python.exe in Task Manager, then rerun.
  echo.
  pause
  exit /b 1
)

set "PYEXE=python"
if exist ".venv\Scripts\python.exe" set "PYEXE=.venv\Scripts\python.exe"

start "" http://127.0.0.1:8000/
"%PYEXE%" -m app.server --port 8000

echo.
echo   Server stopped.
pause
