import urllib.request
import json

data = json.dumps({"external_id": "admin_user", "role": "admin", "department": "IT"}).encode('utf-8')
req = urllib.request.Request("http://localhost:8080/auth/login", data=data, headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req) as res:
    token_resp = json.loads(res.read().decode('utf-8'))
    token = token_resp['access_token']

scan_data = json.dumps({"path": "D:\\PDFs"}).encode('utf-8')
req2 = urllib.request.Request("http://localhost:8080/api/v1/folders/scan", data=scan_data, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}, method='POST')
with urllib.request.urlopen(req2, timeout=600) as res2:
    print(res2.read().decode('utf-8'))
