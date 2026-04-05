@echo off
rem 万能视频下载器快速启动脚本
rem 三阶段迁移：保留原有搜索引擎，逐步替代用户习惯

echo ==============================================
echo  万能视频下载器 - 工业级AI视频分析平台
echo  版本: 1.0.0 (CLI增强版)
echo  作者: AI Native团队
echo ==============================================
echo.

:menu
echo 请选择操作:
echo  1. 启动API服务器
echo  2. 检查服务器状态
echo  3. 解析视频信息
echo  4. 下载视频文件
echo  5. 上传本地视频
echo  6. AI分析视频
echo  7. 用户管理
echo  8. 支付功能
echo  9. 工业级模板
echo  10. 批量处理
echo  11. 查看帮助文档
echo  12. 退出
echo.

set /p choice=请输入选择 (1-12): 

if "%choice%"=="1" goto start_server
if "%choice%"=="2" goto check_status
if "%choice%"=="3" goto parse_video
if "%choice%"=="4" goto download_video
if "%choice%"=="5" goto upload_video
if "%choice%"=="6" goto analyze_video
if "%choice%"=="7" goto user_management
if "%choice%"=="8" goto payment_features
if "%choice%"=="9" goto industrial_templates
if "%choice%"=="10" goto batch_processing
if "%choice%"=="11" goto help_docs
if "%choice%"=="12" goto exit_program

echo 无效选择，请重试
goto menu

:start_server
echo.
echo 启动API服务器...
python main.py
goto menu

:check_status
echo.
call videodl.bat status
goto menu

:parse_video
echo.
set /p url=请输入视频URL: 
call videodl.bat parse "%url%"
goto menu

:download_video
echo.
set /p url=请输入视频URL: 
call videodl.bat download "%url%"
goto menu

:upload_video
echo.
set /p file=请输入视频文件路径: 
call videodl.bat upload "%file%"
goto menu

:analyze_video
echo.
set /p video=请输入视频文件或ID: 
call videodl.bat analyze "%video%"
goto menu

:user_management
echo.
echo 用户管理功能:
echo  1. 用户注册
echo  2. 用户登录
echo  3. 查看用户信息
echo  4. 返回主菜单
echo.
set /p user_choice=请选择: 

if "%user_choice%"=="1" goto register_user
if "%user_choice%"=="2" goto login_user
if "%user_choice%"=="3" goto user_info
if "%user_choice%"=="4" goto menu

echo 无效选择
goto user_management

:register_user
echo.
set /p email=请输入邮箱: 
set /p password=请输入密码: 
call videodl.bat register "%email%" "%password%"
goto menu

:login_user
echo.
set /p email=请输入邮箱: 
set /p password=请输入密码: 
call videodl.bat login "%email%" "%password%"
goto menu

:user_info
echo.
call videodl.bat user
goto menu

:payment_features
echo.
echo 支付功能:
echo  1. 查看支付套餐
echo  2. 查看支付方式
echo  3. 创建支付订单
echo  4. 返回主菜单
echo.
set /p payment_choice=请选择: 

if "%payment_choice%"=="1" (
    call videodl.bat plans
    goto menu
)
if "%payment_choice%"=="2" (
    call videodl.bat payment-methods
    goto menu
)
if "%payment_choice%"=="3" (
    echo.
    echo 注意: 支付订单创建需要API支持
    echo 请参考: 支付安全部署指南.md
    goto menu
)
if "%payment_choice%"=="4" goto menu

echo 无效选择
goto payment_features

:industrial_templates
echo.
call videodl.bat industrial templates
goto menu

:batch_processing
echo.
set /p directory=请输入视频目录路径: 
echo 处理类型:
echo  1. 批量分析
echo  2. 批量上传
echo.
set /p batch_choice=请选择: 

if "%batch_choice%"=="1" (
    call videodl.bat batch "%directory%" --action analyze
    goto menu
)
if "%batch_choice%"=="2" (
    call videodl.bat batch "%directory%" --action upload
    goto menu
)

echo 无效选择
goto batch_processing

:help_docs
echo.
echo ====== 使用指南 ======
echo.
echo 三阶段迁移计划:
echo  1. 阶段一 (1-2周): Web界面 + CLI并行使用
echo      - Web界面继续访问 http://localhost:8000
echo      - CLI尝试基础命令
echo.
echo  2. 阶段二 (2-4周): 常用功能迁移到CLI
echo      - 视频下载: videodl download <URL>
echo      - 批量处理: videodl batch <目录>
echo      - 保留搜索引擎: 搜索 -> 复制URL -> CLI下载
echo.
echo  3. 阶段三 (4周后): 完全CLI化
echo      - 创建命令别名
echo      - 集成到系统PATH
echo      - 自动化工作流
echo.
echo 常用命令:
echo  - 搜索视频 -> 复制URL -> videodl parse <URL>
echo  - 搜索视频 -> 复制URL -> videodl download <URL>
echo  - 批量下载脚本: 创建download_scripts.bat
echo.
pause
goto menu

:exit_program
echo.
echo 谢谢使用万能视频下载器!
echo 记住: 保留搜索引擎习惯，逐步迁移到CLI
echo.
pause
exit /b 0