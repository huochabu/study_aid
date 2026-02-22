from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from services.review_service import ReviewService
from models import FileTextStore
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/review",
    tags=["review"]
)

class ReviewRequest(BaseModel):
    file_id: str
    text: str = None # Optional

@router.post("/generate")
async def generate_review(request: ReviewRequest, db: Session = Depends(get_db)):
    """
    Generate an AI Peer Review for a given file.
    """
    try:
        text = request.text
        if not text and request.file_id:
             # Fetch text from DB
             record = db.query(FileTextStore).filter(FileTextStore.file_id == request.file_id).first()
             if record and record.text:
                 text = record.text
             else:
                 # Try to load from disk if DB is empty (legacy consistency)
                 pass
        
        if not text:
            raise HTTPException(status_code=404, detail="File content not found.")

        logger.info(f"Generating review for file_id: {request.file_id} (Length: {len(text)})")
        review_data = await ReviewService.generate_review(text)
        
        return {"status": "success", "data": review_data}

    except Exception as e:
        logger.error(f"Review generation failed: {e}")
        return {"status": "error", "message": str(e)}
