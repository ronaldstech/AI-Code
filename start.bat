@echo off
setlocal
cd /d "%~dp0"

if not exist "frontend\dist\index.html" (
	echo Frontend build not found. Build it first with:
	echo   cd frontend
	echo   npm install
	echo   npm run build
	echo.
)

if not exist "frontend\dist\assets" (
	echo Warning: the React frontend build is incomplete.
	echo Install Node.js, then run:
	echo   cd frontend
	echo   npm install
	echo   npm run build
	echo.
)

echo Starting Local Coding AI on all network interfaces...
start "Local Coding AI server" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000"

echo.
echo Browser chat: http://127.0.0.1:8000
echo LAN chat:     http://YOUR-PC-IP:8000
ipconfig | findstr /R /C:"IPv4 Address"
echo.
echo Run start_agent.bat for the coding agent in CMD.
