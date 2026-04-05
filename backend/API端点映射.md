# 万能视频下载器 API 端点映射

## 核心视频功能
| 端点 | 方法 | 路径 | 功能 | 需要认证 |
|------|------|------|------|----------|
| 健康检查 | GET | `/api/health` | 服务状态检查 | 否 |
| 解析视频 | POST | `/api/parse` | 解析视频信息 | 否 |
| 下载视频 | POST | `/api/download` | 下载视频文件 | 否 |
| 获取直链 | POST | `/api/direct-url` | 获取视频直链 | 否 |
| 代理缩略图 | GET | `/api/proxy/thumbnail` | 绕过防盗链获取缩略图 | 否 |

## AI分析功能
| 端点 | 方法 | 路径 | 功能 | 需要认证 |
|------|------|------|------|----------|
| 视频摘要 | POST | `/api/summarize` | AI视频摘要（SSE流式） | 可选 |
| 视频问答 | POST | `/api/chat` | AI视频问答（SSE流式） | 可选 |
| 专业分析 | POST | `/api/professional` | 专业级视频分析 | 需要 |
| 学习笔记 | POST | `/api/study-notes` | 生成学习笔记 | 需要 |
| 关键语录 | POST | `/api/key-quotes` | 提取关键语录 | 需要 |

## 用户认证
| 端点 | 方法 | 路径 | 功能 | 需要认证 |
|------|------|------|------|----------|
| 用户注册 | POST | `/api/auth/register` | 新用户注册 | 否 |
| 用户登录 | POST | `/api/auth/login` | 用户登录 | 否 |
| 获取信息 | GET | `/api/auth/me` | 获取当前用户信息 | 需要 |
| 用户统计 | GET | `/api/auth/stats` | 获取用户使用统计 | 需要 |

## 支付系统
### 原支付系统
| 端点 | 方法 | 路径 | 功能 | 需要认证 |
|------|------|------|------|----------|
| 创建订单 | POST | `/api/payment/create-checkout` | 创建支付订单 | 需要 |
| Webhook | POST | `/api/payment/webhook` | Stripe webhook | 否 |
| 订单列表 | GET | `/api/payment/orders` | 获取用户订单 | 需要 |
| 套餐列表 | GET | `/api/payment/plans` | 获取所有套餐 | 否 |

### 安全支付系统（新增）
| 端点 | 方法 | 路径 | 功能 | 需要认证 |
|------|------|------|------|----------|
| 创建支付 | POST | `/api/secure/create` | 创建支付订单 | 可选 |
| 支付宝通知 | POST | `/api/secure/alipay/notify` | 支付宝webhook | 否 |
| 支付方式 | GET | `/api/secure/methods` | 获取支付方式 | 否 |
| 安全指南 | GET | `/api/secure/security/guide` | 资金安全指南 | 否 |
| 成功测试 | GET | `/api/secure/test/success` | 支付成功测试页 | 否 |

## 上传功能
### 极致精简上传
| 端点 | 方法 | 路径 | 功能 | 需要认证 |
|------|------|------|------|----------|
| 上传页面 | GET | `/api/upload` | 单文件HTML页面 | 否 |
| 上传视频 | POST | `/api/upload` | 上传并分析视频 | 否 |
| 系统统计 | GET | `/api/upload/stats` | 系统统计监控 | 否 |

### 其他上传模块
| 端点 | 方法 | 路径 | 功能 | 需要认证 |
|------|------|------|------|----------|
| 简单上传 | POST | `/api/simple` | 简单视频上传 | 否 |
| 测试表单 | GET | `/api/test-form` | 上传测试表单 | 否 |
| 快速指南 | GET | `/api/quick-guide` | 快速使用指南 | 否 |
| 格式支持 | GET | `/api/formats` | 支持格式列表 | 否 |
| 视频上传 | POST | `/api/video` | 视频分析上传 | 可选 |

## 工业级功能
### 模板系统
| 端点 | 方法 | 路径 | 功能 | 需要认证 |
|------|------|------|------|----------|
| 模板列表 | GET | `/api/industrial/templates` | 列出可用模板 | 否 |
| 批量分析 | POST | `/api/industrial/analyze/batch` | 批量分析处理 | 可选 |
| 创建模板 | POST | `/api/industrial/template/create` | 创建新模板 | 需要 |
| 运营统计 | GET | `/api/industrial/stats` | 工业化运营统计 | 否 |

### 商业模式
| 端点 | 方法 | 路径 | 功能 | 需要认证 |
|------|------|------|------|----------|
| 商业报告 | GET | `/api/business/report` | 工业化商业报告 | 否 |
| 复制计划 | GET | `/api/replication/plan` | 工业化复制计划 | 否 |
| 模板评估 | POST | `/api/template/evaluate` | 评估模板效果 | 需要 |

## AI统计功能
| 端点 | 方法 | 路径 | 功能 | 需要认证 |
|------|------|------|------|----------|
| AI统计 | GET | `/api/ai/stats` | AI使用统计 | 需要 |
| 使用历史 | GET | `/api/ai/usage-history` | AI使用历史 | 需要 |

## 专业版功能
| 端点 | 方法 | 路径 | 功能 | 需要认证 |
|------|------|------|------|----------|
| 专业功能 | GET | `/api/professional/features` | 专业版功能列表 | 否 |

## 静态文件服务
| 路径 | 类型 | 说明 |
|------|------|------|
| `/_videos` | 静态文件 | 视频存储目录 |
| `/docs` | Swagger UI | API文档页面 |

## CLI工具对应API
以下是CLI工具可以调用的主要API端点：
1. **视频解析** → `/api/parse`
2. **视频下载** → `/api/download` 
3. **视频上传** → `/api/upload` (精简版)
4. **AI分析** → `/api/professional` 或 `/api/analyze/{id}`
5. **视频摘要** → `/api/summarize`
6. **用户相关** → `/api/auth/*`
7. **支付相关** → `/api/secure/*`
8. **模板系统** → `/api/industrial/templates`
9. **批量处理** → `/api/industrial/analyze/batch`