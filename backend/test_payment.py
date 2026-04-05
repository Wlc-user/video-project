#!/usr/bin/env python3
"""
测试支付API是否正常工作
"""

import requests

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint):
    """测试单个API端点"""
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, timeout=5)
        print(f"测试 {endpoint}: ", end="")
        if response.status_code == 200:
            print(f"[成功] {response.status_code}")
            # 尝试解析JSON
            try:
                data = response.json()
                print(f"    响应: {data.get('success', '未知')}")
                if 'data' in data:
                    print(f"    数据: 有{len(str(data['data']))}字节")
            except:
                print(f"    内容: {response.text[:100]}...")
        else:
            print(f"[失败] {response.status_code}")
            print(f"    错误: {response.text[:100]}")
    except Exception as e:
        print(f"[错误] {str(e)}")

def main():
    print("=" * 60)
    print("支付API测试")
    print("=" * 60)
    
    # 测试所有支付相关API
    endpoints = [
        "/api/payment/security/guide",
        "/api/payment/methods",
        "/api/payment/test/success",
        "/api/payment/plans",  # 原有的套餐API
        "/api/health",  # 健康检查
        "/docs",  # API文档
    ]
    
    for endpoint in endpoints:
        test_endpoint(endpoint)
    
    print("\n" + "=" * 60)
    print("使用说明:")
    print("1. 在浏览器中打开: http://localhost:8000/docs")
    print("2. 查看所有API文档")
    print("3. 或者直接在浏览器中访问上述URL")
    print("=" * 60)
    
    print("\n重要URL汇总:")
    print("• 支付安全指南: http://localhost:8000/api/payment/security/guide")
    print("• 支付方式列表: http://localhost:8000/api/payment/methods")
    print("• 支付成功测试: http://localhost:8000/api/payment/test/success")
    print("• API文档: http://localhost:8000/docs")
    print("• 上传页面: http://localhost:8000/upload")
    print("• 健康检查: http://localhost:8000/api/health")
    print("=" * 60)

if __name__ == "__main__":
    main()