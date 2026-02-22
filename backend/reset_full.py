import sys
import os
import shutil

# Add current directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import FileTextStore, AnalysisHistory
from models.qa_history import QAHistory
from models.graph import GlobalNode, GlobalEdge
from models.teacher_rule import TeacherRule

def reset_system():
    print("🚀 Starting Full System Reset...")
    
    # 1. Clear Database
    db = SessionLocal()
    try:
        print("🧹 Clearing Database Tables...")
        
        # Order matters for foreign keys?
        # Graph edges depend on nodes
        db.query(GlobalEdge).delete()
        print("   - GlobalEdge cleared")
        
        db.query(GlobalNode).delete()
        print("   - GlobalNode cleared")
        
        db.query(TeacherRule).delete()
        print("   - TeacherRule cleared")
        
        db.query(QAHistory).delete()
        print("   - QAHistory cleared")
        
        db.query(AnalysisHistory).delete()
        print("   - AnalysisHistory cleared")
        
        db.query(FileTextStore).delete()
        print("   - FileTextStore cleared")
        
        db.commit()
        print("✅ Database cleared successfully.")
    except Exception as e:
        print(f"❌ Database cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()

    # 2. Clear Upload Directory
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../uploads")
    if os.path.exists(upload_dir):
        print(f"🧹 Clearing Upload Directory: {upload_dir}")
        count = 0
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    count += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    count += 1
            except Exception as e:
                print(f"   Failed to delete {file_path}. Reason: {e}")
        print(f"✅ Deleted {count} files/folders.")
    else:
        print("⚠️ Upload directory not found.")
        
    print("🎉 System Reset Complete!")

if __name__ == "__main__":
    reset_system()
