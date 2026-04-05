# -*- coding: utf-8 -*-
"""
视频指纹数据增强模块
用于增强现有指纹数据，添加新特征，提升检测能力
"""

import os
import json
import numpy as np
import cv2
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from PIL import Image

try:
    import imagehash
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False


class FingerprintAugmenter:
    """视频指纹数据增强器"""

    def __init__(self, fingerprints_dir: str = "data/fingerprints"):
        self.fingerprints_dir = Path(fingerprints_dir)
        self.hash_size = 16

    def compute_wavelet_hash(self, frame: np.ndarray) -> str:
        """计算小波哈希 (wHash) - 对模糊和水印更鲁棒"""
        if not HAS_IMAGEHASH:
            return self._simple_wavelet_hash(frame)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        img = Image.fromarray(rgb)
        return str(imagehash.whash(img, hash_size=self.hash_size))

    def _simple_wavelet_hash(self, frame: np.ndarray) -> str:
        """简化版小波哈希"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (32, 32))

        # 简单的DWT-like变换
        dwt = resized.copy()
        for _ in range(3):
            h, w = dwt.shape
            dwt[:h//2, :w//2] = (dwt[:h//2, :w//2] + dwt[:h//2, w//2:] +
                                  dwt[h//2:, :w//2] + dwt[h//2:, w//2:]) / 4
            dwt[:h//2, :w//2] = dwt[:h//2, :w//2] > dwt[:h//2, :w//2].mean()
            dwt = dwt[:h//2, :w//2]

        # 生成哈希
        avg = dwt.mean()
        bits = dwt > avg
        return ''.join('1' if b else '0' for b in bits.flatten()[:256])

    def compute_lbp_histogram(self, frame: np.ndarray, num_points: int = 8,
                               radius: int = 1) -> np.ndarray:
        """计算局部二值模式 (LBP) - 纹理特征"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        lbp = np.zeros((h - 2 * radius, w - 2 * radius), dtype=np.uint8)

        for i in range(radius, h - radius):
            for j in range(radius, w - radius):
                center = gray[i, j]
                code = 0
                for k in range(num_points):
                    angle = 2 * np.pi * k / num_points
                    x = int(round(i + radius * np.sin(angle)))
                    y = int(round(j + radius * np.cos(angle)))
                    if gray[x, y] >= center:
                        code |= (1 << k)
                lbp[i - radius, j - radius] = code

        # 计算直方图
        hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
        hist = hist.astype(float) / (hist.sum() + 1e-7)
        return hist

    def compute_edge_histogram(self, frame: np.ndarray) -> np.ndarray:
        """计算边缘直方图 - 对形状变化敏感"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Canny边缘检测
        edges = cv2.Canny(gray, 50, 150)

        # 方向梯度直方图
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

        magnitude = np.sqrt(sobelx ** 2 + sobely ** 2)
        angle = np.arctan2(sobely, sobelx) * 180 / np.pi

        # 方向直方图 (9 bins)
        hist, _ = np.histogram(angle[edges > 0], bins=9, range=(-180, 180),
                               weights=magnitude[edges > 0])
        hist = hist.astype(float) / (hist.sum() + 1e-7)
        return hist

    def compute_spatial_pyramid(self, frame: np.ndarray, levels: int = 3) -> np.ndarray:
        """计算空间金字塔特征 - 捕获空间布局"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        features = []

        for level in range(levels):
            h, w = gray.shape
            new_h, new_w = h // (2 ** level), w // (2 ** level)

            if new_h < 4 or new_w < 4:
                break

            # 缩放
            scaled = cv2.resize(gray, (new_w, new_h))

            # 计算每个区域的直方图
            region_h, region_w = 2, 2
            region_features = []
            for i in range(region_h):
                for j in range(region_w):
                    rh, rw = new_h // region_h, new_w // region_w
                    region = scaled[i * rh:(i + 1) * rh, j * rw:(j + 1) * rw]
                    hist, _ = np.histogram(region.ravel(), bins=16, range=(0, 256))
                    region_features.extend(hist / (hist.sum() + 1e-7))

            features.extend(region_features)

        return np.array(features)

    def compute_texture_features(self, frame: np.ndarray) -> Dict:
        """计算纹理特征 (GLCM)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 简化的GLCM特征
        h, w = gray.shape
        glcm = np.zeros((256, 256), dtype=float)

        for i in range(h - 1):
            for j in range(w - 1):
                glcm[gray[i, j], gray[i, j + 1]] += 1

        # 归一化
        glcm = glcm / (glcm.sum() + 1e-7)

        # 计算特征
        contrast = np.sum(glcm * (np.abs(np.arange(256)[:, None] - np.arange(256)) ** 2))
        dissimilarity = np.sum(glcm * np.abs(np.arange(256)[:, None] - np.arange(256)))
        homogeneity = np.sum(glcm / (1 + np.abs(np.arange(256)[:, None] - np.arange(256))))
        energy = np.sum(glcm ** 2)

        return {
            "contrast": float(contrast),
            "dissimilarity": float(dissimilarity),
            "homogeneity": float(homogeneity),
            "energy": float(energy)
        }

    def extract_enhanced_features(self, video_path: str) -> Dict:
        """从视频提取增强特征"""
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if total_frames == 0:
            cap.release()
            return {}

        # 采样帧
        num_samples = 8
        interval = max(1, total_frames // num_samples)

        all_features = {
            "wavelet_hashes": [],
            "lbp_features": [],
            "edge_histograms": [],
            "spatial_pyramids": [],
            "texture_features": []
        }

        for i in range(num_samples):
            frame_pos = i * interval
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = cap.read()

            if not ret:
                continue

            # 调整大小以加速
            frame = cv2.resize(frame, (256, 256))

            # 计算各种特征
            all_features["wavelet_hashes"].append(self.compute_wavelet_hash(frame))
            all_features["lbp_features"].append(self.compute_lbp_histogram(frame).tolist())
            all_features["edge_histograms"].append(self.compute_edge_histogram(frame).tolist())
            all_features["spatial_pyramids"].append(self.compute_spatial_pyramid(frame).tolist())
            all_features["texture_features"].append(self.compute_texture_features(frame))

        cap.release()

        # 计算视频级别的综合特征
        video_level = {
            "avg_texture": {
                "contrast": np.mean([f["contrast"] for f in all_features["texture_features"]]),
                "dissimilarity": np.mean([f["dissimilarity"] for f in all_features["texture_features"]]),
                "homogeneity": np.mean([f["homogeneity"] for f in all_features["texture_features"]]),
                "energy": np.mean([f["energy"] for f in all_features["texture_features"]])
            },
            "wavelet_hash_combined": self._combine_hashes(all_features["wavelet_hashes"]),
            "lbp_mean": np.mean(all_features["lbp_features"], axis=0).tolist(),
            "edge_mean": np.mean(all_features["edge_histograms"], axis=0).tolist(),
            "spatial_mean": np.mean(all_features["spatial_pyramids"], axis=0).tolist()
        }

        return {
            "frame_features": all_features,
            "video_level": video_level,
            "timestamp": datetime.now().isoformat()
        }

    def _combine_hashes(self, hash_list: List[str]) -> str:
        """组合多个哈希值"""
        if not hash_list:
            return ""
        combined = hash_list[0] + hash_list[-1]
        if len(hash_list) > 2:
            combined += hash_list[len(hash_list) // 2]
        return combined[:64]

    def augment_fingerprint(self, video_path: str, existing_fingerprint: Dict) -> Dict:
        """增强现有指纹 - 添加新特征"""
        enhanced = self.extract_enhanced_features(video_path)

        # 合并到现有指纹
        augmented = existing_fingerprint.copy()
        augmented["enhanced_features"] = enhanced
        augmented["has_enhanced_features"] = True
        augmented["augmentation_version"] = "1.0"
        augmented["augmented_at"] = datetime.now().isoformat()

        return augmented

    def batch_augment_database(self, videos_dir: str = "data/uploads",
                               dry_run: bool = False) -> Dict:
        """批量增强指纹数据库"""
        videos_dir = Path(videos_dir)
        videos = list(videos_dir.glob("*.mp4")) + list(videos_dir.glob("*.avi"))

        results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        for video in videos:
            try:
                # 查找对应的指纹文件
                fp_name = video.stem
                fp_files = list(self.fingerprints_dir.glob(f"{fp_name}*.json"))

                if not fp_files:
                    results["skipped"] += 1
                    continue

                # 加载现有指纹
                with open(fp_files[0], 'r', encoding='utf-8') as f:
                    fingerprint = json.load(f)

                # 检查是否已有增强特征
                if fingerprint.get("has_enhanced_features"):
                    results["skipped"] += 1
                    continue

                # 增强
                augmented = self.augment_fingerprint(str(video), fingerprint)

                # 保存
                if not dry_run:
                    with open(fp_files[0], 'w', encoding='utf-8') as f:
                        json.dump(augmented, f, indent=2, ensure_ascii=False)

                results["success"] += 1

            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{video.name}: {str(e)}")

        return results


class EnhancedComparator:
    """增强版比较器 - 使用新增特征"""

    def __init__(self, fingerprints_dir: str = "data/fingerprints"):
        self.fingerprints_dir = Path(fingerprints_dir)
        self.threshold = 10

        # 增强特征权重
        self.weights = {
            "phash": 0.20,
            "wavelet_hash": 0.15,
            "lbp": 0.15,
            "edge": 0.10,
            "texture": 0.10,
            "audio": 0.15,
            "color": 0.10,
            "sift": 0.05
        }

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """计算汉明距离"""
        if not hash1 or not hash2:
            return 999
        min_len = min(len(hash1), len(hash2))
        return sum(c1 != c2 for c1, c2 in zip(hash1[:min_len], hash2[:min_len]))

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """余弦相似度"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        min_len = min(len(vec1), len(vec2))
        vec1 = vec1[:min_len]
        vec2 = vec2[:min_len]

        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def compare_enhanced_fingerprints(self, fp1: Dict, fp2: Dict) -> Dict:
        """比较两个增强指纹"""
        results = {}

        # 基础特征比较
        if "frame_phashes" in fp1 and "frame_phashes" in fp2:
            phash_dist, phash_sim = self._compare_hashes(
                fp1.get("frame_phashes", []),
                fp2.get("frame_phashes", [])
            )
            results["phash"] = {"distance": phash_dist, "similarity": phash_sim}

        # 增强特征比较
        enhanced1 = fp1.get("enhanced_features", {})
        enhanced2 = fp2.get("enhanced_features", {})

        if enhanced1 and enhanced2:
            # 小波哈希比较
            if "video_level" in enhanced1 and "video_level" in enhanced2:
                whash1 = enhanced1["video_level"].get("wavelet_hash_combined", "")
                whash2 = enhanced2["video_level"].get("wavelet_hash_combined", "")
                whash_dist = self.hamming_distance(whash1, whash2)
                results["wavelet_hash"] = {
                    "distance": whash_dist,
                    "similarity": max(0, 100 - whash_dist)
                }

            # LBP比较
            lbp1 = enhanced1.get("video_level", {}).get("lbp_mean", [])
            lbp2 = enhanced2.get("video_level", {}).get("lbp_mean", [])
            if lbp1 and lbp2:
                lbp_sim = self.cosine_similarity(np.array(lbp1), np.array(lbp2)) * 100
                results["lbp"] = {"similarity": lbp_sim}

            # 边缘直方图比较
            edge1 = enhanced1.get("video_level", {}).get("edge_mean", [])
            edge2 = enhanced2.get("video_level", {}).get("edge_mean", [])
            if edge1 and edge2:
                edge_sim = self.cosine_similarity(np.array(edge1), np.array(edge2)) * 100
                results["edge"] = {"similarity": edge_sim}

            # 纹理特征比较
            tex1 = enhanced1.get("video_level", {}).get("avg_texture", {})
            tex2 = enhanced2.get("video_level", {}).get("avg_texture", {})
            if tex1 and tex2:
                tex_sim = self.cosine_similarity(
                    np.array(list(tex1.values())),
                    np.array(list(tex2.values()))
                ) * 100
                results["texture"] = {"similarity": tex_sim}

        # 计算综合相似度
        total_weight = 0
        weighted_sim = 0

        for feature, weight in self.weights.items():
            if feature in results:
                sim = results[feature].get("similarity", 0)
                weighted_sim += sim * weight
                total_weight += weight

        overall = weighted_sim / total_weight if total_weight > 0 else 0
        results["overall_similarity"] = round(overall, 2)

        return results

    def _compare_hashes(self, hashes1: List[str], hashes2: List[str]) -> Tuple[int, float]:
        """比较哈希序列"""
        if not hashes1 or not hashes2:
            return 999, 0.0

        distances = []
        for h1 in hashes1:
            for h2 in hashes2:
                distances.append(self.hamming_distance(h1, h2))

        min_dist = min(distances) if distances else 999
        matches = sum(1 for d in distances if d <= self.threshold)
        sim = (matches / len(distances)) * 100 if distances else 0

        return min_dist, sim

    def compare_with_database(self, test_fingerprint: Dict) -> List[Dict]:
        """与数据库比较"""
        results = []

        for fp_file in self.fingerprints_dir.glob("*.json"):
            try:
                with open(fp_file, 'r', encoding='utf-8') as f:
                    db_fingerprint = json.load(f)

                # 跳过自己
                if fp_file.stem == test_fingerprint.get("video_name", "").split('.')[0]:
                    continue

                comparison = self.compare_enhanced_fingerprints(test_fingerprint, db_fingerprint)
                results.append({
                    "video": db_fingerprint.get("video_name", fp_file.stem),
                    "comparison": comparison
                })

            except Exception as e:
                continue

        # 排序
        results.sort(key=lambda x: x["comparison"].get("overall_similarity", 0), reverse=True)
        return results


