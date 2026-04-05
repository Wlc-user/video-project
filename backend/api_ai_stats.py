"""AI使用统计相关API路由"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import get_current_user
from ai_usage import AIUsageManager

router = APIRouter(prefix="/api/ai", tags=["AI统计"])


class AIStatsResponse(BaseModel):
    user_id: int
    plan: str
    is_professional: bool
    is_vip: bool
    today_usage: int
    daily_limit: str | int
    remaining_today: int | str
    available_features: list[str]
    vip_expire_at: str | None


@router.get("/stats", response_model=AIStatsResponse)
async def get_ai_stats(user: dict = Depends(get_current_user)):
    """获取用户AI使用统计"""
    stats = AIUsageManager.get_user_ai_stats(user["id"])
    return stats


@router.get("/usage-history")
async def get_ai_usage_history(user: dict = Depends(get_current_user), days: int = 7):
    """获取用户AI使用历史"""
    from database import get_user_ai_usage_by_feature
    usage_data = get_user_ai_usage_by_feature(user["id"], days)
    
    # 按功能排序
    sorted_features = sorted(
        usage_data.items(), 
        key=lambda x: x[1]["count"], 
        reverse=True
    )
    
    return {
        "success": True,
        "data": {
            "days": days,
            "total_usage": sum(item[1]["count"] for item in sorted_features),
            "by_feature": [
                {
                    "feature": feature,
                    "count": data["count"],
                    "total_cost": data["total_cost"]
                }
                for feature, data in sorted_features
            ]
        }
    }