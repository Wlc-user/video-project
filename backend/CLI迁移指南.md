# CLI 迁移指南：从 Web 界面到命令行

## 概述

本指南旨在帮助用户从 Web 界面逐步过渡到命令行 (CLI) 操作，保留原有搜索引擎功能的同时，提高工作效率和自动化能力。

## 为什么要迁移到 CLI？

### 优势对比

| 功能 | Web 界面 | CLI 工具 | 优势 |
|------|----------|----------|------|
| **视频解析** | 需要浏览器访问，填写表单 | 一键命令：`videodl parse <URL>` | 速度快，可脚本化 |
| **视频下载** | 点击下载按钮，等待页面刷新 | 直接命令：`videodl download <URL>` | 后台运行，不占用浏览器 |
| **批量处理** | 逐个文件上传 | 批量命令：`videodl batch ./videos/` | 自动化，高效 |
| **AI 分析** | 上传后等待结果 | 命令直接分析：`videodl analyze <视频>` | 实时进度显示 |
| **集成到工作流** | 手动操作 | 可集成到脚本、定时任务 | 自动化流程 |
| **资源占用** | 较高（浏览器内存） | 极低（终端） | 节省系统资源 |

## 三步迁移计划

### 阶段一：并行使用（1-2周）

#### Web 界面继续使用
- 保持访问 `http://localhost:8000`
- 使用原有上传、分析功能

#### CLI 工具初次尝试
1. **安装 CLI 工具**
   ```bash
   cd backend
   # 确保有执行权限（Windows不需要）
   ```

2. **尝试基础命令**
   ```bash
   # 检查服务状态
   python cli_enhanced.py status
   
   # 测试视频解析
   python cli_enhanced.py parse https://www.youtube.com/watch?v=dQw4w9WgXcQ
   
   # 查看支付套餐
   python cli_enhanced.py plans
   ```

3. **创建快捷方式**
   ```bash
   # Windows: 创建快捷命令
   # 在 backend 目录创建 videodl.bat
   @echo off
   python cli_enhanced.py %*
   
   # 然后可以通过 videodl 命令调用
   videodl status
   videodl parse <URL>
   ```

### 阶段二：逐步替代（2-4周）

#### 将常用功能迁移到 CLI

1. **视频下载任务**
   ```bash
   # 之前：浏览器访问 -> 填写URL -> 点击下载
   # 现在：一键命令
   videodl download https://www.bilibili.com/video/BV1GJ411x7h7
   ```

2. **批量分析视频**
   ```bash
   # 之前：逐个上传 -> 等待 -> 查看结果
   # 现在：批量处理
   videodl batch ./videos/ --action analyze
   ```

3. **自动化脚本示例**
   ```bash
   # download_scripts.bat (Windows)
   @echo off
   echo 开始批量下载任务...
   
   videodl download https://youtube.com/watch?v=xxx
   videodl download https://bilibili.com/video/BVyyy
   videodl download https://douyin.com/video/zzz
   
   echo 任务完成！
   pause
   ```

4. **结合原有搜索引擎**
   ```bash
   # 搜索 -> 解析 -> 下载 完整流程
   # 1. 搜索视频（使用原有搜索引擎）
   # 2. 复制视频URL
   # 3. CLI一键下载
   videodl download <复制的URL>
   ```

### 阶段三：完全 CLI 化（4周后）

#### 高级 CLI 使用技巧

1. **命令别名设置**
   ```bash
   # Windows PowerShell 配置文件 ($PROFILE)
   function vd { python "E:\pyspace\free-video-downloader-master\backend\cli_enhanced.py" @args }
   
   # 使用示例
   vd status
   vd parse <URL>
   vd upload <文件>
   ```

2. **集成到系统 PATH**
   ```powershell
   # 添加到系统环境变量
   # 1. 复制 cli_enhanced.py 到系统目录
   # 2. 或创建 bat 文件到 PATH 目录
   
   # 创建 C:\Users\YourName\bin\videodl.bat
   @echo off
   python "E:\pyspace\free-video-downloader-master\backend\cli_enhanced.py" %*
   ```

