
import httpx
import asyncio
import sys

BASE_URL = "http://localhost:8000"

async def test_deduplication():
    # 1. Upload a dummy file first to get a file_id
    dummy_pdf_content = b"%PDF-1.4\n..." # Minimal PDF header
    # Actually, let's use a simple text upload endpoint or just assume we have a file_id
    # But to be robust, let's list files first and pick one.
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check health
        try:
            await client.get(f"{BASE_URL}/")
        except:
            print("Server not running!")
            sys.exit(1)
            
        print("Fetching existing files...")
        files_resp = await client.get(f"{BASE_URL}/files")
        files_data = files_resp.json()
        
        if not files_data.get("files"):
            print("No files found. Cannot test. Please upload a file manually or use existing history.")
            # Fallback: Create a dummy one? Too complex.
            # Let's just create a dummy file ID in DB? No, that requires DB access.
            # Let's hope inspect_qa_history.py showed us a file ID: d31a8035-daa6-469c-a117-bd2410bace91
            file_id = "d31a8035-daa6-469c-a117-bd2410bace91"
            print(f"Using fallback file_id: {file_id}")
        else:
            file_id = files_data["files"][0]["file_id"]
            print(f"Using file_id: {file_id}")
            
        question = "Testing duplication logic " + str(sys.argv[1] if len(sys.argv) > 1 else "123")
        print(f"Sending Question 1: {question}")
        
        # Request 1
        resp1 = await client.get(f"{BASE_URL}/ask", params={"question": question, "file_id": file_id})
        print(f"Resp 1: {resp1.status_code}")
        
        # Request 2 (Immediately)
        print(f"Sending Question 2 (Duplicate): {question}")
        resp2 = await client.get(f"{BASE_URL}/ask", params={"question": question, "file_id": file_id})
        print(f"Resp 2: {resp2.status_code}")
        
        data2 = resp2.json()
        if data2.get("note") == "cached":
            print("✅ Deduplication SUCCESS: Cached response received.")
        else:
            print("❌ Deduplication FAILED: New response generated or note missing.")
            print(data2)

if __name__ == "__main__":
    asyncio.run(test_deduplication())
