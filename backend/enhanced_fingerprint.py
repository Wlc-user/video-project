# -*- coding: utf-8 -*-
"""
增强版视频指纹模块
整合多种算法：pHash + SIFT + 音频指纹 + 关键帧
用于更精准的版权保护和侵权检测
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
import hashlib

# 可选依赖
try:
    import imagehash
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False
    print("警告: imagehash 未安装")

try:
    import librosa
    import soundfile as sf
    HAS_AUDIO = True
    
    # 配置 librosa 使用 audioread（兼容性好）
    import os
    os.environ['LIBROSA_CACHE_DIR'] = 'temp/audio_cache'
    
except ImportError:
    HAS_AUDIO = False
    print("提示: librosa 未安装，音频指纹功能不可用")


class EnhancedVideoFingerprint:
    """增强版视频指纹生成器"""

    def __init__(self, frames_dir: str = "data/fingerprints"):
        self.frames_dir = Path(frames_dir)
        self.frames_dir.mkdir(parents=True, exist_ok=True)

        # 指纹参数
        self.hash_size = 16
        self.threshold = 5
        self.num_frames = 16  # 提取帧数
        self.num_keyframes = 5  # 关键帧数量

        # SIFT 检测器
        self._sift = None
        self._orb = None

    @property
    def sift(self):
        """懒加载SIFT"""
        if self._sift is None:
            self._sift = cv2.SIFT_create(nfeatures=500)
        return self._sift

    @property
    def orb(self):
        """懒加载ORB"""
        if self._orb is None:
            self._orb = cv2.ORB_create(nfeatures=500)
        return self._orb

    def extract_frames(self, video_path: str, num_frames: int = None) -> List[np.ndarray]:
        """从视频中均匀提取帧"""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        if num_frames is None:
            num_frames = self.num_frames

        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

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

    def extract_keyframes(self, video_path: str, num_keyframes: int = None) -> List[Tuple[int, np.ndarray]]:
        """提取视频关键帧（基于场景变化检测）"""
        if num_keyframes is None:
            num_keyframes = self.num_keyframes

        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frames = []
        prev_gray = None
        frame_positions = []

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 每隔几帧采样一次
            if frame_idx % max(1, total_frames // 100) == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if prev_gray is not None:
                    # 计算帧差异
                    diff = cv2.absdiff(gray, prev_gray)
                    score = np.mean(diff)
                    frames.append((frame_idx, frame, score))
                prev_gray = gray

            frame_idx += 1

        cap.release()

        # 选择变化最大的帧作为关键帧
        if len(frames) > num_keyframes:
            frames.sort(key=lambda x: x[2], reverse=True)
            keyframes = [(pos, frame) for pos, frame, _ in frames[:num_keyframes]]
            # 按时间顺序排序
            keyframes.sort(key=lambda x: x[0])
        else:
            keyframes = [(pos, frame) for pos, frame, _ in frames]

        return keyframes

    def compute_phash(self, frame: np.ndarray) -> str:
        """计算帧的 pHash"""
        if HAS_IMAGEHASH:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            return str(imagehash.phash(img, hash_size=self.hash_size))
        return self._simple_phash(frame)

    def compute_dhash(self, frame: np.ndarray) -> str:
        """计算帧的 dHash"""
        if HAS_IMAGEHASH:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            return str(imagehash.dhash(img))
        return self._simple_dhash(frame)

    def compute_sift_features(self, frame: np.ndarray) -> Tuple[List, List]:
        """计算SIFT特征"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        keypoints, descriptors = self.sift.detectAndCompute(gray, None)
        return keypoints, descriptors

    def compute_sift_hash(self, frame: np.ndarray) -> str:
        """计算SIFT特征摘要"""
        _, descriptors = self.compute_sift_features(frame)
        if descriptors is None or len(descriptors) == 0:
            return ""
        # 对特征取均值作为摘要
        mean_desc = np.mean(descriptors, axis=0)
        # 转为字符串
        desc_str = mean_desc.tobytes().hex()[:64]
        return desc_str

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

    def compute_color_histogram(self, frame: np.ndarray) -> np.ndarray:
        """计算颜色直方图特征"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        return hist.flatten()

    def extract_audio_fingerprint(self, video_path: str) -> Optional[Dict]:
        """提取音频指纹"""
        if not HAS_AUDIO:
            return None

        try:
            # 提取音频（使用resampy进行重采样）
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                y, sr = librosa.load(video_path, sr=22050, duration=30)

            if y is None or len(y) == 0:
                return None

            # 计算MFCC特征
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfcc, axis=1)

            # 计算频谱质心
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            sc_mean = np.mean(spectral_centroid)

            # 计算色度特征
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)

            # 音频指纹hash
            audio_hash = hashlib.md5(mfcc_mean.tobytes()).hexdigest()[:32]

            return {
                "audio_hash": audio_hash,
                "mfcc": mfcc_mean.tolist(),
                "spectral_centroid": float(sc_mean),
                "chroma": chroma_mean.tolist(),
                "duration": float(librosa.get_duration(y=y, sr=sr)),
                "sample_rate": sr
            }
        except Exception as e:
            # 音频提取失败不影响主功能，静默返回None
            return None

    def generate_video_fingerprint(self, video_path: str) -> Dict:
        """生成增强版视频指纹"""
        print(f"正在生成增强版视频指纹: {video_path}")

        # 提取帧
        frames = self.extract_frames(video_path)
        if not frames:
            raise ValueError("无法从视频中提取帧")

        # 提取关键帧
        keyframes = self.extract_keyframes(video_path)

        # 计算各帧指纹
        phash_list = []
        dhash_list = []
        sift_hashes = []
        color_hists = []

        for frame in frames:
            ph = self.compute_phash(frame)
            dh = self.compute_dhash(frame)
            sh = self.compute_sift_hash(frame)
            ch = self.compute_color_histogram(frame)

            phash_list.append(ph)
            dhash_list.append(dh)
            sift_hashes.append(sh)
            color_hists.append(ch)

        # 关键帧信息
        keyframe_info = []
        for pos, kf in keyframes:
            keyframe_info.append({
                "position": pos,
                "phash": self.compute_phash(kf),
                "sift_hash": self.compute_sift_hash(kf)
            })

        # 视频级别指纹
        video_phash = self._combine_hashes(phash_list)
        video_dhash = self._combine_hashes(dhash_list)

        # 颜色直方图（多帧平均）
        avg_color_hist = np.mean(color_hists, axis=0) if color_hists else None

        # 音频指纹
        audio_fp = self.extract_audio_fingerprint(video_path)

        # 构建结果
        result = {
            "video_path": video_path,
            "video_name": os.path.basename(video_path),
            "frame_count": len(frames),
            "keyframe_count": len(keyframe_info),
            "timestamp": datetime.now().isoformat(),
            "algorithm_version": "2.0",  # 增强版

            # 帧级指纹
            "frame_phashes": phash_list,
            "frame_dhashes": dhash_list,
            "sift_hashes": sift_hashes,

            # 视频级指纹
            "phash": video_phash,
            "dhash": video_dhash,

            # 颜色特征
            "color_histogram": avg_color_hist.tolist() if avg_color_hist is not None else None,
            "color_hists_sample": [ch.tolist() for ch in color_hists[:3]],

            # 关键帧
            "keyframes": keyframe_info,

            # 音频指纹
            "audio_fingerprint": audio_fp,

            "hash_size": self.hash_size
        }

        return result

    def _combine_hashes(self, hash_list: List[str]) -> str:
        """组合多个哈希值"""
        if not hash_list:
            return ""
        combined = hash_list[0] + hash_list[-1]
        if len(hash_list) > 2:
            combined += hash_list[len(hash_list) // 2]
        return combined[:64]

    def save_fingerprint(self, fingerprint: Dict, output_path: Optional[str] = None) -> str:
        """保存指纹"""
        if output_path is None:
            video_name = fingerprint.get("video_name", "video")
            base_name = os.path.splitext(video_name)[0]
            output_path = self.frames_dir / f"{base_name}.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(fingerprint, f, indent=2, ensure_ascii=False)

        print(f"指纹已保存: {output_path}")
        return str(output_path)

    def load_fingerprint(self, fingerprint_path: str) -> Dict:
        """加载指纹"""
        with open(fingerprint_path, 'r', encoding='utf-8') as f:
            return json.load(f)


def extract_video_fingerprint(video_path: str, output_dir: str = "data/fingerprints") -> Dict:
    """便捷函数：提取视频指纹"""
    generator = EnhancedVideoFingerprint(frames_dir=output_dir)
    fingerprint = generator.generate_video_fingerprint(video_path)
    generator.save_fingerprint(fingerprint)
    return fingerprint


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        result = extract_video_fingerprint(video_path)
        print(f"指纹生成完成: {result['video_name']}")
        print(f"帧数: {result['frame_count']}, 关键帧: {result['keyframe_count']}")
        print(f"音频指纹: {'有' if result.get('audio_fingerprint') else '无'}")
    else:
        print("用法: python enhanced_fingerprint.py <视频路径>")
