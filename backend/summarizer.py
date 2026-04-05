"""AI 视频总结模块：字幕提取 + DeepSeek 大模型总结"""

import json
import os
import re
import tempfile
from typing import Optional

import httpx
import yt_dlp
from openai import OpenAI


def _is_bilibili_url(url: str) -> bool:
    return "bilibili.com" in url or "b23.tv" in url


class SubtitleExtractor:
    """从视频 URL 提取平台字幕（人工字幕 > 自动字幕）"""

    PREFERRED_LANGS = ["zh-Hans", "zh", "zh-CN", "en", "ja", "ko"]
    SUBTITLE_FORMAT = "json3"

    def extract(self, url: str) -> dict:
        """
        提取视频字幕，返回:
        {
            "has_subtitle": bool,
            "language": str,
            "subtitle_type": "manual" | "auto" | "none",
            "segments": [{"start": float, "end": float, "text": str}, ...],
            "full_text": str
        }
        """
        if _is_bilibili_url(url):
            result = self._extract_bilibili(url)
            if result["has_subtitle"]:
                return result

        info = self._get_video_info(url)

        manual_subs = info.get("subtitles") or {}
        auto_subs = info.get("automatic_captions") or {}

        manual_subs = {k: v for k, v in manual_subs.items() if k != "danmaku"}

        lang, sub_url, sub_type = self._pick_best_subtitle(manual_subs, auto_subs)
        if not sub_url:
            return {
                "has_subtitle": False,
                "language": "",
                "subtitle_type": "none",
                "segments": [],
                "full_text": "",
            }

        segments = self._download_and_parse(url, lang, sub_type)

        full_text = " ".join(seg["text"] for seg in segments)

        return {
            "has_subtitle": True,
            "language": lang,
            "subtitle_type": sub_type,
            "segments": segments,
            "full_text": full_text,
        }

    def _extract_bilibili(self, url: str) -> dict:
        """B 站专用字幕提取（通过 dm/view API 获取 CC 字幕和 AI 字幕）"""
        empty = {
            "has_subtitle": False, "language": "", "subtitle_type": "none",
            "segments": [], "full_text": "",
        }
        try:
            bvid = self._parse_bvid(url)
            if not bvid:
                return empty

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": f"https://www.bilibili.com/video/{bvid}",
            }

            view_resp = httpx.get(
                f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
                headers=headers, timeout=15,
            )
            view_data = view_resp.json().get("data", {})
            cid = view_data.get("cid")
            aid = view_data.get("aid")
            if not cid or not aid:
                return empty

            dm_resp = httpx.get(
                f"https://api.bilibili.com/x/v2/dm/view?aid={aid}&oid={cid}&type=1",
                headers=headers, timeout=15,
            )
            dm_data = dm_resp.json().get("data", {})
            subtitle_list = dm_data.get("subtitle", {}).get("subtitles", [])

            if not subtitle_list:
                return empty

            best = subtitle_list[0]
            for s in subtitle_list:
                lang = s.get("lan", "")
                if lang == "zh" or lang == "zh-Hans":
                    best = s
                    break

            sub_type = "auto" if best.get("lan", "").startswith("ai-") else "manual"

            sub_url = best.get("subtitle_url", "")
            if sub_url.startswith("//"):
                sub_url = "https:" + sub_url
            if sub_url.startswith("http://"):
                sub_url = "https://" + sub_url[7:]

            if not sub_url:
                return empty

            sub_resp = httpx.get(sub_url, headers=headers, timeout=15)
            sub_json = sub_resp.json()
            body = sub_json.get("body", [])

            segments = []
            for item in body:
                content = item.get("content", "").strip()
                if not content:
                    continue
                segments.append({
                    "start": round(item.get("from", 0), 2),
                    "end": round(item.get("to", 0), 2),
                    "text": content,
                })

            full_text = " ".join(seg["text"] for seg in segments)
            return {
                "has_subtitle": True,
                "language": best.get("lan", "zh"),
                "subtitle_type": sub_type,
                "segments": segments,
                "full_text": full_text,
            }
        except Exception:
            return empty

    @staticmethod
    def _parse_bvid(url: str) -> Optional[str]:
        m = re.search(r"(BV[a-zA-Z0-9]+)", url)
        return m.group(1) if m else None

    def _get_video_info(self, url: str) -> dict:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extract_flat": False,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError("无法解析该视频链接")
        return info

    def _pick_best_subtitle(
        self, manual_subs: dict, auto_subs: dict
    ) -> tuple[str, Optional[str], str]:
        """按优先级选择最佳字幕，返回 (lang, url, type)"""
        for lang in self.PREFERRED_LANGS:
            if lang in manual_subs:
                formats = manual_subs[lang]
                url = self._get_format_url(formats)
                if url:
                    return lang, url, "manual"

        for lang in self.PREFERRED_LANGS:
            if lang in auto_subs:
                formats = auto_subs[lang]
                url = self._get_format_url(formats)
                if url:
                    return lang, url, "auto"

        if manual_subs:
            first_lang = next(iter(manual_subs))
            url = self._get_format_url(manual_subs[first_lang])
            if url:
                return first_lang, url, "manual"

        if auto_subs:
            first_lang = next(iter(auto_subs))
            url = self._get_format_url(auto_subs[first_lang])
            if url:
                return first_lang, url, "auto"

        return "", None, "none"

    @staticmethod
    def _get_format_url(formats: list) -> Optional[str]:
        preferred = ["json3", "srv3", "vtt", "ttml"]
        for pref in preferred:
            for fmt in formats:
                if fmt.get("ext") == pref:
                    return fmt.get("url")
        return formats[0].get("url") if formats else None

    def _download_and_parse(self, url: str, lang: str, sub_type: str) -> list[dict]:
        """通过 yt-dlp 下载字幕文件并解析为分段列表"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "skip_download": True,
                "writesubtitles": sub_type == "manual",
                "writeautomaticsub": sub_type == "auto",
                "subtitleslangs": [lang],
                "subtitlesformat": "vtt",
                "outtmpl": os.path.join(tmp_dir, "subtitle"),
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            vtt_files = [
                f for f in os.listdir(tmp_dir) if f.endswith(".vtt")
            ]
            if not vtt_files:
                return []

            vtt_path = os.path.join(tmp_dir, vtt_files[0])
            return self._parse_vtt(vtt_path)

    @staticmethod
    def _parse_vtt(filepath: str) -> list[dict]:
        """解析 VTT 字幕文件为结构化分段"""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        segments = []
        blocks = re.split(r"\n\n+", content)
        time_pattern = re.compile(
            r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})"
        )

        seen_texts = set()
        for block in blocks:
            lines = block.strip().split("\n")
            time_match = None
            text_lines = []
            for line in lines:
                m = time_pattern.search(line)
                if m:
                    time_match = m
                elif time_match and line.strip() and not line.strip().isdigit():
                    clean = re.sub(r"<[^>]+>", "", line.strip())
                    if clean:
                        text_lines.append(clean)

            if time_match and text_lines:
                text = " ".join(text_lines)
                if text in seen_texts:
                    continue
                seen_texts.add(text)

                start = _time_to_seconds(time_match.group(1))
                end = _time_to_seconds(time_match.group(2))
                segments.append({
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "text": text,
                })

        return segments


class VideoSummarizer:
    """AI视频分析引擎 - 提供基础到专业的视频理解服务"""

    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY 环境变量未设置")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
        self.model = "deepseek-chat"

    def summarize_stream(self, subtitle_text: str, language: str = "zh", analysis_level: str = "basic", segments: list = None):
        """流式生成视频总结，支持不同分析深度"""
        if analysis_level == "basic":
            prompt = self._build_summary_prompt(subtitle_text, language, segments)
        elif analysis_level == "professional":
            prompt = self._build_professional_analysis_prompt(subtitle_text, language)
        elif analysis_level == "academic":
            prompt = self._build_academic_analysis_prompt(subtitle_text, language)
        elif analysis_level == "business":
            prompt = self._build_business_analysis_prompt(subtitle_text, language)
        else:
            prompt = self._build_summary_prompt(subtitle_text, language)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._get_system_prompt(analysis_level)},
                {"role": "user", "content": prompt},
            ],
            stream=True,
            temperature=0.7,
            max_tokens=4096,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    def generate_mindmap(self, subtitle_text: str, language: str = "zh", style: str = "standard") -> str:
        """生成思维导图 Markdown（支持不同风格）"""
        if style == "detailed":
            prompt = self._build_detailed_mindmap_prompt(subtitle_text, language)
        else:
            prompt = self._build_mindmap_prompt(subtitle_text, language)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个专业的思维导图生成助手，擅长将内容组织为清晰的层级结构。"},
                {"role": "user", "content": prompt},
            ],
            stream=False,
            temperature=0.5,
            max_tokens=4096,
        )
        return response.choices[0].message.content

    def chat_stream(self, subtitle_text: str, question: str, context_mode: str = "basic"):
        """基于视频内容的 AI 问答（支持不同上下文模式）"""
        if context_mode == "deep":
            system_prompt = "你是一个资深视频内容专家，能够结合专业知识背景进行深度分析和推理。"
        elif context_mode == "critical":
            system_prompt = "你是一个批判性思维专家，能够识别视频内容的逻辑漏洞、未明假设和潜在偏见。"
        else:
            system_prompt = "你是一个视频内容问答助手。根据提供的视频字幕内容来回答用户的问题。如果问题超出视频内容范围，请诚实告知。"
        
        prompt = self._build_chat_prompt(subtitle_text, question)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            stream=True,
            temperature=0.7,
            max_tokens=2048,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
    
    def generate_study_notes(self, subtitle_text: str, subject: str = "general") -> str:
        """生成学习笔记（专业功能）"""
        prompt = self._build_study_notes_prompt(subtitle_text, subject)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个专业的教育内容设计者，擅长将视频内容转化为结构化的学习材料。"},
                {"role": "user", "content": prompt},
            ],
            stream=False,
            temperature=0.6,
            max_tokens=3072,
        )
        return response.choices[0].message.content
    
    def extract_key_quotes(self, subtitle_text: str) -> list:
        """提取关键金句（专业功能）"""
        prompt = self._build_key_quotes_prompt(subtitle_text)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个内容摘录专家，擅长从视频中提取有洞察力、有启发性的金句。"},
                {"role": "user", "content": prompt},
            ],
            stream=False,
            temperature=0.5,
            max_tokens=2048,
        )
        return self._parse_quotes_response(response.choices[0].message.content)

    @staticmethod
    def _get_system_prompt(analysis_level: str) -> str:
        """根据分析级别返回系统提示"""
        prompts = {
            "basic": "你是一个专业的视频内容分析助手，擅长提取关键信息并生成结构化的总结。",
            "professional": "你是一个资深视频分析师，具有多领域专业知识。你需要对视频内容进行深度分析，识别知识结构、逻辑脉络和潜在价值。",
            "academic": "你是学术研究专家，擅长分析学术讲座、研究论文视频。你需要识别研究方法、核心论点、数据证据和学术贡献。",
            "business": "你是商业分析师，擅长分析商业演讲、产品发布会、市场分析视频。你需要识别市场机会、竞争策略、商业模式和风险点。"
        }
        return prompts.get(analysis_level, prompts["basic"])

    @staticmethod
    def _build_summary_prompt(subtitle_text: str, language: str) -> str:
        """深度总结提示词"""
        truncated = subtitle_text[:15000]
        lang_hint = "中文" if language.startswith("zh") else "与原文相同的语言"
        return f"""你是一个专业的视频内容分析师。请对以下视频进行深度、多维度的内容分析，使用{lang_hint}输出。