3. **自动化工作流**
   ```bash
   # 每日自动下载任务脚本
   # daily_download.bat
   @echo off
   set DATE=%date%
   echo %DATE% 开始执行视频下载任务...
   
   cd /d E:\pyspace\free-video-downloader-master\backend
   
   # 下载今日热门视频
   python cli_enhanced.py download https://youtube.com/watch?v=video1
   python cli_enhanced.py download https://youtube.com/watch?v=video2
   python cli_enhanced.py download https://youtube.com/watch?v=video3
   
   # 批量分析下载的视频
   python cli_enhanced.py batch ..\downloads\ --action analyze
   
   echo 任务执行完成！
   ```

4. **与原有系统集成**
   ```bash
   # 示例：下载后自动转存到NAS
   videodl download <URL> && copy 下载的文件 \\NAS\Videos\
   
   # 示例：分析后自动生成报告
   videodl analyze <视频> > analysis_report.txt
   ```

## CLI 工具完整命令参考

### 基础命令
```bash
# 检查服务状态
videodl status

# 解析视频信息
videodl parse <视频URL>

# 下载视频
videodl download <视频URL> [--format <格式>]

# 上传视频
videodl upload <视频文件路径>

# AI分析视频
videodl analyze <视频文件或ID>

# 视频摘要
videodl summarize <视频URL> [--level <详细程度>]
```

### 批量处理
```bash
# 批量分析目录中所有视频
videodl batch <目录路径> --action analyze

# 批量上传目录中所有视频
videodl batch <目录路径> --action upload
```

### 商业功能
```bash
# 查看支付套餐
videodl plans

# 查看用户统计
# (需要结合API)

# 工业级模板
videodl industrial templates
```

### 高级功能
```bash
# 获取视频直链
# (需要API支持)

# 批量工业级处理
# (需要API支持)
```

## 常见问题解答

### Q1: CLI 工具和 Web 界面功能一样吗？
**A:** 完全一样！CLI 工具调用的是同样的 API 接口，只是操作方式不同。

### Q2: 如何同时使用两者？
**A:** 可以同时运行 Web 服务和 CLI 工具，它们共享同一个数据库和后端。

### Q3: CLI 工具的进度显示在哪里？
**A:** 在命令行中实时显示，包括下载进度、分析进度等。

### Q4: 如何查看 CLI 命令的历史记录？
**A:** 使用 PowerShell 或 CMD 的历史功能，或重定向输出到日志文件：
```bash
videodl batch ./videos/ > batch_log.txt 2>&1
```

### Q5: 如何恢复 Web 界面操作？
**A:** 随时可以！CLI 工具不会影响 Web 界面，两者可以随时切换。

## 效率提升示例

### 场景：下载并分析 10 个视频

**Web 界面方式：**
1. 打开浏览器 → 访问网站
2. 输入第一个 URL → 点击解析 → 点击下载（等待）
3. 输入第二个 URL → 重复...
4. 上传第一个视频 → 等待分析 → 查看结果
5. 上传第二个视频 → 重复...
6. **总时间：约 30-40 分钟**

**CLI 方式：**
```bash
# 1. 批量下载
videodl download URL1
videodl download URL2
...（可以并行执行）

# 2. 批量分析
videodl batch ./downloads/ --action analyze

# 总时间：约 10-15 分钟（节省 50-75%）
```

## 进阶技巧

### 1. 创建命令快捷脚本
```batch
:: quick_download.bat
@echo off
if "%1"=="" (
    echo 使用方法: quick_download <URL>
    exit /b 1
)

echo 开始下载: %1
python cli_enhanced.py download %1
echo 下载完成！
```

### 2. 集成到任务计划
```batch
:: scheduled_task.bat - 每日凌晨执行
@echo off
cd /d E:\pyspace\free-video-downloader-master\backend
python cli_enhanced.py batch ..\daily_videos\ --action analyze
```

### 3. 使用配置文件
```python
# config.py - 配置文件示例
API_URL = "http://localhost:8000"
DOWNLOAD_DIR = "E:/Videos/Downloads"
LOG_FILE = "videodl.log"
```

## 总结

CLI 工具提供了更高效、更灵活的操作方式，特别适合：
- **批量处理**大量视频
- **自动化**重复任务
- **集成**到现有工作流
- **节省**系统资源

通过三阶段迁移计划，您可以平稳过渡到 CLI 操作，同时保留随时返回 Web 界面的灵活性。

**开始迁移吧！从今天尝试第一个 CLI 命令开始：**
```bash
cd backend
python cli_enhanced.py status
```