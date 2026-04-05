# -*- coding: utf-8 -*-
"""
万能视频下载器 API - 高并发版本
集成：限流、缓存、连接池、性能监控
"""
import os
import asyncio
from contextlib import asynccontextmanager
from urllib.parse import unquote

from dotenv import load_dotenv
load_dotenv()

import httpx
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

from downloader import VideoDownloader
from douyin import DouyinParser, is_douyin_url
from database import init_db

# 高并发模块
from high_concurrency import (
    RateLimiter,
    ConnectionPoolManager,
    CacheManager,
    ConcurrencyMiddleware,
    PerformanceMonitor,
    HIGH_CONCURRENCY_CONFIG,
)


# ==================== 全局资源 ====================

# 限流器
rate_limiter = RateLimiter(
    requests_per_minute=HIGH_CONCURRENCY_CONFIG["rate_limit_rpm"],
    requests_per_second=HIGH_CONCURRENCY_CONFIG["rate_limit_rps"],
)

# 连接池管理器
pool_manager = ConnectionPoolManager()
cache_manager = CacheManager()

# 性能监控
monitor = PerformanceMonitor()

# 下载器 (复用连接池)
downloader = VideoDownloader()
douyin_parser = DouyinParser(download_dir=downloader.DOWNLOAD_DIR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    init_db()
    
    # 预热连接池
    pool_manager.get_pool("default")
    
    print(f"[High Concurrency Mode]")
    print(f"  Rate Limit: {HIGH_CONCURRENCY_CONFIG['rate_limit_rpm']} req/min")
    print(f"  Cache Size: {HIGH_CONCURRENCY_CONFIG['cache_size']}")
    
    yield
    
    # 关闭
    await pool_manager.close_all()
    await cache_manager.close()


app = FastAPI(
    title="万能视频下载器 API",
    description="基于 yt-dlp 的万能视频下载服务，支持 1800+ 平台 | 高并发优化版",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS 配置 (生产环境建议限制 origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 高并发中间件
app.add_middleware(
    ConcurrencyMiddleware,
    rate_limiter=rate_limiter,
    cache_manager=cache_manager,
)


# ==================== 异常处理 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    import traceback
    
    # 记录错误
    print(f"请求错误: {request.url}")
    print(f"错误详情: {exc}")
    traceback.print_exc()
    
    # 更新监控
    monitor._error_count += 1
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail)}
        )
    
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )


# ==================== 数据模型 ====================

class ParseRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    format_id: str = "bestvideo+bestaudio/best"


# ==================== 核心 API ====================

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "message": "万能视频下载器服务运行中 (高并发模式)",
        "version": "2.0.0"
    }


@app.get("/api/stats")
async def get_stats():
    """获取服务统计"""
    return {
        "rate_limiter": rate_limiter.get_stats(),
        "connection_pools": pool_manager.get_stats(),
        "cache": cache_manager._memory_cache.stats() if hasattr(cache_manager, '_memory_cache') else {},
        "performance": monitor.get_stats(),
    }


