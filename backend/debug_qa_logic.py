import asyncio
import json
from sqlalchemy.orm import Session
from database import SessionLocal
from services.graph_service import GraphService
from services.llm import simple_llm
import re

async def debug_qa(question: str):
    db: Session = SessionLocal()
    service = GraphService(db)
    
    print(f"\n--- Debugging Question: '{question}' ---")
    
    # 1. Entity Extraction
    extraction_prompt = [
        {"role": "system", "content": "You are a helper to extract technical entities from a user question. Return only a JSON list of strings, e.g. [\"Transformer\", \"CNN\"]. Do not apologize or explain."},
        {"role": "user", "content": f"Extract key technical terms or concepts from this question: '{question}'"}
    ]
    
    entities = []
    try:
        raw_entities = await simple_llm.chat_completion(extraction_prompt)
        print(f"Raw Entities Output: {raw_entities}")
        match = re.search(r'\[.*\]', raw_entities, re.DOTALL)
        if match:
            entities = json.loads(match.group(0))
        else:
            entities = raw_entities.split(',')
    except Exception as e:
        print(f"Entity extraction failed: {e}")
        
    print(f"Parsed Entities: {entities}")
    
    # 2. Context Retrieval
    context, context_data = service.get_subgraph_context(entities)
    print(f"\nContext Text Length: {len(context)}")
    print(f"Context Text Preview: {context[:200]}...")
    print(f"Context Data (Nodes): {[n for n in context_data.get('nodes', [])]}")
    print(f"Context Data (Edges): {len(context_data.get('edges', []))}")
    
    # 3. Check Grounding Logic
    if not context:
        print("RESULT: No Context Found. Should return 'No info'.")
    else:
        print("RESULT: Context Found. Should highlight nodes.")
        
    # 4. Generate Answer (Test Grounding)
    print("\n--- Generating Answer ---")
    qa_prompt = [
        {"role": "system", "content": "You are an advanced AI assistant with access to a Global Knowledge Graph. \nCRITICAL INSTRUCTION: You must answer the user's question STRICTLY based on the provided Graph Context. \n- If the context contains relevant information, answer and explicitly cite the logic paths (e.g., A -> B -> C).\n- If the context is empty or irrelevant, you must say 'My internal knowledge graph does not contain information about this yet.'\n- DO NOT use your own outside knowledge to answer if the graph is silent."},
        {"role": "user", "content": f"Graph Context:\n{context}\n\nQuestion: {question}"}
    ]
    
    answer = await simple_llm.chat_completion(qa_prompt)
    print(f"FINAL ANSWER:\n{answer}")

if __name__ == "__main__":
    # Test with a term we know exists from seed data, e.g., "Deep Learning"
    asyncio.run(debug_qa("What is Deep Learning based on?"))
    
    # Test with nonsense
    asyncio.run(debug_qa("What is the capital of Mars?"))
