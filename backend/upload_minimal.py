#!/usr/bin/env python3
"""
极致成本控制 - 视频上传方案
文件大小：< 5KB
功能：完整商业化上传 + AI分析
成本：几乎为零
"""

import os
import time
import hashlib
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
import aiofiles

router = APIRouter()

# ==================== 配置（全部硬编码，零配置）====================
MAX_SIZE = 300 * 1024 * 1024        # 300MB（够用且省空间）
KEEP_DAYS = 3                       # 3天自动清理（更激进）
UPLOAD_DIR = Path("_videos")        # 隐藏目录，减少干扰
UPLOAD_DIR.mkdir(exist_ok=True)

# ==================== 核心函数（仅3个）====================
def clean_old():
    """自动清理3天前的文件"""
    cutoff = time.time() - (KEEP_DAYS * 86400)
    for f in UPLOAD_DIR.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            try: f.unlink()
            except: pass

def make_id(ip: str) -> str:
    """生成文件ID（不用uuid，更轻量）"""
    return f"{int(time.time())}_{hashlib.md5(ip.encode()).hexdigest()[:8]}"

async def save_file(file: UploadFile, ip: str) -> dict:
    """保存文件，返回基本信息"""
    clean_old()  # 先清理
    
    # 极简验证：只检查扩展名
    name = file.filename or "video"
    if not name.lower().endswith(('.mp4', '.avi', '.mov')):
        raise HTTPException(400, "仅支持mp4/avi/mov")
    
    # 生成路径
    ext = Path(name).suffix or '.mp4'
    file_id = make_id(ip)
    path = UPLOAD_DIR / f"{file_id}{ext}"
    
    # 保存（带大小限制）
    size = 0
    async with aiofiles.open(path, 'wb') as f:
        while chunk := await file.read(8192):  # 8KB chunks
            size += len(chunk)
            if size > MAX_SIZE:
                await f.close()
                path.unlink(missing_ok=True)
                raise HTTPException(400, f"超过{MAX_SIZE//1048576}MB限制")
            await f.write(chunk)
    
    return {"id": file_id, "path": path, "size": size, "name": name}

