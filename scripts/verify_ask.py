import httpx
import json

def test_query(question: str):
    print("=" * 60)
    print(f"QUESTION: {question}")
    payload = {"question": question}
    try:
        res = httpx.post("http://localhost:8080/api/v1/ask", json=payload, timeout=30.0)
        print("STATUS:", res.status_code)
        data = res.json()
        print("\nANSWER:")
        print(data.get("answer"))
        print("\nCITATIONS:")
        for c in data.get("citations", []):
            print(f"  - {c.get('title')} (Page {c.get('page_number')})")
            print(f"    Snippet: {c.get('snippet')[:100]}...")
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    test_query("when the 1st meeting of academic council was held")
    test_query("when the 2nd meeting of academic council was held")
    test_query("when was the 3rd meeting of academic council held")
    test_query("when was the 1st meeting of court held")
