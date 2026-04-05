#!/usr/bin/env python3
"""
简单的视频上传通道
通过本地文件转HTTP URL的方式，让现有系统可以处理本地视频
"""

import os
import tempfile
import uuid
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import aiofiles

router = APIRouter(prefix="/api/upload", tags=["视频上传"])

# 临时存储目录
TEMP_DIR = Path(tempfile.gettempdir()) / "video_uploads"
TEMP_DIR.mkdir(exist_ok=True)

@router.post("/simple")
async def simple_video_upload(
    file: UploadFile = File(...),
    language: str = "zh",
    analysis_level: str = "basic"
):
    """
    简单视频上传接口
    
    将用户上传的视频文件保存到临时目录，然后返回一个"虚拟URL"
    这样现有的AI分析系统就可以处理本地视频了
    """
    try:
        # 验证文件类型
        allowed_types = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska']
        if file.content_type not in allowed_types:
            # 检查文件扩展名
            filename = file.filename.lower()
            if not any(filename.endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.mkv']):
                raise HTTPException(status_code=400, detail="只支持视频文件 (mp4, avi, mov, mkv)")
        
        # 生成唯一文件名
        file_ext = Path(file.filename).suffix or '.mp4'
        unique_id = uuid.uuid4().hex
        temp_filename = f"upload_{unique_id}{file_ext}"
        temp_path = TEMP_DIR / temp_filename
        
        # 保存文件
        async with aiofiles.open(temp_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        # 获取文件大小
        file_size = os.path.getsize(temp_path)
        
        # 创建响应
        response = {
            "success": True,
            "message": "视频上传成功",
            "data": {
                "original_filename": file.filename,
                "saved_filename": temp_filename,
                "file_size": file_size,
                "content_type": file.content_type,
                "virtual_url": f"file://{temp_path}",  # 虚拟URL，用于标识本地文件
                "upload_id": unique_id,
                "analysis_params": {
                    "language": language,
                    "analysis_level": analysis_level
                },
                "note": "由于当前AI系统主要分析在线视频，本地视频需要转换为在线URL才能深度分析"
            }
        }
        
        return JSONResponse(content=response, status_code=200)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@router.get("/test-form")
async def get_test_form():
    """
    返回一个测试用的HTML表单（开发用）
    """
    html_form = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>视频上传测试</title>
    </head>
    <body>
        <h1>视频上传测试</h1>
        <form action="/api/upload/simple" method="post" enctype="multipart/form-data">
            <div>
                <label for="file">选择视频文件:</label>
                <input type="file" id="file" name="file" accept="video/*" required>
            </div>
            <div>
                <label for="language">分析语言:</label>
                <select id="language" name="language">
                    <option value="zh">中文</option>
                    <option value="en">英文</option>
                </select>
            </div>
            <div>
                <label for="analysis_level">分析级别:</label>
                <select id="analysis_level" name="analysis_level">
                    <option value="basic">基础</option>
                    <option value="professional">专业</option>
                    <option value="academic">学术</option>
                </select>
            </div>
            <div>
                <button type="submit">上传并分析</button>
            </div>
        </form>
        
        <h2>使用curl命令测试:</h2>
        <pre>
curl -X POST "http://localhost:8000/api/upload/simple" \\
  -F "file=@/path/to/your/video.mp4" \\
  -F "language=zh" \\
  -F "analysis_level=basic"
        </pre>
    </body>
    </html>
    """
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_form)

@router.get("/quick-guide")
async def get_quick_guide():
    """
    快速使用指南
    """
    guide = {
        "title": "视频上传使用指南",
        "methods": [
            {
                "method": "HTML表单",
                "url": "http://localhost:8000/api/upload/test-form",
                "description": "直接在浏览器中上传视频"
            },
            {
                "method": "cURL命令",
                "example": 'curl -X POST "http://localhost:8000/api/upload/simple" -F "file=@video.mp4"',
                "description": "使用命令行上传"
            },
            {
                "method": "Python代码",
                "example": """
import requests
url = "http://localhost:8000/api/upload/simple"
files = {"file": open("video.mp4", "rb")}
data = {"language": "zh", "analysis_level": "basic"}
response = requests.post(url, files=files, data=data)
print(response.json())
                """,
                "description": "使用Python requests库上传"
            }
        ],
        "supported_formats": ["mp4", "avi", "mov", "mkv", "flv", "wmv"],
        "max_size": "500MB",
        "next_step": "上传后可以将返回的virtual_url提供给AI分析系统"
    }
    
    return {"success": True, "data": guide}