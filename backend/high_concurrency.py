# -*- coding: utf-8 -*-
"""
高并发优化模块
支持：
1. 多 Worker Uvicorn 配置
2. 异步数据库连接池
3. Redis 缓存层
4. 请求限流和背压
5. 连接池复用
6. 性能监控
"""
import os
import sys
import asyncio
import time
import functools
from typing import Optional, Callable, Any, Dict, List
from datetime import datetime, timedelta
from collections import defaultdict
from contextlib import asynccontextmanager

import httpx
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


# ==================== 限流器 ====================

class RateLimiter:
    """滑动窗口限流器"""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_second: int = 10,
        burst_size: int = 20
    ):
        self.rpm = requests_per_minute
        self.rps = requests_per_second
        self.burst = burst_size
        
        # 滑动窗口
        self.minute_window: Dict[str, List[float]] = defaultdict(list)
        self.second_window: Dict[str, List[float]] = defaultdict(list)
        
        # 协程锁
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
    
    def _get_lock(self, key: str) -> asyncio.Lock:
        return self._locks[key]
    
    async def check_rate_limit(
        self,
        client_id: str,
        weight: int = 1
    ) -> tuple[bool, Dict]:
        """
        检查限流
        Returns: (allowed, info)
        """
        now = time.time()
        key = client_id or "anonymous"
        async with self._get_lock(key):
            # 清理过期记录
            minute_cutoff = now - 60
            second_cutoff = now - 1
            
            self.minute_window[key] = [
                t for t in self.minute_window[key] if t > minute_cutoff
            ]
            self.second_window[key] = [
                t for t in self.second_window[key] if t > second_cutoff
            ]
            
            # 检查限制
            minute_count = len(self.minute_window[key]) + weight
            second_count = len(self.second_window[key]) + weight
            
            if minute_count > self.rpm:
                return False, {
                    "error": "rate_limit_exceeded",
                    "limit": self.rpm,
                    "window": "minute",
                    "retry_after": 60 - (now - self.minute_window[key][0]) if self.minute_window[key] else 60
                }
            
            if second_count > self.rps:
                return False, {
                    "error": "rate_limit_exceeded",
                    "limit": self.rps,
                    "window": "second",
                    "retry_after": 1 - (now - self.second_window[key][0]) if self.second_window[key] else 1
                }
            
            # 记录请求
            self.minute_window[key].append(now)
            self.second_window[key].append(now)
            
            return True, {
                "remaining_minute": self.rpm - minute_count,
                "remaining_second": self.rps - second_count
            }
    
    def get_stats(self) -> Dict:
        """获取限流统计"""
        total_clients = len(self.minute_window)
        total_requests = sum(len(v) for v in self.minute_window.values())
        return {
            "active_clients": total_clients,
            "total_requests": total_requests,
            "limit_per_minute": self.rpm,
            "limit_per_second": self.rps,
        }


# ==================== 连接池管理器 ====================

class ConnectionPoolManager:
    """HTTP 连接池管理器"""
    
    _instance = None
    _pools: Dict[str, httpx.AsyncClient] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_pool(
        self,
        name: str = "default",
        max_connections: int = 100,
        max_keepalive: int = 20,
        timeout: float = 30
    ) -> httpx.AsyncClient:
        """获取或创建连接池"""
        if name not in self._pools:
            limits = httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive,
            )
            timeout_config = httpx.Timeout(timeout)
            
            self._pools[name] = httpx.AsyncClient(
                limits=limits,
                timeout=timeout_config,
                follow_redirects=True,
            )
        return self._pools[name]
    
    async def close_all(self):
        """关闭所有连接池"""
        for pool in self._pools.values():
            await pool.aclose()
        self._pools.clear()
    
    def get_stats(self) -> Dict:
        """获取连接池状态"""
        return {
            name: {
                "max_connections": pool._limits.max_connections,
                "active": len(pool._connections) if hasattr(pool, '_connections') else "unknown"
            }
            for name, pool in self._pools.items()
        }


# ==================== 缓存层 ====================

