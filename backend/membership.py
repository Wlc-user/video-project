# -*- coding: utf-8 -*-
"""
会员等级系统
定义不同会员等级的权限
"""

from enum import Enum
from functools import wraps
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from datetime import datetime


class MembershipTier(str, Enum):
    """会员等级"""
    FREE = "free"           # 免费版
    BASIC = "basic"          # 基础版
    PRO = "pro"              # 专业版
    ENTERPRISE = "enterprise" # 企业版


@dataclass
class TierFeature:
    """等级功能配置"""
    name: str
    free_limit: int
    basic_limit: int
    pro_limit: int
    enterprise_limit: int
    
    def get_limit(self, tier: MembershipTier) -> int:
        """获取指定等级的配额"""
        limits = {
            MembershipTier.FREE: self.free_limit,
            MembershipTier.BASIC: self.basic_limit,
            MembershipTier.PRO: self.pro_limit,
            MembershipTier.ENTERPRISE: self.enterprise_limit,
        }
        return limits.get(tier, 0)
    
    def is_available(self, tier: MembershipTier) -> bool:
        """检查该等级是否有此功能"""
        return self.get_limit(tier) > 0


# 功能配额定义
FEATURE_LIMITS = {
    # 指纹管理
    "fingerprint_count": TierFeature(
        name="视频指纹数量",
        free_limit=3,
        basic_limit=10,
        pro_limit=50,
        enterprise_limit=-1  # 无限制
    ),
    "fingerprint_storage_days": TierFeature(
        name="指纹存储天数",
        free_limit=30,
        basic_limit=90,
        pro_limit=365,
        enterprise_limit=-1
    ),
    
    # 侵权检测
    "detection_per_day": TierFeature(
        name="每日检测次数",
        free_limit=5,
        basic_limit=50,
        pro_limit=200,
        enterprise_limit=-1
    ),
    "detection_platforms": TierFeature(
        name="检测平台数量",
        free_limit=1,
        basic_limit=3,
        pro_limit=-1,  # 全部
        enterprise_limit=-1
    ),
    
    # 监控功能
    "watchlist_count": TierFeature(
        name="监控关键词数量",
        free_limit=2,
        basic_limit=10,
        pro_limit=50,
        enterprise_limit=-1
    ),
    "watchlist_interval_hours": TierFeature(
        name="监控扫描间隔(小时)",
        free_limit=24,
        basic_limit=12,
        pro_limit=1,
        enterprise_limit=0  # 实时
    ),
    
    # 高级功能
    "ai_detection": TierFeature(
        name="AI生成内容检测",
        free_limit=0,
        basic_limit=0,
        pro_limit=1,
        enterprise_limit=1
    ),
    "evidence_export": TierFeature(
        name="证据导出",
        free_limit=0,
        basic_limit=5,
        pro_limit=50,
        enterprise_limit=-1
    ),
    "auto_takedown": TierFeature(
        name="自动下架申请",
        free_limit=0,
        basic_limit=0,
        pro_limit=1,
        enterprise_limit=1
    ),
    "priority_support": TierFeature(
        name="优先客服支持",
        free_limit=0,
        basic_limit=0,
        pro_limit=1,
        enterprise_limit=1
    ),
}


class UsageTracker:
    """用户用量追踪"""
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.usage_file = f"data/usage_{user_id}.json"
        self._load_usage()
    
    def _load_usage(self):
        """加载用量数据"""
        import json
        from pathlib import Path
        
        path = Path(self.usage_file)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.usage = json.load(f)
            except:
                self.usage = {}
        else:
            self.usage = {}
        
        # 确保结构完整
        today = datetime.now().strftime("%Y-%m-%d")
        if "daily_detections" not in self.usage:
            self.usage["daily_detections"] = {}
        if "last_reset" not in self.usage:
            self.usage["last_reset"] = today
    
    def _save_usage(self):
        """保存用量数据"""
        import json
        from pathlib import Path
        
        path = Path(self.usage_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.usage, f, indent=2, ensure_ascii=False)
    
    def record_detection(self):
        """记录一次检测"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 每日重置
        if self.usage.get("last_reset") != today:
            self.usage["daily_detections"] = {}
            self.usage["last_reset"] = today
        
        count = self.usage["daily_detections"].get(today, 0)
        self.usage["daily_detections"][today] = count + 1
        self._save_usage()
        
        return self.usage["daily_detections"][today]
    
    def get_daily_detections(self) -> int:
        """获取今日检测次数"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.usage.get("last_reset") != today:
            return 0
        return self.usage["daily_detections"].get(today, 0)


def check_permission(feature_name: str):
    """权限检查装饰器
    
    用法:
        @check_permission("ai_detection")
        async def ai_detect():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 这里简化处理，实际应该从 session/token 获取用户等级
            # 目前默认使用 PRO 版本演示
            current_tier = MembershipTier.PRO
            
            feature = FEATURE_LIMITS.get(feature_name)
            if not feature:
                return await func(*args, **kwargs)
            
            if not feature.is_available(current_tier):
                raise PermissionError(
                    f"该功能仅对 {feature.name} 以上会员开放。"
                    f"当前等级: {current_tier.value}。"
                    f"请升级您的会员等级。"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# 会员等级对应的价格（按月）
TIER_PRICES = {
    MembershipTier.FREE: 0,
    MembershipTier.BASIC: 99,
    MembershipTier.PRO: 299,
    MembershipTier.ENTERPRISE: 799,
}


def get_tier_display_name(tier: MembershipTier) -> str:
    """获取等级的显示名称"""
    names = {
        MembershipTier.FREE: "免费版",
        MembershipTier.BASIC: "基础版",
        MembershipTier.PRO: "专业版",
        MembershipTier.ENTERPRISE: "企业版",
    }
    return names.get(tier, "未知")


def get_tier_features(tier: MembershipTier) -> Dict[str, Any]:
    """获取等级的所有功能"""
    features = {}
    for name, feature in FEATURE_LIMITS.items():
        limit = feature.get_limit(tier)
        features[name] = {
            "name": feature.name,
            "limit": "无限制" if limit == -1 else limit,
            "available": limit != 0
        }
    return features


def require_feature(feature_name: str, user_tier: MembershipTier = None) -> bool:
    """检查用户是否有某功能权限"""
    if user_tier is None:
        user_tier = MembershipTier.PRO
    
    if feature_name not in FEATURE_LIMITS:
        return True  # 未知功能默认允许
    
    return FEATURE_LIMITS[feature_name].is_available(user_tier)


def check_usage_limit(feature_name: str, user_tier: MembershipTier = None) -> tuple:
    """检查用量是否超限，返回 (是否允许, 剩余次数)"""
    if user_tier is None:
        user_tier = MembershipTier.PRO
    
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
