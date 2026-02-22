import json
import time
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import LearningProgress, LearningModule, Note, QuizAttempt, LearningAnalytics

class RecommendationService:
    """智能推荐系统服务"""
    
    def __init__(self):
        self.recommendation_cache = {}  # 缓存推荐结果，提高性能
    
    def get_recommendations(self, user_id: str, db: Session, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取用户的学习推荐
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            limit: 推荐数量限制
        
        Returns:
            推荐列表，每个元素包含推荐内容的详细信息
        """
        # 尝试从缓存获取
        cache_key = f"{user_id}_{limit}"
        if cache_key in self.recommendation_cache:
            cached_result = self.recommendation_cache[cache_key]
            if time.time() - cached_result['timestamp'] < 3600:  # 缓存1小时
                return cached_result['recommendations']
        
        # 获取用户学习数据
        user_data = self._get_user_learning_data(user_id, db)
        
        # 生成推荐
        recommendations = []
        
        # 1. 推荐未完成的学习模块
        unfinished_modules = self._recommend_unfinished_modules(user_id, db, limit=2)
        recommendations.extend(unfinished_modules)
        
        # 2. 推荐基于学习历史的相关内容
        history_based_recommendations = self._recommend_based_on_history(user_data, db, limit=2)
        recommendations.extend(history_based_recommendations)
        
        # 3. 推荐需要复习的内容
        review_recommendations = self._recommend_for_review(user_id, db, limit=1)
        recommendations.extend(review_recommendations)
        
        # 4. 推荐热门内容（基于所有用户的学习数据）
        popular_recommendations = self._recommend_popular_content(db, limit=2)
        recommendations.extend(popular_recommendations)
        
        # 去重并限制数量
        unique_recommendations = self._deduplicate_recommendations(recommendations)[:limit]
        
        # 缓存结果
        self.recommendation_cache[cache_key] = {
            'recommendations': unique_recommendations,
            'timestamp': time.time()
        }
        
        return unique_recommendations
    
    def _get_user_learning_data(self, user_id: str, db: Session) -> Dict[str, Any]:
        """
        获取用户的学习数据
        
        Args:
            user_id: 用户ID
            db: 数据库会话
        
        Returns:
            用户学习数据
        """
        # 获取学习进度
        progress_records = db.query(LearningProgress).filter(LearningProgress.user_id == user_id).all()
        
        # 获取笔记
        notes = db.query(Note).filter(Note.user_id == user_id).all()
        
        # 获取测验尝试
        quiz_attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id).all()
        
        # 获取学习活动
        activities = db.query(LearningAnalytics).filter(LearningAnalytics.user_id == user_id).all()
        
        return {
            'progress_records': progress_records,
            'notes': notes,
            'quiz_attempts': quiz_attempts,
            'activities': activities
        }
    
    def _recommend_unfinished_modules(self, user_id: str, db: Session, limit: int = 2) -> List[Dict[str, Any]]:
        """
        推荐未完成的学习模块
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            limit: 推荐数量限制
        
        Returns:
            未完成模块推荐列表
        """
        # 获取用户的学习进度
        progress_records = db.query(LearningProgress).filter(
            LearningProgress.user_id == user_id,
            LearningProgress.progress < 100
        ).all()
        
        recommendations = []
        for progress in progress_records[:limit]:
            # 获取模块信息
            module = db.query(LearningModule).filter(LearningModule.id == progress.module_id).first()
            if module:
                recommendations.append({
                    'type': 'unfinished_module',
                    'module_id': module.id,
                    'title': module.title,
                    'description': module.description,
                    'current_progress': progress.progress,
                    'estimated_time': module.estimated_time,
                    'priority': 1.0,  # 高优先级
                    'reason': f'您当前进度为{progress.progress}%，继续完成这个模块'
                })
        
        return recommendations
    
    def _recommend_based_on_history(self, user_data: Dict[str, Any], db: Session, limit: int = 2) -> List[Dict[str, Any]]:
        """
        基于学习历史推荐相关内容
        
        Args:
            user_data: 用户学习数据
            db: 数据库会话
            limit: 推荐数量限制
        
        Returns:
            基于历史的推荐列表
        """
        # 分析用户的学习偏好
        preferences = self._analyze_learning_preferences(user_data)
        
        # 基于偏好推荐内容
        recommendations = []
        
        # 这里可以实现更复杂的推荐算法，例如：
        # 1. 基于学习时间分布推荐相似时长的内容
        # 2. 基于学习频率推荐合适的学习节奏
        # 3. 基于笔记和测验表现推荐需要加强的领域
        
        # 简化实现：推荐与用户最近学习模块相关的内容
        recent_modules = self._get_recently_studied_modules(user_data, db, limit=3)
        
        for module in recent_modules:
            # 查找相关的学习模块（这里简化为同计划的其他模块）
            related_modules = db.query(LearningModule).filter(
                LearningModule.plan_id == module.plan_id,
                LearningModule.id != module.id
            ).limit(limit).all()
            
            for related_module in related_modules:
                # 检查用户是否已经完成该模块
                if not self._is_module_completed(user_data['progress_records'], related_module.id):
                    recommendations.append({
                        'type': 'related_content',
                        'module_id': related_module.id,
                        'title': related_module.title,
                        'description': related_module.description,
                        'estimated_time': related_module.estimated_time,
                        'priority': 0.7,  # 中等优先级
                        'reason': f'基于您对{module.title}的学习，推荐相关内容'
                    })
        
        return recommendations[:limit]
    
    def _recommend_for_review(self, user_id: str, db: Session, limit: int = 1) -> List[Dict[str, Any]]:
        """
        推荐需要复习的内容
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            limit: 推荐数量限制
        
        Returns:
            复习推荐列表
        """
        # 获取用户已完成的模块
        completed_modules = db.query(LearningProgress).filter(
            LearningProgress.user_id == user_id,
            LearningProgress.progress == 100,
            LearningProgress.completed_at.isnot(None)
        ).all()
        
        recommendations = []
        current_time = time.time()
        
        # 推荐7天前完成的模块进行复习
        for progress in completed_modules:
            if progress.completed_at:
                days_since_completion = (current_time - progress.completed_at) / (24 * 3600)
                if 6 <= days_since_completion <= 8:  # 7天左右
                    module = db.query(LearningModule).filter(LearningModule.id == progress.module_id).first()
                    if module:
                        recommendations.append({
                            'type': 'review',
                            'module_id': module.id,
                            'title': module.title,
                            'description': module.description,
                            'days_since_completion': int(days_since_completion),
                            'priority': 0.8,  # 较高优先级
                            'reason': f'您在{int(days_since_completion)}天前完成了这个模块，建议复习'
                        })
        
        return recommendations[:limit]
    
    def _recommend_popular_content(self, db: Session, limit: int = 2) -> List[Dict[str, Any]]:
        """
        推荐热门内容
        
        Args:
            db: 数据库会话
            limit: 推荐数量限制
        
        Returns:
            热门内容推荐列表
        """
        # 分析所有用户的学习数据，找出最受欢迎的模块
        # 简化实现：统计完成次数最多的模块
        
        # 获取所有完成的学习进度记录
        completed_progress = db.query(LearningProgress).filter(
            LearningProgress.progress == 100
        ).all()
        
        # 统计每个模块的完成次数
        module_completion_count = {}
        for progress in completed_progress:
            if progress.module_id in module_completion_count:
                module_completion_count[progress.module_id] += 1
            else:
                module_completion_count[progress.module_id] = 1
        
        # 按完成次数排序
        sorted_modules = sorted(module_completion_count.items(), key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for module_id, count in sorted_modules[:limit]:
            module = db.query(LearningModule).filter(LearningModule.id == module_id).first()
            if module:
                recommendations.append({
                    'type': 'popular',
                    'module_id': module.id,
                    'title': module.title,
                    'description': module.description,
                    'completion_count': count,
                    'estimated_time': module.estimated_time,
                    'priority': 0.5,  # 中等优先级
                    'reason': f'已有{count}人完成了这个模块，很受欢迎'
                })
        
        return recommendations
    
    def _analyze_learning_preferences(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析用户的学习偏好
        
        Args:
            user_data: 用户学习数据
        
        Returns:
            用户学习偏好
        """
        preferences = {
            'preferred_time_of_day': None,
            'average_study_duration': 0,
            'preferred_module_length': 0,
            'strong_topics': [],
            'weak_topics': []
        }
        
        # 分析学习时间偏好
        if user_data['activities']:
            hour_distribution = {}
            total_duration = 0
            
            for activity in user_data['activities']:
                hour = time.localtime(activity.timestamp).tm_hour
                if hour in hour_distribution:
                    hour_distribution[hour] += 1
                else:
                    hour_distribution[hour] = 1
                total_duration += activity.duration
            
            if hour_distribution:
                preferred_hour = max(hour_distribution, key=hour_distribution.get)
                preferences['preferred_time_of_day'] = preferred_hour
            
            if user_data['activities']:
                preferences['average_study_duration'] = total_duration / len(user_data['activities'])
        
        # 分析模块长度偏好
        if user_data['progress_records']:
            module_lengths = []
            for progress in user_data['progress_records']:
                # 这里简化处理，实际应该从LearningModule获取estimated_time
                pass
        
        return preferences
    
    def _get_recently_studied_modules(self, user_data: Dict[str, Any], db: Session, limit: int = 3) -> List:
        """
        获取用户最近学习的模块
        
        Args:
            user_data: 用户学习数据
            db: 数据库会话
            limit: 数量限制
        
        Returns:
            最近学习的模块列表
        """
        # 按最后更新时间排序学习进度
        recent_progress = sorted(
            user_data['progress_records'],
            key=lambda x: x.last_updated or 0,
            reverse=True
        )[:limit]
        
        modules = []
        for progress in recent_progress:
            module = db.query(LearningModule).filter(LearningModule.id == progress.module_id).first()
            if module:
                modules.append(module)
        
        return modules
    
    def _is_module_completed(self, progress_records: List, module_id: str) -> bool:
        """
        检查模块是否已完成
        
        Args:
            progress_records: 学习进度记录
            module_id: 模块ID
        
        Returns:
            是否已完成
        """
        for progress in progress_records:
            if progress.module_id == module_id and progress.progress == 100:
                return True
        return False
    
    def _deduplicate_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        去重推荐结果
        
        Args:
            recommendations: 推荐列表
        
        Returns:
            去重后的推荐列表
        """
        seen_module_ids = set()
        unique_recommendations = []
        
        for rec in recommendations:
            if 'module_id' in rec and rec['module_id'] not in seen_module_ids:
                seen_module_ids.add(rec['module_id'])
                unique_recommendations.append(rec)
            elif 'module_id' not in rec:  # 处理没有module_id的推荐类型
                unique_recommendations.append(rec)
        
        return unique_recommendations

# 创建推荐服务实例
recommendation_service = RecommendationService()