@echo off
chcp 65001 > nul
echo ========================================
echo 🤖 AI Native视频分析平台部署脚本
echo ========================================
echo.

echo 步骤1: 检查Python环境
python --version
if errorlevel 1 (
    echo ❌ Python未安装或不在PATH中
    pause
    exit /b 1
)

echo.
echo 步骤2: 安装必要依赖
pip install python-dateutil -q
echo ✅ python-dateutil安装完成

echo.
echo 步骤3: 初始化数据库
python -c "from database import init_db; init_db(); print('✅ 数据库初始化完成')"
if errorlevel 1 (
    echo ❌ 数据库初始化失败
    pause
    exit /b 1
)

echo.
echo 步骤4: 检查环境配置
if not exist ".env" (
    echo ⚠️ .env文件不存在，复制示例配置
    copy .env.example .env
    echo 📝 请编辑.env文件配置API密钥
    pause
)

echo.
echo 步骤5: 启动FastAPI服务
echo 🚀 服务将在 http://localhost:8000 启动
echo 📚 API文档: http://localhost:8000/docs
echo.
echo 按Ctrl+C停止服务
echo ========================================
echo.

:: 启动服务
python -c "import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)"