【重要原则】
- 不要只做表层总结，要挖掘深层含义和价值
- 每个观点都要有具体内容支撑
- 区分"说了什么"和"意味着什么"
- 识别视频的独到见解和个人观点

【必须输出的分析维度】

## 视频核心主题
用一句话精准概括视频最核心要表达的观点或解决的问题，不超过25字。

## 目标受众与价值
- **主要受众**：谁最适合观看这个视频？
- **核心价值**：观众能获得什么具体收益？
- **前置知识**：观看前需要了解什么？

## 内容难度评级
- **难度等级**：（入门/进阶/高级/专家）给出理由
- **信息密度**：低/中/高
- **实用性**：低/中/高（有多少可直接应用的内容）

## 章节详细解析
按视频顺序逐段分析，每段包含：
- **时间区间**：如 0:00-2:30
- **讲述内容**：具体说了什么
- **核心要点**：这段的关键信息
- **重要程度**：1-5星打分

## 深度洞察
1. **独特观点**：视频有哪些独到见解？
2. **隐藏信息**：有哪些没有明说但重要的内容？
3. **知识关联**：与哪些领域相关联？

## 关键知识点
列出视频中最重要的5-10个具体知识点，每个包含：
- 知识点名称
- 一句话解释
- 实际应用场景

## 核心金句
选出3-5句最值得记住的原话，说明为什么重要

