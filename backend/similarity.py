# -*- coding: utf-8 -*-
"""
相似度检测模块
用于比较视频指纹，判断是否侵权
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import cv2

from video_fingerprint import VideoFingerprint


class SimilarityDetector:
    """视频相似度检测器"""
    
    def __init__(self, fingerprints_dir: str = "data/fingerprints", threshold: int = 10):
        """
        初始化相似度检测器
        
        Args:
            fingerprints_dir: 指纹存储目录
            threshold: 汉明距离阈值（越小越严格）
        """
        self.fingerprints_dir = Path(fingerprints_dir)
        self.threshold = threshold
        self.fingerprint_generator = VideoFingerprint(frames_dir=fingerprints_dir)
        
        # 加载所有指纹
        self.fingerprints_db: Dict[str, Dict] = {}
        self._load_all_fingerprints()
    
    def _load_all_fingerprints(self):
        """加载所有指纹文件"""
        if not self.fingerprints_dir.exists():
            return
        
        loaded = 0
        for fp_file in self.fingerprints_dir.glob("*.json"):
            try:
                with open(fp_file, 'r', encoding='utf-8') as f:
                    fingerprint = json.load(f)
                    # 用文件名作为key（去掉 _fingerprint 后缀兼容旧格式）
                    key = fp_file.stem.replace("_fingerprint", "")
                    self.fingerprints_db[key] = fingerprint
                    loaded += 1
            except Exception as e:
                print(f"加载指纹失败 {fp_file}: {e}")
        
        print(f"共加载 {loaded} 个指纹")
    
    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        计算两个哈希值的汉明距离
        
        Args:
            hash1: 第一个哈希字符串
            hash2: 第二个哈希字符串
            
        Returns:
            汉明距离
        """
        if len(hash1) != len(hash2):
            # 长度不同，尝试对齐
            min_len = min(len(hash1), len(hash2))
            return sum(c1 != c2 for c1, c2 in zip(hash1[:min_len], hash2[:min_len]))
        
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
    
    def compare_frame_hashes(self, hash1: str, hash2: str) -> Tuple[int, float]:
        """
        比较两个帧哈希序列
        
        Args:
            hash1: 第一个视频的帧哈希列表
            hash2: 第二个视频的帧哈希列表
            
        Returns:
            (最小汉明距离, 相似度百分比)
        """
        if not hash1 or not hash2:
            return 999, 0.0
        
        min_distance = 999
        matches = 0
        
        # 使用动态规划找最优匹配
        for h1 in hash1:
            for h2 in hash2:
                dist = self.hamming_distance(h1, h2)
                if dist < min_distance:
                    min_distance = dist
                if dist <= self.threshold:
                    matches += 1
        
        # 计算相似度
        max_possible = len(hash1) * len(hash2)
        similarity = (matches / max_possible) * 100 if max_possible > 0 else 0
        
        return min_distance, similarity
    
    def compare_videos(self, video1_path: str, video2_path: str) -> Dict:
        """
        比较两个视频的相似度
        
        Args:
            video1_path: 第一个视频路径
            video2_path: 第二个视频路径
            
        Returns:
            相似度报告
        """
        print(f"比较视频: {video1_path} vs {video2_path}")
        
        # 生成或加载指纹
        fp1 = self.fingerprint_generator.generate_video_fingerprint(video1_path)
        fp2 = self.fingerprint_generator.generate_video_fingerprint(video2_path)
        
        # 比较 pHash（感知哈希，检测内容相似性）
        phash_dist, phash_similarity = self.compare_frame_hashes(
            fp1.get("frame_phashes", []),
            fp2.get("frame_phashes", [])
        )
        
        # 比较 dHash
        dhash_dist, dhash_similarity = self.compare_frame_hashes(
            fp1.get("frame_dhashes", []),
            fp2.get("frame_dhashes", [])
        )
        
        # 比较颜色直方图
        color_similarity = 0.0
        if fp1.get("color_histogram") and fp2.get("color_histogram"):
            hist1 = np.array(fp1["color_histogram"])
            hist2 = np.array(fp2["color_histogram"])
            # 余弦相似度
            color_similarity = self._cosine_similarity(hist1, hist2) * 100
        
        # 综合评分
        overall_similarity = (
            phash_similarity * 0.4 +
            dhash_similarity * 0.4 +
            color_similarity * 0.2
        )
        
        # 判断是否侵权
        is_plagiarism = (
            phash_dist <= self.threshold or
            dhash_dist <= self.threshold or
            overall_similarity >= 70
        )
        
        result = {
            "video1": os.path.basename(video1_path),
            "video2": os.path.basename(video2_path),
            "timestamp": datetime.now().isoformat(),
            "phash": {
                "min_distance": phash_dist,
                "similarity": round(phash_similarity, 2)
            },
            "dhash": {
                "min_distance": dhash_dist,
                "similarity": round(dhash_similarity, 2)
            },
            "color_histogram_similarity": round(color_similarity, 2),
            "overall_similarity": round(overall_similarity, 2),
            "is_plagiarism": is_plagiarism,
            "plagiarism_level": self._get_plagiarism_level(overall_similarity, phash_dist)
        }
        
        return result
    
    def compare_with_database(self, video_path: str) -> List[Dict]:
        """
        将视频与数据库中的指纹比较
        
        Args:
            video_path: 待检测视频路径
            
        Returns:
            匹配结果列表（按相似度排序）
        """
        print(f"检测视频: {video_path}")
        
        # 生成新视频指纹
        new_fingerprint = self.fingerprint_generator.generate_video_fingerprint(video_path)
        
        results = []
        
        # 与数据库中每个指纹比较
        for name, db_fingerprint in self.fingerprints_db.items():
            # 跳过文件名完全相同的（避免自己和自己比较）
            video_stem = Path(video_path).stem
            if name == video_stem or name == Path(video_path).name:
                continue
            
            # 比较帧哈希
            phash_dist, phash_sim = self.compare_frame_hashes(
                new_fingerprint.get("frame_phashes", []),
                db_fingerprint.get("frame_phashes", [])
            )
            
            dhash_dist, dhash_sim = self.compare_frame_hashes(
                new_fingerprint.get("frame_dhashes", []),
                db_fingerprint.get("frame_dhashes", [])
            )
            
            # 综合相似度
            overall = (phash_sim * 0.5 + dhash_sim * 0.5)
            
            # 颜色直方图比较
            color_sim = 0.0
            if new_fingerprint.get("color_histogram") and db_fingerprint.get("color_histogram"):
                hist1 = np.array(new_fingerprint["color_histogram"])
                hist2 = np.array(db_fingerprint["color_histogram"])
                color_sim = self._cosine_similarity(hist1, hist2) * 100
            
            overall = overall * 0.8 + color_sim * 0.2
            
            results.append({
                "matched_video": name,
                "phash_distance": phash_dist,
                "phash_similarity": round(phash_sim, 2),
                "dhash_similarity": round(dhash_sim, 2),
                "color_similarity": round(color_sim, 2),
                "overall_similarity": round(overall, 2),
                "is_match": phash_dist <= self.threshold or overall >= 60
            })
        
        # 按相似度排序
        results.sort(key=lambda x: x["overall_similarity"], reverse=True)
        
        return results
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot / (norm1 * norm2)
    
    def _get_plagiarism_level(self, similarity: float, phash_dist: int) -> str:
        """判断侵权等级"""
        if similarity >= 90 or phash_dist <= 3:
            return "高度疑似侵权"
        elif similarity >= 70 or phash_dist <= 7:
            return "疑似侵权"
        elif similarity >= 50 or phash_dist <= 10:
            return "可能相似"
        elif similarity >= 30:
            return "轻微相似"
        else:
            return "无明显相似"
    
    def batch_compare(self, video_dir: str, output_file: Optional[str] = None) -> List[Dict]:
        """
        批量比较目录下所有视频
        
        Args:
            video_dir: 视频目录
            output_file: 结果输出文件
            
        Returns:
            所有比较结果
        """
        video_dir = Path(video_dir)
        video_files = list(video_dir.glob("*.mp4")) + \
                     list(video_dir.glob("*.avi")) + \
                     list(video_dir.glob("*.mkv"))
        
        print(f"发现 {len(video_files)} 个视频文件")
        
        all_results = []
        
        # 两两比较
        for i, video1 in enumerate(video_files):
            for video2 in video_files[i+1:]:
                try:
                    result = self.compare_videos(str(video1), str(video2))
                    if result["overall_similarity"] > 30:  # 只保存有相似的结果
                        all_results.append(result)
                except Exception as e:
                    print(f"比较失败 {video1} vs {video2}: {e}")
        
        # 按相似度排序
        all_results.sort(key=lambda x: x["overall_similarity"], reverse=True)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            print(f"结果已保存: {output_file}")
        
        return all_results
    
    def add_to_database(self, video_path: str) -> Dict:
        """
        将视频添加到指纹数据库
        
        Args:
            video_path: 视频路径
            
        Returns:
            添加结果
        """
        fingerprint = self.fingerprint_generator.generate_video_fingerprint(video_path)
        self.fingerprint_generator.save_fingerprint(fingerprint)
        
        # 重新加载
        key = Path(video_path).stem
        self.fingerprints_db[key] = fingerprint
        
        return {
            "status": "success",
            "video": os.path.basename(video_path),
            "phash": fingerprint["phash"][:32] + "..."
        }


def detect_plagiarism(video_path: str, database_dir: str = "data/fingerprints") -> List[Dict]:
    """
    便捷函数：检测视频是否侵权
    
    Args:
        video_path: 待检测视频路径
        database_dir: 指纹数据库目录
        
    Returns:
        匹配结果列表
    """
    detector = SimilarityDetector(fingerprints_dir=database_dir)
    return detector.compare_with_database(video_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        results = detect_plagiarism(video_path)
        
        print(f"\n检测结果:")
        print("-" * 60)
        
        for result in results[:10]:  # 显示前10个
            print(f"视频: {result['matched_video']}")
            print(f"  相似度: {result['overall_similarity']}%")
            print(f"  匹配: {'是' if result['is_match'] else '否'}")
            print()
    else:
        print("用法: python similarity.py <视频路径>")
