@echo off
cd /d %~dp0
where python >nul 2>nul || (echo Python is not installed. Install it from python.org ^(tick PATH^). & pause & exit /b)
if not exist venv python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
echo.
echo Open in your browser: http://localhost:5000   ^(press Ctrl+C to stop^)
python app.py
pause
