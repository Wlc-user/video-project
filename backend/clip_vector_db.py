# -*- coding: utf-8 -*-
"""
CLIP 向量数据库模块
使用 OpenAI CLIP 模型进行语义级别的视频相似度检测
支持动态阈值和多模态融合
"""
import os
import sys
import json
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

import cv2
import torch
from PIL import Image


class CLIPVectorDB:
    """CLIP 向量数据库 - 语义级别的视频相似度检测"""
    
    def __init__(
        self,
        db_path: str = "data/clip_vectors",
        model_name: str = "openai/clip-vit-base-patch32",
        device: str = None,
        index_type: str = "faiss"
    ):
        """
        初始化 CLIP 向量数据库
        
        Args:
            db_path: 向量数据库存储路径
            model_name: CLIP 模型名称
            device: 运行设备 (cuda/cpu)
            index_type: 索引类型 (faiss/hnsw)
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # 设备选择
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        self.index_type = index_type
        self._model = None
        self._index = None
        self._metadata: List[Dict] = []
        self._video_ids: List[str] = []
        self._frame_embeddings: Dict[str, np.ndarray] = {}
        
        # 尝试加载现有数据库
        self._load_index()
    
    @property
    def model(self):
        """懒加载 CLIP 模型"""
        if self._model is None:
            try:
                from transformers import CLIPModel, CLIPProcessor
                
                print(f"Loading CLIP model on {self.device}...")
                self._model = CLIPModel.from_pretrained(self.model_name)
                self._processor = CLIPProcessor.from_pretrained(self.model_name)
                self._model.to(self.device)
                self._model.eval()
                print("CLIP model loaded successfully")
            except Exception as e:
                print(f"Failed to load CLIP: {e}")
                print("Install with: pip install transformers torch")
                raise
        
        return self._model
    
    @property
    def processor(self):
        """获取处理器"""
        _ = self.model  # 确保模型已加载
        return self._processor
    
    @property
    def model_name(self) -> str:
        """获取模型名称"""
        return self._model_name if hasattr(self, '_model_name') else "openai/clip-vit-base-patch32"
    
    @model_name.setter
    def model_name(self, value: str):
        """设置模型名称"""
        self._model_name = value
    
    def _load_index(self):
        """加载现有索引"""
        index_file = self.db_path / "index.faiss"
        meta_file = self.db_path / "metadata.pkl"
        vectors_file = self.db_path / "vectors.npz"
        
        if index_file.exists() and meta_file.exists():
            try:
                import faiss
                
                self._index = faiss.read_index(str(index_file))
                with open(meta_file, 'rb') as f:
                    data = pickle.load(f)
                    self._metadata = data.get('metadata', [])
                    self._video_ids = data.get('video_ids', [])
                
                if vectors_file.exists():
                    vectors_data = np.load(vectors_file)
                    for vid, vec in vectors_data.items():
                        self._frame_embeddings[vid] = vec
                
                print(f"Loaded CLIP index with {len(self._metadata)} entries")
            except Exception as e:
                print(f"Failed to load index: {e}")
                self._reset_index()
        else:
            self._reset_index()
    
    def _reset_index(self):
        """重置索引"""
        import faiss
        
        self._metadata = []
        self._video_ids = []
        self._frame_embeddings = {}
        
        # 初始化 FAISS 索引 (内积度量，用于余弦相似度)
        dimension = 512  # CLIP ViT-B/32 输出维度
        self._index = faiss.IndexFlatIP(dimension)
        
        # 归一化以便使用余弦相似度
        # 注意：这里不用 HNSW 等复杂索引，因为视频数量通常不大
    
    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """L2 归一化向量"""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return vectors / norms
    
    def extract_frame_embedding(self, frame: np.ndarray) -> np.ndarray:
        """
        提取单帧的 CLIP 特征向量
        
        Args:
            frame: BGR 格式的帧图像
            
        Returns:
            512维特征向量
        """
        # 转换颜色空间
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)
        
        # 提取特征
        with torch.no_grad():
            inputs = self.processor(images=pil_image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            image_features = self.model.get_image_features(**inputs)
        
        # 转换为 numpy 并归一化
        embedding = image_features.cpu().numpy().flatten()
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding
    
    def extract_video_embeddings(
        self,
        video_path: str,
        num_frames: int = 16,
        sample_strategy: str = "uniform"
    ) -> Tuple[np.ndarray, List[Dict]]:
        """
        提取视频的 CLIP 特征向量序列
        
        Args:
            video_path: 视频文件路径
            num_frames: 采样帧数
            sample_strategy: 采样策略 (uniform/adaptive/keyframes)
            
        Returns:
            (embeddings, frame_info): 特征向量数组和帧信息
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        embeddings = []
        frame_info = []
        
        if sample_strategy == "uniform":
            indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        elif sample_strategy == "adaptive":
            # 根据视频长度动态调整采样间隔
            interval = max(1, total_frames // num_frames)
            indices = list(range(0, total_frames, interval))[:num_frames]
        else:
            indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            
            if ret and frame is not None:
                try:
                    embedding = self.extract_frame_embedding(frame)
                    embeddings.append(embedding)
                    frame_info.append({
                        "frame_index": idx,
                        "timestamp": idx / fps if fps > 0 else 0,
                    })
                except Exception as e:
                    print(f"Error extracting frame {idx}: {e}")
                    continue
        
        cap.release()
        
        if not embeddings:
            raise ValueError("No valid frames extracted")
        
        return np.array(embeddings), frame_info
    
    def compute_video_signature(
        self,
        video_path: str,
        aggregation: str = "mean"
    ) -> Tuple[np.ndarray, Dict]:
        """
        计算视频的聚合特征签名
        
        Args:
            video_path: 视频路径
            aggregation: 聚合方式 (mean/max/weighted/attentive)
            
        Returns:
            (signature, info): 视频签名和元信息
        """
        embeddings, frame_info = self.extract_video_embeddings(
            video_path,
            num_frames=16,
            sample_strategy="uniform"
        )
        
        if aggregation == "mean":
            signature = np.mean(embeddings, axis=0)
        elif aggregation == "max":
            signature = np.max(embeddings, axis=0)
        elif aggregation == "weighted":
            # 时间加权，越靠前权重越低
            weights = np.linspace(0.5, 1.0, len(embeddings))
            weights = weights / weights.sum()
            signature = np.average(embeddings, axis=0, weights=weights)
        else:
            signature = np.mean(embeddings, axis=0)
        
        # 归一化
        signature = signature / np.linalg.norm(signature)
        
        info = {
            "frame_count": len(embeddings),
            "aggregation": aggregation,
            "frame_info": frame_info,
        }
        
        return signature, info
    
    def add_video(
        self,
        video_id: str,
        video_path: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        添加视频到向量数据库
        
        Args:
            video_id: 视频唯一标识
            video_path: 视频文件路径
            metadata: 视频元信息
            
        Returns:
            添加结果
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        print(f"Processing video: {video_id}")
        
        # 提取帧级嵌入
        frame_embeddings, frame_info = self.extract_video_embeddings(
            str(video_path),
            num_frames=16
        )
        
        # 计算视频级签名
        video_signature, sig_info = self.compute_video_signature(
            str(video_path),
            aggregation="weighted"
        )
        
        # 添加到 FAISS 索引 (签名)
        self._index.add(video_signature.reshape(1, -1).astype(np.float32))
        
        # 存储元数据
        video_meta = {
            "video_id": video_id,
            "video_path": str(video_path),
            "video_name": video_path.stem,
            "timestamp": datetime.now().isoformat(),
            "frame_count": len(frame_embeddings),
            "signature_info": sig_info,
        }
        if metadata:
            video_meta.update(metadata)
        
        self._metadata.append(video_meta)
        self._video_ids.append(video_id)
        
        # 存储帧级嵌入
        self._frame_embeddings[video_id] = frame_embeddings
        
        return {
            "video_id": video_id,
            "frame_count": len(frame_embeddings),
            "signature_dim": len(video_signature),
        }
    
    def search_by_video(
        self,
        query_video_path: str,
        top_k: int = 5,
        threshold: float = 0.7,
        use_frame_search: bool = False
    ) -> List[Dict]:
        """
        通过视频查询相似视频
        
        Args:
            query_video_path: 查询视频路径
            top_k: 返回前k个结果
            threshold: 相似度阈值
            use_frame_search: 是否使用帧级搜索
            
        Returns:
            相似视频列表
        """
        if self._index.ntotal == 0:
            return []
        
        # 提取查询视频签名
        query_signature, _ = self.compute_video_signature(
            query_video_path,
            aggregation="weighted"
        )
        
        # 搜索
        query_vec = query_signature.reshape(1, -1).astype(np.float32)
        distances, indices = self._index.search(query_vec, min(top_k, self._index.ntotal))
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue
            
            similarity = float(dist)  # 内积 = 余弦相似度(因为已归一化)
            
            if similarity < threshold:
                continue
            
            result = {
                "video_id": self._video_ids[idx],
                "video_name": self._metadata[idx].get("video_name", ""),
                "video_path": self._metadata[idx].get("video_path", ""),
                "similarity": round(similarity * 100, 2),  # 转为百分比
                "distance": float(dist),
            }
            
            # 帧级相似度搜索
            if use_frame_search and self._video_ids[idx] in self._frame_embeddings:
                query_frames, _ = self.extract_video_embeddings(
                    query_video_path,
                    num_frames=16
                )
                ref_frames = self._frame_embeddings[self._video_ids[idx]]
                
                # 计算帧级最大相似度
                frame_sims = np.dot(query_frames, ref_frames.T)
                max_frame_sim = float(np.max(frame_sims))
                avg_frame_sim = float(np.mean(np.max(frame_sims, axis=1)))
                
                result["frame_max_similarity"] = round(max_frame_sim * 100, 2)
                result["frame_avg_similarity"] = round(avg_frame_sim * 100, 2)
            
            results.append(result)
        
        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results
    
    def search_by_image(
        self,
        image_path: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        通过图像查询相似视频
        
        Args:
            image_path: 查询图像路径
            top_k: 返回前k个结果
            threshold: 相似度阈值
            
        Returns:
            相似视频列表
        """
        if self._index.ntotal == 0:
            return []
        
        # 读取并提取图像特征
        image = cv2.imread(image_path)
        if image is None:
            image = np.array(Image.open(image_path))
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
            else:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        query_signature = self.extract_frame_embedding(image)
        
        # 搜索
        query_vec = query_signature.reshape(1, -1).astype(np.float32)
        distances, indices = self._index.search(query_vec, min(top_k, self._index.ntotal))
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue
            
            similarity = float(dist)
            
            if similarity < threshold:
                continue
            
            results.append({
                "video_id": self._video_ids[idx],
                "video_name": self._metadata[idx].get("video_name", ""),
                "video_path": self._metadata[idx].get("video_path", ""),
                "similarity": round(similarity * 100, 2),
            })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results
    
    def save_index(self):
        """保存索引到磁盘"""
        import faiss
        
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        index_file = self.db_path / "index.faiss"
        meta_file = self.db_path / "metadata.pkl"
        vectors_file = self.db_path / "vectors.npz"
        
        # 保存 FAISS 索引
        faiss.write_index(self._index, str(index_file))
        
        # 保存元数据
        with open(meta_file, 'wb') as f:
            pickle.dump({
                'metadata': self._metadata,
                'video_ids': self._video_ids,
            }, f)
        
        # 保存帧级嵌入
        if self._frame_embeddings:
            np.savez(
                vectors_file,
                **{k: v for k, v in self._frame_embeddings.items()}
            )
        
        print(f"Saved CLIP index: {self._index.ntotal} videos")
    
    def get_stats(self) -> Dict:
        """获取数据库统计信息"""
        return {
            "total_videos": self._index.ntotal,
            "embedding_dim": 512,
            "index_type": self.index_type,
            "device": self.device,
            "db_path": str(self.db_path),
            "has_frame_embeddings": len(self._frame_embeddings) > 0,
        }


class DynamicThreshold:
    """动态阈值计算器"""
    
    def __init__(
        self,
        base_threshold: float = 0.75,
        min_threshold: float = 0.60,
        max_threshold: float = 0.90
    ):
        self.base_threshold = base_threshold
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
    
    def compute_threshold(
        self,
        video_length: float = None,
        video_quality: float = None,
        frame_diversity: float = None,
        match_history: List[float] = None
    ) -> float:
        """
        根据视频特征计算动态阈值
        
        Args:
            video_length: 视频时长(秒)
            video_quality: 视频质量 (0-1)
            frame_diversity: 帧多样性 (0-1)
            match_history: 历史匹配分数列表
            
        Returns:
            计算后的阈值
        """
        threshold = self.base_threshold
        
        # 短视频调整
        if video_length is not None and video_length < 30:
            threshold -= 0.05  # 短视频降低阈值
        
        # 长视频调整
        if video_length is not None and video_length > 300:
            threshold += 0.03  # 长视频提高阈值
        
        # 低质量视频调整
        if video_quality is not None and video_quality < 0.5:
            threshold -= 0.05
        
        # 高多样性调整
        if frame_diversity is not None and frame_diversity > 0.8:
            threshold -= 0.03
        
        # 基于历史匹配调整
        if match_history and len(match_history) >= 5:
            recent_avg = np.mean(match_history[-5:])
            if recent_avg < 0.7:
                threshold -= 0.05
            elif recent_avg > 0.9:
                threshold += 0.03
        
        return max(self.min_threshold, min(self.max_threshold, threshold))
    
    def get_match_label(self, similarity: float, threshold: float = None) -> str:
        """根据相似度和阈值判断匹配类型"""
        if threshold is None:
            threshold = self.base_threshold
        
        if similarity >= 0.95:
            return "identical"  # 完全相同
        elif similarity >= 0.90:
            return "duplicate"  # 重复
        elif similarity >= threshold:
            return "similar"  # 相似
        elif similarity >= 0.70:
            return "possible_match"  # 可能的匹配
        else:
            return "different"  # 不同


class CLIPVideoDetector:
    """CLIP 视频检测器 - 整合向量数据库和动态阈值"""
    
    def __init__(
        self,
        db_path: str = "data/clip_vectors",
        base_threshold: float = 0.75,
        device: str = None
    ):
        self.vector_db = CLIPVectorDB(db_path=db_path, device=device)
        self.threshold_calc = DynamicThreshold(base_threshold=base_threshold)
    
    def index_video(
        self,
        video_id: str,
        video_path: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """索引视频"""
        result = self.vector_db.add_video(video_id, video_path, metadata)
        self.vector_db.save_index()
        return result
    
    def detect(
        self,
        video_path: str,
        use_dynamic_threshold: bool = True,
        use_frame_search: bool = True
    ) -> Dict:
        """
        检测视频相似度
        
        Args:
            video_path: 待检测视频路径
            use_dynamic_threshold: 使用动态阈值
            use_frame_search: 使用帧级搜索
            
        Returns:
            检测结果
        """
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            video_length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / max(1, cap.get(cv2.CAP_PROP_FPS))
            video_quality = min(1.0, cap.get(cv2.CAP_PROP_FRAME_COUNT) / 300)  # 简单质量估计
            cap.release()
        else:
            video_length = 60
            video_quality = 0.5
        
        # 计算动态阈值
        threshold = self.threshold_calc.base_threshold
        if use_dynamic_threshold:
            threshold = self.threshold_calc.compute_threshold(
                video_length=video_length,
                video_quality=video_quality
            )
        
        # 搜索相似视频
        results = self.vector_db.search_by_video(
            video_path,
            top_k=10,
            threshold=threshold - 0.1,  # 先用较低阈值获取更多结果
            use_frame_search=use_frame_search
        )
        
        # 过滤和标记结果
        detected_matches = []
        for r in results:
            similarity = r["similarity"] / 100
            label = self.threshold_calc.get_match_label(similarity, threshold)
            
            if label != "different":
                r["match_type"] = label
                r["threshold_used"] = round(threshold * 100, 2)
                r["confidence"] = "high" if similarity >= 0.85 else "medium"
                detected_matches.append(r)
        
        return {
            "query_video": video_path,
            "threshold": round(threshold * 100, 2),
            "match_count": len(detected_matches),
            "matches": detected_matches,
        }
    
    def detect_with_traditional(
        self,
        video_path: str,
        traditional_detector
    ) -> Dict:
        """融合 CLIP 和传统方法的结果"""
        # CLIP 结果
        clip_result = self.detect(video_path)
        
        # 传统方法结果
        try:
            trad_results = traditional_detector.compare_with_database(video_path)
            trad_matches = [r for r in trad_results if r.get("is_match", False)]
        except Exception as e:
            trad_matches = []
            print(f"Traditional detection failed: {e}")
        
        # 融合结果
        fused_matches = []
        
        # CLIP 匹配
        for clip_match in clip_result.get("matches", []):
            fused_matches.append({
                "video_id": clip_match["video_id"],
                "video_name": clip_match["video_name"],
                "clip_similarity": clip_match["similarity"],
                "match_type": clip_match.get("match_type"),
                "source": "clip",
            })
        
        # 传统匹配
        for trad_match in trad_matches:
            video_id = trad_match.get("matched_video", "")
            # 检查是否已在 CLIP 结果中
            existing = next((m for m in fused_matches if m["video_id"] == video_id), None)
            
            if existing:
                existing["traditional_similarity"] = trad_match.get("overall_similarity", 0)
                existing["traditional_phash"] = trad_match.get("phash_distance", 999)
                existing["source"] = "both"
            else:
                fused_matches.append({
                    "video_id": video_id,
                    "video_name": trad_match.get("matched_video", ""),
                    "traditional_similarity": trad_match.get("overall_similarity", 0),
                    "traditional_phash": trad_match.get("phash_distance", 999),
                    "match_type": "traditional_match",
                    "source": "traditional",
                })
        
        # 计算综合分数
        for match in fused_matches:
            clip_sim = match.get("clip_similarity", 0) / 100
            trad_sim = match.get("traditional_similarity", 50) / 100
            
            if match["source"] == "both":
                # 加权融合
                match["fused_similarity"] = round(
                    (clip_sim * 0.6 + trad_sim * 0.4) * 100, 2
                )
            elif match["source"] == "clip":
                match["fused_similarity"] = round(clip_sim * 100, 2)
            else:
                match["fused_similarity"] = round(trad_sim * 100, 2)
        
        # 排序
        fused_matches.sort(key=lambda x: x.get("fused_similarity", 0), reverse=True)
        
        return {
            "query_video": video_path,
            "clip_matches": clip_result["matches"],
            "traditional_matches": trad_matches,
            "fused_matches": fused_matches[:10],
        }
