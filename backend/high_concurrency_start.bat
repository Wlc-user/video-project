@echo off
chcp 65001 >nul
REM 高并发启动脚本 (Windows)

echo ========================================
echo   万能视频下载器 - 高并发模式
echo ========================================
echo.

set MODE=%1
if "%MODE%"=="" set MODE=dev

if "%MODE%"=="dev" (
    echo [开发模式] 单进程启动
    python main.py
) else if "%MODE%"=="gunicorn" (
    echo [生产模式] Gunicorn 多进程
    pip install gunicorn
    gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 120
) else if "%MODE%"=="uvicorn" (
    echo [Uvicorn] 多进程模式
    pip install uvicorn[standard] uvloop httptools
    python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --loop uvloop --http httptools
) else (
    echo Usage: high_concurrency_start.bat [dev^|gunicorn^|uvicorn]
    echo   dev      - 开发模式
    echo   gunicorn - Gunicorn 多进程
    echo   uvicorn  - Uvicorn 多进程
)
