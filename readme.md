# DocMind 3.2

## 环境要求
- Python 3.9+
- Node.js 16+
- DashScope Qwen API Key（免费额度足够）

# 1. 克隆项目（假设你已保存为 DocMind-3.0）
git clone <your-repo>  # 或直接解压我给你的包

# 2. 安装依赖（建议使用虚拟环境）
pip install -r api/requirements.txt

# 3. 启动后端
cd backend
记得在backend下面有个.env文件，请把里面两行代码等号右边替换成千问平台的api【免费】
uvicorn main:app --reload --port 8000

# 4. 启动前端（另开终端）
cd frontend
npm install
npm run dev

# 5. 访问 http://localhost:5173
# 上传 data/ 中的任意文件，即可看到：
#   - 解析结果
#   - Agent 分析过程
#   - 思维导图 + 知识图谱
#   - 智能问答 + 评估报告

# 6. 项目文件介绍
# --backend   ==》后端文件
    -agents     ==》调用multi-agent的相关代码
    -knowledge  ==》抽取出知识框架的相关代码
    -models     ==》下载一些模型文件，因为pip网络原因下不下来，直接部署到本地
    -parsers    ==》进行多模态文件解析
    -rag        ==》调用rag进行检索
    -upload     ==》每次在前端上传文件的时候都会传到这里，建议定时清理，不然测试过程中项目体积越来越大
    -utils      ==》一些配置文件



# --frontend   ==》前端文件（使用vue进行构建页面）
    -src    ==》前端页面的代码
      -components/FileUploader.vue       ==>前端主页面最上头的上传文件组件
      -components/KnowledgeGraph.vue     ==>知识图谱的组件
      -components/mindmap.vue            ==》思维导图的组件
      
# .env中修改自己的千问api

