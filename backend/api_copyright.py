# -*- coding: utf-8 -*-
"""
版权保护 API 接口
"""

import json
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

from video_fingerprint import VideoFingerprint
from similarity import SimilarityDetector
from monitor import CopyrightMonitor
from membership import (
    MembershipTier, 
    require_feature, 
    check_usage_limit,
    UsageTracker,
    get_tier_display_name
)

router = APIRouter(prefix="/api/copyright", tags=["版权保护"])

# 初始化组件
_fingerprint_gen = None
_similarity_detector = None
_monitor = None


def get_fingerprint_gen():
    global _fingerprint_gen
    if _fingerprint_gen is None:
        _fingerprint_gen = VideoFingerprint(frames_dir="data/fingerprints")
    return _fingerprint_gen


def get_similarity_detector():
    global _similarity_detector
    if _similarity_detector is None:
        _similarity_detector = SimilarityDetector(fingerprints_dir="data/fingerprints")
    return _similarity_detector


def get_monitor():
    global _monitor
    if _monitor is None:
        _monitor = CopyrightMonitor(
            fingerprints_dir="data/fingerprints",
            download_dir="data/downloads"
        )
    return _monitor


# 请求/响应模型
class WatchlistRequest(BaseModel):
    keyword: str
    platforms: Optional[List[str]] = None
    priority: Optional[int] = 1


class CompareRequest(BaseModel):
    video1_path: str
    video2_path: str


# ============== 指纹管理 API ==============