## 总结与延伸
- 一句话总结
- 推荐哪些人一定要看？
- 延伸学习方向建议

---
视频字幕内容：
{truncated}"""

    @staticmethod
    def _build_professional_analysis_prompt(subtitle_text: str, language: str) -> str:
        """专业深度分析提示词"""
        truncated = subtitle_text[:15000]
        lang_hint = "中文" if language.startswith("zh") else "与原文相同的语言"
        return f"""请对以下视频内容进行专业级深度分析，使用{lang_hint}输出。

要求：
## 一、深度内容解构
1. **内容架构分析**：识别视频的叙事结构、逻辑层次
2. **知识体系拆解**：将内容分解为可复用的知识点单元
3. **观点与论证分析**：识别核心观点、支持论据、论证逻辑

## 二、价值洞察
1. **信息密度评估**：评估每分钟有效信息量
2. **学习曲线分析**：内容的难易度分布和学习路径
3. **实践指导价值**：可操作的建议和具体应用场景

## 三、结构化输出
- 使用清晰的层级结构
- 每个分析点要有具体的时间戳参考（如"3:15-5:20"）
- 区分事实描述和推理分析

---
视频字幕内容：
{truncated}"""

    @staticmethod
    def _build_academic_analysis_prompt(subtitle_text: str, language: str) -> str:
        """学术分析提示词"""
        truncated = subtitle_text[:15000]
        lang_hint = "中文" if language.startswith("zh") else "与原文相同的语言"
        return f"""请对以下学术视频内容进行专业分析，使用{lang_hint}输出。

