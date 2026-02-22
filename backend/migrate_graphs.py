import logging
import json
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import AnalysisHistory
from services.graph_service import GraphService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_historical_graphs():
    """
    Reads all AnalysisHistory records and syncs their knowledge graphs 
    into the new Global Graph tables (global_nodes, global_edges).
    """
    db: Session = SessionLocal()
    try:
        # Get all history records
        history_records = db.query(AnalysisHistory).all()
        logger.info(f"📚 Found {len(history_records)} historical analysis records.")
        
        service = GraphService(db)
        total_nodes = 0
        total_edges = 0
        
        for record in history_records:
            try:
                result_data = record.get_result_dict()
                kg = result_data.get("knowledge_graph", {})
                
                nodes = kg.get("nodes", [])
                edges = kg.get("edges", [])
                
                if not nodes and not edges:
                    logger.warning(f"⚠️ Empty graph for file: {record.filename} ({record.file_id})")
                    continue
                
                logger.info(f"🔄 Syncing {record.filename}: {len(nodes)} nodes, {len(edges)} edges")
                
                # Add Nodes
                for node in nodes:
                    node_name = node.get("label") or node.get("id")
                    if node_name:
                        service.add_node(
                            name=node_name,
                            category=node.get("type", "Concept"),
                            source_doc_id=record.file_id
                        )
                        total_nodes += 1
                
                # Add Edges
                for edge in edges:
                    service.add_edge(
                        source_name=edge.get("source"),
                        target_name=edge.get("target"),
                        relation=edge.get("relation", "related_to")
                    )
                    total_edges += 1
                    
            except Exception as e:
                logger.error(f"❌ Failed to process record {record.id}: {e}")
        
        # Re-calculate stats
        logger.info("📊 Updating Graph Statistics (PageRank)...")
        service.update_pagerank()
        
        logger.info(f"✅ Migration Complete! Added {total_nodes} nodes and {total_edges} edges.")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Starting Knowledge Graph Migration...")
    migrate_historical_graphs()
