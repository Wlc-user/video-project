#!/usr/bin/env python3
"""
万能视频下载器 CLI 工具
基于 yt-dlp，支持 1800+ 平台的视频下载，同时提供 AI 视频分析功能
保留原有搜索引擎，逐步替代用户习惯的 CLI 工具
"""

import os
import sys
import json
import argparse
import subprocess
from typing import Dict, Any, Optional
import yt_dlp
import requests
from pathlib import Path

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
UPLOAD_DIR = os.path.join(BASE_DIR, "user_uploads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# API 服务器配置
API_BASE_URL = "http://localhost:8000"


class VideoDownloaderCLI:
    """视频下载器 CLI 核心类"""
    
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'noplaylist': True,
        }
    
    def parse_video(self, url: str) -> Dict[str, Any]:
        """解析视频信息"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                result = {
                    'title': info.get('title', '未知标题'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', '未知作者'),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'description': info.get('description', '')[:200] + '...' if info.get('description') else '',
                    'formats': []
                }
                
                if 'formats' in info:
                    for fmt in info['formats']:
                        if fmt.get('ext') in ['mp4', 'webm', 'mkv', 'flv']:
                            result['formats'].append({
                                'format_id': fmt.get('format_id', ''),
                                'ext': fmt.get('ext', ''),
                                'resolution': fmt.get('resolution', ''),
                                'filesize': fmt.get('filesize', 0),
                            })
                
                return result
        except Exception as e:
            return {'error': str(e)}
    
    def download_video(self, url: str, output_dir: str = None) -> Dict[str, Any]:
        """下载视频"""
        if output_dir is None:
            output_dir = DOWNLOAD_DIR
        
        download_opts = {
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'quiet': False,
            'progress_hooks': [self._progress_hook],
        }
        
        try:
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                for ext in ['mp4', 'webm', 'mkv', 'flv', 'm4a']:
                    possible_file = filename.rsplit('.', 1)[0] + '.' + ext
                    if os.path.exists(possible_file):
                        filename = possible_file
                        break
                
                return {
                    'success': True,
                    'filename': os.path.basename(filename),
                    'filepath': filename,
                    'title': info.get('title', '未知标题'),
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _progress_hook(self, d):
        """下载进度回调"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').strip()
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            print(f"\r下载进度: {percent} | 速度: {speed}/s | 剩余时间: {eta}", end='', flush=True)
        elif d['status'] == 'finished':
            print(f"\n下载完成！")


class APIClient:
    """API 客户端类"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
    
    def check_api_status(self) -> bool:
        """检查API服务状态"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def analyze_video(self, video_path: str) -> Dict[str, Any]:
        """分析视频内容"""
        if not os.path.exists(video_path):
            return {'error': f'文件不存在: {video_path}'}
        
        try:
            upload_url = f"{self.base_url}/api/upload"
            with open(video_path, 'rb') as f:
                files = {'file': (os.path.basename(video_path), f, 'video/mp4')}
                response = requests.post(upload_url, files=files)
            
            if response.status_code != 200:
                return {'error': f'上传失败: {response.text}'}
            
            return response.json()
        except Exception as e:
            return {'error': str(e)}
    
    def get_payment_plans(self) -> Dict[str, Any]:
        """获取支付套餐"""
        try:
            response = requests.get(f"{self.base_url}/api/payment/plans")
            return response.json()
        except Exception as e:
            return {'error': str(e)}


def display_formatted_json(data: Dict[str, Any]):
    """格式化显示JSON数据"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="万能视频下载器 CLI 工具 - 支持 1800+ 平台视频下载和AI分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s parse https://www.youtube.com/watch?v=dQw4w9WgXcQ
  %(prog)s download https://www.bilibili.com/video/BV1GJ411x7h7
  %(prog)s analyze ./my_video.mp4
  %(prog)s status
  %(prog)s plans
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # parse 命令
    parse_parser = subparsers.add_parser('parse', help='解析视频信息')
    parse_parser.add_argument('url', help='视频URL')
    
    # download 命令
    download_parser = subparsers.add_parser('download', help='下载视频')
    download_parser.add_argument('url', help='视频URL')
    download_parser.add_argument('-o', '--output', help='输出目录', default=None)
    
    # analyze 命令
    analyze_parser = subparsers.add_parser('analyze', help='AI分析视频')
    analyze_parser.add_argument('video_path', help='视频文件路径')
    
    # status 命令
    subparsers.add_parser('status', help='检查API服务状态')
    
    # plans 命令
    subparsers.add_parser('plans', help='查看支付套餐')
    
    # search 命令
    search_parser = subparsers.add_parser('search', help='搜索视频内容')
    search_parser.add_argument('query', help='搜索关键词')
    search_parser.add_argument('-l', '--limit', type=int, default=10, help='结果数量限制')
    
    # upload 命令
    upload_parser = subparsers.add_parser('upload', help='上传视频到平台')
    upload_parser.add_argument('video_path', help='视频文件路径')
    
    # 批量处理命令
    batch_parser = subparsers.add_parser('batch', help='批量处理视频')
    batch_parser.add_argument('input_dir', help='输入目录')
    batch_parser.add_argument('-t', '--type', choices=['analyze', 'upload'], default='analyze', help='处理类型')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 初始化组件
    downloader = VideoDownloaderCLI()
    api_client = APIClient()
    
    try:
        if args.command == 'parse':
            print(f"正在解析视频: {args.url}")
            result = downloader.parse_video(args.url)
            display_formatted_json(result)
            
        elif args.command == 'download':
            print(f"正在下载视频: {args.url}")
            result = downloader.download_video(args.url, args.output)
            display_formatted_json(result)
            
        elif args.command == 'analyze':
            print(f"正在分析视频: {args.video_path}")
            result = api_client.analyze_video(args.video_path)
            display_formatted_json(result)
            
        elif args.command == 'status':
            if api_client.check_api_status():
                print("✅ API服务运行正常")
            else:
                print("❌ API服务未运行，请先启动服务器")
                print(f"运行: cd {BASE_DIR} && python main.py")
                
        elif args.command == 'plans':
            print("正在获取支付套餐信息...")
            result = api_client.get_payment_plans()
            display_formatted_json(result)
            
        elif args.command == 'search':
            print(f"正在搜索: {args.query}")
            # 这里可以调用搜索API
            print("搜索功能需要API支持，请确保服务器已启动")
            
        elif args.command == 'upload':
            print(f"正在上传视频: {args.video_path}")
            result = api_client.analyze_video(args.video_path)
            display_formatted_json(result)
            
        elif args.command == 'batch':
            input_path = Path(args.input_dir)
            if not input_path.exists():
                print(f"错误: 目录不存在 - {args.input_dir}")
                sys.exit(1)
                
            video_files = list(input_path.glob("*.mp4")) + list(input_path.glob("*.avi")) + \
                         list(input_path.glob("*.mov")) + list(input_path.glob("*.mkv"))
            
            print(f"找到 {len(video_files)} 个视频文件")
            
            for i, video_file in enumerate(video_files, 1):
                print(f"\n[{i}/{len(video_files)}] 处理: {video_file.name}")
                
                if args.type == 'analyze':
                    result = api_client.analyze_video(str(video_file))
                    print(f"分析结果: {result.get('success', False)}")
                elif args.type == 'upload':
                    # 上传逻辑
                    pass
            
            print(f"\n批量处理完成！")
            
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(0)
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()