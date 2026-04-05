# -*- coding: utf-8 -*-
"""
增强版相似度检测模块
整合多种算法：pHash + SIFT + 音频指纹 + 颜色直方图
多模态融合判断侵权
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import cv2

from enhanced_fingerprint import EnhancedVideoFingerprint


class EnhancedSimilarityDetector:
    """增强版视频相似度检测器"""

    def __init__(self, fingerprints_dir: str = "data/fingerprints", threshold: int = 10):
        """
        初始化相似度检测器

        Args:
            fingerprints_dir: 指纹存储目录
            threshold: 汉明距离阈值
        """
        self.fingerprints_dir = Path(fingerprints_dir)
        self.threshold = threshold
        self.fingerprint_generator = EnhancedVideoFingerprint(frames_dir=fingerprints_dir)

        # 加载所有指纹
        self.fingerprints_db: Dict[str, Dict] = {}
        self._load_all_fingerprints()

        # 检测权重（可调整）
        self.weights = {
            "phash": 0.25,       # pHash权重
            "dhash": 0.15,       # dHash权重
            "wavelet_hash": 0.10,  # 小波哈希权重 (新增)
            "lbp": 0.08,          # LBP纹理权重 (新增)
            "sift": 0.15,         # SIFT特征权重
            "color": 0.10,        # 颜色直方图权重
            "audio": 0.12,        # 音频指纹权重
            "edge": 0.05,         # 边缘直方图权重 (新增)
        }

    def _load_all_fingerprints(self):
        """加载所有指纹文件"""
        if not self.fingerprints_dir.exists():
            return

        loaded = 0
        for fp_file in self.fingerprints_dir.glob("*.json"):
            try:
                with open(fp_file, 'r', encoding='utf-8') as f:
                    fingerprint = json.load(f)
                    key = fp_file.stem.replace("_fingerprint", "")
                    self.fingerprints_db[key] = fingerprint
                    loaded += 1
            except Exception as e:
                print(f"加载指纹失败 {fp_file}: {e}")

        print(f"共加载 {loaded} 个指纹")

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """计算汉明距离"""
        if not hash1 or not hash2:
            return 999
        min_len = min(len(hash1), len(hash2))
        return sum(c1 != c2 for c1, c2 in zip(hash1[:min_len], hash2[:min_len]))

    def compare_frame_hashes(self, hash_list1: List[str], hash_list2: List[str]) -> Tuple[int, float]:
        """比较帧哈希序列"""
        if not hash_list1 or not hash_list2:
            return 999, 0.0

        min_distance = 999
        matches = 0
        total_comparisons = 0

        for h1 in hash_list1:
            for h2 in hash_list2:
                total_comparisons += 1
                dist = self.hamming_distance(h1, h2)
                if dist < min_distance:
                    min_distance = dist
                if dist <= self.threshold:
                    matches += 1

        similarity = (matches / total_comparisons) * 100 if total_comparisons > 0 else 0
        return min_distance, similarity

    def compare_sift_features(self, sift1: List[str], sift2: List[str]) -> Tuple[int, float]:
        """比较SIFT特征哈希"""
        # 处理缺失字段
        if not sift1 or not sift2 or sift1 == [""] or sift2 == [""]:
            return 999, 0.0
        return self.compare_frame_hashes(sift1, sift2)

    def compare_keyframes(self, kf1: List[Dict], kf2: List[Dict]) -> float:
        """比较关键帧序列"""
        # 处理缺失或空数据
        if not kf1 or not kf2 or kf1 == [{}] or kf2 == [{}]:
            return 0.0

        matches = 0
        for k1 in kf1:
            if not k1:
                continue
            for k2 in kf2:
                if not k2:
                    continue
                # 比较位置和内容
                pos_dist = abs(k1.get("position", 0) - k2.get("position", 0))
                phash_dist = self.hamming_distance(k1.get("phash", ""), k2.get("phash", ""))
                if phash_dist <= self.threshold:
                    matches += 1
                    break

        return (matches / max(len(kf1), len(kf2), 1)) * 100

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        # 确保维度一致
        min_len = min(len(vec1), len(vec2))
        if min_len == 0:
            return 0.0
        
        vec1 = np.array(vec1[:min_len])
        vec2 = np.array(vec2[:min_len])
        
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def compare_color_histograms(self, hist1: List, hist2: List) -> float:
        """比较颜色直方图"""
        # 处理缺失或空数据
        if not hist1 or not hist2 or hist1 == [] or hist2 == []:
            return 0.0

        # 处理维度不匹配
        arr1 = np.array(hist1)
        arr2 = np.array(hist2)

        # 如果维度不同，尝试对齐
        if len(arr1) != len(arr2):
            # 使用前min_len个元素
            min_len = min(len(arr1), len(arr2))
            if min_len == 0:
                return 0.0
            arr1 = arr1[:min_len]
            arr2 = arr2[:min_len]

        if len(arr1) == 0:
            return 0.0

        return self.cosine_similarity(arr1, arr2) * 100

    def compare_audio_fingerprints(self, audio1: Optional[Dict], audio2: Optional[Dict]) -> Tuple[float, str]:
        """比较音频指纹"""
        if not audio1 or not audio2:
            return 0.0, "no_audio"

        # 音频hash直接比较
        audio_hash_dist = self.hamming_distance(
            audio1.get("audio_hash", ""),
            audio2.get("audio_hash", "")
        )

        # 音频hash相似度（反向）
        audio_sim = max(0, 100 - audio_hash_dist * 5)

        # MFCC特征比较
        mfcc_sim = 0.0
        if audio1.get("mfcc") and audio2.get("mfcc"):
            mfcc1 = np.array(audio1["mfcc"])
            mfcc2 = np.array(audio2["mfcc"])
            mfcc_sim = self.cosine_similarity(mfcc1, mfcc2) * 100

        # 综合音频相似度
        combined_sim = audio_sim * 0.6 + mfcc_sim * 0.4

        return combined_sim, "audio_similar" if combined_sim > 60 else "audio_different"

    def compare_wavelet_hashes(self, whash1: str, whash2: str) -> Tuple[int, float]:
        """比较小波哈希 (对模糊和水印更鲁棒)"""
        dist = self.hamming_distance(whash1, whash2)
        sim = max(0, 100 - dist)
        return dist, sim

    def compare_lbp_features(self, lbp1: List, lbp2: List) -> float:
        """比较LBP纹理特征"""
        if not lbp1 or not lbp2 or lbp1 == [] or lbp2 == []:
            return 0.0
        return self.cosine_similarity(np.array(lbp1), np.array(lbp2)) * 100

    def compare_edge_histograms(self, edge1: List, edge2: List) -> float:
        """比较边缘直方图"""
        if not edge1 or not edge2 or edge1 == [] or edge2 == []:
            return 0.0
        return self.cosine_similarity(np.array(edge1), np.array(edge2)) * 100

    def compare_texture_features(self, tex1: Dict, tex2: Dict) -> float:
        """比较纹理特征"""
        if not tex1 or not tex2:
            return 0.0
        vec1 = np.array(list(tex1.values()))
        vec2 = np.array(list(tex2.values()))
        return self.cosine_similarity(vec1, vec2) * 100

    def compare_enhanced_features(self, fp1: Dict, fp2: Dict) -> Dict:
        """比较增强特征（SIFT, wavelet, LBP等）"""
        results = {}

        # 小波哈希
        if "enhanced_features" in fp1 and "enhanced_features" in fp2:
            whash1 = fp1["enhanced_features"].get("video_level", {}).get("wavelet_hash_combined", "")
            whash2 = fp2["enhanced_features"].get("video_level", {}).get("wavelet_hash_combined", "")
            if whash1 and whash2:
                dist, sim = self.compare_wavelet_hashes(whash1, whash2)
                results["wavelet_hash"] = {"distance": dist, "similarity": sim}

            # LBP
            lbp1 = fp1["enhanced_features"].get("video_level", {}).get("lbp_mean", [])
            lbp2 = fp2["enhanced_features"].get("video_level", {}).get("lbp_mean", [])
            if lbp1 and lbp2:
                results["lbp"] = {"similarity": self.compare_lbp_features(lbp1, lbp2)}

            # 边缘直方图
            edge1 = fp1["enhanced_features"].get("video_level", {}).get("edge_mean", [])
            edge2 = fp2["enhanced_features"].get("video_level", {}).get("edge_mean", [])
            if edge1 and edge2:
                results["edge"] = {"similarity": self.compare_edge_histograms(edge1, edge2)}

            # 纹理特征
            tex1 = fp1["enhanced_features"].get("video_level", {}).get("avg_texture", {})
            tex2 = fp2["enhanced_features"].get("video_level", {}).get("avg_texture", {})
            if tex1 and tex2:
                results["texture"] = {"similarity": self.compare_texture_features(tex1, tex2)}

        return results

    def compare_videos(self, video1_path: str, video2_path: str) -> Dict:
        """比较两个视频的相似度（多模态融合）"""
        print(f"增强版比较: {video1_path} vs {video2_path}")

        # 生成指纹
        fp1 = self.fingerprint_generator.generate_video_fingerprint(video1_path)
        fp2 = self.fingerprint_generator.generate_video_fingerprint(video2_path)

        # 1. pHash 比较
        phash_dist, phash_sim = self.compare_frame_hashes(
            fp1.get("frame_phashes", []),
            fp2.get("frame_phashes", [])
        )

        # 2. dHash 比较
        dhash_dist, dhash_sim = self.compare_frame_hashes(
            fp1.get("frame_dhashes", []),
            fp2.get("frame_dhashes", [])
        )

        # 3. SIFT特征比较
        sift_dist, sift_sim = self.compare_sift_features(
            fp1.get("sift_hashes") or [],
            fp2.get("sift_hashes") or []
        )

        # 4. 关键帧比较
        keyframe_sim = self.compare_keyframes(
            fp1.get("keyframes") or [],
            fp2.get("keyframes") or []
        )

        # 5. 颜色直方图比较
        color_sim = self.compare_color_histograms(
            fp1.get("color_histogram") or [],
            fp2.get("color_histogram") or []
        )

        # 6. 音频指纹比较
        audio_sim, audio_status = self.compare_audio_fingerprints(
            fp1.get("audio_fingerprint") or None,
            fp2.get("audio_fingerprint") or None
        )

        # 多模态融合
        overall_similarity = (
            phash_sim * self.weights["phash"] +
            dhash_sim * self.weights["dhash"] +
            sift_sim * self.weights["sift"] +
            keyframe_sim * 0.0 +  # 已包含在sift中
            color_sim * self.weights["color"] +
            audio_sim * self.weights["audio"]
        )

        # 侵权判定
        is_plagiarism, plagiarism_reason = self._judge_plagiarism(
            phash_dist, phash_sim, sift_sim, audio_sim, overall_similarity
        )

        result = {
            "video1": os.path.basename(video1_path),
            "video2": os.path.basename(video2_path),
            "timestamp": datetime.now().isoformat(),

            # 各维度相似度
            "visual": {
                "phash": {"distance": phash_dist, "similarity": round(phash_sim, 2)},
                "dhash": {"distance": dhash_dist, "similarity": round(dhash_sim, 2)},
                "sift": {"distance": sift_dist, "similarity": round(sift_sim, 2)},
                "keyframes": {"similarity": round(keyframe_sim, 2)},
                "color": {"similarity": round(color_sim, 2)},
            },

            # 音频
            "audio": {
                "similarity": round(audio_sim, 2),
                "status": audio_status,
            },

            # 综合
            "overall_similarity": round(overall_similarity, 2),
            "is_plagiarism": is_plagiarism,
            "plagiarism_reason": plagiarism_reason,
            "plagiarism_level": self._get_plagiarism_level(overall_similarity, phash_dist),
        }

        return result

    def compare_with_database(self, video_path: str) -> List[Dict]:
        """将视频与数据库比较"""
        print(f"增强版检测: {video_path}")

        new_fingerprint = self.fingerprint_generator.generate_video_fingerprint(video_path)
        results = []

        for name, db_fingerprint in self.fingerprints_db.items():
            video_stem = Path(video_path).stem
            if name == video_stem or name == Path(video_path).name:
                continue

            # 各维度比较
            phash_dist, phash_sim = self.compare_frame_hashes(
                new_fingerprint.get("frame_phashes", []),
                db_fingerprint.get("frame_phashes", [])
            )

            dhash_dist, dhash_sim = self.compare_frame_hashes(
                new_fingerprint.get("frame_dhashes", []),
                db_fingerprint.get("frame_dhashes", [])
            )

            sift_result = self.compare_sift_features(
                new_fingerprint.get("sift_hashes", []) or [],
                db_fingerprint.get("sift_hashes", []) or []
            )
            sift_sim = sift_result[1]

            color_sim = self.compare_color_histograms(
                new_fingerprint.get("color_histogram") or [],
                db_fingerprint.get("color_histogram") or []
            )

            audio_sim, audio_status = self.compare_audio_fingerprints(
                new_fingerprint.get("audio_fingerprint"),
                db_fingerprint.get("audio_fingerprint")
            )

            # 增强特征比较 (小波哈希, LBP, 边缘直方图)
            enhanced_sim = {
                "wavelet_hash": 0.0,
                "lbp": 0.0,
                "edge": 0.0
            }
            enhanced_comparison = self.compare_enhanced_features(new_fingerprint, db_fingerprint)
            if enhanced_comparison.get("wavelet_hash"):
                enhanced_sim["wavelet_hash"] = enhanced_comparison["wavelet_hash"].get("similarity", 0)
            if enhanced_comparison.get("lbp"):
                enhanced_sim["lbp"] = enhanced_comparison["lbp"].get("similarity", 0)
            if enhanced_comparison.get("edge"):
                enhanced_sim["edge"] = enhanced_comparison["edge"].get("similarity", 0)

            # 融合 (使用可用特征的权重)
            overall = (
                phash_sim * self.weights["phash"] +
                dhash_sim * self.weights["dhash"] +
                enhanced_sim["wavelet_hash"] * self.weights.get("wavelet_hash", 0.1) +
                enhanced_sim["lbp"] * self.weights.get("lbp", 0.08) +
                sift_sim * self.weights["sift"] +
                color_sim * self.weights["color"] +
                audio_sim * self.weights["audio"] +
                enhanced_sim["edge"] * self.weights.get("edge", 0.05)
            )

            # 判定
            is_match, reason = self._judge_plagiarism(
                phash_dist, phash_sim, sift_sim, audio_sim, overall
            )

            results.append({
                "matched_video": name,
                "phash_distance": phash_dist,
                "visual_similarity": round(
                    phash_sim * 0.4 + dhash_sim * 0.3 + sift_sim * 0.3, 2
                ),
                "audio_similarity": round(audio_sim, 2),
                "audio_status": audio_status,
                "enhanced_features": {
                    "wavelet_hash": round(enhanced_sim["wavelet_hash"], 2),
                    "lbp": round(enhanced_sim["lbp"], 2),
                    "edge": round(enhanced_sim["edge"], 2),
                },
                "overall_similarity": round(overall, 2),
                "is_match": is_match,
                "match_reason": reason,
            })

        results.sort(key=lambda x: x["overall_similarity"], reverse=True)
        return results

    def _judge_plagiarism(self, phash_dist: int, phash_sim: float,
                          sift_sim: float, audio_sim: float,
                          overall: float) -> Tuple[bool, str]:
        """判断是否侵权"""
        reasons = []

        # 视觉高度相似
        if phash_dist <= 3 or phash_sim >= 90:
            reasons.append("视觉内容高度相似")
            return True, "视觉内容高度相似"

        # SIFT特征匹配
        if sift_sim >= 80:
            reasons.append("特征点匹配度高")
            return True, "特征点匹配"

        # 音频完全相同
        if audio_sim >= 90:
            reasons.append("音频内容相同")
            return True, "音频内容相同"

        # 视觉+音频综合
        if phash_sim >= 70 and audio_sim >= 60:
            reasons.append("视觉和音频均相似")
            return True, "多模态综合相似"

        # 整体阈值
        if overall >= 75:
            reasons.append("综合相似度高")
            return True, "综合相似"

        # 轻微相似
        if overall >= 50 or audio_sim >= 50:
            reasons.append("存在一定相似性")
            return False, "轻微相似"

        return False, "无明显相似"

    def _get_plagiarism_level(self, similarity: float, phash_dist: int) -> str:
        """判定侵权等级"""
        if similarity >= 90 or phash_dist <= 3:
            return "🎯 高度疑似侵权"
        elif similarity >= 75 or phash_dist <= 7:
            return "⚠️ 疑似侵权"
        elif similarity >= 50:
            return "🤔 可能相似"
        elif similarity >= 30:
            return "✅ 轻微相似"
        else:
            return "✅ 无明显相似"

    def add_to_database(self, video_path: str) -> Dict:
        """将视频添加到指纹数据库"""
        fingerprint = self.fingerprint_generator.generate_video_fingerprint(video_path)
        self.fingerprint_generator.save_fingerprint(fingerprint)

        key = Path(video_path).stem
        self.fingerprints_db[key] = fingerprint

        return {
            "status": "success",
            "video": os.path.basename(video_path),
            "phash": fingerprint["phash"][:32] + "...",
            "has_audio": fingerprint.get("audio_fingerprint") is not None,
        }


def detect_plagiarism(video_path: str, database_dir: str = "data/fingerprints") -> List[Dict]:
    """便捷函数：检测视频侵权"""
    detector = EnhancedSimilarityDetector(fingerprints_dir=database_dir)
    return detector.compare_with_database(video_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        results = detect_plagiarism(video_path)

        print(f"\n检测结果:")
        print("-" * 60)

        for result in results[:10]:
            print(f"视频: {result['matched_video']}")
            print(f"  视觉相似度: {result['visual_similarity']}%")
            print(f"  音频相似度: {result['audio_similarity']}%")
            print(f"  综合相似度: {result['overall_similarity']}%")
            print(f"  匹配: {'是' if result['is_match'] else '否'} - {result['match_reason']}")
            print()
    else:
        print("用法: python enhanced_similarity.py <视频路径>")