@app.post("/api/parse")
async def parse_video(req: ParseRequest, request: Request):
    """解析视频信息"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        # 尝试缓存
        cache_key = f"parse:{req.url}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        # 执行解析
        if is_douyin_url(req.url):
            result = await asyncio.get_event_loop().run_in_executor(
                None, douyin_parser.parse, req.url
            )
        else:
            result = await asyncio.get_event_loop().run_in_executor(
                None, downloader.parse_video, req.url
            )
        
        response = {"success": True, "data": result}
        
        # 缓存结果 (短期)
        await cache_manager.set(cache_key, response, ttl=60)
        
        # 记录性能
        await monitor.record_request(
            "/api/parse",
            asyncio.get_event_loop().time() - start_time,
            200
        )
        
        return response
        
    except Exception as e:
        await monitor.record_request("/api/parse", asyncio.get_event_loop().time() - start_time, 500, error=True)
        raise HTTPException(status_code=400, detail={"success": False, "error": f"解析失败: {str(e)}"})


@app.post("/api/download")
async def download_video(req: DownloadRequest, request: Request):
    """下载视频 (不使用缓存)"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        loop = asyncio.get_event_loop()
        if is_douyin_url(req.url):
            result = await loop.run_in_executor(None, douyin_parser.download, req.url)
        else:
            result = await loop.run_in_executor(
                None, downloader.download_video, req.url, req.format_id
            )
        
        filepath = result["filepath"]
        if not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="下载的文件不存在")
        
        await monitor.record_request("/api/download", asyncio.get_event_loop().time() - start_time, 200)
        
        return FileResponse(
            path=filepath,
            filename=result["filename"],
            media_type="application/octet-stream",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await monitor.record_request("/api/download", asyncio.get_event_loop().time() - start_time, 500, error=True)
        raise HTTPException(status_code=400, detail={"success": False, "error": f"下载失败: {str(e)}"})


@app.post("/api/direct-url")
async def get_direct_url(req: DownloadRequest, request: Request):
    """获取直链"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        # 缓存直链
        cache_key = f"direct:{req.url}:{req.format_id}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        result = await asyncio.get_event_loop().run_in_executor(
            None, downloader.get_direct_url, req.url, req.format_id
        )
        
        response = {"success": True, "data": result}
        await cache_manager.set(cache_key, response, ttl=300)
        
        await monitor.record_request("/api/direct-url", asyncio.get_event_loop().time() - start_time, 200)
        
        return response
        
    except Exception as e:
        await monitor.record_request("/api/direct-url", asyncio.get_event_loop().time() - start_time, 500, error=True)
        raise HTTPException(status_code=400, detail={"success": False, "error": f"获取直链失败: {str(e)}"})


@app.get("/api/proxy/thumbnail")
async def proxy_thumbnail(url: str = Query(..., description="缩略图URL")):
    """代理获取缩略图 (带缓存)"""
    # 缓存键
    cache_key = f"thumb:{url}"
    cached = await cache_manager.get(cache_key)
    if cached:
        return JSONResponse(content=cached)
    
    try:
        async with httpx.AsyncClient(
            timeout=15,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        ) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": url,
            })
            resp.raise_for_status()
            
            content_type = resp.headers.get("content-type", "image/jpeg")
            
            # 缓存图片
            await cache_manager.set(cache_key, {
                "content": resp.content.hex(),
                "content_type": content_type
            }, ttl=86400)
            
            return StreamingResponse(
                iter([resp.content]),
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception:
        raise HTTPException(status_code=502, detail="缩略图加载失败")


# ==================== 挂载功能模块路由 ====================

from api_summarize import router as summarize_router
from api_auth import router as auth_router
from api_payment import router as payment_router
from api_ai_stats import router as ai_stats_router
from api_professional import router as professional_router
from upload_minimal import router as upload_router
from industrial_template import router as template_router
from industrial_business import router as business_router
from secure_payment import router as secure_payment_router
from api_copyright import router as copyright_router
from api_membership import router as membership_router
from api_enhanced_detection import router as enhanced_detection_router

app.include_router(summarize_router)
app.include_router(auth_router)
app.include_router(payment_router)
app.include_router(ai_stats_router)
app.include_router(professional_router)
app.include_router(upload_router)
app.include_router(template_router)
app.include_router(business_router)
app.include_router(secure_payment_router)
app.include_router(copyright_router)
app.include_router(membership_router)
app.include_router(enhanced_detection_router)


# 静态文件
from fastapi.staticfiles import StaticFiles
app.mount("/_videos", StaticFiles(directory="_videos"), name="videos")


# ==================== 启动方式 ====================

if __name__ == "__main__":
    import uvicorn
    import platform
    
    # 开发模式 - 单进程
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
    
    # Windows 不支持 uvloop，使用默认事件循环
    if platform.system() == "Windows":
        print("Running on Windows (default event loop)")
    else:
        try:
            import uvloop
            config.loop = "uvloop"
            print("Using uvloop event loop")
        except ImportError:
            print("uvloop not available, using default event loop")
    
    server = uvicorn.Server(config)
    server.run()
