import requests
import json

# Test specific document endpoint
for doc_id in [1, 4]:
    try:
        resp = requests.get(f'http://localhost:8000/api/documents/{doc_id}/')
        print(f'\nDocument {doc_id}:')
        print(f'  Status: {resp.status_code}')
        if resp.status_code == 200:
            data = resp.json()
            print(f'  Title: {data.get("title", "N/A")}')
        else:
            print(f'  Error: {resp.text[:300]}')
    except Exception as e:
        print(f'  Exception: {e}')