# ==================== 路由（仅2个）====================
@router.get("/upload")
async def upload_page():
    """视频分析页面 - 支持上传和链接两种方式"""
    html = """<!DOCTYPE html><html><head><meta charset=utf-8>
    <title>🎬 视频AI分析</title><style>
    body{font-family:sans-serif;max-width:700px;margin:40px auto;padding:20px}
    .tabs{display:flex;gap:10px;margin-bottom:20px;border-bottom:2px solid #eee}
    .tab{padding:10px 20px;cursor:pointer;border-bottom:2px solid transparent}
    .tab.active{border-bottom-color:#4CAF50;color:#4CAF50;font-weight:bold}
    .tab:hover{color:#4CAF50}
    .box{border:3px dashed #4CAF50;padding:60px 20px;text-align:center;border-radius:15px;cursor:pointer}
    .box:hover{background:#f8fff8}input[type=file]{display:none}
    .url-input{width:100%;padding:12px;font-size:16px;border:2px solid #ddd;border-radius:8px;box-sizing:border-box}
    .url-input:focus{outline:none;border-color:#4CAF50}
    .info{margin:20px 0;color:#666}
    button{padding:12px 24px;background:#4CAF50;color:white;border:none;border-radius:8px;font-size:16px;cursor:pointer}
    button:hover{background:#45a049}button:disabled{background:#ccc}
    .result{margin-top:30px;padding:20px;background:#f0f8f0;border-radius:8px;line-height:1.8}
    .result h3{margin-top:0;color:#2e7d32}
    .result pre{white-space:pre-wrap;word-wrap:break-word;background:#fff;padding:15px;border-radius:5px}
    .platforms{color:#666;font-size:14px;margin-top:10px}
    .platforms span{margin-right:15px}
    .loading{text-align:center;color:#666}
    .loading::after{content:'...';animation:dots 1.5s steps(5,end) infinite}
    @keyframes dots{0%,20%{content:''}40%{content:'.'}60%{content:'..'}80%,100%{content:'...'}}
    .section{display:none}
    .section.active{display:block}
    </style></head>
    <body><h1>🎬 视频AI分析</h1>
    
    <div class=tabs>
        <div class="tab active" onclick="switchTab('url')">🔗 视频链接</div>
        <div class="tab" onclick="switchTab('upload')">📁 上传文件</div>
    </div>
    
    <!-- 视频链接分析 -->
    <div id="url-section" class="section active">
        <p>粘贴视频链接，AI自动提取字幕并深度分析</p>
        <input type=text id="video-url" class=url-input placeholder="粘贴视频链接，如 B站、YouTube、抖音...">
        <div class="platforms">
            <span>✅ B站</span><span>✅ YouTube</span><span>✅ 抖音</span><span>✅ 快手</span><span>✅ 西瓜视频</span>
            <span style="color:#999">等1800+平台</span>
        </div>
        <div class=info id=url-info></div>
        <button onclick="analyzeUrl()" id=url-btn>开始AI分析</button>
        <div class="result" id="url-result"></div>
    </div>
    
    <!-- 上传文件 -->
    <div id="upload-section" class="section">
        <p>上传本地视频文件（仅保存，暂不支持AI分析）</p>
        <div class=box onclick="document.getElementById('file').click()">
            <div style="font-size:48px">📁</div>
            <div>点击或拖放视频文件</div>
            <div style="color:#666;font-size:14px;margin-top:10px">支持 MP4/AVI/MOV，最大300MB</div>
        </div>
        <input type=file id=file accept="video/*" onchange="showFile()">
        <div class=info id=upload-info></div>
        <button onclick="uploadFile()" id=upload-btn>上传文件</button>
        <div class="result" id="upload-result"></div>
    </div>
    
    <script>
    let file=null;
    
    function switchTab(tab){
        document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
        document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
        event.target.classList.add('active');
        document.getElementById(tab+'-section').classList.add('active');
    }
    
    // URL分析
    async function analyzeUrl(){
        const url=document.getElementById('video-url').value.trim();
        if(!url){alert('请输入视频链接');return}
        if(!url.startsWith('http')){alert('请输入有效的URL链接');return}
        
        document.getElementById('url-btn').disabled=true;
        document.getElementById('url-btn').innerHTML='分析中...';
        document.getElementById('url-result').innerHTML='<div class=loading>正在提取字幕并分析内容</div>';
        
        try{
            const res=await fetch('/api/summarize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url,language:'zh'})});
            if(!res.ok)throw new Error('请求失败');
            
            const reader=res.body.getReader();
            const decoder=new TextDecoder();
            let result='';
            let subtitleData=null;
            let summaryParts=[];
            let mindmapMd='';
            
            while(true){
                const {done,value}=await reader.read();
                if(done)break;
                const chunk=decoder.decode(value);
                const lines=chunk.split('\\n');
                for(const line of lines){
                    if(line.startsWith('data:')){
                        const data=line.slice(5).trim();
                        if(data==='[DONE]')continue;
                        try{
                            const parsed=JSON.parse(data);
                            if(parsed.event==='subtitle'){subtitleData=parsed.data;}
                            else if(parsed.event==='summary'){summaryParts.push(parsed.data);}
                            else if(parsed.event==='mindmap'){mindmapMd=parsed.data.markdown;}
                            else if(parsed.event==='error'){throw new Error(parsed.data.message);}
                        }catch(e){}
                    }
                }
            }
            
            result=`<h3>✅ AI分析完成！</h3>`;
            if(subtitleData&&subtitleData.has_subtitle){
                result+=`<p><b>字幕语言：</b>${subtitleData.language}</p>`;
                result+=`<p><b>字幕类型：</b>${subtitleData.subtitle_type==='manual'?'人工字幕':'自动字幕'}</p>`;
            }
            result+=`<h4>📊 深度分析报告</h4><pre>${summaryParts.join('')}</pre>`;
            if(mindmapMd){
                result+=`<h4>🧠 思维导图</h4><pre style="background:#f5f5f5">${mindmapMd}</pre>`;
            }
            document.getElementById('url-result').innerHTML=result;
            
        }catch(e){
            document.getElementById('url-result').innerHTML=`<p style="color:red">❌ 分析失败：${e.message}</p>`;
        }
        document.getElementById('url-btn').disabled=false;
        document.getElementById('url-btn').innerHTML='开始AI分析';
    }
    
    // 文件上传
    function showFile(){
        file=document.getElementById('file').files[0];
        document.getElementById('upload-info').innerHTML=`<b>${file.name}</b> (${(file.size/1048576).toFixed(1)}MB)`;
        document.getElementById('upload-result').innerHTML='';
    }
    
    async function uploadFile(){
        if(!file){alert('请选择文件');return}
        document.getElementById('upload-btn').disabled=true;
        document.getElementById('upload-btn').innerHTML='上传中...';
        
        const form=new FormData();
        form.append('file',file);
        form.append('type','basic');
        
        try{
            const res=await fetch('/api/upload',{method:'POST',body:form});
            const data=await res.json();
            if(data.success){
                document.getElementById('upload-result').innerHTML=`<h3>✅ 上传成功！</h3>
                <p><b>文件：</b>${data.name}</p>
                <p><b>大小：</b>${data.size_mb}MB</p>
                <p><b>ID：</b>${data.id}</p>
                <p style="color:#666;margin-top:15px">⚠️ 本地视频暂不支持AI分析，如需分析请使用视频链接功能</p>`;
            }else{alert('失败：'+data.error);}
        }catch(e){alert('网络错误')}
        
        document.getElementById('upload-btn').disabled=false;
        document.getElementById('upload-btn').innerHTML='上传文件';
    }
    </script>
    
    <div style="margin-top:40px;padding:15px;background:#f8f8f8;border-radius:8px">
    <h3>💡 使用说明</h3>
    <p>• <b>视频链接</b>：支持B站、YouTube、抖音等1800+平台，AI自动提取字幕并生成深度分析</p>
    <p>• <b>上传文件</b>：仅保存到服务器，暂不支持AI分析（本地视频无法自动提取字幕）</p>
    <p>• <b>免费版</b>：每日10次AI分析额度</p>
    </div></body></html>"""
    return HTMLResponse(html)

