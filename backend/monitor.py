# -*- coding: utf-8 -*-
"""
定时巡检模块
定时检测目标平台是否有侵权内容
"""

import os
import re
import time
import json
import smtplib
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from abc import ABC, abstractmethod
import requests

from similarity import SimilarityDetector
from video_fingerprint import VideoFingerprint, extract_video_fingerprint


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PlatformScraper(ABC):
    """平台爬虫基类"""
    
    @abstractmethod
    def get_videos(self, keyword: str, limit: int = 20) -> List[Dict]:
        """获取视频列表"""
        pass


class BilibiliScraper(PlatformScraper):
    """B站爬虫"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.bilibili.com'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_videos(self, keyword: str, limit: int = 20) -> List[Dict]:
        """搜索B站视频"""
        videos = []
        
        try:
            url = f"https://api.bilibili.com/master/web/search/search_type/video"
            params = {
                'search_type': 'video',
                'keyword': keyword,
                'page': 1,
                'page_size': limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('code') == 0:
                for item in data.get('data', {}).get('result', []):
                    videos.append({
                        'title': item.get('title', ''),
                        'bvid': item.get('bvid', ''),
                        'author': item.get('author', ''),
                        'play': item.get('play', 0),
                        'url': f"https://www.bilibili.com/video/{item.get('bvid', '')}"
                    })
        
        except Exception as e:
            logger.error(f"B站搜索失败: {e}")
        
        return videos


class DouyinScraper(PlatformScraper):
    """抖音爬虫"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
        }
    
    def get_videos(self, keyword: str, limit: int = 20) -> List[Dict]:
        """搜索抖音视频"""
        videos = []
        
        try:
            headers = {
                **self.headers,
                'Referer': 'https://www.douyin.com/'
            }
            
            response = requests.get(
                "https://www.douyin.com/aweme/v1/web/search/item/",
                params={'keyword': keyword, 'count': limit},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get('item_list', []):
                    videos.append({
                        'title': item.get('desc', ''),
                        'aweme_id': item.get('aweme_id', ''),
                        'author': item.get('author', {}).get('nickname', ''),
                        'url': f"https://www.douyin.com/video/{item.get('aweme_id', '')}"
                    })
        
        except Exception as e:
            logger.error(f"抖音搜索失败: {e}")
        
        return videos


class CopyrightMonitor:
    """版权监控系统"""
    
    def __init__(
        self,
        fingerprints_dir: str = "data/fingerprints",
        download_dir: str = "data/downloads",
        checkpoint_file: str = "data/monitor_checkpoint.json"
    ):
        self.fingerprints_dir = Path(fingerprints_dir)
        self.download_dir = Path(download_dir)
        self.checkpoint_file = Path(checkpoint_file)
        
        self.fingerprints_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.fingerprint_gen = VideoFingerprint(frames_dir=str(self.fingerprints_dir))
        self.similarity_detector = SimilarityDetector(fingerprints_dir=str(self.fingerprints_dir))
        
        self.scrapers = {
            'bilibili': BilibiliScraper(),
            'douyin': DouyinScraper()
        }
        
        self.watchlist: List[Dict] = []
        self.load_checkpoint()
    
    def load_checkpoint(self):
        """加载检查点"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.watchlist = data.get('watchlist', [])
                    logger.info(f"已加载 {len(self.watchlist)} 个监控关键词")
            except Exception as e:
                logger.error(f"加载检查点失败: {e}")
    
    def save_checkpoint(self):
        """保存检查点"""
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'watchlist': self.watchlist,
                    'last_update': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
    
    def add_to_watchlist(self, keyword: str, platforms: List[str] = None, priority: int = 1, video_path: str = None):
        """添加监控关键词
        
        Args:
            keyword: 监控关键词（用于在平台搜索）
            platforms: 监控平台列表
            priority: 优先级
            video_path: 原始视频路径（可选，如果不提供则使用默认路径）
        """
        if platforms is None:
            platforms = ['bilibili', 'douyin']
        
        # 如果没有提供视频路径，使用默认路径
        if video_path is None:
            video_path = f"data/uploads/{keyword}.mp4"
        
        # 检查视频文件或指纹是否存在
        fingerprint_path = f"data/fingerprints/{keyword}.json"
        video_exists = Path(video_path).exists()
        fingerprint_exists = Path(fingerprint_path).exists()
        
        if not video_exists and not fingerprint_exists:
            logger.warning(f"⚠️ 视频文件不存在: {video_path}")
            logger.warning(f"⚠️ 指纹文件不存在: {fingerprint_path}")
            logger.warning(f"⚠️ 请先生成指纹: python video_fingerprint.py generate \"{video_path}\"")
        
        self.watchlist.append({
            'keyword': keyword,
            'platforms': platforms,
            'priority': priority,
            'video_path': video_path,
            'added_at': datetime.now().isoformat(),
            'last_check': None,
            'matches': []
        })
        
        self.save_checkpoint()
        logger.info(f"已添加监控: {keyword}")
        logger.info(f"  - 视频路径: {video_path}")
        logger.info(f"  - 监控平台: {', '.join(platforms)}")
    
    def remove_from_watchlist(self, keyword: str):
        """移除监控关键词"""
        self.watchlist = [w for w in self.watchlist if w['keyword'] != keyword]
        self.save_checkpoint()
    
    def check_platform(self, platform: str, keyword: str) -> List[Dict]:
        """检查单个平台"""
        if platform not in self.scrapers:
            logger.warning(f"不支持的平台: {platform}")
            return []
        
        scraper = self.scrapers[platform]
        
        try:
            videos = scraper.get_videos(keyword, limit=30)
            logger.info(f"{platform} 找到 {len(videos)} 个视频: {keyword}")
            return videos
        except Exception as e:
            logger.error(f"{platform} 检查失败: {e}")
            return []
    
    def check_all_platforms(self, keyword: str) -> List[Dict]:
        """检查所有平台"""
        results = []
        
        for platform in ['bilibili', 'douyin']:
            videos = self.check_platform(platform, keyword)
            for video in videos:
                video['platform'] = platform
                results.append(video)
        
        return results
    
    def scan_for_infringement(
        self,
        original_video_path: str,
        keyword: str = None,
        platforms: List[str] = None,
        threshold: float = 60.0
    ) -> List[Dict]:
        """扫描侵权内容
        
        优先使用已存在的指纹，避免重复生成
        """
        if keyword is None:
            keyword = Path(original_video_path).stem
        
        logger.info(f"开始扫描侵权内容: {keyword}")
        
        # 尝试使用已存在的指纹
        # 尝试多种可能的指纹文件名
        possible_paths = [
            f"data/fingerprints/{keyword}.json",
            f"data/fingerprints/{Path(original_video_path).stem}.json",
            f"data/fingerprints/{Path(original_video_path).name}.json",
        ]
        
        original_fp = None
        
        # 先检查是否有现有指纹
        for fp_path in possible_paths:
            fp_file = Path(fp_path)
            if fp_file.exists():
                try:
                    with open(fp_file, 'r', encoding='utf-8') as f:
                        fp_data = json.load(f)
                        original_fp = fp_data
                        logger.info(f"已加载现有指纹: {fp_path}")
                        break
                except Exception as e:
                    logger.warning(f"加载指纹失败: {e}")
        
        # 如果没有现有指纹，尝试生成
        if original_fp is None:
            video_file = Path(original_video_path)
            if video_file.exists():
                try:
                    original_fp = self.fingerprint_gen.generate_video_fingerprint(str(video_file))
                    # 保存指纹以便下次使用
                    self.fingerprint_gen.save_fingerprint(original_fp)
                    logger.info(f"已生成新指纹: {original_video_path}")
                except Exception as e:
                    logger.error(f"生成指纹失败: {e}")
                    return []
            else:
                logger.error(f"视频文件不存在: {original_video_path}")
                logger.info(f"提示: 请先上传视频并生成指纹")
                return []
        
        matches = []
        
        # 在平台上搜索
        for platform in (platforms or ['bilibili', 'douyin']):
            videos = self.check_platform(platform, keyword)
            
            for video in videos:
                matches.append({
                    'video': video,
                    'original': keyword,
                    'platform': platform,
                    'status': 'pending_check',
                    'checked_at': datetime.now().isoformat()
                })
        
        logger.info(f"发现 {len(matches)} 个疑似侵权内容")
        return matches
    
    def run_scheduled_scan(self):
        """运行定时扫描"""
        logger.info("=" * 50)
        logger.info("开始定时巡检")
        logger.info("=" * 50)
        
        if not self.watchlist:
            logger.info("监控列表为空，请先添加监控项")
            logger.info("用法: python monitor.py add <关键词> [平台1] [平台2]")
            return []
        
        scan_results = []
        
        for watch_item in self.watchlist:
            keyword = watch_item['keyword']
            platforms = watch_item['platforms']
            video_path = watch_item.get('video_path', f"data/uploads/{keyword}.mp4")
            
            logger.info(f"检查关键词: {keyword}")
            logger.info(f"视频路径: {video_path}")
            
            matches = self.scan_for_infringement(
                original_video_path=video_path,
                keyword=keyword,
                platforms=platforms
            )
            
            watch_item['last_check'] = datetime.now().isoformat()
            watch_item['matches'] = matches
            
            scan_results.append({
                'keyword': keyword,
                'matches_count': len(matches),
                'matches': matches
            })
        
        self.save_checkpoint()
        
        alert_count = sum(r['matches_count'] for r in scan_results)
        if alert_count > 0:
            self._send_notification(scan_results)
        
        return scan_results
    
    def _send_notification(self, results: List[Dict]):
        """发送通知"""
        alert_count = sum(r['matches_count'] for r in results)
        logger.warning(f"⚠️ 发现 {alert_count} 个疑似侵权内容！")
        
        alert_file = Path("data/alerts.json")
        with open(alert_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': results
            }, f, indent=2, ensure_ascii=False)
    
    def set_email_notification(
        self,
        smtp_server: str,
        smtp_port: int,
        sender: str,
        password: str,
        recipients: List[str]
    ):
        """配置邮件通知"""
        self.email_config = {
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'sender': sender,
            'password': password,
            'recipients': recipients
        }
    
    def send_email(self, subject: str, content: str):
        """发送邮件"""
        if not hasattr(self, 'email_config'):
            return
        
        config = self.email_config
        
        msg = MIMEMultipart()
        msg['From'] = config['sender']
        msg['To'] = ', '.join(config['recipients'])
        msg['Subject'] = subject
        
        msg.attach(MIMEText(content, 'html', 'utf-8'))
        
        try:
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            server.login(config['sender'], config['password'])
            server.send_message(msg)
            server.quit()
            logger.info("邮件发送成功")
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")


class MonitorScheduler:
    """监控调度器"""
    
    def __init__(self, monitor: CopyrightMonitor):
        self.monitor = monitor
        self.running = False
    
    def start(self, interval_hours: int = 24):
        """启动定时监控"""
        self.running = True
        interval_seconds = interval_hours * 3600
        
        logger.info(f"监控已启动，间隔: {interval_hours} 小时")
        
        while self.running:
            try:
                self.monitor.run_scheduled_scan()
            except Exception as e:
                logger.error(f"监控执行失败: {e}")
            
            logger.info(f"等待 {interval_hours} 小时后再次扫描...")
            
            for _ in range(interval_seconds):
                if not self.running:
                    break
                time.sleep(1)
    
    def stop(self):
        """停止监控"""
        self.running = False
        logger.info("监控已停止")


if __name__ == "__main__":
    import sys
    
    monitor = CopyrightMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "add":
            if len(sys.argv) > 2:
                keyword = sys.argv[2]
                
                # 解析参数：--video 或 -v 指定视频路径
                platforms = []
                video_path = None
                
                for arg in sys.argv[3:]:
                    if arg.startswith('--video=') or arg.startswith('-v='):
                        video_path = arg.split('=', 1)[1]
                    elif arg.startswith('-'):
                        continue  # 跳过其他选项
                    else:
                        platforms.append(arg)
                
                if not platforms:
                    platforms = None  # 使用默认平台
                
                monitor.add_to_watchlist(keyword, platforms, video_path=video_path)
            else:
                print("用法: python monitor.py add <关键词> [平台1] [平台2] [--video=<视频路径>]")
                print("")
                print("示例:")
                print("  python monitor.py add \"我的视频标题\"                    # 添加监控（使用默认视频路径）")
                print("  python monitor.py add \"我的视频标题\" --video=\"D:/video.mp4\"  # 指定视频路径")
                print("  python monitor.py add \"我的视频标题\" bilibili douyin       # 只监控B站和抖音")
        
        elif command == "remove":
            if len(sys.argv) > 2:
                keyword = sys.argv[2]
                monitor.remove_from_watchlist(keyword)
            else:
                print("用法: python monitor.py remove <关键词>")
        
        elif command == "scan":
            monitor.run_scheduled_scan()
        
        elif command == "watchlist":
            print("\n当前监控列表:")
            print("-" * 50)
            if not monitor.watchlist:
                print("(空)")
            for i, item in enumerate(monitor.watchlist):
                print(f"{i+1}. {item['keyword']}")
                print(f"   视频路径: {item.get('video_path', '未设置')}")
                print(f"   平台: {', '.join(item['platforms'])}")
                print(f"   添加时间: {item['added_at']}")
                print(f"   上次检查: {item.get('last_check', '从未检查')}")
                print(f"   发现疑似侵权: {len(item.get('matches', []))} 个")
                print()
        
        elif command == "daemon":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            scheduler = MonitorScheduler(monitor)
            scheduler.start(interval)
    else:
        print("""
版权监控工具 v2.0
================
用法:
  python monitor.py add <关键词> [平台...] [--video=<路径>]   - 添加监控
  python monitor.py remove <关键词>                           - 移除监控
  python monitor.py scan                                       - 立即扫描
  python monitor.py watchlist                                   - 查看监控列表
  python monitor.py daemon [小时数]                            - 启动定时监控

工作流程:
  1. 将原创视频放入 data/uploads/ 目录
  2. 使用 video_fingerprint.py 生成指纹
  3. 使用 monitor.py add 添加监控关键词
  4. 使用 monitor.py scan 或 daemon 进行巡检
        """)
