from fastapi import APIRouter, HTTPException, Depends, Query, Form, Body
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from models import LearningPlan, LearningModule, LearningProgress, Note, Quiz, Question, QuizAttempt, LearningAnalytics, Collaboration, User, LearningPreference, LearningBehavior, LearningPrediction
from services.recommendation import recommendation_service
import json
import time
import uuid

router = APIRouter(prefix="/api/learning", tags=["Learning"])

# ======================
# 学习计划管理
# ======================

@router.post("/plans")
def create_learning_plan(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    start_date: float = Form(...),
    end_date: float = Form(...),
    user_id: str = Form("default"),
    db: Session = Depends(get_db)
):
    """创建学习计划"""
    try:
        plan_id = str(uuid.uuid4())
        new_plan = LearningPlan(
            id=plan_id,
            user_id=user_id,
            title=title,
            description=description or "",
            start_date=start_date,
            end_date=end_date,
            status="active"
        )
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)
        return {"id": plan_id, "title": title, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建学习计划失败: {str(e)}")

@router.get("/plans")
def get_learning_plans(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """获取用户的学习计划列表"""
    plans = db.query(LearningPlan).filter(LearningPlan.user_id == user_id).all()
    return [{
        "id": plan.id,
        "title": plan.title,
        "description": plan.description,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "status": plan.status,
        "created_at": plan.created_at
    } for plan in plans]

@router.get("/plans/{plan_id}")
def get_learning_plan_detail(
    plan_id: str,
    db: Session = Depends(get_db)
):
    """获取学习计划详情"""
    plan = db.query(LearningPlan).filter(LearningPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    
    modules = db.query(LearningModule).filter(LearningModule.plan_id == plan_id).order_by(LearningModule.order_index).all()
    
    return {
        "id": plan.id,
        "title": plan.title,
        "description": plan.description,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "status": plan.status,
        "modules": [{
            "id": module.id,
            "title": module.title,
            "description": module.description,
            "order_index": module.order_index,
            "estimated_time": module.estimated_time
        } for module in modules]
    }

@router.put("/plans/{plan_id}")
def update_learning_plan(
    plan_id: str,
    title: str = None,
    description: str = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """更新学习计划"""
    plan = db.query(LearningPlan).filter(LearningPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    
    if title:
        plan.title = title
    if description:
        plan.description = description
    if status:
        plan.status = status
    
    db.commit()
    return {"id": plan_id, "status": "updated"}

@router.delete("/plans/{plan_id}")
def delete_learning_plan(
    plan_id: str,
    db: Session = Depends(get_db)
):
    """删除学习计划"""
    plan = db.query(LearningPlan).filter(LearningPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    
    # 删除相关的模块
    modules = db.query(LearningModule).filter(LearningModule.plan_id == plan_id).all()
    for module in modules:
        db.delete(module)
    
    db.delete(plan)
    db.commit()
    return {"id": plan_id, "status": "deleted"}

# ======================
# 学习模块管理
# ======================

@router.post("/modules")
def create_learning_module(
    plan_id: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    order_index: int = Form(...),
    estimated_time: int = Form(...),
    db: Session = Depends(get_db)
):
    """创建学习模块"""
    try:
        # 验证计划是否存在
        plan = db.query(LearningPlan).filter(LearningPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="学习计划不存在")
        
        module_id = str(uuid.uuid4())
        new_module = LearningModule(
            id=module_id,
            plan_id=plan_id,
            title=title,
            description=description or "",
            order_index=order_index,
            estimated_time=estimated_time
        )
        db.add(new_module)
        db.commit()
        db.refresh(new_module)
        return {"id": module_id, "title": title, "status": "created"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"创建学习模块失败: {str(e)}")

@router.get("/modules/{plan_id}")
def get_modules_by_plan(
    plan_id: str,
    db: Session = Depends(get_db)
):
    """获取学习计划的所有模块"""
    modules = db.query(LearningModule).filter(LearningModule.plan_id == plan_id).order_by(LearningModule.order_index).all()
    return [{
        "id": module.id,
        "title": module.title,
        "description": module.description,
        "order_index": module.order_index,
        "estimated_time": module.estimated_time
    } for module in modules]

@router.delete("/modules/{module_id}")
def delete_module(
    module_id: str,
    db: Session = Depends(get_db)
):
    """删除学习模块"""
    module = db.query(LearningModule).filter(LearningModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="学习模块不存在")
    
    # 删除模块
    db.delete(module)
    db.commit()
    return {"id": module_id, "status": "deleted"}

# ======================
# 学习进度跟踪
# =======================

@router.post("/progress")
def update_learning_progress(
    user_id: str = Form("default"),
    module_id: str = Form(...),
    plan_id: str = Form(...),
    progress: int = Form(...),
    db: Session = Depends(get_db)
):
    """更新学习进度"""
    # 查找是否已有进度记录
    existing_progress = db.query(LearningProgress).filter(
        LearningProgress.user_id == user_id,
        LearningProgress.module_id == module_id
    ).first()
    
    current_time = time.time()
    completed_at = current_time if progress == 100 else None
    
    if existing_progress:
        # 更新现有进度
        existing_progress.progress = progress
        existing_progress.last_updated = current_time
        existing_progress.completed_at = completed_at
    else:
        # 创建新进度记录
        progress_id = str(uuid.uuid4())
        new_progress = LearningProgress(
            id=progress_id,
            user_id=user_id,
            module_id=module_id,
            plan_id=plan_id,
            progress=progress,
            last_updated=current_time,
            completed_at=completed_at
        )
        db.add(new_progress)
    
    db.commit()
    return {"status": "updated", "progress": progress}

@router.get("/progress/{plan_id}")
def get_learning_progress(
    plan_id: str,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """获取学习计划的进度"""
    modules = db.query(LearningModule).filter(LearningModule.plan_id == plan_id).all()
    module_ids = [module.id for module in modules]
    
    progress_records = db.query(LearningProgress).filter(
        LearningProgress.user_id == user_id,
        LearningProgress.module_id.in_(module_ids)
    ).all()
    
    progress_dict = {record.module_id: record.progress for record in progress_records}
    
    # 计算总体进度
    total_modules = len(modules)
    if total_modules > 0:
        # 计算所有模块的平均进度
        total_progress = sum(progress_dict.get(module.id, 0) for module in modules)
        overall_progress = total_progress / total_modules
    else:
        overall_progress = 0
    
    return {
        "overall_progress": int(overall_progress),
        "module_progress": [{
            "module_id": module.id,
            "module_title": module.title,
            "progress": progress_dict.get(module.id, 0)
        } for module in modules]
    }

# ======================
# 笔记管理
# ======================

@router.post("/notes")
def create_note(
    title: str = Form(...),
    content: str = Form(...),
    user_id: str = Form("default"),
    module_id: str = Form(None),
    tags: str = Form(None),
    db: Session = Depends(get_db)
):
    """创建笔记"""
    note_id = str(uuid.uuid4())
    current_time = time.time()
    
    # 解析tags字符串为列表
    tags_list = []
    if tags:
        try:
            tags_list = json.loads(tags)
        except json.JSONDecodeError:
            tags_list = []
    
    new_note = Note(
        id=note_id,
        user_id=user_id,
        module_id=module_id,
        title=title,
        content=content,
        tags=json.dumps(tags_list) if tags_list else "[]",
        created_at=current_time,
        updated_at=current_time
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return {"id": note_id, "title": title, "status": "created"}

@router.get("/notes")
def get_notes(
    user_id: str = "default",
    module_id: str = None,
    db: Session = Depends(get_db)
):
    """获取用户的笔记列表"""
    query = db.query(Note).filter(Note.user_id == user_id)
    if module_id:
        query = query.filter(Note.module_id == module_id)
    
    notes = query.order_by(Note.updated_at.desc()).all()
    return [{
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "module_id": note.module_id,
        "tags": json.loads(note.tags) if note.tags else [],
        "created_at": note.created_at,
        "updated_at": note.updated_at
    } for note in notes]

@router.put("/notes/{note_id}")
def update_note(
    note_id: str,
    title: str = Form(None),
    content: str = Form(None),
    module_id: str = Form(None),
    tags: str = Form(None),
    db: Session = Depends(get_db)
):
    """更新笔记"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    
    if title:
        note.title = title
    if content:
        note.content = content
    if module_id is not None:
        note.module_id = module_id
    if tags is not None:
        try:
            tags_list = json.loads(tags)
            note.tags = json.dumps(tags_list)
        except json.JSONDecodeError:
            pass
    note.updated_at = time.time()
    
    db.commit()
    return {"id": note_id, "status": "updated"}

@router.delete("/notes/{note_id}")
def delete_note(
    note_id: str,
    db: Session = Depends(get_db)
):
    """删除笔记"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    
    db.delete(note)
    db.commit()
    return {"id": note_id, "status": "deleted"}

# ======================
# 测验与练习
# ======================

@router.post("/quizzes")
def create_quiz(
    module_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    time_limit: str = Form(...),
    db: Session = Depends(get_db)
):
    """创建测验"""
    try:
        # 转换 time_limit 为整数
        time_limit_int = int(time_limit)
        quiz_id = str(uuid.uuid4())
        new_quiz = Quiz(
            id=quiz_id,
            module_id=module_id,
            title=title,
            description=description,
            time_limit=time_limit_int
        )
        db.add(new_quiz)
        db.commit()
        db.refresh(new_quiz)
        return {"id": quiz_id, "title": title, "status": "created"}
    except ValueError:
        raise HTTPException(status_code=400, detail="time_limit 必须是有效的整数")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建测验失败: {str(e)}")

@router.get("/quizzes")
def get_quizzes(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """获取测验列表"""
    quizzes = db.query(Quiz).all()
    return [{
        "id": quiz.id,
        "module_id": quiz.module_id,
        "title": quiz.title,
        "description": quiz.description,
        "time_limit": quiz.time_limit
    } for quiz in quizzes]

@router.post("/quizzes/{quiz_id}/questions")
def add_question(
    quiz_id: str,
    content: str = Form(...),
    question_type: str = Form(...),
    options: str = Form(None),
    correct_answer: str = Form(None),
    points: int = Form(10),
    db: Session = Depends(get_db)
):
    """添加问题到测验"""
    question_id = str(uuid.uuid4())
    
    # 解析options字符串为列表
    options_list = []
    if options:
        try:
            options_list = json.loads(options)
        except json.JSONDecodeError:
            options_list = []
    
    new_question = Question(
        id=question_id,
        quiz_id=quiz_id,
        content=content,
        question_type=question_type,
        options=json.dumps(options_list) if options_list else "[]",
        correct_answer=correct_answer,
        points=points
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    return {"id": question_id, "content": content, "status": "created"}

@router.get("/quizzes/{quiz_id}")
def get_quiz_detail(
    quiz_id: str,
    db: Session = Depends(get_db)
):
    """获取测验详情和问题"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="测验不存在")
    
    questions = db.query(Question).filter(Question.quiz_id == quiz_id).all()
    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "time_limit": quiz.time_limit,
        "questions": [{
            "id": q.id,
            "content": q.content,
            "question_type": q.question_type,
            "options": json.loads(q.options) if q.options else [],
            "correct_answer": q.correct_answer,
            "points": q.points
        } for q in questions]
    }

@router.post("/quizzes/{quiz_id}/attempt")
def submit_quiz_attempt(
    quiz_id: str,
    user_id: str = "default",
    answers: str = Form(...),
    db: Session = Depends(get_db)
):
    """提交测验答案"""
    try:
        # 解析 JSON 字符串为字典
        answers_dict = json.loads(answers)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="answers 必须是有效的 JSON 字符串")
    
    # 获取测验的所有问题
    questions = db.query(Question).filter(Question.quiz_id == quiz_id).all()
    if not questions:
        raise HTTPException(status_code=404, detail="测验无问题")
    
    # 计算分数
    score = 0
    total_points = 0
    for question in questions:
        total_points += question.points
        user_answer = answers_dict.get(question.id)
        if user_answer == question.correct_answer:
            score += question.points
    
    # 创建测验尝试记录
    attempt_id = str(uuid.uuid4())
    new_attempt = QuizAttempt(
        id=attempt_id,
        user_id=user_id,
        quiz_id=quiz_id,
        score=score,
        total_points=total_points,
        completed_at=time.time(),
        answers=json.dumps(answers_dict) if answers_dict else "{}"
    )
    db.add(new_attempt)
    db.commit()
    
    # 计算百分比
    percentage = (score / total_points * 100) if total_points > 0 else 0
    
    return {
        "score": score,
        "total_points": total_points,
        "percentage": round(percentage, 2),
        "status": "completed"
    }

@router.post("/quizzes/generate")
async def generate_quiz(
    module_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    question_count: int = Form(5),
    time_limit: int = Form(30),
    db: Session = Depends(get_db)
):
    """通过AI生成测验"""
    try:
        from services.llm import simple_llm
        
        # 获取模块信息
        module = db.query(LearningModule).filter(LearningModule.id == module_id).first()
        if not module:
            raise HTTPException(status_code=404, detail="学习模块不存在")
        
        # 生成测验题目提示
        prompt = f"""请为学习模块 "{module.title}" 生成 {question_count} 个测验题目。
        模块描述: {module.description}
        
        每个题目需要包含：
        1. 题目内容
        2. 题目类型（选择题使用 multiple_choice，判断题使用 true_false，简答题使用 short_answer）
        3. 如果是选择题，需要提供4个选项
        4. 正确答案
        5. 分值（默认10分）
        
        重要要求：
        - 请严格按照指定的JSON格式输出
        - 只返回JSON数据，不要添加任何解释或前言
        - 确保JSON格式正确，可被直接解析
        - 选择题的选项必须是数组格式
        - 正确答案必须与选项中的内容完全匹配
        
        示例输出格式：
        {{"questions": [
            {{"content": "Vue 3的核心特性是什么？", "question_type": "multiple_choice", "options": ["选项A", "选项B", "选项C", "选项D"], "correct_answer": "选项A", "points": 10}},
            {{"content": "FastAPI是基于Python的Web框架吗？", "question_type": "true_false", "options": [], "correct_answer": "True", "points": 10}}
        ]}}
        
        请生成完整的JSON格式数据：
        """
        
        # 调用LLM生成题目
        response = await simple_llm.chat_completion([
            {"role": "user", "content": prompt}
        ])
        
        # 解析LLM响应
        import json
        import re
        try:
            # 尝试从响应中提取JSON部分
            # 查找JSON开始和结束的位置
            json_match = re.search(r'\{\s*"questions"\s*:\s*\[', response)
            if json_match:
                # 找到JSON开始位置
                start_pos = json_match.start()
                # 尝试找到匹配的结束位置
                # 简单的括号匹配逻辑
                brace_count = 0
                end_pos = start_pos
                for i in range(start_pos, len(response)):
                    if response[i] == '{':
                        brace_count += 1
                    elif response[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                # 提取JSON部分
                json_str = response[start_pos:end_pos]
                quiz_data = json.loads(json_str)
            else:
                # 尝试直接解析整个响应
                quiz_data = json.loads(response)
            
            questions = quiz_data.get("questions", [])
            
            # 验证题目数据
            if not questions:
                raise HTTPException(status_code=400, detail="AI未能生成有效的测验题目")
            
            # 验证每个题目的格式
            for i, q in enumerate(questions):
                if "content" not in q:
                    raise HTTPException(status_code=400, detail=f"第{i+1}题缺少题目内容")
                if "question_type" not in q:
                    raise HTTPException(status_code=400, detail=f"第{i+1}题缺少题目类型")
                if "correct_answer" not in q:
                    raise HTTPException(status_code=400, detail=f"第{i+1}题缺少正确答案")
                if q["question_type"] == "multiple_choice" and ("options" not in q or not isinstance(q["options"], list)):
                    raise HTTPException(status_code=400, detail=f"第{i+1}题缺少选项或选项格式错误")
                if "points" not in q:
                    q["points"] = 10
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"AI生成的测验格式错误：{str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"解析测验数据失败：{str(e)}")
        
        
        
        # 创建测验
        quiz_id = str(uuid.uuid4())
        new_quiz = Quiz(
            id=quiz_id,
            module_id=module_id,
            title=title,
            description=description,
            time_limit=time_limit
        )
        db.add(new_quiz)
        db.commit()
        db.refresh(new_quiz)
        
        # 添加题目
        for question_data in questions:
            question_id = str(uuid.uuid4())
            new_question = Question(
                id=question_id,
                quiz_id=quiz_id,
                content=question_data.get("content"),
                question_type=question_data.get("question_type", "multiple_choice"),
                options=json.dumps(question_data.get("options", [])) if "options" in question_data else "[]",
                correct_answer=question_data.get("correct_answer"),
                points=question_data.get("points", 10)
            )
            db.add(new_question)
        
        db.commit()
        
        return {
            "id": quiz_id,
            "title": title,
            "question_count": len(questions),
            "status": "generated"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成测验失败: {str(e)}")

@router.delete("/quizzes/{quiz_id}")
def delete_quiz(
    quiz_id: str,
    db: Session = Depends(get_db)
):
    """删除测验"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="测验不存在")
    
    # 删除相关的问题
    questions = db.query(Question).filter(Question.quiz_id == quiz_id).all()
    for question in questions:
        db.delete(question)
    
    # 删除测验
    db.delete(quiz)
    db.commit()
    return {"id": quiz_id, "status": "deleted"}

# =======================
# 学习分析
# ======================

@router.post("/analytics")
def log_learning_activity(
    user_id: str = Form("default"),
    module_id: str = Form(None),
    activity_type: str = Form("study"),
    duration: int = Form(0),
    metadata: str = Form(None),
    db: Session = Depends(get_db)
):
    """记录学习活动"""
    # 解析 metadata 参数
    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            metadata_dict = {}
    
    analytics_id = str(uuid.uuid4())
    new_analytics = LearningAnalytics(
        id=analytics_id,
        user_id=user_id,
        module_id=module_id,
        activity_type=activity_type,
        duration=duration,
        timestamp=time.time(),
        extra_metadata=json.dumps(metadata_dict) if metadata_dict else "{}"
    )
    db.add(new_analytics)
    db.commit()
    db.refresh(new_analytics)
    return {"id": analytics_id, "status": "logged"}

@router.get("/analytics/{user_id}")
def get_learning_analytics(
    user_id: str = "default",
    start_date: float = None,
    end_date: float = None,
    db: Session = Depends(get_db)
):
    """获取用户的学习分析数据"""
    query = db.query(LearningAnalytics).filter(LearningAnalytics.user_id == user_id)
    if start_date:
        query = query.filter(LearningAnalytics.timestamp >= start_date)
    if end_date:
        query = query.filter(LearningAnalytics.timestamp <= end_date)
    
    activities = query.order_by(LearningAnalytics.timestamp.desc()).all()
    
    # 计算统计数据
    total_study_time = sum(a.duration for a in activities if a.activity_type == "study")
    total_quiz_time = sum(a.duration for a in activities if a.activity_type == "quiz")
    activity_count = len(activities)
    
    return {
        "total_study_time": total_study_time,
        "total_quiz_time": total_quiz_time,
        "activity_count": activity_count,
        "activities": [{
            "id": a.id,
            "activity_type": a.activity_type,
            "duration": a.duration,
            "timestamp": a.timestamp,
            "metadata": json.loads(a.extra_metadata) if a.extra_metadata else {}
        } for a in activities]
    }

@router.get("/analytics/default")
def get_default_learning_analytics(
    start_date: float = None,
    end_date: float = None,
    db: Session = Depends(get_db)
):
    """获取默认用户的学习分析数据"""
    user_id = "default"
    query = db.query(LearningAnalytics).filter(LearningAnalytics.user_id == user_id)
    if start_date:
        query = query.filter(LearningAnalytics.timestamp >= start_date)
    if end_date:
        query = query.filter(LearningAnalytics.timestamp <= end_date)
    
    activities = query.order_by(LearningAnalytics.timestamp.desc()).all()
    
    # 计算统计数据
    total_study_time = sum(a.duration for a in activities if a.activity_type == "study")
    total_quiz_time = sum(a.duration for a in activities if a.activity_type == "quiz")
    activity_count = len(activities)
    
    return {
        "total_study_time": total_study_time,
        "total_quiz_time": total_quiz_time,
        "activity_count": activity_count,
        "activities": [{
            "id": a.id,
            "activity_type": a.activity_type,
            "duration": a.duration,
            "timestamp": a.timestamp,
            "metadata": json.loads(a.extra_metadata) if a.extra_metadata else {}
        } for a in activities]
    }

# ======================
# 协作学习
# ======================

@router.post("/collaboration")
def join_collaboration(
    plan_id: str = Form(...),
    user_id: str = Form("default"),
    role: str = Form("contributor"),
    db: Session = Depends(get_db)
):
    """加入协作学习计划"""
    # 检查学习计划是否存在
    plan = db.query(LearningPlan).filter(LearningPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    
    # 检查是否已经加入
    existing = db.query(Collaboration).filter(
        Collaboration.plan_id == plan_id,
        Collaboration.user_id == user_id
    ).first()
    
    if existing:
        return {"status": "already_joined", "role": existing.role}
    
    # 创建协作记录
    collaboration_id = str(uuid.uuid4())
    new_collaboration = Collaboration(
        id=collaboration_id,
        plan_id=plan_id,
        user_id=user_id,
        role=role,
        joined_at=time.time()
    )
    db.add(new_collaboration)
    db.commit()
    db.refresh(new_collaboration)
    return {"id": collaboration_id, "role": role, "status": "joined"}

@router.get("/collaboration/{plan_id}")
def get_collaborators(
    plan_id: str,
    db: Session = Depends(get_db)
):
    """获取学习计划的协作者"""
    collaborations = db.query(Collaboration).filter(Collaboration.plan_id == plan_id).all()
    return [{
        "user_id": c.user_id,
        "role": c.role,
        "joined_at": c.joined_at
    } for c in collaborations]

@router.delete("/collaboration/{plan_id}")
def leave_collaboration(
    plan_id: str,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """退出协作学习计划"""
    # 查找协作记录
    collaboration = db.query(Collaboration).filter(
        Collaboration.plan_id == plan_id,
        Collaboration.user_id == user_id
    ).first()
    
    if not collaboration:
        raise HTTPException(status_code=404, detail="协作记录不存在")
    
    # 删除协作记录
    db.delete(collaboration)
    db.commit()
    
    return {"status": "success", "message": "成功退出协作"}

# ======================
# 智能推荐系统
# ======================

@router.get("/recommendations")
def get_learning_recommendations(
    user_id: str = "default",
    limit: int = Query(5, ge=1, le=10, description="推荐数量限制"),
    db: Session = Depends(get_db)
):
    """获取学习推荐"""
    try:
        recommendations = recommendation_service.get_recommendations(user_id, db, limit)
        return {
            "status": "success",
            "recommendations": recommendations,
            "total": len(recommendations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取推荐失败: {str(e)}")

@router.get("/recommendations/{user_id}")
def get_user_recommendations(
    user_id: str,
    limit: int = Query(5, ge=1, le=10, description="推荐数量限制"),
    db: Session = Depends(get_db)
):
    """获取指定用户的学习推荐"""
    try:
        recommendations = recommendation_service.get_recommendations(user_id, db, limit)
        return {
            "status": "success",
            "user_id": user_id,
            "recommendations": recommendations,
            "total": len(recommendations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取推荐失败: {str(e)}")

# ======================
# 个性化学习
# ======================

@router.post("/preferences")
def update_learning_preferences(
    user_id: str = Form("default"),
    learning_style: str = Form(None),
    preferred_difficulty: str = Form(None),
    study_time_preference: str = Form(None),
    goals: str = Form(None),
    db: Session = Depends(get_db)
):
    """更新学习偏好"""
    current_time = time.time()
    
    # 解析goals字符串为字典
    goals_dict = {}
    if goals:
        try:
            goals_dict = json.loads(goals)
        except json.JSONDecodeError:
            goals_dict = {}
    
    # 查找是否已有偏好记录
    existing_preference = db.query(LearningPreference).filter(
        LearningPreference.user_id == user_id
    ).first()
    
    if existing_preference:
        # 更新现有记录
        if learning_style:
            existing_preference.learning_style = learning_style
        if preferred_difficulty:
            existing_preference.preferred_difficulty = preferred_difficulty
        if study_time_preference:
            existing_preference.study_time_preference = study_time_preference
        if goals_dict:
            existing_preference.goals = json.dumps(goals_dict)
        existing_preference.updated_at = current_time
    else:
        # 创建新记录
        preference_id = str(uuid.uuid4())
        new_preference = LearningPreference(
            id=preference_id,
            user_id=user_id,
            learning_style=learning_style or "visual",
            preferred_difficulty=preferred_difficulty or "medium",
            study_time_preference=study_time_preference or "afternoon",
            goals=json.dumps(goals_dict) if goals_dict else "{}",
            created_at=current_time,
            updated_at=current_time
        )
        db.add(new_preference)
    
    db.commit()
    return {"status": "success", "message": "学习偏好已更新"}

@router.get("/preferences/{user_id}")
def get_learning_preferences(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """获取用户学习偏好"""
    preference = db.query(LearningPreference).filter(
        LearningPreference.user_id == user_id
    ).first()
    
    if not preference:
        return {
            "status": "success",
            "preferences": None,
            "message": "暂无学习偏好记录"
        }
    
    return {
        "status": "success",
        "preferences": {
            "id": preference.id,
            "user_id": preference.user_id,
            "learning_style": preference.learning_style,
            "preferred_difficulty": preference.preferred_difficulty,
            "study_time_preference": preference.study_time_preference,
            "goals": json.loads(preference.goals) if preference.goals else {},
            "created_at": preference.created_at,
            "updated_at": preference.updated_at
        }
    }

@router.post("/behaviors")
def log_learning_behavior(
    user_id: str = Form("default"),
    module_id: str = Form(None),
    behavior_type: str = Form("view"),
    duration: int = Form(0),
    metadata: str = Form(None),
    db: Session = Depends(get_db)
):
    """记录学习行为"""
    behavior_id = str(uuid.uuid4())
    current_time = time.time()
    
    # 解析metadata字符串为字典
    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            metadata_dict = {}
    
    new_behavior = LearningBehavior(
        id=behavior_id,
        user_id=user_id,
        module_id=module_id,
        behavior_type=behavior_type,
        duration=duration,
        timestamp=current_time,
        extra_metadata=json.dumps(metadata_dict) if metadata_dict else "{}"
    )
    
    db.add(new_behavior)
    db.commit()
    return {"status": "success", "id": behavior_id}

# ======================
# 高级数据分析
# ======================

@router.get("/analytics/behavior/{user_id}")
def get_learning_behavior_analysis(
    user_id: str = "default",
    start_date: float = None,
    end_date: float = None,
    db: Session = Depends(get_db)
):
    """获取学习行为分析"""
    query = db.query(LearningBehavior).filter(LearningBehavior.user_id == user_id)
    
    if start_date:
        query = query.filter(LearningBehavior.timestamp >= start_date)
    if end_date:
        query = query.filter(LearningBehavior.timestamp <= end_date)
    
    behaviors = query.order_by(LearningBehavior.timestamp.desc()).all()
    
    # 计算统计数据
    behavior_stats = {}
    total_duration = 0
    
    for behavior in behaviors:
        if behavior.behavior_type not in behavior_stats:
            behavior_stats[behavior.behavior_type] = {
                "count": 0,
                "total_duration": 0
            }
        behavior_stats[behavior.behavior_type]["count"] += 1
        behavior_stats[behavior.behavior_type]["total_duration"] += behavior.duration
        total_duration += behavior.duration
    
    return {
        "status": "success",
        "total_duration": total_duration,
        "behavior_stats": behavior_stats,
        "behaviors": [{
            "id": b.id,
            "behavior_type": b.behavior_type,
            "duration": b.duration,
            "timestamp": b.timestamp,
            "module_id": b.module_id,
            "metadata": json.loads(b.extra_metadata) if b.extra_metadata else {}
        } for b in behaviors]
    }

@router.get("/analytics/behavior/default")
def get_default_learning_behavior_analysis(
    start_date: float = None,
    end_date: float = None,
    db: Session = Depends(get_db)
):
    """获取默认用户的学习行为分析"""
    user_id = "default"
    return get_learning_behavior_analysis(user_id, start_date, end_date, db)

@router.get("/analytics/prediction/{user_id}")
def get_learning_predictions(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """获取学习预测数据"""
    predictions = db.query(LearningPrediction).filter(
        LearningPrediction.user_id == user_id
    ).order_by(LearningPrediction.created_at.desc()).all()
    
    return {
        "status": "success",
        "predictions": [{
            "id": p.id,
            "module_id": p.module_id,
            "predicted_completion_time": p.predicted_completion_time,
            "difficulty_prediction": p.difficulty_prediction,
            "success_probability": p.success_probability,
            "created_at": p.created_at
        } for p in predictions]
    }

@router.get("/analytics/prediction/default")
def get_default_learning_predictions(
    db: Session = Depends(get_db)
):
    """获取默认用户的学习预测数据"""
    user_id = "default"
    return get_learning_predictions(user_id, db)

@router.post("/analytics/generate-prediction")
def generate_learning_prediction(
    user_id: str = Form(default="default"),
    module_id: Optional[str] = Form(default=None),
    db: Session = Depends(get_db)
):
    """生成学习预测"""
    # 打印参数值
    print(f"接收到的参数: user_id={user_id}, module_id={module_id}")
    # 简单的预测逻辑，实际项目中可以使用更复杂的算法
    prediction_id = str(uuid.uuid4())
    current_time = time.time()
    
    # 基于历史行为数据进行预测
    history_behaviors = db.query(LearningBehavior).filter(
        LearningBehavior.user_id == user_id,
        LearningBehavior.module_id == module_id
    ).all()
    
    # 计算平均学习时间
    avg_duration = 0
    if history_behaviors:
        total_duration = sum(b.duration for b in history_behaviors)
        avg_duration = total_duration / len(history_behaviors)
    else:
        avg_duration = 3600  # 默认1小时
    
    # 生成预测
    predicted_completion_time = current_time + avg_duration
    difficulty_prediction = "medium"  # 默认中等难度
    success_probability = 0.7  # 默认70%成功概率
    
    # 查找是否已有预测记录
    existing_prediction = db.query(LearningPrediction).filter(
        LearningPrediction.user_id == user_id,
        LearningPrediction.module_id == module_id
    ).first()
    
    if existing_prediction:
        # 更新现有预测
        existing_prediction.predicted_completion_time = predicted_completion_time
        existing_prediction.difficulty_prediction = difficulty_prediction
        existing_prediction.success_probability = success_probability
        existing_prediction.created_at = current_time
    else:
        # 创建新预测
        new_prediction = LearningPrediction(
            id=prediction_id,
            user_id=user_id,
            module_id=module_id,
            predicted_completion_time=predicted_completion_time,
            difficulty_prediction=difficulty_prediction,
            success_probability=success_probability,
            created_at=current_time
        )
        db.add(new_prediction)
    
    db.commit()
    
    return {
        "status": "success",
        "prediction": {
            "id": existing_prediction.id if existing_prediction else prediction_id,
            "user_id": user_id,
            "module_id": module_id,
            "predicted_completion_time": predicted_completion_time,
            "difficulty_prediction": difficulty_prediction,
            "success_probability": success_probability,
            "created_at": current_time
        }
    }

@router.get("/analytics/comparison/{user_id}")
def get_learning_comparison(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """获取学习对比分析"""
    # 获取用户的学习数据
    user_progress = db.query(LearningProgress).filter(
        LearningProgress.user_id == user_id
    ).all()
    
    # 计算用户的平均进度
    user_avg_progress = 0
    if user_progress:
        user_avg_progress = sum(p.progress for p in user_progress) / len(user_progress)
    
    # 简单的对比逻辑，实际项目中可以与其他用户或历史数据对比
    return {
        "status": "success",
        "comparison": {
            "user_avg_progress": user_avg_progress,
            "average_progress": 50,  # 默认平均进度
            "percentile": 75,  # 默认百分位数
            "recommendations": [
                "继续保持当前的学习节奏",
                "可以尝试增加学习时间",
                "建议重点关注未完成的模块"
            ]
        }
    }

@router.get("/analytics/comparison/default")
def get_default_learning_comparison(
    db: Session = Depends(get_db)
):
    """获取默认用户的学习对比分析"""
    user_id = "default"
    return get_learning_comparison(user_id, db)
