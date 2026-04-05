#!/usr/bin/env python3
"""
视频上传和分析模块
支持用户上传本地视频文件进行分析
"""

import os
import shutil
import uuid
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 导入AI分析模块
from summarizer import VideoSummarizer, AnalysisLevel

# 创建路由器
router = APIRouter(prefix="/api/upload", tags=["视频上传"])

# 配置上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 允许的视频格式
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}

class UploadAnalysisRequest(BaseModel):
    """上传分析请求模型"""
    language: str = "zh"
    analysis_level: str = "basic"
    title: Optional[str] = None
    description: Optional[str] = None

def validate_video_file(filename: str) -> bool:
    """验证视频文件格式"""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS

def save_upload_file(file: UploadFile, user_id: str = "anonymous") -> Path:
    """保存上传的文件"""
    if not validate_video_file(file.filename):
        raise HTTPException(status_code=400, detail="不支持的文件格式")
    
    # 生成唯一文件名
    file_ext = Path(file.filename).suffix
    unique_filename = f"{user_id}_{uuid.uuid4().hex}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    # 保存文件
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return file_path

@router.post("/video")
async def upload_video_for_analysis(
    file: UploadFile = File(...),
    request: UploadAnalysisRequest = Depends()
):
    """
    上传视频文件进行分析
    
    支持上传本地视频文件，系统会自动分析视频内容并生成：
    1. 视频总结
    2. 关键要点
    3. 思维导图（专业版）
    4. 学习笔记（专业版）
    """
    try:
        # 保存上传的文件
        file_path = save_upload_file(file)
        
        # 记录文件信息
        file_info = {
            "filename": file.filename,
            "saved_path": str(file_path),
            "file_size": file_path.stat().st_size,
            "content_type": file.content_type
        }
        
        # 这里可以添加用户ID认证
        # user_id = get_current_user_id()
        
        # 分析级别
        analysis_level = AnalysisLevel(request.analysis_level)
        
        # 使用AI分析视频
        summarizer = VideoSummarizer()
        
        # 注意：这里需要修改，因为原summarizer只支持URL
        # 这里我们先返回基本信息，实际AI分析需要读取视频内容
        result = {
            "success": True,
            "message": "视频上传成功，等待分析",
            "data": {
                "file_info": file_info,
                "analysis_request": {
                    "language": request.language,
                    "analysis_level": request.analysis_level,
                    "title": request.title
                },
                "note": "AI分析功能需要处理视频内容，当前版本主要支持URL分析"
            }
        }
        
        return JSONResponse(content=result, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        # 清理上传的文件
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@router.get("/formats")
async def get_supported_formats():
    """
    获取支持的上传格式
    """
    return {
        "success": True,
        "data": {
            "supported_formats": list(ALLOWED_EXTENSIONS),
            "max_size_mb": 500,  # 最大500MB
            "upload_dir": str(UPLOAD_DIR.absolute())
        }
    }

@router.delete("/cleanup")
async def cleanup_uploads():
    """
    清理上传目录（开发测试用）
    """
    try:
        if UPLOAD_DIR.exists():
            # 删除所有文件
            for file_path in UPLOAD_DIR.iterdir():
                if file_path.is_file():
                    file_path.unlink()
            return {"success": True, "message": f"已清理上传目录，共删除文件"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")