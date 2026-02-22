from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import FileTextStore, AnalysisHistory
import json
from datetime import datetime

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"]
)

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    获取仪表盘统计数据：
    1. 热力图数据 (按日期统计上传量)
    2. 文件类型占比
    3. 词云数据 (Top 50 关键词)
    4. 总字数统计
    """
    try:
        # 1. 知识热力图 (Activity Heatmap)
        # SQLite 的 date 函数用法可能略有不同，但通常支持 date(created_at)
        # 注意: SQLAlchemy 的 func.date 在不同数据库下行为可能不同
        # 这里假设是 SQLite
        heatmap_data = db.query(
            func.date(FileTextStore.created_at).label("date"), 
            func.count(FileTextStore.file_id).label("count")
        ).group_by(func.date(FileTextStore.created_at)).all()
        
        # 转换格式为前端易读的列表: [['2023-01-01', 5], ...]
        heatmap_list = [[str(row.date), row.count] for row in heatmap_data if row.date]

        # 2. 文件分类占比 (File Type Distribution)
        all_files = db.query(FileTextStore.original_filename).all()
        type_counts = {"PDF": 0, "Video": 0, "Log": 0, "Other": 0}
        
        for f in all_files:
            if not f.original_filename:
                continue
            ext = f.original_filename.split('.')[-1].lower() if '.' in f.original_filename else ""
            
            if ext == 'pdf':
                type_counts['PDF'] += 1
            elif ext in ['mp4', 'bv', 'avi', 'mov']:
                type_counts['Video'] += 1
            elif ext in ['log', 'txt']:
                type_counts['Log'] += 1
            else:
                type_counts['Other'] += 1
        
        # 转换为 ECharts Pie 格式
        pie_data = [{"name": k, "value": v} for k, v in type_counts.items() if v > 0]

        # 3. 领域词云 (Topic Word Cloud)
        word_freq = {}
        # 只查询有关键词的记录
        all_keywords = db.query(FileTextStore.keywords).filter(FileTextStore.keywords.isnot(None)).all()
        
        for kw_json in all_keywords:
            try:
                # 兼容可能存储为空字符串或非JSON的情况
                if not kw_json[0]:
                    continue
                keywords = json.loads(kw_json[0])
                if isinstance(keywords, list):
                    # Define blocklist for immediate cleanup on read
                    structure_stops = {
                        '核心主题', '现象', '原因', '解决方案', '影响范围', '攻击手段', 
                        '深度分析', '总结', '创新点', '方法论', '结论', '树形思维导图', 
                        '文本描述', '子节点', '分析完成', 'terminate', 'novelty', 
                        'methodology', 'conclusion', 'chapter', 'summary', 'concepts',
                        'end-to-endlogging', # Specific bad case seen in screenshot
                        '树形思维导图文本描述', '第三部分', '第二部分', '第一部分',
                        '深度分析总结'
                    }
                    for k in keywords:
                        k = k.strip()
                        # Filtering logic:
                        # 1. Must be non-empty and > 1 char
                        # 2. Must NOT be in blocklist
                        # 3. Must NOT be too long (filtering out sentences, but allowing longer technical terms) - max 20 chars
                        if (k and len(k) > 1 and len(k) < 20 and
                            k.lower() not in structure_stops):
                            word_freq[k] = word_freq.get(k, 0) + 1
                        else:
                            # DEBUG: Verify what is being dropped
                            pass 
                            # print(f"Dropped keyword: {k} (Len: {len(k)})")
            except Exception:
                continue
        
        # 取前 100 个高频词
        top_words = sorted(word_freq.items(), key=lambda x: -x[1])[:100]
        wordcloud_data = [{"name": k, "value": v} for k, v in top_words]

        # 4. 总字数 (Total Word Count)
        total_chars = db.query(func.sum(func.length(FileTextStore.text))).scalar() or 0

        return {
            "heatmap": heatmap_list,
            "file_types": pie_data,
            "word_cloud": wordcloud_data,
            "total_chars": total_chars
        }

    except Exception as e:
        print(f"Error generating dashboard stats: {e}")
        # 出错时返回空数据，避免页面崩溃
        return {
            "heatmap": [],
            "file_types": [],
            "word_cloud": [],
            "total_chars": 0
        }
