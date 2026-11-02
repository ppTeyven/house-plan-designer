@echo off
cd /d "%~dp0"
netstat -ano | findstr /R /C:"TCP.*:8899.*LISTENING" >nul
if %errorlevel%==0 (
  echo Server already running on http://127.0.0.1:8899/template.html
  timeout /t 3 >nul
  exit /b
)
:loop
echo [%time%] serving http://127.0.0.1:8899/template.html  (no-cache, close window to stop)
python serve.py
timeout /t 2 >nul
goto loop
