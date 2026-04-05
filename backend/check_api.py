#!/usr/bin/env python3
"""
快速检查所有API端点是否可访问
"""

import requests
import sys

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint, method="GET", data=None):
    """测试单个端点"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        
        print(f"Testing {endpoint}: ", end="")
        if response.status_code == 200:
            print(f"[OK] {response.status_code}")
            return True
        else:
            print(f"[ERROR] {response.status_code}")
            if response.text:
                print(f"    Response: {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"Testing {endpoint}: [ERROR] Connection failed (service not running?)")
        return False
    except Exception as e:
        print(f"Testing {endpoint}: [ERROR] {str(e)}")
        return False

def main():
    print("=" * 60)
    print("API Endpoints Health Check")
    print("=" * 60)
    
    # 1. 测试基本端点
    print("\n1. Basic endpoints:")
    endpoints = [
        ("/api/health", "GET"),
        ("/docs", "GET"),  # FastAPI文档
        ("/redoc", "GET"),  # 备选文档
    ]
    
    for endpoint, method in endpoints:
        test_endpoint(endpoint, method)
    
    # 2. 测试认证模块端点
    print("\n2. Auth module endpoints:")
    auth_endpoints = [
        ("/api/auth/register", "POST"),
        ("/api/auth/login", "POST"),
    ]
    
    for endpoint, method in auth_endpoints:
        # 对于POST端点，使用测试数据
        test_data = {"email": "test@example.com", "password": "test123"}
        test_endpoint(endpoint, method, test_data)
    
    # 3. 测试支付模块端点
    print("\n3. Payment module endpoints:")
    test_endpoint("/api/payment/plans", "GET")
    
    # 4. 测试AI统计端点
    print("\n4. AI Stats endpoints:")
    test_endpoint("/api/ai/stats", "GET")
    
    # 5. 测试总结模块端点（POST需要认证，这里只测试连接）
    print("\n5. Summary module endpoints (connection only):")
    test_endpoint("/api/summarize", "POST")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("1. 如果大部分端点返回 [ERROR]，可能是服务没有正确启动")
    print("2. 如果只有部分端点失败，可能是模块导入问题")
    print("3. 如果 /docs 和 /redoc 可以访问，说明FastAPI框架正常")
    print("=" * 60)
    
    print("\nNext steps:")
    print("1. 检查服务启动日志中是否有ImportError")
    print("2. 查看 main.py 中是否所有模块都正确导入")
    print("3. 运行验证脚本: python quick_verify_win.py")
    print("=" * 60)

if __name__ == "__main__":
    main()