@router.post("/fingerprint/generate")
async def generate_fingerprint(video: UploadFile = File(...)):
    """生成视频指纹"""
    try:
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        video_path = upload_dir / f"{video.filename}"
        
        with open(video_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        gen = get_fingerprint_gen()
        fingerprint = gen.generate_video_fingerprint(str(video_path))
        gen.save_fingerprint(fingerprint)
        
        return {
            "status": "success",
            "video_name": fingerprint["video_name"],
            "fingerprint": {
                "phash": fingerprint["phash"][:32] + "...",
                "dhash": fingerprint["dhash"][:32] + "...",
                "frame_count": fingerprint["frame_count"]
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fingerprint/list")
async def list_fingerprints():
    """获取所有指纹列表"""
    try:
        detector = get_similarity_detector()
        
        fingerprints = []
        for name, fp in detector.fingerprints_db.items():
            fingerprints.append({
                "name": name,
                "video_name": fp.get("video_name", name),
                "timestamp": fp.get("timestamp"),
                "frame_count": fp.get("frame_count", 0)
            })
        
        return {
            "status": "success",
            "count": len(fingerprints),
            "fingerprints": fingerprints
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/fingerprint/{video_name}")
async def delete_fingerprint(video_name: str):
    """删除指纹"""
    try:
        fp_dir = Path("data/fingerprints")
        fp_file = fp_dir / f"{video_name}_fingerprint.json"
        
        if fp_file.exists():
            fp_file.unlink()
            return {"status": "success", "message": f"已删除 {video_name}"}
        else:
            raise HTTPException(status_code=404, detail="指纹不存在")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== 相似度检测 API ==============

@router.post("/compare")
async def compare_videos(request: CompareRequest):
    """比较两个视频的相似度"""
    try:
        detector = get_similarity_detector()
        result = detector.compare_videos(request.video1_path, request.video2_path)
        
        return {
            "status": "success",
            "result": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect")
async def detect_plagiarism(video: UploadFile = File(...)):
    """检测视频侵权（高级功能）"""
    # 检查高级功能权限
    if not require_feature("detection_per_day"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "feature_locked",
                "message": "侵权检测是高级功能，需要升级到专业版或更高版本",
                "upgrade_url": "/membership",
                "current_plan": get_tier_display_name(MembershipTier.PRO)
            }
        )
    
    # 检查用量限制
    allowed, remaining = check_usage_limit("detection_per_day")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_exceeded",
                "message": f"今日检测次数已用完，请明天再来或升级到更高版本",
                "remaining": 0,
                "upgrade_url": "/membership"
            }
        )
    
    try:
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        video_path = upload_dir / f"detect_{video.filename}"
        
        with open(video_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        detector = get_similarity_detector()
        results = detector.compare_with_database(str(video_path))
        
        # 记录检测次数
        tracker = UsageTracker()
        current_usage = tracker.record_detection()
        
        matches = [r for r in results if r.get("is_match", False)]
        
        return {
            "status": "success",
            "video": video.filename,
            "total_checked": len(results),
            "matches": matches,
            "has_infringement": len(matches) > 0,
            "usage": {
                "today_used": current_usage,
                "remaining": remaining - 1 if remaining > 0 else -1
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare/batch")
async def batch_compare(video_dir: str = "data/uploads"):
    """批量比较目录下所有视频"""
    try:
        detector = get_similarity_detector()
        results = detector.batch_compare(video_dir, output_file="data/comparison_results.json")
        
        return {
            "status": "success",
            "total_comparisons": len(results),
            "results": results[:50]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== 监控管理 API ==============

@router.post("/watchlist/add")
async def add_to_watchlist(request: WatchlistRequest):
    """添加监控关键词"""
    # 检查监控数量限制
    from membership import FEATURE_LIMITS, MembershipTier
    current_tier = MembershipTier.PRO
    watchlist_limit = FEATURE_LIMITS["watchlist_count"].get_limit(current_tier)
    
    if watchlist_limit != -1:
        current_count = len(get_monitor().watchlist)
        if current_count >= watchlist_limit:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "watchlist_limit_exceeded",
                    "message": f"监控关键词数量已达上限（{watchlist_limit}个），请升级会员等级或删除部分监控",
                    "current_count": current_count,
                    "limit": watchlist_limit,
                    "upgrade_url": "/membership"
                }
            )
    
    try:
        monitor = get_monitor()
        monitor.add_to_watchlist(
            keyword=request.keyword,
            platforms=request.platforms,
            priority=request.priority
        )
        
        return {
            "status": "success",
            "message": f"已添加监控: {request.keyword}",
            "watchlist_count": len(monitor.watchlist),
            "watchlist_limit": watchlist_limit
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/watchlist/{keyword}")
async def remove_from_watchlist(keyword: str):
    """移除监控关键词"""
    try:
        monitor = get_monitor()
        monitor.remove_from_watchlist(keyword)
        
        return {
            "status": "success",
            "message": f"已移除监控: {keyword}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist")
async def get_watchlist():
    """获取监控列表"""
    try:
        monitor = get_monitor()
        
        return {
            "status": "success",
            "count": len(monitor.watchlist),
            "watchlist": monitor.watchlist
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan")
async def run_scan():
    """运行侵权扫描"""
    try:
        monitor = get_monitor()
        results = monitor.run_scheduled_scan()
        
        total_matches = sum(r['matches_count'] for r in results)
        
        return {
            "status": "success",
            "keywords_scanned": len(results),
            "total_matches": total_matches,
            "results": results,
            "has_alerts": total_matches > 0
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts():
    """获取告警列表"""
    try:
        alert_file = Path("data/alerts.json")
        
        if alert_file.exists():
            with open(alert_file, 'r', encoding='utf-8') as f:
                alerts = json.load(f)
            return {
                "status": "success",
                "alerts": alerts
            }
        else:
            return {
                "status": "success",
                "alerts": None,
                "message": "暂无告警"
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """获取版权保护统计"""
    try:
        detector = get_similarity_detector()
        monitor = get_monitor()
        from membership import MembershipTier, FEATURE_LIMITS, get_tier_display_name, UsageTracker
        
        current_tier = MembershipTier.PRO
        tracker = UsageTracker()
        
        # 获取用量
        detection_limit = FEATURE_LIMITS["detection_per_day"].get_limit(current_tier)
        watchlist_limit = FEATURE_LIMITS["watchlist_count"].get_limit(current_tier)
        fingerprint_limit = FEATURE_LIMITS["fingerprint_count"].get_limit(current_tier)
        
        return {
            "status": "success",
            "membership": {
                "tier": current_tier.value,
                "tier_name": get_tier_display_name(current_tier)
            },
            "resources": {
                "fingerprints": {
                    "used": len(detector.fingerprints_db),
                    "limit": "无限制" if fingerprint_limit == -1 else fingerprint_limit,
                    "is_unlimited": fingerprint_limit == -1
                },
                "watchlist": {
                    "used": len(monitor.watchlist),
                    "limit": "无限制" if watchlist_limit == -1 else watchlist_limit,
                    "is_unlimited": watchlist_limit == -1
                }
            },
            "daily_usage": {
                "detections_used": tracker.get_daily_detections(),
                "detections_limit": "无限制" if detection_limit == -1 else detection_limit,
                "is_unlimited": detection_limit == -1
            },
            "settings": {
                "similarity_threshold": detector.threshold
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
