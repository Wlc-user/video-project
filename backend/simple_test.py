#!/usr/bin/env python3
"""
简单测试脚本，不触发服务重启
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("=" * 60)
    print("Simple API Test")
    print("=" * 60)
    
    # 1. 测试健康检查
    print("\n1. Testing /api/health:")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        else:
            print(f"   Error: {response.text[:100]}")
    except Exception as e:
        print(f"   Error: {str(e)}")
    
    # 2. 测试用户注册
    print("\n2. Testing user registration:")
    try:
        data = {
            "email": f"test_user_{1234}@example.com",
            "password": "test123"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", 
                                json=data, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"   Success! User registered")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
        else:
            print(f"   Error: {response.text[:100]}")
    except Exception as e:
        print(f"   Error: {str(e)}")
    
    # 3. 测试登录
    print("\n3. Testing login:")
    try:
        data = {
            "email": f"test_user_{1234}@example.com",
            "password": "test123"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", 
                                json=data, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                token = result["data"]["access_token"]
                print(f"   Success! Got token: {token[:30]}...")
                
                # 4. 测试AI统计
                print("\n4. Testing AI stats with token:")
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get(f"{BASE_URL}/api/ai/stats", 
                                       headers=headers, timeout=5)
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    stats = response.json()
                    print(f"   Plan: {stats.get('plan', 'unknown')}")
                    print(f"   Remaining today: {stats.get('remaining_today', 'unknown')}")
                else:
                    print(f"   Error: {response.text[:100]}")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
        else:
            print(f"   Error: {response.text[:100]}")
    except Exception as e:
        print(f"   Error: {str(e)}")
    
    # 5. 测试套餐列表
    print("\n5. Testing payment plans:")
    try:
        response = requests.get(f"{BASE_URL}/api/payment/plans", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                plans = result.get("data", [])
                print(f"   Found {len(plans)} plans:")
                for plan in plans:
                    print(f"   - {plan.get('name')}: {plan.get('display_price')}")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
        else:
            print(f"   Error: {response.text[:100]}")
    except Exception as e:
        print(f"   Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    
    print("\nManual testing instructions:")
    print("1. Keep service running in one window")
    print("2. Open browser: http://localhost:8000/docs")
    print("3. Test APIs manually from the Swagger UI")

if __name__ == "__main__":
    test_api()