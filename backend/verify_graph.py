import requests
import json

BASE_URL = "http://localhost:8000"

def seed_graph():
    try:
        print("🌱 Seeding graph data...")
        response = requests.get(f"{BASE_URL}/api/graph/seed")
        if response.status_code == 200:
            print("✅ Seeding successful:", response.json())
        else:
            print(f"❌ Seeding failed ({response.status_code}):", response.text)
    except Exception as e:
        print(f"❌ Connection failed: {e}")

def check_graph_data():
    try:
        print("🔍 Checking graph data...")
        response = requests.get(f"{BASE_URL}/api/graph/data")
        if response.status_code == 200:
            data = response.json()
            nodes = data.get("nodes", [])
            links = data.get("links", [])
            print(f"✅ Graph data retrieved: {len(nodes)} nodes, {len(links)} links")
        else:
            print(f"❌ Failed to get data ({response.status_code}):", response.text)
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    seed_graph()
    check_graph_data()
