@echo off
chcp 65001 > nul
echo ========================================
echo AI Native Video Analysis Platform Deployment
echo ========================================
echo.

echo Step 1: Check Python environment
python --version
if errorlevel 1 (
    echo [ERROR] Python not installed or not in PATH
    pause
    exit /b 1
)

echo.
echo Step 2: Install required dependencies
pip install python-dateutil -q
echo [OK] python-dateutil installed

echo.
echo Step 3: Initialize database
python -c "from database import init_db; init_db(); print('[OK] Database initialized')"
if errorlevel 1 (
    echo [ERROR] Database initialization failed
    pause
    exit /b 1
)

echo.
echo Step 4: Check environment configuration
if not exist ".env" (
    echo [WARN] .env file not found, copying sample config
    copy .env.example .env
    echo [INFO] Please edit .env file to configure API keys
    pause
)

echo.
echo Step 5: Start FastAPI service
echo [INFO] Service starting at http://localhost:8000
echo [INFO] API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop service
echo ========================================
echo.

:: Start service
python -c "import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)"