要求：
## 一、研究内容分析
1. **研究问题**：明确的研究问题和假设
2. **研究方法**：研究设计、数据收集、分析方法
3. **研究发现**：核心研究结果和数据证据
4. **理论贡献**：对现有理论的补充或挑战

## 二、学术价值评估
1. **创新性**：研究的原创性和新颖性
2. **严谨性**：方法的科学性和严谨程度
3. **影响力**：对领域的影响和实际应用价值
4. **局限性**：研究的局限性和未来方向

## 三、结构化笔记
- 按学术论文结构组织（引言、方法、结果、讨论）
- 提取关键公式、数据、图表信息
- 标注参考文献和进一步阅读建议

---
视频字幕内容：
{truncated}"""

    @staticmethod
    def _build_business_analysis_prompt(subtitle_text: str, language: str) -> str:
        """商业分析提示词"""
        truncated = subtitle_text[:15000]
        lang_hint = "中文" if language.startswith("zh") else "与原文相同的语言"
        return f"""请对以下商业视频内容进行分析，使用{lang_hint}输出。

要求：
## 一、商业内容分析
1. **商业模式**：盈利模式、价值主张、客户细分
2. **市场分析**：市场规模、竞争格局、增长趋势
3. **产品策略**：产品特点、差异化优势、定价策略
4. **营销策略**：目标受众、渠道策略、推广方式

## 二、投资与风险评估
1. **机会识别**：市场机会、增长潜力、竞争优势
2. **风险评估**：市场风险、竞争风险、执行风险
3. **财务评估**：收入模型、成本结构、盈利预测
4. **团队评估**：创始人背景、团队能力、执行力

## 三、行动建议
- SWOT分析（优势、劣势、机会、威胁）
- 具体行动步骤和优先顺序
- 关键指标和成功标准

