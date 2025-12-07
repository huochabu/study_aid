#!/bin/bash
echo "🚀 启动 DocMind 3.2..."

# 启动后端
cd backend
python main.py &

# 启动前端
cd ../frontend
npm install
npm run dev &

echo "✅ 服务已启动！"
echo "🌐 访问 http://localhost:5173"