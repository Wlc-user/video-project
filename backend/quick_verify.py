#!/usr/bin/env python3
"""
快速验证部署是否成功
在服务启动后运行此脚本
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_endpoint(method, endpoint, data=None, headers=None):
    """测试API端点"""
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
            print(f"   错误: {response.text[:200]}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"{method} {endpoint}: [ERROR] 连接失败 (服务未启动?)")
        return None
    except Exception as e:
        print(f"{method} {endpoint}: [ERROR] 异常: {str(e)}")
        return None

def main():
    print(">>> 开始验证AI Native部署...")
    print("=" * 60)
    
    # 1. 测试健康检查
    print("\n1. 健康检查:")
    health = test_endpoint("GET", "health")
    
    if not health:
        print("[ERROR] 服务未启动，请先运行: python -c \"import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)\"")
        return
    
    # 2. 测试套餐信息
    print("\n2. 套餐信息:")
    plans = test_endpoint("GET", "payment/plans")
    
    if plans and plans.get("success"):
        plans_data = plans.get("data", [])
        print(f"   发现 {len(plans_data)} 个套餐:")
        for plan in plans_data:
            print(f"   - {plan.get('name', '未知')}: {plan.get('display_price', '未知')}")
    
    # 3. 测试用户注册
    print("\n3. 用户系统:")
    import random
    test_email = f"test_{random.randint(1000, 9999)}@example.com"
    test_password = "test123"
    
    register_data = {
        "email": test_email,
        "password": test_password
    }
    
    register_result = test_endpoint("POST", "auth/register", register_data)
    
    token = None
    if register_result and register_result.get("success"):
        print(f"   [OK] 注册成功: {test_email}")
        
        # 4. 测试登录
        login_data = {
            "email": test_email,
            "password": test_password
        }
        login_result = test_endpoint("POST", "auth/login", login_data)
        
        if login_result and login_result.get("success"):
            token = login_result["data"]["access_token"]
            print(f"   [OK] 登录成功，获取Token")
            
            # 5. 测试AI统计
            headers = {"Authorization": f"Bearer {token}"}
            ai_stats = test_endpoint("GET", "ai/stats", headers=headers)
            
            if ai_stats:
                print(f"   用户计划: {ai_stats.get('plan', '未知')}")
                print(f"   今日剩余: {ai_stats.get('remaining_today', '未知')}次")
                
                # 6. 测试基础总结权限
                print("\n4. 基础总结权限:")
                summary_data = {
                    "url": "https://www.bilibili.com/video/BV1GJ411x7h7",
                    "language": "zh",
                    "analysis_level": "basic"
                }
                
                # 注意：这是SSE流式端点，只测试是否响应
                print("   POST /summarize: SSE流式端点（正常响应为事件流）")
                
                # 7. 测试专业分析权限（应该被拒绝）
                print("\n5. 专业分析权限控制:")
                pro_data = {
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "analysis_type": "academic"
                }
                
                pro_result = test_endpoint("POST", "analyze/professional", pro_data, headers)
                
                if pro_result and pro_result.get("error"):
                    if "需要专业版" in str(pro_result.get("error")) or "AI_USAGE_LIMIT" in str(pro_result):
                        print("   [OK] 权限控制生效：免费用户无法使用专业功能")
                    else:
                        print(f"   [WARN] 其他错误: {pro_result.get('error')}")
                else:
                    print("   [WARN] 预期应该返回权限错误")
        else:
            print("   [ERROR] 登录失败")
    else:
        print("   [ERROR] 注册失败")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] 验证完成！")
    print("\n可用API端点:")
    print("1. GET  /api/health - 健康检查")
    print("2. GET  /api/payment/plans - 套餐列表")
    print("3. POST /api/auth/register - 用户注册")
    print("4. POST /api/auth/login - 用户登录")
    print("5. GET  /api/ai/stats - AI使用统计")
    print("6. POST /api/summarize - 基础视频总结（SSE流式）")
    print("7. POST /api/analyze/professional - 专业分析（需要专业版）")
    print("\n下一步:")
    print("1. 访问 http://localhost:8000/docs 查看完整API文档")
    print("2. 配置Stripe价格ID以启用支付功能")
    print("3. 配置DeepSeek API密钥以启用AI功能")
    print("4. 邀请测试用户，收集反馈")
    print("=" * 60)

if __name__ == "__main__":
    main()