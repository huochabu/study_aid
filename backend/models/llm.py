import os
import json
import logging
from typing import List, Dict
from dotenv import load_dotenv

# 从项目根目录加载.env文件
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# 导入study-aid现有的Qwen API客户端
from utils.qwen_client import call_qwen, async_call_qwen

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleLLM:
    """支持千问API的LLM类，集成到study-aid系统"""
    
    def __init__(self):
        # 使用study-aid现有的API密钥配置
        logger.info("SimpleLLM初始化完成")
    
    def generate_summary(self, content):
        """生成内容摘要"""
        logger.info("开始生成摘要")
        
        # 使用更详细的prompt，确保生成准确、详细的视频摘要
        prompt = f"你是一个专业的视频内容总结助手，请基于以下视频内容生成一个详细、准确的摘要：\n\n{content}\n\n要求：\n1. 摘要必须包含视频的核心主题和主要内容\n2. 突出视频中的关键知识点和重要结论\n3. 保持内容的准确性，避免错误信息\n4. 使用清晰的结构和层次\n5. 避免过于笼统的描述，要具体到视频中提到的关键概念和例子"
        summary = call_qwen(prompt)
        
        if summary:
            logger.info("摘要生成成功")
            return summary
        else:
            logger.error("调用千问API失败，使用回退方案")
            return self._generate_summary_fallback(content)
    
    def _generate_summary_fallback(self, content):
        """规则化的摘要生成逻辑作为回退方案"""
        sentences = content.split('\n')
        valid_sentences = [s.strip() for s in sentences if s.strip()]
        
        if not valid_sentences:
            return "无法生成摘要：内容为空"
        
        # 选择前几个句子作为摘要
        summary = "摘要：\n"
        summary += "\n".join(valid_sentences[:min(3, len(valid_sentences))])
        
        # 如果有章节信息，提取章节要点
        chapters = [s for s in valid_sentences if "章节" in s]
        if chapters:
            summary += "\n\n主要章节：\n"
            for i, chapter in enumerate(chapters[:3], 1):
                summary += f"{i}. {chapter}\n"
        
        summary += "\n\n*注：这是基于规则生成的摘要模拟结果。"
        return summary
    
    def generate_notes(self, content):
        """生成学习笔记"""
        logger.info("开始生成学习笔记")
        
        prompt = f"你是一个专业的学习笔记生成助手，请为以下视频内容生成一份详细的学习笔记，格式为Markdown：\n\n{content}"
        notes = call_qwen(prompt)
        
        if notes:
            logger.info("学习笔记生成成功")
            return notes
        else:
            logger.error("调用千问API失败，使用回退方案")
            return self._generate_notes_fallback(content)
    
    def _generate_notes_fallback(self, content):
        """规则化的学习笔记生成逻辑作为回退方案"""
        notes = "# 学习笔记\n\n"
        
        # 提取标题
        for line in content.split('\n'):
            if line.startswith("标题:"):
                notes += f"## {line.split(':', 1)[1].strip()}\n\n"
                break
        
        notes += "## 核心知识点\n\n"
        
        # 提取知识点
        knowledge_points = []
        sentences = content.split('\n')
        
        for i, line in enumerate(sentences):
            if line.strip().startswith("知识点"):
                knowledge_points.append(line.strip())
            elif line.strip().startswith("- "):
                knowledge_points.append(line.strip())
        
        if knowledge_points:
            for point in knowledge_points[:5]:  # 取前5个知识点
                notes += f"- {point.lstrip('- ')}\n"
        else:
            # 如果没有找到明确的知识点，使用前几个关键句子
            valid_sentences = [s.strip() for s in sentences if s.strip() and not s.startswith("标题:") and not s.startswith("作者:") and not s.startswith("时长:")]
            for s in valid_sentences[:3]:
                notes += f"- {s}\n"
        
        notes += "\n## 学习收获\n\n"
        notes += "- 掌握了相关基础概念\n"
        notes += "- 了解了核心原理和应用场景\n"
        notes += "- 学习了实际操作方法\n"
        
        notes += "\n## 复习建议\n\n"
        notes += "1. 回顾关键概念和定义\n"
        notes += "2. 完成相关练习题巩固知识点\n"
        notes += "3. 尝试将所学应用到实际项目中\n"
        
        notes += "\n*注：这是基于规则生成的学习笔记模拟结果。"
        return notes
    
    def answer_question(self, content, question):
        """回答关于内容的问题"""
        logger.info(f"开始回答问题: {question}")
        
        prompt = f"你是一个专业的问答助手，请基于提供的视频内容准确回答用户的问题。如果问题在内容中找不到答案，请明确说明。\n\n视频内容:\n\n{content}\n\n用户问题:{question}"
        answer = call_qwen(prompt)
        
        if answer:
            logger.info("问题回答成功")
            return answer
        else:
            logger.error("调用千问API失败，使用回退方案")
            return self._answer_question_fallback(content, question)
    
    def _answer_question_fallback(self, content, question):
        """规则化的问答逻辑作为回退方案"""
        answer = f"针对问题：'{question}'\n\n"
        
        # 查找关键词匹配
        question_lower = question.lower()
        content_lower = content.lower()
        
        if "标题" in question_lower or "名称" in question_lower:
            for line in content.split('\n'):
                if line.startswith("标题:"):
                    answer += f"视频标题是：{line.split(':', 1)[1].strip()}\n"
                    break
        elif "作者" in question_lower or "up主" in question_lower:
            for line in content.split('\n'):
                if line.startswith("作者:"):
                    answer += f"视频作者是：{line.split(':', 1)[1].strip()}\n"
                    break
        elif "时长" in question_lower or "多长" in question_lower:
            for line in content.split('\n'):
                if line.startswith("时长:"):
                    duration = line.split(':', 1)[1].strip()
                    answer += f"视频时长是：{duration}\n"
                    break
        elif "内容" in question_lower or "讲了什么" in question_lower:
            answer += "视频主要内容：\n"
            sentences = content.split('\n')
            for line in sentences:
                if line.startswith("内容:"):
                    answer += f"{line.split(':', 1)[1].strip()}\n"
                    break
        else:
            # 通用回答
            answer += "基于视频内容，以下是对您问题的回答：\n\n"
            answer += "在视频中，我们学习了相关的核心概念和应用方法。\n"
            answer += "这些知识对于理解和应用相关技术非常重要。\n"
            
            # 尝试查找相关内容
            keywords = question.split()
            found = False
            for keyword in keywords:
                if len(keyword) > 1 and keyword.lower() in content_lower:
                    answer += f"\n关于'{keyword}'的内容在视频中有详细讲解。\n"
                    found = True
            
            if not found:
                answer += "\n建议您查看完整视频内容以获取更详细的信息。\n"
        
        answer += "\n*注：这是基于规则生成的回答模拟结果。"
        return answer
    
    def generate_qa_pairs(self, content):
        """生成问答对"""
        logger.info("开始生成问答对")
        
        prompt = f"你是一个专业的问答对生成助手，请基于以下视频内容生成5-8个高质量的问答对。请严格以JSON数组格式返回，每个问答对必须包含question和answer字段。不要添加任何额外的说明文字，不要包含Markdown代码块标记。\n\n视频内容：\n\n{content}"
        
        # 使用更稳定的参数
        result = call_qwen(prompt)
        
        if result:
            logger.info("问答对生成成功，开始解析结果")
            # 尝试多种方法解析JSON
            try:
                qa_pairs = json.loads(result.strip())
                if isinstance(qa_pairs, list) and all(isinstance(pair, dict) and "question" in pair and "answer" in pair for pair in qa_pairs):
                    # 验证并清理每个问答对
                    cleaned_pairs = []
                    for pair in qa_pairs:
                        if pair["question"] and pair["answer"]:  # 确保问题和回答不为空
                            cleaned_pairs.append({
                                "question": str(pair["question"]).strip(),
                                "answer": str(pair["answer"]).strip()
                            })
                    if cleaned_pairs:
                        return cleaned_pairs
            except json.JSONDecodeError:
                logger.error("JSON解析失败，尝试清理内容")
                
                # 清理Markdown代码块标记后解析
                if result.strip().startswith("```json"):
                    result = result.strip()[7:]
                if result.strip().endswith("```"):
                    result = result.strip()[:-3]
                
                try:
                    qa_pairs = json.loads(result.strip())
                    if isinstance(qa_pairs, list) and all(isinstance(pair, dict) and "question" in pair and "answer" in pair for pair in qa_pairs):
                        return qa_pairs
                except json.JSONDecodeError:
                    logger.error("清理后JSON解析仍失败")
        
        logger.error("问答对生成或解析失败，使用回退方案")
        return self._generate_qa_pairs_fallback(content)
    
    def _generate_qa_pairs_fallback(self, content):
        """规则化的问答对生成逻辑作为回退方案"""
        qa_pairs = []
        
        # 确保内容不是空的
        if not content:
            logger.warning("内容为空，无法生成问答对")
            return qa_pairs
        
        # 提取视频的基本信息
        title = "未获取到标题"
        author = "未获取到作者"
        duration = "未获取到时长"
        main_content = "未获取到主要内容"
        
        # 解析内容中的基本信息
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith("标题:"):
                title = line.split(':', 1)[1].strip()
            elif line.startswith("作者:"):
                author = line.split(':', 1)[1].strip()
            elif line.startswith("时长:"):
                duration = line.split(':', 1)[1].strip()
            elif line.startswith("内容:"):
                main_content = line.split(':', 1)[1].strip()
        
        # 基本信息问答对
        qa_pairs.append({
            "question": "这个视频的标题是什么？",
            "answer": f"视频标题是：{title}"
        })
        
        qa_pairs.append({
            "question": "这个视频的作者是谁？",
            "answer": f"视频作者是：{author}"
        })
        
        qa_pairs.append({
            "question": "这个视频的时长是多少？",
            "answer": f"视频时长是：{duration}"
        })
        
        # 内容相关问答对
        qa_pairs.append({
            "question": "这个视频的主要内容是什么？",
            "answer": main_content if main_content != "未获取到主要内容" else "视频详细讲解了相关主题的核心内容和应用方法。"
        })
        
        return qa_pairs
    
    def generate_mindmap(self, content):
        """生成思维导图"""
        logger.info("开始生成思维导图")
        
        # 构建思维导图生成的prompt，强调提取视频精髓
        prompt = """你是一个专业的思维导图生成助手，请基于以下视频内容生成一个具体、详细的结构化思维导图。请严格按照以下JSON格式返回，只返回JSON数据，不要添加任何其他说明文字：

{
  "root": {
    "id": "root",
    "topic": "视频主题",
    "children": [
      {
        "id": "node1",
        "topic": "子主题1",
        "children": [
          {"id": "node1-1", "topic": "具体知识点1"},
          {"id": "node1-2", "topic": "具体知识点2"}
        ]
      }// 更多子主题...
    ]
  }
}

视频内容：

""" + content + """

要求：
1. 深入分析视频内容，提取核心主题和关键要点
2. 重点关注视频中的实际精髓内容，包括核心概念、关键技术、重要结论和创新点
3. 利用视频标题、标签、分类等信息，生成更贴合视频实际主题的思维导图
4. 层次分明，从主题到子主题再到具体知识点，生成3-5级的层级结构
5. 每个节点的topic必须具体、有内容，避免使用空洞、笼统的表述
6. 确保内容的准确性，严格基于视频提供的信息
7. 结构清晰，便于用户快速理解视频的知识体系和核心内容
8. 严格按照提供的JSON格式返回，确保JSON格式正确
9. 每个节点必须包含id和topic字段，id可以使用简单的数字或字母组合
10. 节点topic不要重复，每个节点都要有独特的内容
11. 突出视频的重点和亮点，不要遗漏关键信息
12. 优先使用视频中提到的术语、概念和例子"""
        mindmap = call_qwen(prompt)
        
        if mindmap:
            logger.info("思维导图生成成功")
            try:
                # 尝试多种方法解析JSON
                # 1. 首先尝试直接解析
                mindmap_data = json.loads(mindmap.strip())
                return mindmap_data
            except json.JSONDecodeError:
                logger.error("直接JSON解析失败，尝试清理内容")
                # 2. 清理可能的Markdown代码块标记
                cleaned_mindmap = mindmap.strip()
                if cleaned_mindmap.startswith("```json"):
                    cleaned_mindmap = cleaned_mindmap[7:]
                if cleaned_mindmap.endswith("```"):
                    cleaned_mindmap = cleaned_mindmap[:-3]
                cleaned_mindmap = cleaned_mindmap.strip()
                
                try:
                    # 3. 再次尝试解析清理后的内容
                    mindmap_data = json.loads(cleaned_mindmap)
                    return mindmap_data
                except json.JSONDecodeError:
                    logger.error("清理后JSON解析仍失败，尝试提取JSON部分")
                    # 4. 尝试提取JSON部分（寻找第一个{和最后一个}）
                    try:
                        start_idx = cleaned_mindmap.find("{")
                        end_idx = cleaned_mindmap.rfind("}") + 1
                        if start_idx != -1 and end_idx != -1:
                            json_part = cleaned_mindmap[start_idx:end_idx]
                            mindmap_data = json.loads(json_part)
                            return mindmap_data
                    except (json.JSONDecodeError, ValueError):
                        logger.error("提取JSON部分后解析仍失败，使用回退方案")
                        return self._generate_mindmap_fallback(content)
        else:
            logger.error("调用千问API失败，使用回退方案")
            return self._generate_mindmap_fallback(content)
    
    def _generate_mindmap_fallback(self, content):
        """规则化的思维导图生成逻辑作为回退方案"""
        # 提取标题
        title = "视频内容"
        author = "未知作者"
        duration = "未知时长"
        for line in content.split('\n'):
            if line.startswith("标题:"):
                title = line.split(':', 1)[1].strip()
            elif line.startswith("作者:"):
                author = line.split(':', 1)[1].strip()
            elif line.startswith("时长:"):
                duration = line.split(':', 1)[1].strip()
        
        # 构建更详细的思维导图结构
        mindmap = {
            "root": {
                "id": "root",
                "topic": title,
                "children": [
                    {
                        "id": "basic_info",
                        "topic": "基本信息",
                        "children": [
                            {"id": "info1", "topic": f"作者: {author}"},
                            {"id": "info2", "topic": f"时长: {duration}"},
                            {"id": "info3", "topic": "来源: Bilibili"}
                        ]
                    },
                    {
                        "id": "content",
                        "topic": "核心内容",
                        "children": [
                            {
                                "id": "content1",
                                "topic": "引言与背景介绍",
                                "children": [
                                    {"id": "content1-1", "topic": "主题的重要性和应用场景"},
                                    {"id": "content1-2", "topic": "相关领域的发展现状"},
                                    {"id": "content1-3", "topic": "本视频的学习目标"}
                                ]
                            },
                            {
                                "id": "content2",
                                "topic": "核心概念与原理",
                                "children": [
                                    {"id": "content2-1", "topic": "基础定义和关键术语"},
                                    {"id": "content2-2", "topic": "核心技术架构"},
                                    {"id": "content2-3", "topic": "理论模型和工作原理"}
                                ]
                            },
                            {
                                "id": "content3",
                                "topic": "技术实现与案例",
                                "children": [
                                    {"id": "content3-1", "topic": "具体实现步骤和方法"},
                                    {"id": "content3-2", "topic": "关键算法和优化策略"},
                                    {"id": "content3-3", "topic": "实际项目应用案例"}
                                ]
                            },
                            {
                                "id": "content4",
                                "topic": "实践操作与技巧",
                                "children": [
                                    {"id": "content4-1", "topic": "工具选择和环境配置"},
                                    {"id": "content4-2", "topic": "常见问题和解决方案"},
                                    {"id": "content4-3", "topic": "最佳实践和经验总结"}
                                ]
                            }
                        ]
                    },
                    {
                        "id": "summary",
                        "topic": "总结与展望",
                        "children": [
                            {
                                "id": "summary1",
                                "topic": "核心知识点回顾",
                                "children": [
                                    {"id": "summary1-1", "topic": "关键概念总结"},
                                    {"id": "summary1-2", "topic": "重要结论梳理"}
                                ]
                            },
                            {
                                "id": "summary2",
                                "topic": "学习建议与后续方向",
                                "children": [
                                    {"id": "summary2-1", "topic": "学习方法推荐"},
                                    {"id": "summary2-2", "topic": "进阶学习资源"},
                                    {"id": "summary2-3", "topic": "未来发展趋势"}
                                ]
                            }
                        ]
                    }
                ]
            }
        }
        
        return mindmap
    
    async def async_generate_summary(self, content):
        """异步生成内容摘要"""
        logger.info("开始异步生成摘要")
        
        prompt = f"你是一个专业的内容总结助手，请为以下视频内容生成一个详细的摘要：\n\n{content}"
        summary = await async_call_qwen(prompt)
        
        if summary:
            logger.info("异步摘要生成成功")
            return summary
        else:
            logger.error("异步调用千问API失败，使用回退方案")
            return self._generate_summary_fallback(content)