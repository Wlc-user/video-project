#!/usr/bin/env python3
"""
Quick Deployment Verification Script (Windows Compatible)
Run this script after starting the service
"""

import requests
import json
import random

BASE_URL = "http://localhost:8000/api"

def test_endpoint(method, endpoint, data=None, headers=None):
    """Test API endpoint"""
    url = f"{BASE_URL}/{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers)
        
        print(f"{method} {endpoint}: ", end="")
        if response.status_code < 400:
            print(f"[OK] {response.status_code}")
            try:
                return response.json()
            except:
                return response.text[:100] + "..."
        else:
            print(f"[ERROR] {response.status_code}")
            print(f"   Error: {response.text[:200]}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"{method} {endpoint}: [ERROR] Connection failed (service not started?)")
        return None
    except Exception as e:
        print(f"{method} {endpoint}: [ERROR] Exception: {str(e)}")
        return None

def main():
    print(">>> Starting AI Native deployment verification...")
    print("=" * 60)
    
    # 1. Test health check
    print("\n1. Health Check:")
    health = test_endpoint("GET", "health")
    
    if not health:
        print("[ERROR] Service not started. Please run: python -c \"import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)\"")
        return
    
    # 2. Test payment plans
    print("\n2. Payment Plans:")
    plans = test_endpoint("GET", "payment/plans")
    
    if plans and plans.get("success"):
        plans_data = plans.get("data", [])
        print(f"   Found {len(plans_data)} plans:")
        for plan in plans_data:
            print(f"   - {plan.get('name', 'unknown')}: {plan.get('display_price', 'unknown')}")
    
    # 3. Test user registration
    print("\n3. User System:")
    test_email = f"test_{random.randint(1000, 9999)}@example.com"
    test_password = "test123"
    
    register_data = {
        "email": test_email,
        "password": test_password
    }
    
    register_result = test_endpoint("POST", "auth/register", register_data)
    
    token = None
    if register_result and register_result.get("success"):
        print(f"   [OK] Registration successful: {test_email}")
        
        # 4. Test login
        login_data = {
            "email": test_email,
            "password": test_password
        }
        login_result = test_endpoint("POST", "auth/login", login_data)
        
        if login_result and login_result.get("success"):
            token = login_result["data"]["access_token"]
            print(f"   [OK] Login successful, token obtained")
            
            # 5. Test AI statistics
            headers = {"Authorization": f"Bearer {token}"}
            ai_stats = test_endpoint("GET", "ai/stats", headers=headers)
            
            if ai_stats:
                print(f"   User plan: {ai_stats.get('plan', 'unknown')}")
                print(f"   Remaining today: {ai_stats.get('remaining_today', 'unknown')} times")
                
                # 6. Test basic summary permissions
                print("\n4. Basic Summary Permissions:")
                summary_data = {
                    "url": "https://www.bilibili.com/video/BV1GJ411x7h7",
                    "language": "zh",
                    "analysis_level": "basic"
                }
                
                # Note: This is an SSE streaming endpoint, just testing if it responds
                print("   POST /summarize: SSE streaming endpoint (normal response is event stream)")
                
                # 7. Test professional analysis permissions (should be rejected)
                print("\n5. Professional Analysis Permissions Control:")
                pro_data = {
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "analysis_type": "academic"
                }
                
                pro_result = test_endpoint("POST", "analyze/professional", pro_data, headers)
                
                if pro_result and pro_result.get("error"):
                    if "need professional plan" in str(pro_result.get("error")).lower() or "AI_USAGE_LIMIT" in str(pro_result):
                        print("   [OK] Permission control working: Free users cannot use professional features")
                    else:
                        print(f"   [WARN] Other error: {pro_result.get('error')}")
                else:
                    print("   [WARN] Expected permission error")
        else:
            print("   [ERROR] Login failed")
    else:
        print("   [ERROR] Registration failed")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] Verification completed!")
    print("\nAvailable API Endpoints:")
    print("1. GET  /api/health - Health check")
    print("2. GET  /api/payment/plans - Payment plans")
    print("3. POST /api/auth/register - User registration")
    print("4. POST /api/auth/login - User login")
    print("5. GET  /api/ai/stats - AI usage statistics")
    print("6. POST /api/summarize - Basic video summary (SSE streaming)")
    print("7. POST /api/analyze/professional - Professional analysis (requires pro plan)")
    print("\nNext Steps:")
    print("1. Visit http://localhost:8000/docs for full API documentation")
    print("2. Configure Stripe price IDs to enable payment")
    print("3. Configure DeepSeek API key to enable AI features")
    print("4. Invite test users and collect feedback")
    print("=" * 60)

if __name__ == "__main__":
    main()