@echo off
echo 启动万能视频下载器服务...
echo =====================================

cd /d %~dp0

echo 1. 检查Python依赖...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Python未安装或不在PATH中
    echo 请安装Python 3.8+并添加到系统PATH
    pause
    exit /b 1
)

echo 2. 安装依赖包...
python -m pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo 警告: 依赖安装失败，尝试继续启动...
)

echo 3. 启动FastAPI服务...
echo 服务将运行在: http://localhost:8000
echo.
echo 按 Ctrl+C 停止服务
echo =====================================
echo.

uvicorn main:app --host 0.0.0.0 --port 8000 --reload