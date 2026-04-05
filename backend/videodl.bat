@echo off
rem 万能视频下载器 - Windows批处理入口
rem 保留原有搜索引擎 + 逐步替代用户习惯

echo 万能视频下载器 CLI 工具
echo 基于AI的工业级视频分析平台
echo.

set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%cli_enhanced.py

rem 检查Python脚本是否存在
if not exist "%PYTHON_SCRIPT%" (
    echo 错误: 找不到脚本文件 %PYTHON_SCRIPT%
    echo 请确保在backend目录下运行此脚本
    pause
    exit /b 1
)

rem 执行Python脚本
python "%PYTHON_SCRIPT%" %*

if errorlevel 1 (
    echo.
    echo 执行出错，请检查:
    echo 1. Python是否已安装 (python --version)
    echo 2. 服务是否运行 (videodl status)
    echo 3. 网络连接是否正常
    echo.
) else (
    echo.
    echo 命令执行完成!
)