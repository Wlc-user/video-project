"""专业分析API路由"""

import asyncio
import json
from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel

from auth import get_current_user
from ai_usage import require_ai_permission
from summarizer import SubtitleExtractor, VideoSummarizer

router = APIRouter(prefix="/api/analyze", tags=["专业分析"])


class ProfessionalAnalysisRequest(BaseModel):
    url: str
    analysis_type: str = "professional"  # professional/academic/business
    language: str = "zh"
    output_format: str = "structured"  # text/json/markdown


class StudyNotesRequest(BaseModel):
    url: str
    subject: str = "general"  # machine_learning/business/technology/etc.
    language: str = "zh"


class KeyQuotesRequest(BaseModel):
    url: str
    max_quotes: int = 8
    language: str = "zh"


def _get_summarizer():
    """延迟初始化VideoSummarizer"""
    if not hasattr(_get_summarizer, "_instance"):
        try:
            _get_summarizer._instance = VideoSummarizer()
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))
    return _get_summarizer._instance


def _get_extractor():
    """延迟初始化SubtitleExtractor"""
    if not hasattr(_get_extractor, "_instance"):
        _get_extractor._instance = SubtitleExtractor()
    return _get_extractor._instance


@router.post("/professional", response_class=EventSourceResponse)
async def professional_analysis(
    req: ProfessionalAnalysisRequest,
    permission=Depends(require_ai_permission("professional_analysis"))
) -> AsyncIterable[ServerSentEvent]:
    """专业级视频分析（SSE流式）"""
    user = permission["user"]
    
    try:
        loop = asyncio.get_event_loop()
        extractor = _get_extractor()
        summarizer = _get_summarizer()
        
        # 提取字幕
        subtitle_data = await loop.run_in_executor(
            None, extractor.extract, req.url
        )
        
        yield ServerSentEvent(
            raw_data=json.dumps({
                "subtitle_info": {
                    "has_subtitle": subtitle_data["has_subtitle"],
                    "language": subtitle_data["language"],
                    "segments_count": len(subtitle_data["segments"])
                }
            }, ensure_ascii=False),
            event="info",
        )
        
        if not subtitle_data["has_subtitle"]:
            yield ServerSentEvent(
                raw_data=json.dumps({"message": "该视频没有可用的字幕，无法进行分析"}, ensure_ascii=False),
                event="error",
            )
            return
        
        full_text = subtitle_data["full_text"]
        
        # 根据分析类型选择对应的分析级别
        analysis_level_map = {
            "professional": "professional",
            "academic": "academic", 
            "business": "business"
        }
        
        analysis_level = analysis_level_map.get(req.analysis_type, "professional")
        
        # 流式生成专业分析
        for token in summarizer.summarize_stream(full_text, req.language, analysis_level):
            yield ServerSentEvent(
                raw_data=json.dumps({"token": token, "type": "analysis"}, ensure_ascii=False),
                event="analysis",
            )
        
        # 生成详细思维导图
        mindmap = await loop.run_in_executor(
            None, summarizer.generate_mindmap, full_text, req.language, "detailed"
        )
        
        yield ServerSentEvent(
            raw_data=json.dumps({"markdown": mindmap}, ensure_ascii=False),
            event="mindmap",
        )
        
        # 完成
        yield ServerSentEvent(
            raw_data=json.dumps({
                "message": "分析完成",
                "analysis_type": req.analysis_type,
                "remaining": permission.get("remaining", "无限")
            }, ensure_ascii=False),
            event="complete",
        )
        
        yield ServerSentEvent(raw_data="[DONE]", event="done")
        
    except Exception as e:
        yield ServerSentEvent(
            raw_data=json.dumps({"message": f"分析失败: {str(e)}"}, ensure_ascii=False),
            event="error",
        )


@router.post("/study-notes")
async def generate_study_notes(
    req: StudyNotesRequest,
    permission=Depends(require_ai_permission("study_notes"))
):
    """生成学习笔记"""
    user = permission["user"]
    
    try:
        loop = asyncio.get_event_loop()
        extractor = _get_extractor()
        summarizer = _get_summarizer()
        
        # 提取字幕
        subtitle_data = await loop.run_in_executor(
            None, extractor.extract, req.url
        )
        
        if not subtitle_data["has_subtitle"]:
            raise HTTPException(status_code=400, detail="该视频没有可用的字幕，无法生成学习笔记")
        
        full_text = subtitle_data["full_text"]
        
        # 生成学习笔记
        study_notes = await loop.run_in_executor(
            None, summarizer.generate_study_notes, full_text, req.subject
        )
        
        return {
            "success": True,
            "data": {
                "notes": study_notes,
                "subject": req.subject,
                "language": req.language,
                "video_url": req.url
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成学习笔记失败: {str(e)}")


@router.post("/key-quotes")
async def extract_key_quotes(
    req: KeyQuotesRequest,
    permission=Depends(require_ai_permission("key_quotes"))
):
    """提取关键金句"""
    user = permission["user"]
    
    try:
        loop = asyncio.get_event_loop()
        extractor = _get_extractor()
        summarizer = _get_summarizer()
        
        # 提取字幕
        subtitle_data = await loop.run_in_executor(
            None, extractor.extract, req.url
        )
        
        if not subtitle_data["has_subtitle"]:
            raise HTTPException(status_code=400, detail="该视频没有可用的字幕，无法提取金句")
        
        full_text = subtitle_data["full_text"]
        
        # 提取金句
        key_quotes = await loop.run_in_executor(
            None, summarizer.extract_key_quotes, full_text
        )
        
        # 限制数量
        if len(key_quotes) > req.max_quotes:
            key_quotes = key_quotes[:req.max_quotes]
        
        return {
            "success": True,
            "data": {
                "quotes": key_quotes,
                "total_found": len(key_quotes),
                "max_quotes": req.max_quotes,
                "video_url": req.url
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提取关键金句失败: {str(e)}")