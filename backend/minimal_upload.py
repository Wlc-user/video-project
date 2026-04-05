#!/usr/bin/env python3
"""
最小化视频上传方案 - 最低维护成本

特点：
1. 使用临时存储，自动清理
2. 支持多用户并发
3. 生成可用URL供现有AI系统处理
4. 保留流量扩展能力
"""

import os
import tempfile
import uuid
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
import shutil

from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import aiofiles

router = APIRouter(prefix="/api/upload", tags=["视频上传"])

# 配置
class Config:
    # 存储设置
    STORAGE_DIR = Path("user_uploads")
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    RETENTION_DAYS = 7  # 文件保留7天
    
    # 支持格式
    ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
    
    # 定价方案
    PRICING = {
        "free": {"daily_limit": 10, "features": ["基础总结"]},
        "vip": {"daily_limit": 50, "features": ["基础总结", "快速处理"]},
        "pro": {"daily_limit": -1, "features": ["全部功能", "专业分析", "学术分析"]}
    }

# 初始化目录
Config.STORAGE_DIR.mkdir(exist_ok=True)

class UploadManager:
    """上传管理器"""
    
    @staticmethod
    def generate_file_id(user_ip: str) -> str:
        """生成唯一文件ID"""
        timestamp = int(time.time())
        random_hash = hashlib.md5(f"{user_ip}_{timestamp}_{uuid.uuid4()}".encode()).hexdigest()[:12]
        return f"{timestamp}_{random_hash}"
    
    @staticmethod
    def get_user_upload_dir(user_ip: str) -> Path:
        """获取用户上传目录"""
        # 使用IP哈希避免直接暴露IP
        ip_hash = hashlib.md5(user_ip.encode()).hexdigest()[:8]
        user_dir = Config.STORAGE_DIR / ip_hash
        user_dir.mkdir(exist_ok=True)
        return user_dir
    
    @staticmethod
    def cleanup_old_files():
        """清理过期文件"""
        cutoff_time = time.time() - (Config.RETENTION_DAYS * 24 * 3600)
        
        for user_dir in Config.STORAGE_DIR.iterdir():
            if user_dir.is_dir():
                for file_path in user_dir.iterdir():
                    if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                        try:
                            file_path.unlink()
                        except:
                            pass

@router.get("/")
async def upload_page():
    """上传页面"""
    html_path = Path(__file__).parent / "templates" / "upload_page.html"
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@router.post("/minimal")
async def minimal_upload(
    request: Request,
    file: UploadFile = File(...),
    analysis_type: str = "basic",
    language: str = "zh"
):
    """
    最小化上传接口
    
    商业化可用，维护成本最低
    1. 文件存储到本地目录
    2. 生成临时访问URL
    3. 集成到现有AI分析系统
    """
    try:
        # 获取用户IP（用于限流）
        user_ip = request.client.host if request.client else "unknown"
        
        # 验证文件
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名无效")
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in Config.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件格式。支持: {', '.join(Config.ALLOWED_EXTENSIONS)}"
            )
        
        # 清理过期文件
        UploadManager.cleanup_old_files()
        
        # 生成文件ID和路径
        file_id = UploadManager.generate_file_id(user_ip)
        user_dir = UploadManager.get_user_upload_dir(user_ip)
        save_filename = f"{file_id}{file_ext}"
        save_path = user_dir / save_filename
        
        # 保存文件（支持大文件）
        file_size = 0
        async with aiofiles.open(save_path, 'wb') as out_file:
            # 分块读取，避免内存问题
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                file_size += len(chunk)
                
                # 检查文件大小限制
                if file_size > Config.MAX_FILE_SIZE:
                    await out_file.close()
                    if save_path.exists():
                        save_path.unlink()
                    raise HTTPException(
                        status_code=400, 
                        detail=f"文件太大，最大支持{Config.MAX_FILE_SIZE // (1024*1024)}MB"
                    )
                
                await out_file.write(chunk)
        
        # 生成访问URL（这里简化处理，实际部署需要配置域名）
        # 在实际部署中，这里应该返回一个真实可访问的URL
        temp_url = f"/uploads/{user_dir.name}/{save_filename}"
        
        # 根据分析类型处理
        ai_result = None
        status = "uploaded"
        
        if analysis_type == "basic":
            # 基础分析可以立即处理
            status = "processing"
            # 这里可以调用现有的AI分析系统
            # ai_result = await analyze_video(save_path, language)
        else:
            # 高级功能需要升级
            status = "requires_upgrade"
        
        # 构建响应
        response_data = {
            "success": True,
            "message": "视频上传成功",
            "data": {
                "file_id": file_id,
                "original_name": file.filename,
                "file_size": file_size,
                "saved_path": str(save_path.relative_to(Path(__file__).parent)),
                "temp_url": temp_url,
                "analysis_type": analysis_type,
                "language": language,
                "status": status,
                "expires_at": datetime.now() + timedelta(days=Config.RETENTION_DAYS),
                "ai_result": ai_result,
                "pricing_note": get_pricing_note(analysis_type)
            }
        }
        
        return JSONResponse(content=response_data, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

def get_pricing_note(analysis_type: str) -> str:
    """获取定价提示"""
    if analysis_type == "basic":
        return "✅ 基础功能免费使用"
    elif analysis_type == "professional":
        return "🔒 专业功能需要升级到专业版 (29.9元/月)"
    elif analysis_type == "academic":
        return "🔒 学术分析需要专业版订阅"
    return ""

@router.get("/pricing")
async def get_pricing_info():
    """获取定价信息"""
    return {
        "success": True,
        "data": Config.PRICING
    }

@router.get("/stats")
async def get_upload_stats():
    """获取上传统计（用于监控）"""
    total_files = 0
    total_size = 0
    user_count = 0
    
    if Config.STORAGE_DIR.exists():
        for user_dir in Config.STORAGE_DIR.iterdir():
            if user_dir.is_dir():
                user_count += 1
                for file_path in user_dir.iterdir():
                    if file_path.is_file():
                        total_files += 1
                        total_size += file_path.stat().st_size
    
    return {
        "success": True,
        "data": {
            "total_users": user_count,
            "total_files": total_files,
            "total_size_mb": total_size / (1024 * 1024),
            "storage_dir": str(Config.STORAGE_DIR.absolute()),
            "retention_days": Config.RETENTION_DAYS
        }
    }

@router.delete("/cleanup")
async def manual_cleanup():
    """手动清理（维护用）"""
    try:
        UploadManager.cleanup_old_files()
        return {"success": True, "message": "已清理过期文件"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")