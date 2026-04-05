"""AI使用权限验证和配额管理"""

import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

from database import (
    get_user_by_id,
    record_ai_usage,
    get_user_ai_usage_today,
    update_user_plan,
    FREE_DAILY_AI_LIMIT,
    PROFESSIONAL_AI_FEATURES,
)


class AIUsageManager:
    """管理AI功能的使用权限和配额"""
    
    @staticmethod
    def check_ai_permission(user_id: int, feature: str = "basic_summary") -> Tuple[bool, str, int]:
        """
        检查用户是否有权限使用AI功能
        
        Args:
            user_id: 用户ID
            feature: AI功能类型 (basic_summary, professional_analysis, study_notes, etc.)
            
        Returns:
            (allowed: bool, message: str, remaining: int)
        """
        user = get_user_by_id(user_id)
        if not user:
            return False, "用户不存在", 0
        
        # 检查用户计划
        is_professional = user.get("is_vip") and user.get("plan_type", "").startswith("professional")
        is_vip = user.get("is_vip", False)
        
        # 功能权限映射
        feature_permissions = {
            "basic_summary": True,  # 所有人都可用基础总结
            "professional_analysis": is_professional,
            "academic_analysis": is_professional,
            "business_analysis": is_professional,
            "detailed_mindmap": is_professional,
            "study_notes": is_professional,
            "key_quotes": is_professional,
            "deep_context_qa": is_professional,
        }
        
        # 检查功能权限
        allowed_for_feature = feature_permissions.get(feature, False)
        if not allowed_for_feature:
            if feature in ["professional_analysis", "academic_analysis", "business_analysis"]:
                return False, "此功能需要专业版会员", 0
            elif feature in ["study_notes", "key_quotes", "deep_context_qa"]:
                return False, "此功能需要专业版会员", 0
            else:
                return False, "此功能暂不可用", 0
        
        # 检查使用次数限制
        if is_professional:
            # 专业用户无限次数
            return True, "专业版用户无限使用", -1
        elif is_vip:
            # VIP用户每日限制
            today_usage = get_user_ai_usage_today(user_id)
            remaining = max(0, 50 - today_usage)  # VIP用户每日50次
            if remaining <= 0:
                return False, "今日AI使用次数已用完，请升级专业版", 0
            return True, f"VIP用户今日剩余{remaining}次", remaining
        else:
            # 免费用户限制
            today_usage = get_user_ai_usage_today(user_id)
            remaining = max(0, FREE_DAILY_AI_LIMIT - today_usage)
            if remaining <= 0:
                return False, f"今日免费AI使用次数已用完（每日{FREE_DAILY_AI_LIMIT}次），升级VIP可获更多次数", 0
            return True, f"今日剩余{remaining}次免费使用", remaining
    
    @staticmethod
    def record_ai_usage(user_id: int, feature: str, video_url: str = "", cost_units: int = 1) -> bool:
        """
        记录AI使用情况
        
        Args:
            user_id: 用户ID
            feature: 使用的AI功能
            video_url: 视频URL（可选）
            cost_units: 消耗的单位数（基础功能=1，高级功能可能>1）
            
        Returns:
            是否记录成功
        """
        user = get_user_by_id(user_id)
        if not user:
            return False
        
        # 检查是否有权限
        allowed, _, _ = AIUsageManager.check_ai_permission(user_id, feature)
        if not allowed:
            return False
        
        # 记录使用情况
        success = record_ai_usage(
            user_id=user_id,
            feature=feature,
            video_url=video_url,
            cost_units=cost_units
        )
        
        return success
    
    @staticmethod
    def get_user_ai_stats(user_id: int) -> dict:
        """获取用户AI使用统计"""
        user = get_user_by_id(user_id)
        if not user:
            return {"error": "用户不存在"}
        
        is_professional = user.get("is_vip") and user.get("plan_type", "").startswith("professional")
        is_vip = user.get("is_vip", False)
        
        today_usage = get_user_ai_usage_today(user_id)
        
        if is_professional:
            limit = "无限"
            remaining = "无限"
        elif is_vip:
            limit = 50
            remaining = max(0, 50 - today_usage)
        else:
            limit = FREE_DAILY_AI_LIMIT
            remaining = max(0, FREE_DAILY_AI_LIMIT - today_usage)
        
        # 可用功能列表
        available_features = ["basic_summary"]
        if is_professional:
            available_features.extend(PROFESSIONAL_AI_FEATURES)
        
        return {
            "user_id": user_id,
            "plan": user.get("plan_type", "free"),
            "is_professional": is_professional,
            "is_vip": is_vip,
            "today_usage": today_usage,
            "daily_limit": limit,
            "remaining_today": remaining,
            "available_features": available_features,
            "vip_expire_at": user.get("vip_expire_at"),
        }
    
    @staticmethod
    def get_feature_cost(feature: str) -> int:
        """获取功能消耗单位数"""
        cost_map = {
            "basic_summary": 1,
            "professional_analysis": 3,
            "academic_analysis": 3,
            "business_analysis": 3,
            "detailed_mindmap": 2,
            "study_notes": 2,
            "key_quotes": 1,
            "deep_context_qa": 2,
        }
        return cost_map.get(feature, 1)


def require_ai_permission(feature: str = "basic_summary"):
    """FastAPI依赖：检查AI使用权限"""
    from fastapi import Depends, HTTPException
    from auth import get_current_user
    
    async def permission_checker(user: dict = Depends(get_current_user)):
        allowed, message, remaining = AIUsageManager.check_ai_permission(user["id"], feature)
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "error": message,
                    "code": "AI_USAGE_LIMIT_EXCEEDED",
                    "remaining": remaining,
                }
            )
        
        # 记录使用（在实际调用时记录，这里只检查权限）
        return {
            "user": user,
            "feature": feature,
            "allowed": allowed,
            "remaining": remaining,
        }
    
    return permission_checker