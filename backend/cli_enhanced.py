#!/usr/bin/env python3
"""
万能视频下载器 - 增强版 CLI 工具
集成所有 API 功能，提供完整的命令行操作体验
"""

import os
import sys
import json
import argparse
import time
import requests
from typing import Dict, Any, List
from pathlib import Path
from dataclasses import dataclass

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 默认API服务器
DEFAULT_API_URL = "http://localhost:8000"


@dataclass
class APIClient:
    """增强版API客户端"""
    
    base_url: str = DEFAULT_API_URL
    timeout: int = 30
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError:
            return {"error": "响应不是有效的JSON格式"}
    
    def get(self, endpoint: str, params=None) -> Dict[str, Any]:
        """发送GET请求"""
        return self._make_request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, data=None, files=None) -> Dict[str, Any]:
        """发送POST请求"""
        return self._make_request("POST", endpoint, data=data, files=files)
    
    def check_health(self) -> bool:
        """检查API服务状态"""
        try:
            result = self.get("/api/health")
            return result.get("status") == "ok"
        except:
            return False
    
    def parse_video(self, url: str) -> Dict[str, Any]:
        """解析视频信息"""
        return self.post("/api/parse", data={"url": url})
    
    def download_video(self, url: str, format_id: str = "best") -> Dict[str, Any]:
        """下载视频"""
        return self.post("/api/download", data={"url": url, "format_id": format_id})
    
    def get_direct_url(self, url: str, format_id: str = "best") -> Dict[str, Any]:
        """获取视频直链"""
        return self.post("/api/direct-url", data={"url": url, "format_id": format_id})
    
    def upload_video(self, video_path: str) -> Dict[str, Any]:
        """上传视频"""
        if not os.path.exists(video_path):
            return {"error": f"文件不存在: {video_path}"}
        
        with open(video_path, 'rb') as f:
            files = {'file': (os.path.basename(video_path), f, 'video/mp4')}
            return self.post("/api/upload", files=files)
    
    def analyze_video(self, video_id: str) -> Dict[str, Any]:
        """分析视频"""
        return self.post(f"/api/analyze/{video_id}")
    
    def summarize_video(self, url: str, level: str = "medium") -> Dict[str, Any]:
        """视频摘要"""
        return self.post("/api/summarize", data={"url": url, "level": level})
    
    def get_payment_plans(self) -> Dict[str, Any]:
        """获取支付套餐"""
        return self.get("/api/payment/plans")
    
    def get_user_stats(self) -> Dict[str, Any]:
        """获取用户统计"""
        return self.get("/api/auth/stats")
    
    def get_professional_features(self) -> Dict[str, Any]:
        """获取专业版功能"""
        return self.get("/api/professional/features")
    
    def get_ai_stats(self) -> Dict[str, Any]:
        """获取AI使用统计"""
        return self.get("/api/ai/stats")
    
    def get_industrial_templates(self) -> Dict[str, Any]:
        """获取工业级模板"""
        return self.get("/api/industrial/templates")
    
    def create_industrial_batch(self, template_id: str, urls: List[str]) -> Dict[str, Any]:
        """创建工业级批量处理"""
        return self.post("/api/industrial/analyze/batch", data={
            "template_id": template_id,
            "urls": urls
        })
    
    def get_direct_url(self, url: str, format_id: str = "best") -> Dict[str, Any]:
        """获取视频直链"""
        return self.post("/api/direct-url", data={"url": url, "format_id": format_id})
    
    def get_proxy_thumbnail(self, url: str) -> Dict[str, Any]:
        """代理获取缩略图"""
        return self.get(f"/api/proxy/thumbnail?url={url}")
    
    def chat_with_video(self, video_id: str, question: str) -> Dict[str, Any]:
        """AI视频问答"""
        return self.post("/api/chat", data={"video_id": video_id, "question": question})
    
    def professional_analysis(self, video_url: str, analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """专业视频分析"""
        return self.post("/api/professional", data={"url": video_url, "analysis_type": analysis_type})
    
    def generate_study_notes(self, video_url: str) -> Dict[str, Any]:
        """生成学习笔记"""
        return self.post("/api/study-notes", data={"url": video_url})
    
    def extract_key_quotes(self, video_url: str) -> Dict[str, Any]:
        """提取关键语录"""
        return self.post("/api/key-quotes", data={"url": video_url})
    
    def register_user(self, email: str, password: str) -> Dict[str, Any]:
        """用户注册"""
        return self.post("/api/auth/register", data={"email": email, "password": password})
    
    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        return self.post("/api/auth/login", data={"email": email, "password": password})
    
    def get_user_info(self, token: str = None) -> Dict[str, Any]:
        """获取用户信息"""
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return self.get("/api/auth/me", headers=headers)
    
    def get_payment_methods(self) -> Dict[str, Any]:
        """获取支付方式"""
        return self.get("/api/secure/methods")
    
    def create_payment_order(self, amount: float, description: str, method: str = "alipay") -> Dict[str, Any]:
        """创建支付订单"""
        return self.post("/api/secure/create", data={
            "amount": amount,
            "description": description,
            "method": method
        })
    
    def get_industrial_report(self) -> Dict[str, Any]:
        """获取工业化商业报告"""
        return self.get("/api/business/report")
    
    def get_replication_plan(self) -> Dict[str, Any]:
        """获取工业化复制计划"""
        return self.get("/api/replication/plan")
    
    def get_upload_stats(self) -> Dict[str, Any]:
        """获取上传统计"""
        return self.get("/api/upload/stats")
    
    def get_supported_formats(self) -> Dict[str, Any]:
        """获取支持的格式"""
        return self.get("/api/formats")


class ColorFormatter:
    """彩色输出格式化器"""
    
    COLORS = {
        'green': '\033[92m',
        'yellow': '\033[93m',
        'red': '\033[91m',
        'blue': '\033[94m',
        'cyan': '\033[96m',
        'magenta': '\033[95m',
        'reset': '\033[0m',
        'bold': '\033[1m',
    }
    
    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """添加颜色"""
        color_code = cls.COLORS.get(color, '')
        reset = cls.COLORS['reset']
        return f"{color_code}{text}{reset}"
    
    @classmethod
    def success(cls, text: str) -> str:
        """成功消息"""
        return cls.colorize(f"✓ {text}", "green")
    
    @classmethod
    def error(cls, text: str) -> str:
        """错误消息"""
        return cls.colorize(f"✗ {text}", "red")
    
    @classmethod
    def warning(cls, text: str) -> str:
        """警告消息"""
        return cls.colorize(f"⚠ {text}", "yellow")
    
    @classmethod
    def info(cls, text: str) -> str:
        """信息消息"""
        return cls.colorize(f"ℹ {text}", "blue")
    
    @classmethod
    def header(cls, text: str) -> str:
        """标题"""
        return cls.colorize(f"\n=== {text} ===\n", "cyan")
    
    @classmethod
    def subheader(cls, text: str) -> str:
        """子标题"""
        return cls.colorize(f"--- {text} ---", "magenta")


class CLIHandler:
    """CLI处理程序"""
    
    def __init__(self, api_url: str = DEFAULT_API_URL):
        self.api = APIClient(api_url)
        self.color = ColorFormatter()
    
    def check_server(self) -> bool:
        """检查服务器状态"""
        print(self.color.header("检查服务器状态"))
        
        if self.api.check_health():
            print(self.color.success("API服务器运行正常"))
            return True
        else:
            print(self.color.error("API服务器未运行"))
            print("\n请先启动服务器:")
            print(f"  cd {BASE_DIR}")
            print(f"  python main.py")
            print("\n或使用: python run_deployment_win.bat")
            return False
    
    def handle_parse(self, url: str):
        """处理解析命令"""
        print(self.color.header(f"解析视频: {url}"))
        
        result = self.api.parse_video(url)
        if "success" in result and result["success"]:
            data = result.get("data", {})
            print(self.color.success("解析成功！"))
            print(f"\n标题: {data.get('title', 'N/A')}")
            print(f"作者: {data.get('uploader', 'N/A')}")
            print(f"时长: {data.get('duration', 0)}秒")
            print(f"观看数: {data.get('view_count', 0)}")
            print(f"缩略图: {data.get('thumbnail', 'N/A')}")
            
            if 'formats' in data and data['formats']:
                print(f"\n可用格式 ({len(data['formats'])}种):")
                for fmt in data['formats'][:5]:  # 显示前5种格式
                    print(f"  - {fmt.get('format_id', 'N/A')}: {fmt.get('resolution', 'N/A')}")
        else:
            print(self.color.error(f"解析失败: {result.get('error', '未知错误')}"))
    
    def handle_download(self, url: str, format_id: str = "best"):
        """处理下载命令"""
        print(self.color.header(f"下载视频: {url}"))
        
        # 先解析视频信息
        parse_result = self.api.parse_video(url)
        if not parse_result.get("success"):
            print(self.color.error("无法解析视频信息"))
            return
        
        video_title = parse_result.get("data", {}).get("title", "unknown")
        print(f"视频标题: {video_title}")
        
        # 开始下载
        print("\n开始下载...")
        result = self.api.download_video(url, format_id)
        
        if "success" in result and result["success"]:
            print(self.color.success("下载完成！"))
            print(f"文件已保存到: {result.get('filename', 'unknown')}")
        else:
            print(self.color.error(f"下载失败: {result.get('error', '未知错误')}"))
    
    def handle_upload(self, video_path: str):
        """处理上传命令"""
        print(self.color.header(f"上传视频: {video_path}"))
        
        if not os.path.exists(video_path):
            print(self.color.error(f"文件不存在: {video_path}"))
            return
        
        file_size = os.path.getsize(video_path)
        print(f"文件大小: {file_size / 1024 / 1024:.2f} MB")
        
        print("\n正在上传...")
        result = self.api.upload_video(video_path)
        
        if "success" in result and result["success"]:
            print(self.color.success("上传成功！"))
            video_id = result.get("video_id")
            print(f"视频ID: {video_id}")
            
            # 可选：自动分析视频
            choice = input("\n是否立即分析视频？(y/n): ").lower()
            if choice == 'y':
                self.handle_analyze(video_id)
        else:
            print(self.color.error(f"上传失败: {result.get('error', '未知错误')}"))
    
    def handle_analyze(self, video_id_or_path: str):
        """处理分析命令"""
        print(self.color.header("分析视频"))
        
        # 判断是视频ID还是文件路径
        if os.path.exists(video_id_or_path):
            # 是文件路径，先上传
            upload_result = self.api.upload_video(video_id_or_path)
            if not upload_result.get("success"):
                return
            video_id = upload_result.get("video_id")
        else:
            # 是视频ID
            video_id = video_id_or_path
        
        print(f"视频ID: {video_id}")
        print("\n正在分析...")
        
        result = self.api.analyze_video(video_id)
        if "success" in result and result["success"]:
            print(self.color.success("分析完成！"))
            
            data = result.get("data", {})
            print(f"\n分析结果:")
            print(f"标题: {data.get('title', 'N/A')}")
            print(f"时长: {data.get('duration', 0)}秒")
            
            if 'summary' in data:
                print(f"\n视频摘要:")
                print(f"  {data['summary'][:200]}...")
            
            if 'tags' in data and data['tags']:
                print(f"\n标签: {', '.join(data['tags'][:10])}")
        else:
            print(self.color.error(f"分析失败: {result.get('error', '未知错误')}"))
    
    def handle_summarize(self, url: str, level: str = "medium"):
        """处理摘要命令"""
        print(self.color.header(f"生成视频摘要: {url}"))
        
        print(f"摘要级别: {level}")
        print("\n正在生成摘要...")
        
        result = self.api.summarize_video(url, level)
        if "success" in result and result["success"]:
            print(self.color.success("摘要生成完成！"))
            
            data = result.get("data", {})
            print(f"\n标题: {data.get('title', 'N/A')}")
            print(f"时长: {data.get('duration', 0)}秒")
            
            if 'summary' in data:
                print(f"\n摘要内容:")
                print(data['summary'])
        else:
            print(self.color.error(f"摘要生成失败: {result.get('error', '未知错误')}"))
    
    def handle_status(self):
        """处理状态命令"""
        print(self.color.header("系统状态"))
        
        # 检查服务器
        if not self.check_server():
            return
        
        # 获取用户统计
        print(self.color.subheader("用户统计"))
        stats = self.api.get_user_stats()
        if "success" in stats and stats["success"]:
            data = stats.get("data", {})
            print(f"用户ID: {data.get('user_id', 'N/A')}")
            print(f"用户级别: {data.get('user_level', '免费用户')}")
            print(f"使用次数: {data.get('usage_count', 0)}")
            print(f"剩余次数: {data.get('remaining_quota', 0)}")
        else:
            print(self.color.warning("无法获取用户统计"))
        
        # 获取AI统计
        print(self.color.subheader("AI使用统计"))
        ai_stats = self.api.get_ai_stats()
        if "success" in ai_stats and ai_stats["success"]:
            data = ai_stats.get("data", {})
            print(f"今日使用: {data.get('today_usage', 0)}次")
            print(f"本月使用: {data.get('month_usage', 0)}次")
            print(f"总使用: {data.get('total_usage', 0)}次")
        else:
            print(self.color.warning("无法获取AI统计"))
    
    def handle_plans(self):
        """处理套餐命令"""
        print(self.color.header("支付套餐"))
        
        result = self.api.get_payment_plans()
        if "success" in result and result["success"]:
            plans = result.get("data", [])
            
            for plan in plans:
                print(f"\n{self.color.colorize(plan.get('name', '未知套餐'), 'cyan')}")
                print(f"价格: ¥{plan.get('price', 0)}")
                print(f"周期: {plan.get('period', 'N/A')}")
                print(f"功能: {plan.get('description', '无描述')}")
                print(f"限额: {plan.get('quota', '无限制')}")
        else:
            print(self.color.error(f"获取套餐失败: {result.get('error', '未知错误')}"))
    
    def handle_industrial(self, action: str, **kwargs):
        """处理工业级功能"""
        if action == "templates":
            print(self.color.header("工业级模板"))
            
            result = self.api.get_industrial_templates()
            if "success" in result and result["success"]:
                templates = result.get("data", [])
                
                for template in templates:
                    print(f"\n{self.color.colorize(template.get('name', '未知模板'), 'magenta')}")
                    print(f"ID: {template.get('id', 'N/A')}")
                    print(f"描述: {template.get('description', '无描述')}")
                    print(f"输出格式: {template.get('output_format', 'N/A')}")
            else:
                print(self.color.error(f"获取模板失败: {result.get('error', '未知错误')}"))
    
    def handle_batch(self, input_dir: str, action: str = "analyze"):
        """处理批量命令"""
        print(self.color.header(f"批量处理: {input_dir}"))
        
        input_path = Path(input_dir)
        if not input_path.exists():
            print(self.color.error(f"目录不存在: {input_dir}"))
            return
        
        # 查找视频文件
        video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.flv']
        video_files = []
        for ext in video_extensions:
            video_files.extend(list(input_path.glob(ext)))
        
        if not video_files:
            print(self.color.warning("未找到视频文件"))
            return
        
        print(f"找到 {len(video_files)} 个视频文件")
        
        for i, video_file in enumerate(video_files, 1):
            print(f"\n[{i}/{len(video_files)}] 处理: {video_file.name}")
            
            if action == "analyze":
                self.handle_analyze(str(video_file))
            elif action == "upload":
                self.handle_upload(str(video_file))
            
            # 添加延迟，避免请求过快
            if i < len(video_files):
                time.sleep(1)
        
        print(self.color.success(f"\n批量处理完成！共处理 {len(video_files)} 个文件"))
    
    def handle_direct_url(self, url: str, format_id: str = "best"):
        """处理直链命令"""
        print(self.color.header(f"获取视频直链: {url}"))
        
        result = self.api.get_direct_url(url, format_id)
        if "success" in result and result["success"]:
            print(self.color.success("直链获取成功！"))
            data = result.get("data", {})
            
            if isinstance(data, dict):
                print(f"视频标题: {data.get('title', 'N/A')}")
                print(f"格式: {data.get('format_id', 'N/A')}")
                if 'url' in data:
                    print(f"直链URL: {data['url']}")
                    print(f"文件大小: {data.get('filesize', 0) / 1024 / 1024:.2f} MB")
                else:
                    print(f"可用格式: {data.get('formats', [])}")
            else:
                print(f"直链数据: {data}")
        else:
            print(self.color.error(f"获取直链失败: {result.get('error', '未知错误')}"))
    
    def handle_register(self, email: str, password: str):
        """处理用户注册"""
        print(self.color.header("用户注册"))
        
        result = self.api.register_user(email, password)
        if "success" in result and result["success"]:
            print(self.color.success("注册成功！"))
            print(f"用户ID: {result.get('user_id', 'N/A')}")
            print(f"令牌: {result.get('token', 'N/A')[:20]}...")
        else:
            print(self.color.error(f"注册失败: {result.get('error', '未知错误')}"))
    
    def handle_login(self, email: str, password: str):
        """处理用户登录"""
        print(self.color.header("用户登录"))
        
        result = self.api.login_user(email, password)
        if "success" in result and result["success"]:
            print(self.color.success("登录成功！"))
            print(f"用户ID: {result.get('user_id', 'N/A')}")
            token = result.get('token', 'N/A')
            print(f"令牌: {token[:20]}...")
            
            # 保存令牌供后续使用
            token_file = Path.home() / ".videodl_token"
            try:
                with open(token_file, 'w') as f:
                    f.write(token)
                print(f"令牌已保存到: {token_file}")
            except:
                print("警告: 无法保存令牌文件")
        else:
            print(self.color.error(f"登录失败: {result.get('error', '未知错误')}"))
    
    def handle_user_info(self, token: str = None):
        """处理用户信息命令"""
        print(self.color.header("用户信息"))
        
        if not token:
            token_file = Path.home() / ".videodl_token"
            if token_file.exists():
                try:
                    with open(token_file, 'r') as f:
                        token = f.read().strip()
                except:
                    token = None
        
        if not token:
            print(self.color.warning("未找到令牌，请先登录"))
            return
        
        result = self.api.get_user_info(token)
        if "success" in result and result["success"]:
            data = result.get("data", {})
            print(self.color.success("获取用户信息成功！"))
            print(f"用户ID: {data.get('id', 'N/A')}")
            print(f"邮箱: {data.get('email', 'N/A')}")
            print(f"级别: {data.get('level', '免费用户')}")
            print(f"创建时间: {data.get('created_at', 'N/A')}")
        else:
            print(self.color.error(f"获取用户信息失败: {result.get('error', '未知错误')}"))
    
    def handle_payment_methods(self):
        """处理支付方式命令"""
        print(self.color.header("支付方式"))
        
        result = self.api.get_payment_methods()
        if "success" in result and result["success"]:
            methods = result.get("data", [])
            
            for method in methods:
                print(f"\n{self.color.colorize(method.get('name', '未知方式'), 'cyan')}")
                print(f"类型: {method.get('type', 'N/A')}")
                print(f"费率: {method.get('fee_rate', 0) * 100:.2f}%")
                print(f"描述: {method.get('description', '无描述')}")
        else:
            print(self.color.error(f"获取支付方式失败: {result.get('error', '未知错误')}"))
    
    def handle_industrial_report(self):
        """处理工业报告命令"""
        print(self.color.header("工业化商业报告"))
        
        result = self.api.get_industrial_report()
        if "success" in result and result["success"]:
            data = result.get("data", {})
            
            if 'metrics' in data:
                metrics = data['metrics']
                print(self.color.subheader("关键指标"))
                print(f"用户增长率: {metrics.get('user_growth_rate', 0) * 100:.2f}%")
                print(f"付费转化率: {metrics.get('conversion_rate', 0) * 100:.2f}%")
                print(f"月收入: ¥{metrics.get('monthly_revenue', 0)}")
                print(f"客户获取成本: ¥{metrics.get('cac', 0)}")
            
            if 'recommendations' in data:
                print(self.color.subheader("优化建议"))
                for rec in data['recommendations'][:3]:
                    print(f"- {rec}")
        else:
            print(self.color.error(f"获取报告失败: {result.get('error', '未知错误')}"))
    
    def handle_formats(self):
        """处理格式命令"""
        print(self.color.header("支持的视频格式"))
        
        result = self.api.get_supported_formats()
        if "success" in result and result["success"]:
            formats = result.get("data", [])
            
            for fmt in formats:
                print(f"\n{self.color.colorize(fmt.get('name', '未知格式'), 'green')}")
                print(f"扩展名: {', '.join(fmt.get('extensions', []))}")
                print(f"描述: {fmt.get('description', '无描述')}")
        else:
            print(self.color.warning("无法获取格式列表，可能API端点不存在"))
            print("已知支持的格式: mp4, avi, mov, mkv, flv, wmv")


def main():
    parser = argparse.ArgumentParser(
        description="万能视频下载器 - 增强版 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  视频功能:
    %(prog)s parse https://youtube.com/watch?v=xxx
    %(prog)s download https://bilibili.com/video/BVxxx
    %(prog)s direct https://youtube.com/watch?v=xxx --format best
    %(prog)s upload ./my_video.mp4
  
  AI分析功能:
    %(prog)s analyze ./my_video.mp4
    %(prog)s summarize https://youtube.com/watch?v=xxx --level high
  
  用户功能:
    %(prog)s register user@example.com password123
    %(prog)s login user@example.com password123
    %(prog)s user --token <token>
  
  商业功能:
    %(prog)s status
    %(prog)s plans
    %(prog)s payment-methods
    %(prog)s industrial templates
    %(prog)s industrial-report
    %(prog)s formats
  
  批量处理:
    %(prog)s batch ./videos/ --action analyze
    %(prog)s batch ./uploads/ --action upload
  
  保留原有搜索引擎用法:
    1. 搜索视频 -> 复制URL
    2. 使用CLI: %(prog)s parse <URL>
    3. 使用CLI: %(prog)s download <URL>
        """
    )
    
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"API服务器URL (默认: {DEFAULT_API_URL})")
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # parse 命令
    parse_parser = subparsers.add_parser('parse', help='解析视频信息')
    parse_parser.add_argument('url', help='视频URL')
    
    # download 命令
    download_parser = subparsers.add_parser('download', help='下载视频')
    download_parser.add_argument('url', help='视频URL')
    download_parser.add_argument('--format', default='best', help='视频格式 (默认: best)')
    
    # upload 命令
    upload_parser = subparsers.add_parser('upload', help='上传视频')
    upload_parser.add_argument('video_path', help='视频文件路径')
    
    # analyze 命令
    analyze_parser = subparsers.add_parser('analyze', help='AI分析视频')
    analyze_parser.add_argument('video', help='视频文件路径或视频ID')
    
    # summarize 命令
    summarize_parser = subparsers.add_parser('summarize', help='视频摘要')
    summarize_parser.add_argument('url', help='视频URL')
    summarize_parser.add_argument('--level', choices=['simple', 'medium', 'detailed'], 
                                  default='medium', help='摘要详细程度')
    
    # status 命令
    subparsers.add_parser('status', help='检查系统状态')
    
    # plans 命令
    subparsers.add_parser('plans', help='查看支付套餐')
    
    # industrial 命令
    industrial_parser = subparsers.add_parser('industrial', help='工业级功能')
    industrial_subparsers = industrial_parser.add_subparsers(dest='industrial_action', help='工业级操作')
    industrial_subparsers.add_parser('templates', help='查看工业级模板')
    
    # batch 命令
    batch_parser = subparsers.add_parser('batch', help='批量处理')
    batch_parser.add_argument('input_dir', help='输入目录')
    batch_parser.add_argument('--action', choices=['analyze', 'upload'], default='analyze', help='处理类型')
    
    # direct-url 命令
    direct_parser = subparsers.add_parser('direct', help='获取视频直链')
    direct_parser.add_argument('url', help='视频URL')
    direct_parser.add_argument('--format', default='best', help='视频格式 (默认: best)')
    
    # register 命令
    register_parser = subparsers.add_parser('register', help='用户注册')
    register_parser.add_argument('email', help='用户邮箱')
    register_parser.add_argument('password', help='用户密码')
    
    # login 命令
    login_parser = subparsers.add_parser('login', help='用户登录')
    login_parser.add_argument('email', help='用户邮箱')
    login_parser.add_argument('password', help='用户密码')
    
    # user 命令
    user_parser = subparsers.add_parser('user', help='用户信息')
    user_parser.add_argument('--token', help='认证令牌，如未提供则从~/.videodl_token读取')
    
    # payment-methods 命令
    subparsers.add_parser('payment-methods', help='查看支付方式')
    
    # industrial-report 命令
    subparsers.add_parser('industrial-report', help='工业化商业报告')
    
    # formats 命令
    subparsers.add_parser('formats', help='查看支持的视频格式')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 初始化CLI处理器
    handler = CLIHandler(args.api_url)
    
    try:
        if args.command == 'parse':
            handler.handle_parse(args.url)
        elif args.command == 'download':
            handler.handle_download(args.url, args.format)
        elif args.command == 'upload':
            handler.handle_upload(args.video_path)
        elif args.command == 'analyze':
            handler.handle_analyze(args.video)
        elif args.command == 'summarize':
            handler.handle_summarize(args.url, args.level)
        elif args.command == 'status':
            handler.handle_status()
        elif args.command == 'plans':
            handler.handle_plans()
        elif args.command == 'industrial':
            if args.industrial_action == 'templates':
                handler.handle_industrial('templates')
            else:
                print("请指定工业级操作，如: templates")
        elif args.command == 'batch':
            handler.handle_batch(args.input_dir, args.action)
        elif args.command == 'direct':
            handler.handle_direct_url(args.url, args.format)
        elif args.command == 'register':
            handler.handle_register(args.email, args.password)
        elif args.command == 'login':
            handler.handle_login(args.email, args.password)
        elif args.command == 'user':
            handler.handle_user_info(args.token)
        elif args.command == 'payment-methods':
            handler.handle_payment_methods()
        elif args.command == 'industrial-report':
            handler.handle_industrial_report()
        elif args.command == 'formats':
            handler.handle_formats()
        else:
            print(f"未知命令: {args.command}")
            
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()