---
视频字幕内容：
{truncated}"""

    @staticmethod
    def _build_mindmap_prompt(subtitle_text: str, language: str) -> str:
        truncated = subtitle_text[:15000]
        lang_hint = "中文" if language.startswith("zh") else "与原文相同的语言"
        return f"""请将以下视频字幕内容整理为思维导图结构，使用{lang_hint}输出。

要求：
1. 使用 Markdown 标题层级格式（# 一级标题，## 二级标题，### 三级标题）
2. 最外层是视频主题
3. 第二层是主要章节/模块
4. 第三层是各章节的要点
5. 可以有第四层做更细的展开
6. 每个节点的文字要简洁精炼
7. 只输出 Markdown 内容，不要其他说明文字

---
视频字幕内容：
{truncated}"""

    @staticmethod
    def _build_chat_prompt(subtitle_text: str, question: str) -> str:
        truncated = subtitle_text[:12000]
        return f"""以下是一个视频的字幕内容，请根据这些内容回答用户的问题。

视频字幕内容：
{truncated}

---
用户问题：{question}

请基于视频内容给出准确、详细的回答。如果视频内容中没有相关信息，请诚实说明。"""

    @staticmethod
    def _build_detailed_mindmap_prompt(subtitle_text: str, language: str) -> str:
        """详细思维导图提示词"""
        truncated = subtitle_text[:12000]
        lang_hint = "中文" if language.startswith("zh") else "与原文相同的语言"
        return f"""请将以下视频内容整理为详细的思维导图结构，使用{lang_hint}输出。

要求：
1. 深度层级结构（可到5级标题）
2. 每个节点包含具体的事实、数据或观点
3. 标注重要的时间戳参考
4. 识别内容之间的逻辑关系
5. 区分主要内容和细节补充
6. 使用标准的Markdown格式

---
视频字幕内容：
{truncated}"""

    @staticmethod
    def _build_study_notes_prompt(subtitle_text: str, subject: str) -> str:
        """学习笔记提示词"""
        truncated = subtitle_text[:12000]
        subject_hint = f"{subject}领域" if subject != "general" else "通用"
        return f"""请将以下视频内容整理为专业的学习笔记，针对{subject_hint}学习者。

要求格式：
## 学习目标
- 列出本视频需要掌握的核心知识点

## 重点概念
- 关键术语定义和解释
- 重要公式、原理、定理

## 学习要点
1. 每个知识点包含：
   - 核心内容
   - 应用示例
   - 易错提醒

## 练习题
- 基于视频内容的思考题
- 自我检测题目

## 拓展阅读
- 相关概念链接
- 深入学习的参考资料

---
视频字幕内容：
{truncated}"""

    @staticmethod
    def _build_key_quotes_prompt(subtitle_text: str) -> str:
        """关键金句提取提示词"""
        truncated = subtitle_text[:10000]
        return f"""请从以下视频内容中提取最有价值、最有洞察力的5-8个关键金句。

要求：
1. 每个金句要有完整性和独立性
2. 按重要性排序
3. 标注大致的时间位置（如"约10:25处"）
4. 简要说明为什么这个金句重要
5. 输出格式：
   - **时间**: [时间位置]
   - **内容**: [金句文本]
   - **价值**: [为什么重要]

---
视频字幕内容：
{truncated}"""

    @staticmethod
    def _parse_quotes_response(response_text: str) -> list:
        """解析金句响应"""
        quotes = []
        lines = response_text.strip().split('\n')
        
        current_quote = {}
        for line in lines:
            line = line.strip()
            if line.startswith('- **时间**:'):
                current_quote['time'] = line.replace('- **时间**:', '').strip()
            elif line.startswith('- **内容**:'):
                current_quote['content'] = line.replace('- **内容**:', '').strip()
            elif line.startswith('- **价值**:'):
                current_quote['value'] = line.replace('- **价值**:', '').strip()
                if current_quote:
                    quotes.append(current_quote.copy())
                    current_quote = {}
        
        return quotes if quotes else [{"error": "未能提取到金句，请重试"}]


def _time_to_seconds(time_str: str) -> float:
    """将 HH:MM:SS.mmm 转为秒数"""
    parts = time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds
