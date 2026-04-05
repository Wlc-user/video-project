@echo off
rem 快速下载脚本 - 保留搜索引擎习惯
rem 使用方法: 双击运行，或拖动URL到脚本图标上

echo =====================================
echo  快速视频下载器
echo  保留搜索引擎，简化下载步骤
echo =====================================
echo.

if "%1"=="" (
    echo 使用方法:
    echo  1. 在浏览器中搜索视频
    echo  2. 复制视频URL
    echo  3. 运行此脚本并粘贴URL
    echo  4. 或直接将URL拖到脚本图标上
    echo.
    set /p video_url=请粘贴视频URL: 
) else (
    set video_url=%1
    echo 从参数获取URL: %video_url%
)

echo.
echo 开始处理: %video_url%

rem 检查服务状态
cd /d %~dp0
cd ..
call videodl.bat status

echo.
echo 正在解析视频信息...
call videodl.bat parse "%video_url%"

echo.
echo 是否下载此视频?
choice /c YN /m "是否下载 (Y/N): "

if errorlevel 2 (
    echo 取消下载
    pause
    exit /b 0
)

echo.
echo 开始下载...
call videodl.bat download "%video_url%"

echo.
echo 下载完成!
echo 请检查当前目录下的视频文件
echo.
pause