def augment_fingerprint(video_path: str, output_dir: str = "data/fingerprints") -> Dict:
    """便捷函数：增强视频指纹"""
    augmenter = FingerprintAugmenter(fingerprints_dir=output_dir)

    # 查找现有指纹
    video_name = Path(video_path).stem
    fp_files = list(Path(output_dir).glob(f"{video_name}*.json"))

    existing_fp = {}
    if fp_files:
        with open(fp_files[0], 'r', encoding='utf-8') as f:
            existing_fp = json.load(f)

    return augmenter.augment_fingerprint(video_path, existing_fp)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        print(f"增强视频指纹: {video_path}")

        augmenter = FingerprintAugmenter()
        features = augmenter.extract_enhanced_features(video_path)

        print(f"提取的特征:")
        print(f"  - 小波哈希: {len(features.get('wavelet_hashes', []))} 个")
        print(f"  - LBP特征: {len(features.get('lbp_features', []))} 个")
        print(f"  - 边缘直方图: {len(features.get('edge_histograms', []))} 个")
        print(f"  - 空间金字塔: {len(features.get('spatial_pyramids', []))} 个")
        print(f"  - 纹理特征: {len(features.get('texture_features', []))} 个")

        # 批量增强
        if "--batch" in sys.argv:
            print("\n批量增强数据库...")
            results = augmenter.batch_augment_database(dry_run=False)
            print(f"成功: {results['success']}, 失败: {results['failed']}, 跳过: {results['skipped']}")

    else:
        print("用法:")
        print("  python fingerprint_augmenter.py <视频路径>")
        print("  python fingerprint_augmenter.py <视频路径> --batch")
