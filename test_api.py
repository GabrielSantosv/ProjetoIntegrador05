import requests

resp = requests.get('http://localhost:8000/api/documents/')
print(f'Status: {resp.status_code}')
data = resp.json()
print(f'Documentos: {len(data)}')
for doc in data[:3]:
    print(f"  - {doc['title']} ({doc['status']})")
