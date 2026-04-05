#!/usr/bin/env python3
"""
简单服务状态检查脚本 - Windows兼容版
"""
import sys
import time

try:
    import requests
except ImportError:
    print("安装requests库...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

def check_service():
    """检查服务状态"""
    base_url = "http://localhost:8000"
    
    print("=" * 50)
    print("万能视频下载器 - 服务状态检查")
    print("=" * 50)
    
    # 检查服务是否运行
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 服务状态: {data.get('status', 'unknown')}")
            print(f"✓ 服务版本: {data.get('version', '1.0.0')}")
            print(f"✓ 检查时间: {data.get('timestamp', time.strftime('%Y-%m-%d %H:%M:%S'))}")
        else:
            print(f"✗ 服务异常 (状态码: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("✗ 服务未运行")
        print("  请先运行: start_service.bat")
        return False
    except Exception as e:
        print(f"✗ 检查失败: {e}")
        return False
    
    print()
    
    # 测试核心功能端点
    endpoints = [
        ("/api/parse", "视频解析"),
        ("/api/download", "视频下载"),
        ("/api/upload", "视频上传"),
        ("/api/auth/register", "用户注册"),
        ("/api/payment/plans", "支付套餐"),
    ]
    
    print("测试核心API端点:")
    print("-" * 40)
    
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=3)
            status = "✓" if response.status_code < 500 else "✗"
            print(f"  {status} {description}: HTTP {response.status_code}")
        except:
            print(f"  ✗ {description}: 连接失败")
    
    print()
    
    # CLI工具检查
    print("CLI工具检查:")
    print("-" * 40)
    
    cli_commands = [
        "python cli_enhanced.py --help",
        "python cli_enhanced.py status",
        "python cli_enhanced.py plans"
    ]
    
    for cmd in cli_commands:
        try:
            import subprocess
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"  ✓ {cmd.split()[2]}: 可用")
            else:
                print(f"  ✗ {cmd.split()[2]}: 错误")
        except:
            print(f"  ✗ {cmd.split()[2]}: 异常")
    
    print()
    print("=" * 50)
    print("使用指南:")
    print("1. 启动服务: start_service.bat")
    print("2. 使用CLI: python cli_enhanced.py <命令>")
    print("3. 使用批处理: videodl.bat <命令>")
    print("4. Web界面: http://localhost:8000")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    check_service()