class MemoryCache:
    """内存缓存 (LRU)"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._access_order: List[str] = []
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        async with self._lock:
            if key in self._cache:
                value, expires = self._cache[key]
                if time.time() < expires:
                    # 更新访问顺序
                    if key in self._access_order:
                        self._access_order.remove(key)
                    self._access_order.append(key)
                    return value
                else:
                    # 已过期
                    del self._cache[key]
                    self._access_order.remove(key)
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """设置缓存"""
        async with self._lock:
            expires = time.time() + (ttl or self.ttl)
            self._cache[key] = (value, expires)
            
            if key not in self._access_order:
                self._access_order.append(key)
            
            # LRU 淘汰
            while len(self._cache) > self.max_size:
                oldest = self._access_order.pop(0)
                if oldest in self._cache:
                    del self._cache[oldest]
    
    async def delete(self, key: str):
        """删除缓存"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._access_order.remove(key)
    
    async def clear(self):
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def stats(self) -> Dict:
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl": self.ttl
        }


class CacheManager:
    """缓存管理器 - 支持内存和 Redis"""
    
    def __init__(
        self,
        use_redis: bool = False,
        redis_url: str = None
    ):
        self.use_redis = use_redis
        self._memory_cache = MemoryCache(max_size=2000, ttl=300)
        self._redis = None
        
        if use_redis and redis_url:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(redis_url, decode_responses=True)
            except ImportError:
                print("Redis not available, using memory cache only")
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if self._redis:
            try:
                value = await self._redis.get(key)
                return value if value else None
            except Exception:
                pass
        return await self._memory_cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        """设置缓存"""
        if self._redis:
            try:
                import json
                await self._redis.setex(key, ttl, json.dumps(value))
                return
            except Exception:
                pass
        await self._memory_cache.set(key, value, ttl)
    
    async def delete(self, key: str):
        """删除缓存"""
        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception:
                pass
        await self._memory_cache.delete(key)
    
    async def close(self):
        """关闭连接"""
        if self._redis:
            await self._redis.close()


# ==================== 异步任务队列 ====================

class AsyncTaskQueue:
    """异步任务队列 (带优先级)"""
    
    def __init__(self, max_concurrent: int = 50):
        self.max_concurrent = max_concurrent
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._active = 0
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._workers: List[asyncio.Task] = []
        self._running = False
    
    async def _worker(self, worker_id: int):
        """工作协程"""
        while self._running:
            try:
                priority, task_id, coro = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            
            async with self._semaphore:
                try:
                    self._active += 1
                    await coro
                except Exception as e:
                    print(f"Task {task_id} failed: {e}")
                finally:
                    self._active -= 1
                    self._queue.task_done()
    
    def start(self, num_workers: int = 10):
        """启动工作协程"""
        self._running = True
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)
    
    async def stop(self):
        """停止工作协程"""
        self._running = False
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
    
    async def submit(
        self,
        coro: Callable,
        priority: int = 5,
        task_id: str = None
    ):
        """提交任务"""
        await self._queue.put((priority, task_id or str(time.time()), coro))
    
    def get_stats(self) -> Dict:
        return {
            "max_concurrent": self.max_concurrent,
            "active": self._active,
            "queue_size": self._queue.qsize(),
            "workers": len(self._workers),
        }


# ==================== 高并发中间件 ====================

class ConcurrencyMiddleware(BaseHTTPMiddleware):
    """高并发中间件"""
    
    def __init__(
        self,
        app,
        rate_limiter: RateLimiter = None,
        cache_manager: CacheManager = None
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.cache = cache_manager or CacheManager()
    
    async def dispatch(self, request: Request, call_next):
        # 获取客户端标识
        client_id = self._get_client_id(request)
        
        # 限流检查
        allowed, rate_info = await self.rate_limiter.check_rate_limit(client_id)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": rate_info,
                    "retry_after": rate_info.get("retry_after", 60)
                },
                headers={"Retry-After": str(rate_info.get("retry_after", 60))}
            )
        
        # 性能监控
        start_time = time.time()
        
        response = await call_next(request)
        
        # 添加响应头
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-RateLimit-Remaining"] = str(rate_info.get("remaining_minute", 0))
        response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", str(time.time()))
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用 X-Forwarded-For
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # 使用真实 IP
        client = request.client
        if client:
            return client.host
        
        return "unknown"


# ==================== 性能监控 ====================

