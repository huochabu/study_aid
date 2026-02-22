from models.document import BilibiliLoader
from models.llm import SimpleLLM
import logging
import re

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoProcessor:
    """视频处理器类，整合加载器和LLM模型"""
    
    def __init__(self):
        self.llm = SimpleLLM()
        logger.info("VideoProcessor初始化完成")
    
    def load_and_split(self, video_id):
        """加载视频内容并进行处理"""
        try:
            logger.info(f"开始加载和分割视频内容，视频ID: {video_id}")
            # 创建加载器并加载视频内容
            loader = BilibiliLoader(video_id)
            document = loader.load()
            
            logger.info(f"视频内容加载成功，视频标题: {document.metadata.get('title', 'Unknown')}")
            logger.info(f"视频内容加载成功，内容长度: {len(document.content)} 字符")
            return document
        except Exception as e:
            logger.error(f"加载和分割视频内容失败: {str(e)}")
            raise
    
    def get_summary(self, video_id):
        """获取视频摘要"""
        try:
            logger.info(f"Generating summary for video: {video_id}")
            # 加载视频内容
            document = self.load_and_split(video_id)
            
            # 生成摘要
            summary = self.llm.generate_summary(document.content)
            logger.info(f"Summary generated successfully")
            
            return {
                "task_type": "summary",
                "data": summary,
                "metadata": document.metadata
            }
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            raise
    
    def get_answer(self, video_id, question):
        """获取视频问答答案"""
        try:
            logger.info(f"Generating answer for video: {video_id}, question: {question}")
            # 加载视频内容
            document = self.load_and_split(video_id)
            
            # 生成回答
            answer = self.llm.answer_question(document.content, question)
            logger.info(f"Answer generated successfully")
            
            # 修改返回格式，确保前端能够正确识别和显示问答结果
            # 使用answer字段包装回答内容，方便前端提取
            return {
                "task_type": "qa",
                "data": {
                    "question": question,
                    "answer": answer
                },
                "metadata": document.metadata
            }
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            raise
    
    def get_question_answers(self, video_id):
        """获取视频问答对"""
        try:
            logger.info(f"Generating Q&A pairs for video: {video_id}")
            # 加载视频内容
            document = self.load_and_split(video_id)
            
            # 生成问答对
            qa_pairs = self.llm.generate_qa_pairs(document.content)
            logger.info(f"Generated {len(qa_pairs)} Q&A pairs")
            
            return {
                "task_type": "qapairs",
                "data": qa_pairs,
                "metadata": document.metadata
            }
        except Exception as e:
            logger.error(f"Error generating Q&A pairs: {str(e)}")
            raise
    
    def get_mindmap(self, video_id):
        """获取视频思维导图"""
        try:
            logger.info(f"Generating mindmap for video: {video_id}")
            # 加载视频内容
            document = self.load_and_split(video_id)
            
            # 生成思维导图
            mindmap = self.llm.generate_mindmap(document.content)
            logger.info(f"Mindmap generated successfully")
            
            return {
                "task_type": "mindmap",
                "data": mindmap,
                "metadata": document.metadata
            }
        except Exception as e:
            logger.error(f"Error generating mindmap: {str(e)}")
            raise
    
    def get_notes(self, video_id):
        """获取视频学习笔记"""
        try:
            logger.info(f"Generating notes for video: {video_id}")
            # 加载视频内容
            document = self.load_and_split(video_id)
            
            # 生成学习笔记
            notes = self.llm.generate_notes(document.content)
            logger.info(f"Notes generated successfully")
            
            return {
                "task_type": "notes",
                "data": notes,
                "metadata": document.metadata
            }
        except Exception as e:
            logger.error(f"Error generating notes: {str(e)}")
            raise
    
    def extract_bvid(self, video_id):
        """从视频ID或URL中提取纯BV号"""
        # 支持多种B站URL格式的BV号提取
        bv_patterns = [
            r'BV[0-9A-Za-z]{10,12}',  # 匹配BV号本身
            r'bvid=(BV[0-9A-Za-z]{10,12})',  # 匹配URL中的bvid参数
        ]
        
        # 尝试所有模式提取BV号
        for pattern in bv_patterns:
            match = re.search(pattern, video_id)
            if match:
                # 如果是带参数的模式，返回第一个捕获组
                if match.groups():
                    return match.group(1)
                return match.group(0)
        
        # 如果已经是纯BV号，直接返回
        if video_id.startswith('BV') and 12 <= len(video_id) <= 14:
            return video_id
        
        logger.warning(f"无法从输入中提取有效的BV号: {video_id}")
        return video_id
    
    def process_video_task(self, video_id, task_type, question=None):
        """统一的视频任务处理入口"""
        logger.info(f"开始处理视频任务，任务类型: {task_type}，视频ID: {video_id}")
        if question:
            logger.info(f"任务包含问题: {question}")
            
        try:
            # 按照指定顺序处理不同类型的任务
            if task_type == "play":
                logger.info(f"[任务:{task_type}] 执行播放任务")
                # 提取纯BV号用于嵌入URL
                pure_bvid = self.extract_bvid(video_id)
                logger.info(f"提取的纯BV号: {pure_bvid}")
                
                # 获取视频详细信息
                try:
                    document = self.load_and_split(pure_bvid)
                    # 提供视频页面链接和B站分享信息
                    video_info = {
                        "video_id": video_id,
                        "title": document.metadata.get('title', f"B站视频 - {pure_bvid}"),
                        "author": document.metadata.get('author', '未知作者'),
                        "duration": document.metadata.get('duration', '未知时长'),
                        "description": document.metadata.get('description', ''),
                        # 视频页面链接
                        "video_url": f"https://www.bilibili.com/video/{pure_bvid}/",
                        # 保持嵌入URL以便前端可以尝试
                        "embed_url": f"https://player.bilibili.com/player.html?bvid={pure_bvid}&page=1&high_quality=1&danmaku=0"
                    }
                    result = {
                        "data": video_info,
                        "metadata": document.metadata
                    }
                except Exception as e:
                    logger.warning(f"获取视频详细信息失败，使用默认信息: {str(e)}")
                    # 失败时使用默认信息
                    video_info = {
                        "video_id": video_id,
                        "title": f"B站视频 - {pure_bvid}",
                        "author": "未知作者",
                        "duration": "未知时长",
                        "description": "无法获取视频描述",
                        "video_url": f"https://www.bilibili.com/video/{pure_bvid}/",
                        "embed_url": f"https://player.bilibili.com/player.html?bvid={pure_bvid}&page=1&high_quality=1&danmaku=0"
                    }
                    result = {
                        "data": video_info,
                        "metadata": {}
                    }
                logger.info(f"[任务:{task_type}] 播放任务执行完成")
            elif task_type == "summary":
                logger.info(f"[任务:{task_type}] 开始生成视频总结")
                result = self.get_summary(video_id)
                logger.info(f"[任务:{task_type}] 视频总结生成完成")
            elif task_type == "mindmap":
                logger.info(f"[任务:{task_type}] 开始生成思维导图")
                result = self.get_mindmap(video_id)
                logger.info(f"[任务:{task_type}] 思维导图生成完成")
            elif task_type == "notes":
                logger.info(f"[任务:{task_type}] 开始生成学习笔记")
                result = self.get_notes(video_id)
                logger.info(f"[任务:{task_type}] 学习笔记生成完成")
            elif task_type == "qapairs":
                logger.info(f"[任务:{task_type}] 开始生成问答对")
                result = self.get_question_answers(video_id)
                logger.info(f"[任务:{task_type}] 问答对生成完成")
            elif task_type == "qa":
                if not question:
                    raise ValueError("Question is required for QA task")
                logger.info(f"[任务:{task_type}] 开始回答问题: {question}")
                result = self.get_answer(video_id, question)
                logger.info(f"[任务:{task_type}] 问题回答完成")
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            logger.info(f"视频任务处理成功，任务类型: {task_type}")
            return {
                "task_type": task_type,
                "data": result['data'] if isinstance(result, dict) and 'data' in result else result,
                "metadata": result['metadata'] if isinstance(result, dict) and 'metadata' in result else {},
                "status": "success"
            }
        except Exception as e:
            logger.error(f"视频任务处理失败，任务类型: {task_type}，错误: {str(e)}")
            return {
                "task_type": task_type,
                "error": str(e),
                "video_id": video_id,
                "status": "error"
            }