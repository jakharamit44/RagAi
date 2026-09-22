import time
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def wait_for_server(max_retries=15, delay=2):
    print("Checking if server is online...")
    for i in range(max_retries):
        try:
            r = requests.get(f"{BASE_URL}/api/v1/version", timeout=3)
            if r.status_code == 200:
                print("Server is UP and operational!", r.json())
                return True
        except Exception as e:
            pass
        time.sleep(delay)
    print("Server failed to respond within timeout.")
    return False

def run_tests():
    if not wait_for_server():
        return False

    session_id = f"test_session_{int(time.time())}"
    print(f"\n1. Testing Student Query to /api/v1/ask with session_id='{session_id}'...")
    ask_payload = {
        "question": "What is the examination datesheet for BCA and B.Tech in MDU?",
        "session_id": session_id,
        "department": "Computer Science",
        "stream": False
    }
    r = requests.post(f"{BASE_URL}/api/v1/ask", json=ask_payload, timeout=30)
    print(f"Ask response status: {r.status_code}")
    assert r.status_code == 200, f"Ask failed: {r.text}"
    ask_data = r.json()
    print(f"Answer snippet: {ask_data.get('answer', '')[:120]}...")
    print(f"Confidence: {ask_data.get('confidence')}, CRAG: {ask_data.get('crag_decision')}")
    assert ask_data.get("session_id") == session_id

    time.sleep(1) # Allow async background write to complete

    print(f"\n2. Testing Feedback Submission for query_id='{session_id}'...")
    fb_payload = {
        "query_id": session_id,
        "feedback": "down",
        "reason": "Needs more details on roll number slip and center timings"
    }
    r_fb = requests.post(f"{BASE_URL}/api/v1/feedback", json=fb_payload, timeout=10)
    print(f"Feedback status: {r_fb.status_code}, response: {r_fb.json()}")
    assert r_fb.status_code == 200

    time.sleep(1) # Allow async background feedback update to complete

    print("\n3. Testing Admin Login to get JWT Bearer token...")
    login_payload = {
        "username": "admin",
        "password": "Admin@MDU2026!"
    }
    r_login = requests.post(f"{BASE_URL}/api/v1/admin/auth/login", json=login_payload, timeout=10)
    print(f"Login status: {r_login.status_code}")
    assert r_login.status_code == 200, f"Admin login failed: {r_login.text}"
    token = r_login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    print("\n4. Testing GET /api/v1/admin/conversations/sessions...")
    r_sess = requests.get(f"{BASE_URL}/api/v1/admin/conversations/sessions", headers=headers, timeout=10)
    print(f"Sessions status: {r_sess.status_code}")
    assert r_sess.status_code == 200
    sess_data = r_sess.json()
    print(f"Total sessions: {sess_data.get('total')}, Page: {sess_data.get('page')}")
    found = any(s["session_id"] == session_id for s in sess_data.get("items", []))
    print(f"Target test session found in admin list: {found}")
    assert found, "Created session was not returned in admin sessions list!"

    print(f"\n5. Testing GET /api/v1/admin/conversations/sessions/{session_id}...")
    r_det = requests.get(f"{BASE_URL}/api/v1/admin/conversations/sessions/{session_id}", headers=headers, timeout=10)
    print(f"Session detail status: {r_det.status_code}")
    assert r_det.status_code == 200
    det_data = r_det.json()
    print(f"Session title: {det_data['session']['title']}")
    print(f"Has negative feedback: {det_data['session']['has_negative_feedback']}")
    print(f"Messages count: {len(det_data.get('messages', []))}")
    assert len(det_data.get("messages", [])) >= 2, "Expected at least 2 messages (user + assistant)!"
    asst_msg = [m for m in det_data["messages"] if m["sender"] == "assistant"][0]
    print(f"Assistant feedback recorded: {asst_msg['feedback']}, reason: {asst_msg['feedback_reason']}")
    assert asst_msg["feedback"] == "down", f"Expected feedback 'down', got {asst_msg['feedback']}"

    print("\n6. Testing GET /api/v1/admin/conversations/stats...")
    r_stats = requests.get(f"{BASE_URL}/api/v1/admin/conversations/stats", headers=headers, timeout=10)
    print(f"Stats status: {r_stats.status_code}")
    assert r_stats.status_code == 200
    stats_data = r_stats.json()
    print(f"Stats overview: Total Sessions={stats_data['total_sessions']}, Total Messages={stats_data['total_messages']}, Negative Feedback={stats_data['negative_feedback_count']}, Satisfaction={stats_data['satisfaction_rate_pct']}%")

    print("\n7. Testing Autonomous AI Self-Improvement Hook POST /api/v1/admin/conversations/optimize-from-failures...")
    r_opt = requests.post(f"{BASE_URL}/api/v1/admin/conversations/optimize-from-failures", headers=headers, timeout=120)
    print(f"Optimize status: {r_opt.status_code}")
    assert r_opt.status_code == 200
    opt_data = r_opt.json()
    print("Self-improvement cycle result:")
    print(json.dumps(opt_data, indent=2))
    assert opt_data.get("status") == "success"

    print("\nALL END-TO-END CONVERSATION PERSISTENCE, ADMIN INSPECTOR, AND AI SELF-IMPROVEMENT TESTS PASSED! [PASS]")
    return True

if __name__ == "__main__":
    run_tests()
