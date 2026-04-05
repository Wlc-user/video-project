@echo off
rem YouTube批量下载脚本
rem 保留搜索引擎习惯，批量处理收藏夹

echo =====================================
echo  YouTube批量下载器
echo  基于搜索引擎收藏夹的批量下载
echo =====================================
echo.

echo 假设你已通过搜索引擎收藏了以下视频:
echo  1. 科技教程
echo  2. 学习资源  
echo  3. 娱乐内容
echo  4. 新闻资讯
echo.

echo 创建URL列表文件...
echo https://www.youtube.com/watch?v=dQw4w9WgXcQ > youtube_urls.txt
echo https://www.youtube.com/watch?v=9bZkp7q19f0 >> youtube_urls.txt
echo https://www.youtube.com/watch?v=JGwWNGJdvx8 >> youtube_urls.txt

echo URL列表已保存到: youtube_urls.txt
echo.

echo 开始批量下载...
set count=0

for /f "tokens=*" %%i in (youtube_urls.txt) do (
    set /a count+=1
    echo.
    echo [%count%] 处理: %%i
    call ..\videodl.bat download "%%i"
    
    if errorlevel 1 (
        echo 下载失败，跳过此视频
    ) else (
        echo 下载成功
    )
    
    rem 添加延迟，避免请求过快
    timeout /t 2 /nobreak >nul
)

echo.
echo =====================================
echo 批量下载完成!
echo 共处理 %count% 个视频
echo.
echo 保留搜索引擎习惯的建议:
echo  1. 在浏览器中创建视频收藏夹
echo  2. 定期导出收藏夹链接到文本文件
echo  3. 使用此脚本批量下载收藏内容
echo  4. 保持搜索方式不变，只改变下载方式
echo =====================================
echo.
pause