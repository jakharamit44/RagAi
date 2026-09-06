import urllib.request
import urllib.error
import json
import time

API_URL = "http://localhost:8080/api/v1/ask"

QUESTIONS = [
    "What are the specific dates and paper codes for the B.Sc.(Bio-tech) 5th Semester Physical Chemistry exam versus the M.Sc. 3rd Semester Medical Bio Tech 'Stem Cell Biology' exam, and how many years apart are these two exams scheduled?",
    "Which M.Sc. 3rd Semester subjects have examinations scheduled on both June 2nd, 2026 and June 6th, 2026? Please list the full nomenclatures of those subjects."
]

def wait_for_api():
    print("Waiting for API to be ready...")
    for _ in range(60):
        try:
            req = urllib.request.Request("http://localhost:8080/docs")
            with urllib.request.urlopen(req) as res:
                if res.getcode() == 200:
                    print("API is ready.")
                    time.sleep(5)
                    return True
        except urllib.error.URLError:
            pass
        time.sleep(2)
    return False

def main():
    if not wait_for_api():
        print("API failed to start.")
        return

    results = []
    
    for q in QUESTIONS:
        print(f"Asking: {q}")
        payload = json.dumps({
            "question": q,
            "stream": False
        }).encode('utf-8')
        
        req = urllib.request.Request(API_URL, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
        
        try:
            start_time = time.time()
            with urllib.request.urlopen(req, timeout=120) as response:
                elapsed = time.time() - start_time
                if response.getcode() == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    results.append({
                        "question": q,
                        "answer": data.get("answer", ""),
                        "citations": data.get("citations", []),
                        "time": round(elapsed, 2)
                    })
                    print(f"Success in {elapsed:.2f}s")
                else:
                    print(f"Error {response.getcode()}")
                    results.append({
                        "question": q,
                        "answer": f"Error: {response.getcode()}",
                        "citations": []
                    })
        except Exception as e:
            print(f"Exception: {e}")
            results.append({
                "question": q,
                "answer": f"Exception: {str(e)}",
                "citations": []
            })
            
    # Save to md
    with open("qa_test_results.md", "w", encoding="utf-8") as f:
        f.write("# RAG System QA Test Results\n\n")
        for res in results:
            f.write(f"## Question\n**{res['question']}**\n\n")
            f.write(f"### Answer ({res.get('time', 'N/A')}s)\n{res['answer']}\n\n")
            if res['citations']:
                f.write("### Citations\n")
                for c in res['citations']:
                    f.write(f"- **{c.get('title', 'Unknown')}** (Page {c.get('page_number', '?')}): {c.get('snippet', '')[:100]}...\n")
            f.write("\n---\n\n")
            
    print("Results saved to qa_test_results.md")

if __name__ == "__main__":
    main()