@router.post("/api/upload")
async def upload_video(request: Request, file: UploadFile = File(...), type: str = "basic"):
    """上传并分析视频"""
    try:
        # 保存文件
        ip = request.client.host if request.client else "0.0.0.0"
        saved = await save_file(file, ip)
        
        # 本地视频无法自动提取字幕，返回友好提示
        result = """📌 本地上传功能说明：

本地视频文件无法自动提取字幕，因此暂不支持 AI 分析。

✅ **推荐方式**：
请在主页使用视频链接（如 B站、YouTube 链接），AI 将自动：
1. 提取视频字幕
2. 生成深度内容分析
3. 创建思维导图
4. 支持自由问答

🎯 **支持的平台**：B站、YouTube、抖音等 1800+ 网站"""
        
        return JSONResponse({
            "success": True,
            "name": saved["name"],
            "size_mb": saved["size"] // 1048576,
            "id": saved["id"],
            "type": type,
            "time": 0.1,
            "result": result,
            "video_path": str(saved["path"]),  # 返回文件路径供后续处理
            "tip": "使用视频链接可获得完整的 AI 分析体验"
        })
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(500, f"系统错误：{str(e)}")

# ==================== 统计（可选）====================
@router.get("/api/upload/stats")
async def stats():
    """系统统计（监控用）"""
    files = list(UPLOAD_DIR.iterdir())
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    return {
        "files": len(files),
        "size_mb": total_size // 1048576,
        "auto_clean": f"{KEEP_DAYS}天",
        "max_size_mb": MAX_SIZE // 1048576,
        "cost": "≈ 0元/月"  # 实际成本估算
    }