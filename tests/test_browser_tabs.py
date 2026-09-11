import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
import websockets

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
]

def find_browser():
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Neither Google Chrome nor Microsoft Edge was found.")

async def run_cdp_audit():
    browser_exe = find_browser()
    temp_dir = tempfile.mkdtemp(prefix="ragai_browser_audit_")
    port = 9222

    print(f"[1] Launching browser: {browser_exe} on debugging port {port}...")
    chrome_proc = subprocess.Popen([
        browser_exe,
        "--headless=new",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={temp_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-translate",
        "--disable-gpu",
        "about:blank"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for remote debugging endpoint to become ready
    ws_url = None
    for _ in range(30):
        await asyncio.sleep(0.3)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as resp:
                tabs = json.loads(resp.read().decode())
                if tabs and "webSocketDebuggerUrl" in tabs[0]:
                    ws_url = tabs[0]["webSocketDebuggerUrl"]
                    break
        except Exception:
            pass

    if not ws_url:
        chrome_proc.terminate()
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("Could not obtain webSocketDebuggerUrl from browser CDP.")

    print(f"[2] Connected to browser WebSocket: {ws_url}")

    console_logs = []
    console_errors = []
    unhandled_exceptions = []
    failed_requests = []
    msg_id = 0

    async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
        async def send_cmd(method, params=None):
            nonlocal msg_id
            msg_id += 1
            cur_id = msg_id
            payload = {"id": cur_id, "method": method}
            if params:
                payload["params"] = params
            await ws.send(json.dumps(payload))
            return cur_id

        # Enable domains
        await send_cmd("Page.enable")
        await send_cmd("Console.enable")
        await send_cmd("Runtime.enable")
        await send_cmd("Network.enable")

        # Background listener task
        stop_listener = False

        async def listener():
            while not stop_listener:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.2)
                    event = json.loads(raw)
                    method = event.get("method", "")

                    if method == "Runtime.consoleAPICalled":
                        p = event.get("params", {})
                        log_type = p.get("type", "log")
                        args = [str(a.get("value") or a.get("description") or "") for a in p.get("args", [])]
                        text = " ".join(args)
                        entry = {"type": log_type, "text": text}
                        console_logs.append(entry)
                        if log_type in ("error", "assert"):
                            console_errors.append(entry)
                            print(f"   [CONSOLE ERROR] {text}")
                        elif log_type == "warning":
                            print(f"   [CONSOLE WARN]  {text}")

                    elif method == "Runtime.exceptionThrown":
                        p = event.get("params", {})
                        details = p.get("exceptionDetails", {})
                        text = details.get("text", "")
                        exception = details.get("exception", {}).get("description", "")
                        entry = {"text": text, "description": exception, "url": details.get("url")}
                        unhandled_exceptions.append(entry)
                        print(f"   [UNCAUGHT EXCEPTION] {text}: {exception}")

                    elif method == "Network.responseReceived":
                        resp = event.get("params", {}).get("response", {})
                        status = resp.get("status", 200)
                        url = resp.get("url", "")
                        if status >= 400 and not url.endswith("favicon.ico"):
                            failed_requests.append({"status": status, "url": url})
                            print(f"   [HTTP ERROR {status}] {url}")

                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    if not stop_listener:
                        break

        listener_task = asyncio.create_task(listener())

        # Test Admin Hub (/admin)
        print("\n[3] Navigating to Admin Hub: http://127.0.0.1:8000/admin ...")
        await send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/admin"})
        await asyncio.sleep(3.0)

        # List of all Admin tabs to click and inspect
        admin_tabs = [
            ("tab-brain", "Tab 0: Cognitive AI Brain & Live Neural Visualizer"),
            ("tab-context", "Tab 12: Context Filesystem & OpenViking Tiered Storage"),
            ("tab-ingest", "Tab 1: Ingest & Watched Folders"),
            ("tab-pipeline", "Tab 2: Ingestion Pipeline & Queue Monitor"),
            ("tab-failed", "Tab 3: Failed Ingestions & Diagnostics"),
            ("tab-docs", "Tab 4: Indexed Document Library"),
            ("tab-apikeys", "Tab 5: API Key Lifecycle & RBAC Management"),
            ("tab-urls", "Tab 6: URL Access Control & SSRF Firewall"),
            ("tab-scraper", "Tab 7: Automated Web Scraper & Notice Crawler"),
            ("tab-manifest", "Tab 8: Cryptographic File Integrity Manifest"),
            ("tab-security", "Tab 9: Security Audit & Threat Monitoring"),
            ("tab-diagnostics", "Tab 10: Corrective RAG Diagnostics & Self-Tuning"),
            ("tab-settings", "Tab 11: System Settings & Hardware Management"),
        ]

        print(f"\n[4] Switching through all {len(admin_tabs)} Admin Hub Tabs...")
        tab_results = {}

        for tab_id, tab_label in admin_tabs:
            print(f" --> Inspecting {tab_label} ('{tab_id}')...")
            err_count_before = len(console_errors) + len(unhandled_exceptions)
            
            # Execute tab switch in browser DOM
            script = f"if (typeof switchTab === 'function') {{ switchTab('{tab_id}'); true; }} else {{ false; }}"
            await send_cmd("Runtime.evaluate", {"expression": script})
            await asyncio.sleep(1.2)

            err_count_after = len(console_errors) + len(unhandled_exceptions)
            new_errors = err_count_after - err_count_before
            tab_results[tab_id] = {
                "label": tab_label,
                "new_errors": new_errors,
                "status": "PASS" if new_errors == 0 else "FAIL"
            }
            if new_errors == 0:
                print(f"     [PASS] Zero console errors on {tab_id}")
            else:
                print(f"     [FAIL] {new_errors} new console error(s) on {tab_id}")

        # Test Student Chat Portal (/chat)
        print("\n[5] Navigating to Student Chat Portal: http://127.0.0.1:8000/chat ...")
        chat_err_before = len(console_errors) + len(unhandled_exceptions)
        await send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/chat"})
        await asyncio.sleep(3.0)

        # Test interaction with elements in Chat
        chat_test_script = """
        (() => {
            const input = document.getElementById('chat-input') || document.querySelector('textarea');
            const dept = document.getElementById('chat-dept-select') || document.querySelector('select');
            return { hasInput: !!input, hasDept: !!dept };
        })()
        """
        await send_cmd("Runtime.evaluate", {"expression": chat_test_script})
        await asyncio.sleep(1.0)
        chat_err_after = len(console_errors) + len(unhandled_exceptions)
        chat_new_errors = chat_err_after - chat_err_before
        print(f" --> Student Chat Portal Result: {'PASS' if chat_new_errors == 0 else 'FAIL'} ({chat_new_errors} errors)")

        # Finish listening
        await asyncio.sleep(1.0)
        stop_listener = True
        listener_task.cancel()

    # Cleanup browser process
    chrome_proc.terminate()
    try:
        chrome_proc.wait(timeout=3)
    except Exception:
        chrome_proc.kill()
    shutil.rmtree(temp_dir, ignore_errors=True)

    # Generate Audit Report
    report = {
        "admin_tabs": tab_results,
        "chat_portal_errors": chat_new_errors,
        "total_console_errors": len(console_errors),
        "total_unhandled_exceptions": len(unhandled_exceptions),
        "total_failed_requests": len(failed_requests),
        "errors": console_errors,
        "exceptions": unhandled_exceptions,
        "failed_requests": failed_requests
    }

    with open("tests/browser_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "="*70)
    print("           BROWSER CONSOLE & UI TAB AUDIT SUMMARY")
    print("="*70)
    print(f"Total Admin Tabs Checked:      {len(admin_tabs)}")
    print(f"Total Console Errors:          {len(console_errors)}")
    print(f"Total Unhandled Exceptions:    {len(unhandled_exceptions)}")
    print(f"Total Failed Network Requests: {len(failed_requests)}")
    print("="*70)

    for tab_id, r in tab_results.items():
        print(f"  [{r['status']}] {r['label']}: {r['new_errors']} errors")
    print(f"  [{'PASS' if chat_new_errors == 0 else 'FAIL'}] Student Chat Portal (/chat): {chat_new_errors} errors")
    print("="*70)

    if console_errors:
        print("\nIdentified Console Errors:")
        for e in console_errors:
            print(f"  - {e['text']}")

    if unhandled_exceptions:
        print("\nIdentified Unhandled Exceptions:")
        for ex in unhandled_exceptions:
            print(f"  - {ex['text']}: {ex['description']}")

    if failed_requests:
        print("\nIdentified Failed Network Requests:")
        for req in failed_requests:
            print(f"  - HTTP {req['status']}: {req['url']}")

    return len(console_errors) == 0 and len(unhandled_exceptions) == 0 and len(failed_requests) == 0

if __name__ == "__main__":
    success = asyncio.run(run_cdp_audit())
    exit(0 if success else 1)
