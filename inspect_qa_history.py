
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal
from models.qa_history import QAHistory

def inspect_history():
    db = SessionLocal()
    try:
        # Get all QA records
        records = db.query(QAHistory).order_by(QAHistory.created_at.desc()).all()
        print(f"Total QA Records: {len(records)}")
        
        seen = {}
        for r in records:
            key = (r.file_id, r.question)
            time_str = str(r.created_at)
            print(f"ID: {r.id} | File: {r.file_id} | Time: {time_str} | Q: {r.question[:30]}...")
            
            if key in seen:
                print(f"⚠️ POTENTIAL DUPLICATE with {seen[key]}")
            seen[key] = r.id
            
    finally:
        db.close()

if __name__ == "__main__":
    inspect_history()
