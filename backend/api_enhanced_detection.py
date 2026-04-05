# -*- coding: utf-8 -*-
"""
增强版侵权检测 API
需要专业版或更高会员才能使用
"""

import json
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

from enhanced_fingerprint import EnhancedVideoFingerprint
from enhanced_similarity import EnhancedSimilarityDetector
from membership import (
    MembershipTier, 
    require_feature, 
    check_usage_limit,
    get_tier_display_name
)

router = APIRouter(prefix="/api/enhanced-detection", tags=["增强版侵权检测"])


# 缓存检测器实例
_detector = None
_fingerprint_gen = None


def get_detector():
    """获取检测器实例"""
    global _detector, _fingerprint_gen
    if _detector is None:
        _fingerprint_gen = EnhancedVideoFingerprint(frames_dir="data/fingerprints")
        _detector = EnhancedSimilarityDetector(fingerprints_dir="data/fingerprints")
    return _detector


# ==================== 请求模型 ====================
class DatabaseFingerprintRequest(BaseModel):
    """数据库指纹请求"""
    video_name: str


# ==================== API端点 ====================

@router.post("/fingerprint/generate")
async def generate_enhanced_fingerprint(video: UploadFile = File(...)):
    """
    生成增强版视频指纹
    需要专业版会员
    """
    # 检查会员权限
    if not require_feature("detection_per_day"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "feature_locked",
                "message": "增强版指纹生成需要专业版或更高版本会员",
                "upgrade_url": "/membership",
                "required_tier": "PRO"
            }
        )
    
    try:
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        video_path = upload_dir / f"enhanced_{video.filename}"
        
        with open(video_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        # 使用增强版指纹生成器
        detector = get_detector()
        fingerprint = detector.fingerprint_generator.generate_video_fingerprint(str(video_path))
        
        # 保存指纹
        detector.fingerprint_generator.save_fingerprint(fingerprint)
        
        # 返回结果
        return {
            "status": "success",
            "video_name": video.filename,
            "algorithm_version": fingerprint.get("algorithm_version", "2.0"),
            "frame_count": fingerprint.get("frame_count", 0),
            "keyframe_count": fingerprint.get("keyframe_count", 0),
            "has_audio": fingerprint.get("audio_fingerprint") is not None,
            "phash": fingerprint.get("phash", "")[:32] + "..."
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect")
async def enhanced_detect(video: UploadFile = File(...)):
    """
    增强版侵权检测（多模态融合）
    需要专业版会员
    """
    # 检查会员权限
    if not require_feature("detection_per_day"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "feature_locked",
                "message": "增强版侵权检测需要专业版或更高版本会员",
                "upgrade_url": "/membership",
                "required_tier": "PRO"
            }
        )
    
    # 检查用量限制
    allowed, remaining = check_usage_limit("detection_per_day")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_exceeded",
                "message": "今日检测次数已用完，请明天再来或升级到更高版本",
                "remaining": 0,
                "upgrade_url": "/membership"
            }
        )
    
    try:
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        video_path = upload_dir / f"detect_enhanced_{video.filename}"
        
        with open(video_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        # 使用增强版检测
        detector = get_detector()
        results = detector.compare_with_database(str(video_path))
        
        # 过滤高相似度结果
        high_similarity = [r for r in results if r.get("overall_similarity", 0) >= 50]
        
        return {
            "status": "success",
            "video": video.filename,
            "algorithm": "多模态融合 (pHash + SIFT + 音频)",
            "version": "2.0",
            "total_matches": len(results),
            "high_risk_count": len(high_similarity),
            "high_risk_results": high_similarity[:5],  # 只返回前5个高风险
            "all_results": results[:10],  # 返回前10个结果
            "usage": {
                "remaining": remaining - 1 if remaining > 0 else -1
            },
            "membership_required": True
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare")
async def compare_two_videos(video1: str, video2: str):
    """
    比较两个视频的相似度
    需要专业版会员
    """
    if not require_feature("detection_per_day"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "feature_locked",
                "message": "视频对比需要专业版或更高版本会员",
                "upgrade_url": "/membership"
            }
        )
    
    try:
        detector = get_detector()
        result = detector.compare_videos(video1, video2)
        
        return {
            "status": "success",
            "data": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_enhanced_stats():
    """获取增强版检测统计"""
    try:
        detector = get_detector()
        
        from membership import MembershipTier, FEATURE_LIMITS
        
        current_tier = MembershipTier.PRO
        
        return {
            "status": "success",
            "algorithm_version": "2.0",
            "features": {
                "sift_detection": True,
                "audio_fingerprint": True,
                "keyframe_extraction": True,
                "multimodal_fusion": True
            },
            "database": {
                "fingerprints_count": len(detector.fingerprints_db)
            },
            "membership_required": {
                "all_features": "PRO"
            },
            "weights": detector.weights
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/membership-status")
async def get_membership_status():
    """获取会员状态和功能权限"""
    from membership import MembershipTier, FEATURE_LIMITS, get_tier_features, get_tier_display_name
    
    current_tier = MembershipTier.PRO
    
    return {
        "status": "success",
        "current_tier": current_tier.value,
        "tier_name": get_tier_display_name(current_tier),
        "can_use_enhanced": require_feature("detection_per_day"),
        "features": get_tier_features(current_tier),
        "upgrade_info": {
            "required": "PRO",
            "benefits": [
                "增强版侵权检测（多模态融合）",
                "SIFT特征点匹配",
                "音频指纹识别",
                "关键帧提取",
                "每日200次检测额度"
            ]
        }
    }
