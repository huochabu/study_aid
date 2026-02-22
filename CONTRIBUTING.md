# 贡献指南

感谢你对 study-ai 项目的关注！我们欢迎任何形式的贡献。

## 如何贡献

### 报告问题

如果你发现了 bug 或有功能建议：

1. 在 [Issues](https://github.com/huochabu/study_aid/issues) 页面搜索是否已有相同问题
2. 如果没有，创建新的 Issue，详细描述：
   - 问题和重现步骤
   - 期望的行为
   - 截图（如果适用）
   - 环境信息（操作系统、Python 版本等）

### 提交代码

#### 1. Fork 项目

点击 GitHub 页面右上角的 Fork 按钮

#### 2. 克隆你的 Fork

```bash
git clone https://github.com/huochabu/study_aid.git
cd study_aid
```

#### 3. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

#### 4. 进行修改

- 遵循现有代码风格
- 添加必要的测试
- 更新相关文档

#### 5. 提交修改

```bash
git add .
git commit -m "feat: 添加你的功能描述"
# 或
git commit -m "fix: 修复某个问题"
```

提交信息格式建议：
- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具相关

#### 6. 推送到你的 Fork

```bash
git push origin feature/your-feature-name
```

#### 7. 创建 Pull Request

1. 访问原项目的 GitHub 页面：https://github.com/huochabu/study_aid
2. 点击 "Pull Requests" → "New Pull Request"
3. 选择你的分支
4. 填写 PR 描述：
   - 说明你的修改内容
   - 关联相关 Issue（如果有）
   - 添加截图（如果适用）

## 开发规范

### 代码风格

#### Python（后端）
- 遵循 PEP 8 规范
- 使用类型注解
- 添加文档字符串

```python
def example_function(param1: str, param2: int) -> bool:
    """
    函数功能描述

    Args:
        param1: 参数1说明
        param2: 参数2说明

    Returns:
        返回值说明
    """
    pass
```

#### JavaScript/Vue（前端）
- 使用 Vue 3 组合式 API
- 遵循 ESLint 配置
- 组件命名使用 PascalCase
- 使用有意义的变量名

### 测试

- 为新功能添加测试
- 确保所有测试通过
- 测试覆盖率不应降低

### 文档

- 更新 README.md（如果需要）
- 为新功能添加注释
- 更新 API 文档

## 开发环境设置

### 后端开发

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

## 行为准则

- 尊重所有贡献者
- 使用包容性语言
- 接受建设性批评
- 关注对社区最有利的事情

## 许可证

通过贡献代码，你同意你的贡献将使用 MIT 许可证进行授权。

## 获取帮助

如果你有任何问题：
- 查看 [文档](readme.md)
- 搜索 [Issues](https://github.com/huochabu/study_aid/issues)
- 创建新的 Issue 或 Discussion

再次感谢你的贡献！
