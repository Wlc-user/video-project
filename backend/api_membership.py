# -*- coding: utf-8 -*-
"""
会员管理 API 接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List, Any

from membership import (
    MembershipTier, 
    TIER_PRICES, 
    get_tier_display_name, 
    get_tier_features,
    FEATURE_LIMITS,
    UsageTracker
)

router = APIRouter(prefix="/api/membership", tags=["会员服务"])

# 当前用户等级（简化处理，实际应从认证系统获取）
_current_user_tier = MembershipTier.PRO


class UserInfo(BaseModel):
    """用户信息"""
    tier: str
    tier_name: str
    features: Dict[str, Any]


class FeatureCheckRequest(BaseModel):
    """功能检查请求"""
    feature: str


class FeatureCheckResponse(BaseModel):
    """功能检查响应"""
    available: bool
    current_usage: int
    limit: int
    message: str


# ============== 会员信息 API ==============

@router.get("/info", response_model=UserInfo)
async def get_user_info():
    """获取当前用户会员信息"""
    tier = _current_user_tier
    
    return {
        "tier": tier.value,
        "tier_name": get_tier_display_name(tier),
        "features": get_tier_features(tier)
    }


@router.get("/plans")
async def get_plans():
    """获取会员套餐列表"""
    plans = []
    
    for tier in MembershipTier:
        plans.append({
            "id": tier.value,
            "name": get_tier_display_name(tier),
            "price": TIER_PRICES[tier],
            "price_unit": "元/月" if tier != MembershipTier.FREE else "免费",
            "features": get_tier_features(tier)
        })
    
    return {
        "status": "success",
        "plans": plans
    }


@router.get("/features")
async def list_all_features():
    """获取所有功能及等级要求"""
    features = []
    
    for name, feature in FEATURE_LIMITS.items():
        tier_requirements = {}
        for tier in MembershipTier:
            if feature.is_available(tier):
                tier_requirements[tier.value] = feature.get_limit(tier)
        
        features.append({
            "id": name,
            "name": feature.name,
            "tier_requirements": tier_requirements,
            "min_tier": _get_min_tier(feature)
        })
    
    return {
        "status": "success",
        "features": features
    }


def _get_min_tier(feature) -> str:
    """获取功能的最低要求等级"""
    for tier in MembershipTier:
        if feature.is_available(tier):
            return tier.value
    return "none"


# ============== 用量追踪 API ==============

@router.get("/usage/{feature}")
async def get_feature_usage(feature: str):
    """获取功能使用量"""
    if feature not in FEATURE_LIMITS:
        raise HTTPException(status_code=404, detail="未知功能")
    
    tracker = UsageTracker()
    feature_config = FEATURE_LIMITS[feature]
    limit = feature_config.get_limit(_current_user_tier)
    
    # 根据功能类型获取不同用量
    if feature == "detection_per_day":
        usage = tracker.get_daily_detections()
    elif feature == "fingerprint_count":
        usage = _count_fingerprints()
    elif feature == "watchlist_count":
        usage = _count_watchlist()
    else:
        usage = 0
    
    return {
        "status": "success",
        "feature": feature,
        "feature_name": feature_config.name,
        "current_usage": usage,
        "limit": "无限制" if limit == -1 else limit,
        "remaining": "无限制" if limit == -1 else max(0, limit - usage),
        "is_unlimited": limit == -1
    }


@router.post("/usage/record/{feature}")
async def record_feature_usage(feature: str):
    """记录功能使用（用于检测次数等）"""
    if feature not in FEATURE_LIMITS:
        raise HTTPException(status_code=404, detail="未知功能")
    
    feature_config = FEATURE_LIMITS[feature]
    limit = feature_config.get_limit(_current_user_tier)
    
    # 检查是否无限制
    if limit == -1:
        return {
            "status": "success",
            "message": "功能无使用限制",
            "remaining": "无限制"
        }
    
    tracker = UsageTracker()
    
    if feature == "detection_per_day":
        current = tracker.record_detection()
        remaining = max(0, limit - current)
        allowed = current <= limit
        
        return {
            "status": "success" if allowed else "limit_exceeded",
            "feature": feature,
            "current_usage": current,
            "limit": limit,
            "remaining": remaining,
            "message": "检测成功" if allowed else f"今日检测次数已用完（{limit}次）"
        }
    
    return {
        "status": "success",
        "message": "已记录"
    }


@router.post("/check/{feature}")
async def check_feature_access(feature: str):
    """检查功能是否可用"""
    if feature not in FEATURE_LIMITS:
        raise HTTPException(status_code=404, detail="未知功能")
    
    feature_config = FEATURE_LIMITS[feature]
    is_available = feature_config.is_available(_current_user_tier)
    
    if not is_available:
        min_tier = _get_min_tier(feature_config)
        return {
            "status": "unavailable",
            "available": False,
            "message": f"该功能需要 {get_tier_display_name(MembershipTier(min_tier))} 或更高版本",
            "upgrade_required": True,
            "min_tier": min_tier
        }
    
    return {
        "status": "success",
        "available": True,
        "message": "功能可用",
        "upgrade_required": False
    }


# ============== 辅助函数 ==============

def _count_fingerprints() -> int:
    """统计指纹数量"""
    from pathlib import Path
    fp_dir = Path("data/fingerprints")
    if not fp_dir.exists():
        return 0
    return len(list(fp_dir.glob("*.json")))


def _count_watchlist() -> int:
    """统计监控数量"""
    from pathlib import Path
    checkpoint = Path("data/monitor_checkpoint.json")
    if not checkpoint.exists():
        return 0
    import json
    try:
        with open(checkpoint, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return len(data.get("watchlist", []))
    except:
        return 0


# ============== 内部检查函数（供其他模块调用）==============

def require_feature(feature_name: str, user_tier: MembershipTier = None) -> bool:
    """检查用户是否有某功能权限"""
    if user_tier is None:
        user_tier = _current_user_tier
    
    if feature_name not in FEATURE_LIMITS:
        return True  # 未知功能默认允许
    
    return FEATURE_LIMITS[feature_name].is_available(user_tier)


def check_usage_limit(feature_name: str, user_tier: MembershipTier = None) -> tuple:
    """检查用量是否超限，返回 (是否允许, 剩余次数)"""
    if user_tier is None:
        user_tier = _current_user_tier
    
    if feature_name not in FEATURE_LIMITS:
        return (True, -1)
    
    feature = FEATURE_LIMITS[feature_name]
    limit = feature.get_limit(user_tier)
    
    if limit == -1:
        return (True, -1)
    
    tracker = UsageTracker()
    
    if feature_name == "detection_per_day":
        current = tracker.get_daily_detections()
        remaining = max(0, limit - current)
        return (current < limit, remaining)
    
    return (True, limit)
