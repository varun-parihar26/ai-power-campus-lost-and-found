@echo off
echo Starting Campus Lost & Found...
echo.

REM Start backend in a new window
start "Lost & Found - Backend" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate && python app.py"

REM Wait a few seconds so backend has time to start
timeout /t 5 /nobreak >nul

REM Start frontend in a new window
start "Lost & Found - Frontend" cmd /k "cd /d %~dp0frontend && python -m http.server 5500"

REM Wait a moment then open the browser
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5500/

echo.
echo Both servers are starting in separate windows.
echo Backend:  http://127.0.0.1:5000
echo Frontend: http://127.0.0.1:5500/
echo.
echo Close this window anytime - it does not stop the servers.
pause
