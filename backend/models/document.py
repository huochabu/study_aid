import requests
import re
import os
import random
from dotenv import load_dotenv
import logging
from typing import Optional, Dict, Any

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Document:
    """文档模型类"""
    
    def __init__(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.content = content
        self.metadata = metadata or {}

class BilibiliLoader:
    """B站视频内容加载器"""
    
    def __init__(self, video_id: str):
        self.video_id = video_id
        self.bvid = self._extract_bv_id(video_id)
        # 获取B站API接口地址
        self.api_url = os.getenv('BILIBILI_API_URL', 'https://api.bilibili.com/x/web-interface/view')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def _extract_bv_id(self, input_str: str) -> str:
        """从输入中提取BV号"""
        # 匹配BV号的正则表达式
        bv_pattern = r'BV[0-9A-Za-z]{10,12}'
        match = re.search(bv_pattern, input_str)
        if match:
            return match.group(0)
        return input_str
    
    def load(self) -> Document:
        """加载视频内容"""
        logger.info(f"开始加载B站视频内容，BV号: {self.bvid}")
        
        try:
            # 调用B站API获取视频信息
            params = {'bvid': self.bvid}
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') != 0:
                logger.error(f"B站API返回错误: {data.get('message')}")
                raise Exception(f"B站API返回错误: {data.get('message')}")
            
            # 提取视频基本信息
            video_data = data['data']
            title = video_data['title']
            description = video_data['desc']
            owner = video_data['owner']['name']
            duration = self._format_duration(video_data['duration'])
            
            # 提取更多视频信息，用于生成更准确的思维导图
            tags = []
            if 'tags' in video_data:
                tags = [tag['name'] for tag in video_data['tags']]
            
            # 提取视频分类信息
            category = video_data['tname'] if 'tname' in video_data else ''
            
            # 构建内容
            content = f"标题: {title}\n"
            content += f"作者: {owner}\n"
            content += f"时长: {duration}\n"
            content += f"分类: {category}\n"
            if tags:
                content += f"标签: {', '.join(tags)}\n"
            content += f"内容: {description}\n"
            
            # 注意：当前实现只能获取视频的基本信息和描述，无法获取完整的视频内容或字幕
            # 实际项目中，您可能需要集成专门的视频内容提取服务或字幕API
            # 以下为基于视频描述的扩展内容，用于增强AI分析效果
            if description:
                content += "\n详细内容：\n"
                content += "根据视频描述，该视频主要涵盖以下内容：\n"
                # 将描述拆分为要点
                points = description.split('。')
                for i, point in enumerate(points):
                    if point.strip():
                        content += f"{i+1}. {point.strip()}\n"
            
            metadata = {
                'title': title,
                'author': owner,
                'duration': duration,
                'video_id': self.bvid,
                'source': 'bilibili'
            }
            
            logger.info(f"B站视频内容加载成功，标题: {title}")
            return Document(content, metadata)
        
        except requests.exceptions.RequestException as e:
            logger.error(f"请求B站API失败: {str(e)}")
            raise Exception(f"请求B站API失败: {str(e)}")
        except Exception as e:
            logger.error(f"加载视频内容失败: {str(e)}")
            raise Exception(f"加载视频内容失败: {str(e)}")
    
    def _format_duration(self, seconds: int) -> str:
        """将秒数转换为时分秒格式"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}小时{minutes}分钟{secs}秒"
        elif minutes > 0:
            return f"{minutes}分钟{secs}秒"
        else:
            return f"{secs}秒"
    
    def _generate_simulation_content(self, title: str, description: str, tags: list, category: str) -> str:
        """生成模拟的视频内容，基于视频的实际信息"""
        content = "\n详细内容：\n"
        
        # 根据视频标题和标签生成更相关的内容
        content += "1. 引言与背景介绍：\n"
        content += f"   - 介绍{title}的核心主题和重要性\n"
        content += f"   - 讲解{title}在{category}领域的应用场景和价值\n"
        content += f"   - 概述本视频的主要内容和学习目标\n"
        
        content += "\n2. 核心概念与关键技术：\n"
        if tags:
            for tag in tags[:3]:  # 使用前3个标签作为核心概念
                content += f"   - {tag}的定义、特点和工作原理\n"
        else:
            content += "   - 核心概念1：详细解释相关基础概念\n"
            content += "   - 核心概念2：讲解关键技术的工作原理\n"
        
        content += "\n3. 实际应用与案例分析：\n"
        content += f"   - {title}在实际项目中的应用案例\n"
        content += "   - 案例中遇到的问题和解决方案\n"
        content += "   - 案例的效果评估和经验总结\n"
        
        content += "\n4. 实践操作与技巧分享：\n"
        content += f"   - 如何实现{title}的核心功能\n"
        content += "   - 常见问题的排查和解决方法\n"
        content += "   - 优化和改进的建议\n"
        
        content += "\n5. 总结与展望：\n"
        content += f"   - 总结{title}的核心知识点和关键要点\n"
        content += f"   - 讨论{title}的未来发展趋势和方向\n"
        content += "   - 提供进一步学习和实践的建议\n"
        
        # 如果有视频描述，基于描述生成更相关的内容
        if description:
            content += "\n6. 视频描述要点展开：\n"
            # 将描述拆分为要点并展开
            points = description.split('。')
            for i, point in enumerate(points):
                if point.strip():
                    content += f"   - {point.strip()}（详细展开）\n"
        
        return content
    
    def _determine_content_type(self) -> str:
        """根据BV号确定内容类型（模拟）"""
        # 简单模拟：根据BV号的某些字符特征来判断内容类型
        char_sum = sum(ord(c) for c in self.bvid)
        if char_sum % 3 == 0:
            return 'technology'
        elif char_sum % 3 == 1:
            return 'education'
        else:
            return 'entertainment'
    
    def _generate_mock_content(self) -> Document:
        """生成模拟内容作为回退方案"""
        logger.info("使用模拟内容作为回退方案")
        
        # 生成模拟的视频标题
        content_type = self._determine_content_type()
        if content_type == 'technology':
            topics = ['人工智能', '机器学习', 'Python编程', '数据分析', '前端开发']
            title = f"{random.choice(topics)}入门教程 - 从零基础到精通"
        elif content_type == 'education':
            subjects = ['高等数学', '线性代数', '大学物理', '英语四级', '考研政治']
            title = f"{random.choice(subjects)}重点知识点讲解"
        elif content_type == 'entertainment':
            types = ['电影推荐', '游戏攻略', '美食制作', '旅行vlog', '音乐分享']
            title = f"我的{random.choice(types)} - 精彩内容不容错过"
        else:
            title = f"B站视频 - {self.bvid}"
        
        # 构建模拟内容
        content = f"标题: {title}\n"
        content += f"作者: 模拟UP主\n"
        content += f"时长: 15分钟30秒\n"
        content += f"内容: 这是一个模拟的视频内容，实际项目中会从B站API获取真实数据。\n"
        
        # 添加详细的模拟内容
        content += "\n视频主要内容：\n"
        content += "1. 介绍部分：讲解视频的主题和目标\n"
        content += "2. 核心内容：详细讲解相关知识点和技术\n"
        content += "3. 案例分析：通过实际案例加深理解\n"
        content += "4. 总结回顾：总结视频的主要内容和重点\n"
        content += "\n感谢大家的观看，记得点赞、投币、收藏支持哦！\n"
        
        metadata = {
            'title': title,
            'author': '模拟UP主',
            'duration': '15分钟30秒',
            'video_id': self.bvid,
            'source': 'mock'
        }
        
        return Document(content, metadata)