#!/bin/bash
# AI Native升级部署测试脚本

echo "🚀 开始部署AI Native升级版本"

# 步骤1: 检查环境
echo "📋 步骤1: 检查Python环境"
python --version
pip --version

# 步骤2: 安装依赖
echo "📦 步骤2: 安装依赖"
pip install python-dateutil stripe
pip install -r requirements.txt

# 步骤3: 初始化数据库
echo "🗃️ 步骤3: 初始化数据库"
python -c "
from database import init_db
init_db()
print('✅ 数据库初始化完成')
"

# 步骤4: 配置环境变量
echo "⚙️ 步骤5: 检查环境变量配置"
if [ ! -f ".env" ]; then
    echo "⚠️ 警告: .env文件不存在，创建示例配置"
    cat > .env.example << 'EOF'
# DeepSeek AI API Key
DEEPSEEK_API_KEY=sk-your-deepseek-api-key

# JWT密钥
JWT_SECRET=your-jwt-secret-change-in-production

# Stripe支付配置
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_signing_secret
STRIPE_PRICE_ID_MONTHLY=price_your_monthly_price_id
STRIPE_PRICE_ID_PROFESSIONAL_MONTHLY=price_your_professional_monthly_price_id
STRIPE_PRICE_ID_PROFESSIONAL_YEARLY=price_your_professional_yearly_price_id

# 前端URL
FRONTEND_URL=http://localhost:5173
EOF
    echo "📝 请复制.env.example为.env并填写实际配置"
else
    echo "✅ .env文件已存在"
fi

# 步骤5: 启动服务
echo "🚀 步骤6: 启动FastAPI服务"
echo "启动命令: uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "📊 测试端点:"
echo "1. 健康检查: http://localhost:8000/api/health"
echo "2. 用户注册: POST http://localhost:8000/api/auth/register"
echo "3. 基础总结: POST http://localhost:8000/api/summarize"
echo "4. 专业分析: POST http://localhost:8000/api/analyze/professional"
echo "5. 支付套餐: GET http://localhost:8000/api/payment/plans"
echo ""
echo "💡 小步快跑建议:"
echo "1. 先上线基础功能验证稳定性"
echo "2. 邀请10个核心用户测试专业功能"
echo "3. 收集反馈，快速迭代"
echo "4. 一周后评估付费转化率"

echo ""
echo "✅ 部署准备完成！开始你的AI Native之旅吧！"