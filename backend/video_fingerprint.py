# -*- coding: utf-8 -*-
"""
视频指纹模块 - 使用 pHash 和 dHash 算法生成视频指纹
用于版权保护和侵权检测
"""

import os
import cv2
import imagehash
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import json

# 可选依赖
try:
    import imagehash
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False
    print("警告: imagehash 未安装, 将使用简化版 pHash")


class VideoFingerprint:
    """视频指纹生成器"""
    
    def __init__(self, frames_dir: str = "data/fingerprints"):
        """
        初始化视频指纹生成器
        
        Args:
            frames_dir: 帧提取存储目录
        """
        self.frames_dir = Path(frames_dir)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        
        # 指纹参数
        self.hash_size = 16  # pHash 大小
        self.threshold = 5   # 汉明距离阈值
    
    def extract_frames(self, video_path: str, num_frames: int = 16) -> List[np.ndarray]:
        """
        从视频中均匀提取帧
        
        Args:
            video_path: 视频文件路径
            num_frames: 提取的帧数
            
        Returns:
            帧列表
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames == 0:
            cap.release()
            raise ValueError(f"无法读取视频: {video_path}")
        
        frames = []
        interval = max(1, total_frames // num_frames)
        
        for i in range(num_frames):
            frame_pos = i * interval
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = cap.read()
            
            if ret:
                frames.append(frame)
        
        cap.release()
        return frames
    
    def frame_to_grayscale(self, frame: np.ndarray) -> Image.Image:
        """
        将帧转换为灰度图像
        
        Args:
            frame: OpenCV 帧 (BGR)
            
        Returns:
            PIL 图像
        """
        # BGR 转 RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
    
    def compute_phash(self, frame: np.ndarray) -> str:
        """
        计算帧的 pHash
        
        Args:
            frame: OpenCV 帧
            
        Returns:
            pHash 字符串
        """
        if HAS_IMAGEHASH:
            img = self.frame_to_grayscale(frame)
            return str(imagehash.phash(img, hash_size=self.hash_size))
        else:
            # 简化版 pHash 实现
            return self._simple_phash(frame)
    
    def compute_dhash(self, frame: np.ndarray) -> str:
        """
        计算帧的 dHash
        
        Args:
            frame: OpenCV 帧
            
        Returns:
            dHash 字符串
        """
        if HAS_IMAGEHASH:
            img = self.frame_to_grayscale(frame)
            return str(imagehash.dhash(img))
        else:
            return self._simple_dhash(frame)
    
    def compute_ahash(self, frame: np.ndarray) -> str:
        """计算帧的 aHash"""
        if HAS_IMAGEHASH:
            img = self.frame_to_grayscale(frame)
            return str(imagehash.ahash(img))
        return self._simple_ahash(frame)
    
    def _simple_phash(self, frame: np.ndarray) -> str:
        """简化版 pHash"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (self.hash_size + 1, self.hash_size + 1))
        diff = resized[:, :-1] > resized[:, 1:]
        return ''.join(diff.flatten().astype(str))
    
    def _simple_dhash(self, frame: np.ndarray) -> str:
        """简化版 dHash"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (self.hash_size + 1, self.hash_size), interpolation=cv2.INTER_AREA)
        diff = resized[:, :-1] > resized[:, 1:]
        return ''.join(diff.flatten().astype(str))
    
    def _simple_ahash(self, frame: np.ndarray) -> str:
        """简化版 aHash"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (self.hash_size, self.hash_size))
        avg = resized.mean()
        bits = resized > avg
        return ''.join(bits.flatten().astype(str))
    
    def generate_video_fingerprint(self, video_path: str) -> Dict:
        """
        生成视频指纹
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            包含多种指纹的字典
        """
        print(f"正在生成视频指纹: {video_path}")
        
        # 提取帧
        frames = self.extract_frames(video_path, num_frames=16)
        
        if not frames:
            raise ValueError("无法从视频中提取帧")
        
        # 计算各帧指纹
        phash_list = []
        dhash_list = []
        
        for i, frame in enumerate(frames):
            ph = self.compute_phash(frame)
            dh = self.compute_dhash(frame)
            phash_list.append(ph)
            dhash_list.append(dh)
        
        # 计算视频级别指纹（所有帧指纹的组合）
        video_phash = self._combine_hashes(phash_list)
        video_dhash = self._combine_hashes(dhash_list)
        
        # 计算颜色直方图特征
        color_hist = self._compute_color_histogram(frames)
        
        result = {
            "video_path": video_path,
            "video_name": os.path.basename(video_path),
            "frame_count": len(frames),
            "timestamp": datetime.now().isoformat(),
            "phash": video_phash,
            "dhash": video_dhash,
            "frame_phashes": phash_list[:8],  # 保留前8帧
            "frame_dhashes": dhash_list[:8],
            "color_histogram": color_hist.tolist() if color_hist is not None else None,
            "hash_size": self.hash_size
        }
        
        return result
    
    def _combine_hashes(self, hash_list: List[str]) -> str:
        """组合多个哈希值"""
        if not hash_list:
            return ""
        
        # 取第一个和最后一个帧的指纹组合
        combined = hash_list[0] + hash_list[-1]
        if len(hash_list) > 2:
            # 添加中间帧增加区分度
            combined += hash_list[len(hash_list) // 2]
        return combined[:64]  # 限制长度
    
    def _compute_color_histogram(self, frames: List[np.ndarray]) -> Optional[np.ndarray]:
        """计算颜色直方图特征"""
        if not frames:
            return None
        
        # 使用第一帧、中间帧、最后一帧
        sample_frames = [frames[0], frames[len(frames)//2], frames[-1]]
        
        hist_features = []
        for frame in sample_frames:
            # 计算 HSV 颜色空间的直方图
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            hist_features.extend(hist.flatten())
        
        return np.array(hist_features)
    
    def save_fingerprint(self, fingerprint: Dict, output_path: Optional[str] = None) -> str:
        """
        保存指纹到文件
        
        Args:
            fingerprint: 指纹数据
            output_path: 输出路径（可选）
            
        Returns:
            保存的路径
        """
        if output_path is None:
            # 优先使用视频名作为基础名称（去掉扩展名）
            video_name = fingerprint.get("video_name", "video")
            base_name = os.path.splitext(video_name)[0]
            output_path = self.frames_dir / f"{base_name}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(fingerprint, f, indent=2, ensure_ascii=False)
        
        print(f"指纹已保存: {output_path}")
        return str(output_path)
    
    def load_fingerprint(self, fingerprint_path: str) -> Dict:
        """加载指纹文件"""
        with open(fingerprint_path, 'r', encoding='utf-8') as f:
            return json.load(f)


def extract_video_fingerprint(video_path: str, output_dir: str = "data/fingerprints") -> Dict:
    """
    便捷函数：提取视频指纹
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        
    Returns:
        指纹数据
    """
    generator = VideoFingerprint(frames_dir=output_dir)
    fingerprint = generator.generate_video_fingerprint(video_path)
    generator.save_fingerprint(fingerprint)
    return fingerprint


if __name__ == "__main__":
    # 测试
    import sys
    
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        result = extract_video_fingerprint(video_path)
        print(f"指纹生成完成: {result['video_name']}")
        print(f"pHash: {result['phash'][:32]}...")
    else:
        print("用法: python video_fingerprint.py <视频路径>")
