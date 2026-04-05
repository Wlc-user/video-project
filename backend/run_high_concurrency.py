#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高并发启动器
支持多种部署模式
"""
import os
import sys
import multiprocessing

# CPU 核心数
CPU_COUNT = multiprocessing.cpu_count()

# ==================== 配置 ====================

# 开发模式配置
DEV_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "reload": True,
    "workers": 1,
    "loop": "uvloop",
    "http": "httptools",
}

# 生产模式配置 (Gunicorn)
PROD_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "workers": CPU_COUNT * 2 + 1,  # 推荐: 2 * CPU + 1
    "worker_class": "uvicorn.workers.UvicornWorker",
    "timeout": 120,
    "keepalive": 65,
    "max_requests": 1000,
    "max_requests_jitter": 50,
}

# 高性能模式配置
HIGH_PERF_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "workers": CPU_COUNT * 4,  # IO 密集型可以更多
    "threads": 4,  # 多线程
    "worker_class": "uvicorn.workers.UvicornWorker",
    "timeout": 120,
    "keepalive": 65,
    "backlog": 2048,
    "max_requests": 5000,
    "max_requests_jitter": 100,
}


def start_dev():
    """开发模式"""
    import uvicorn
    import platform
    
    print("=" * 50)
    print("Starting in DEV mode")
    print("=" * 50)
    print(f"Platform: {platform.system()}")
    print(f"Config: {DEV_CONFIG}")
    print()
    
    config = uvicorn.Config(
        "main:app",
        host=DEV_CONFIG["host"],
        port=DEV_CONFIG["port"],
        reload=DEV_CONFIG["reload"],
    )
    
    server = uvicorn.Server(config)
    server.run()


def start_prod():
    """生产模式 (使用 Gunicorn)"""
    print("=" * 50)
    print("Starting in PROD mode (Gunicorn)")
    print("=" * 50)
    print(f"Workers: {PROD_CONFIG['workers']}")
    print()
    
    os.system(
        f'''gunicorn main:app \\
    -w {PROD_CONFIG["workers"]} \\
    -k "{PROD_CONFIG["worker_class"]}" \\
    -b {PROD_CONFIG["host"]}:{PROD_CONFIG["port"]} \\
    --timeout {PROD_CONFIG["timeout"]} \\
    --keep-alive {PROD_CONFIG["keepalive"]} \\
    --max-requests {PROD_CONFIG["max_requests"]} \\
    --max-requests-jitter {PROD_CONFIG["max_requests_jitter"]} \\
    --access-logfile - \\
    --error-logfile -'''
    )


def start_high_perf():
    """高性能模式"""
    print("=" * 50)
    print("Starting in HIGH PERFORMANCE mode")
    print("=" * 50)
    print(f"Workers: {HIGH_PERF_CONFIG['workers']}")
    print(f"Threads: {HIGH_PERF_CONFIG['threads']}")
    print()
    
    os.system(
        f'''gunicorn main:app \\
    -w {HIGH_PERF_CONFIG["workers"]} \\
    -k "{HIGH_PERF_CONFIG["worker_class"]}" \\
    -b {HIGH_PERF_CONFIG["host"]}:{HIGH_PERF_CONFIG["port"]} \\
    --threads {HIGH_PERF_CONFIG["threads"]} \\
    --timeout {HIGH_PERF_CONFIG["timeout"]} \\
    --keep-alive {HIGH_PERF_CONFIG["keepalive"]} \\
    --backlog {HIGH_PERF_CONFIG["backlog"]} \\
    --max-requests {HIGH_PERF_CONFIG["max_requests"]} \\
    --max-requests-jitter {HIGH_PERF_CONFIG["max_requests_jitter"]} \\
    --access-logfile - \\
    --error-logfile -'''
    )


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "dev"
    
    if mode == "dev":
        start_dev()
    elif mode == "prod":
        start_prod()
    elif mode == "high":
        start_high_perf()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python run_high_concurrency.py [dev|prod|high]")
