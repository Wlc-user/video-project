@echo off
rem 搜索引擎集成工具
rem 保留原有搜索引擎习惯，逐步替代用户操作

echo ==============================================
echo  搜索引擎集成 - 万能视频下载器
echo  理念: "保留原有搜索引擎 + 逐步替代用户习惯"
echo ==============================================
echo.

:main_menu
echo 选择搜索引擎集成方式:
echo  1. 搜索引擎 -> 复制URL -> 一键下载
echo  2. 搜索引擎 -> 复制URL -> 批量下载脚本
echo  3. 搜索引擎 -> 收藏夹 -> 定时自动下载
echo  4. 搜索引擎 -> API -> 完全自动化
echo  5. 查看当前集成状态
echo  6. 返回上级菜单
echo.

set /p integration_choice=请选择 (1-6): 

if "%integration_choice%"=="1" goto copy_paste_download
if "%integration_choice%"=="2" goto batch_download_script
if "%integration_choice%"=="3" goto scheduled_download
if "%integration_choice%"=="4" goto fully_automated
if "%integration_choice%"=="5" goto integration_status
if "%integration_choice%"=="6" goto exit_menu

echo 无效选择
goto main_menu

:copy_paste_download
echo.
echo ====== 模式1: 复制粘贴下载 ======
echo.
echo 步骤:
echo  1. 在浏览器中打开搜索引擎 (YouTube/B站/抖音等)
echo  2. 搜索你想要的视频
echo  3. 复制视频URL (右键 -> 复制链接地址)
echo  4. 回到此窗口，选择操作:
echo.

echo 请选择操作:
echo  1. 解析视频信息
echo  2. 下载视频文件
echo  3. 获取视频直链
echo  4. 返回主菜单
echo.

set /p operation=请选择 (1-4): 

if "%operation%"=="1" goto parse_url
if "%operation%"=="2" goto download_url
if "%operation%"=="3" goto direct_url
if "%operation%"=="4" goto main_menu

echo 无效选择
goto copy_paste_download

:parse_url
echo.
set /p video_url=请粘贴视频URL: 
echo 正在解析视频信息...
call videodl.bat parse "%video_url%"
goto copy_paste_download

:download_url
echo.
set /p video_url=请粘贴视频URL: 
echo 正在下载视频...
call videodl.bat download "%video_url%"
goto copy_paste_download

:direct_url
echo.
set /p video_url=请粘贴视频URL: 
echo 正在获取视频直链...
call videodl.bat direct "%video_url%"
goto copy_paste_download

:batch_download_script
echo.
echo ====== 模式2: 批量下载脚本 ======
echo.
echo 创建批量下载脚本，自动化处理多个视频URL
echo.

if not exist "download_scripts\" mkdir download_scripts

echo 请选择:
echo  1. 创建新的批量下载脚本
echo  2. 编辑现有脚本
echo  3. 运行批量脚本
echo  4. 返回主菜单
echo.

set /p batch_choice=请选择: 

if "%batch_choice%"=="1" goto create_batch_script
if "%batch_choice%"=="2" goto edit_batch_script
if "%batch_choice%"=="3" goto run_batch_script
if "%batch_choice%"=="4" goto main_menu

echo 无效选择
goto batch_download_script

:create_batch_script
echo.
echo 创建批量下载脚本...
echo 请按以下格式输入视频URL (每行一个，输入空行结束):
echo.

set script_name=download_scripts\%date:~0,4%%date:~5,2%%date:~8,2%_batch.bat
echo @echo off > "%script_name%"
echo rem 批量下载脚本 - 生成于 %date% %time% >> "%script_name%"
echo echo 开始批量下载... >> "%script_name%"
echo. >> "%script_name%"

:add_urls
set /p url=请输入视频URL (直接回车结束): 
if "%url%"=="" goto finish_script
echo call videodl.bat download "%url%" >> "%script_name%"
goto add_urls

:finish_script
echo. >> "%script_name%"
echo echo 批量下载完成! >> "%script_name%"
echo pause >> "%script_name%"

echo.
echo 脚本已创建: %script_name%
echo 使用方法: 双击运行该脚本
echo.
pause
goto batch_download_script

:edit_batch_script
echo.
echo 可用脚本:
dir /b download_scripts\*.bat
echo.
set /p script_to_edit=请输入脚本文件名: 
notepad download_scripts\%script_to_edit%
goto batch_download_script

:run_batch_script
echo.
echo 可用脚本:
dir /b download_scripts\*.bat
echo.
set /p script_to_run=请输入脚本文件名: 
call download_scripts\%script_to_run%
goto batch_download_script

:scheduled_download
echo.
echo ====== 模式3: 定时自动下载 ======
echo.
echo 此功能需要Windows任务计划程序
echo 请参考CLI迁移指南.md中的"集成到任务计划"部分
echo.
echo 基本步骤:
echo  1. 创建收藏夹列表 (favorites.txt)
echo  2. 创建定时下载脚本
echo  3. 配置Windows任务计划
echo.
pause
goto main_menu

:fully_automated
echo.
echo ====== 模式4: 完全自动化 ======
echo.
echo 高级功能，需要API集成和编程知识
echo 包括:
echo  - 搜索引擎API调用
echo  - 自动关键词搜索
echo  - 智能视频筛选
echo  - 自动下载和分析
echo.
echo 请联系技术支持获取更多信息
pause
goto main_menu

:integration_status
echo.
echo ====== 当前集成状态 ======
echo.
echo 当前支持的搜索引擎:
echo  - YouTube (支持)
echo  - Bilibili (支持)
echo  - 抖音 (支持)
echo  - 快手 (支持)
echo  - Twitter/X (部分支持)
echo  - Instagram (部分支持)
echo.
echo 用户习惯替代进度:
echo  - 阶段一: 复制粘贴下载 ✓
echo  - 阶段二: 批量脚本下载 ✓
echo  - 阶段三: 定时自动下载 ⚠ (需要配置)
echo  - 阶段四: 完全自动化 ✗ (开发中)
echo.
echo 推荐使用模式:
echo  - 新手: 模式1 (复制粘贴)
echo  - 进阶: 模式2 (批量脚本)
echo  - 专业: 模式3+ (定时+自动化)
echo.
pause
goto main_menu

:exit_menu
echo.
echo 记住: 保留你的搜索引擎习惯!
echo 我们只是让下载更高效，搜索方式不变
echo.
pause
exit /b 0