class PerformanceMonitor:
    """性能监控器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self._request_times: List[float] = []
        self._request_count = 0
        self._error_count = 0
        self._active_requests = 0
        self._endpoint_stats: Dict[str, Dict] = defaultdict(lambda: {
            "count": 0, "total_time": 0, "errors": 0
        })
        self._lock = asyncio.Lock()
    
    async def record_request(
        self,
        endpoint: str,
        duration: float,
        status_code: int,
        error: bool = False
    ):
        """记录请求"""
        async with self._lock:
            self._request_times.append(duration)
            self._request_count += 1
            
            if len(self._request_times) > 1000:
                self._request_times = self._request_times[-500:]
            
            self._endpoint_stats[endpoint]["count"] += 1
            self._endpoint_stats[endpoint]["total_time"] += duration
            
            if error:
                self._error_count += 1
                self._endpoint_stats[endpoint]["errors"] += 1
    
    def get_stats(self) -> Dict:
        """获取统计"""
        avg_time = sum(self._request_times) / len(self._request_times) if self._request_times else 0
        sorted_times = sorted(self._request_times)
        p95 = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
        p99 = sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0
        
        return {
            "total_requests": self._request_count,
            "active_requests": self._active_requests,
            "total_errors": self._error_count,
            "error_rate": f"{(self._error_count / max(1, self._request_count)) * 100:.2f}%",
            "avg_response_time": f"{avg_time * 1000:.2f}ms",
            "p95_response_time": f"{p95 * 1000:.2f}ms",
            "p99_response_time": f"{p99 * 1000:.2f}ms",
            "endpoints": {
                k: {
                    "count": v["count"],
                    "avg_time": f"{v['total_time'] / max(1, v['count']) * 1000:.2f}ms",
                    "error_rate": f"{(v['errors'] / max(1, v['count'])) * 100:.2f}%"
                }
                for k, v in self._endpoint_stats.items()
            }
        }


# ==================== 高并发优化配置 ====================

HIGH_CONCURRENCY_CONFIG = {
    # Worker 配置
    "workers": 4,                    # 生产环境建议 CPU 核心数 * 2
    "worker_class": "uvicorn.workers.UvicornWorker",  # Gunicorn worker
    "threads": 4,                   # 每个 worker 的线程数
    
    # 超时配置
    "timeout": 120,                 # 请求超时 (秒)
    "keepalive": 65,                # keep-alive 超时
    
    # 连接配置
    "max_connections": 1000,        # 最大并发连接
    "backlog": 2048,                # 等待队列大小
    
    # 限流配置
    "rate_limit_rpm": 100,           # 每分钟请求数
    "rate_limit_rps": 20,           # 每秒请求数
    
    # 缓存配置
    "cache_size": 5000,             # 内存缓存大小
    "cache_ttl": 300,               # 缓存 TTL (秒)
    
    # 任务队列
    "max_concurrent_tasks": 100,    # 最大并发任务数
    "task_workers": 20,             # 任务工作协程数
    
    # HTTP 客户端
    "http_max_connections": 200,    # HTTP 连接池大小
    "http_timeout": 60,             # HTTP 请求超时
}


# ==================== 优化装饰器 ====================

def cached(ttl: int = 300, key_prefix: str = ""):
    """缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        cache = MemoryCache(max_size=1000, ttl=ttl)
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试获取缓存
            result = await cache.get(cache_key)
            if result is not None:
                return result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 设置缓存
            await cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def rate_limited(requests_per_minute: int = 60):
    """限流装饰器"""
    limiter = RateLimiter(requests_per_minute=requests_per_minute)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_id = request.client.host if request.client else "unknown"
            allowed, info = await limiter.check_rate_limit(client_id)
            
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=info
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# ==================== 高并发启动脚本 ====================

HIGH_CONCURRENCY_STARTUP = '''#!/bin/bash
# 高并发启动脚本

# 使用 Gunicorn + Uvicorn Workers
gunicorn \\
    main:app \\
    -w {workers} \\
    -k uvicorn.workers.UvicornWorker \\
    -b 0.0.0.0:8000 \\
    --timeout {timeout} \\
    --keep-alive {keepalive} \\
    --max-requests {max_requests} \\
    --max-requests-jitter {jitter} \\
    --access-logfile - \\
    --error-logfile - \\
    --log-level info
'''

HIGH_CONCURRENCY_DOCKER = '''# Dockerfile 高并发优化
FROM python:3.11-slim

# 安装编译依赖
RUN apt-get update && apt-get install -y \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# 设置 workers
ENV WEB_CONCURRENCY=4

CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
'''

if __name__ == "__main__":
    print("High Concurrency Module")
    print("=" * 50)
    print("Available components:")
    print("  - RateLimiter: 滑动窗口限流")
    print("  - ConnectionPoolManager: HTTP连接池")
    print("  - MemoryCache: LRU内存缓存")
    print("  - AsyncTaskQueue: 异步任务队列")
    print("  - ConcurrencyMiddleware: 高并发中间件")
    print("  - PerformanceMonitor: 性能监控")
    print()
    print("Config:", HIGH_CONCURRENCY_CONFIG)
