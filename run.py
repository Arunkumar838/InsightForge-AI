import os
import subprocess
import sys
import time
import webbrowser

def main():
    print("==================================================")
    print("      INSIGHTFORGE AI - QUANTUM LOCAL LAUNCHER    ")
    print("==================================================")
    
    # 1. Install/Update requirements
    print("\n[Step 1] Synchronizing packages via pip...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print(">> Requirements synchronization successful.")
    except Exception as e:
        print(f">> WARNING: requirements sync encountered issue: {str(e)}")
        print(">> Will attempt to start server with existing environment packages.")

    # 2. Run verification test suite
    print("\n[Step 2] Validating internal modules test suite...")
    test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_backend.py")
    if os.path.exists(test_script):
        try:
            res = subprocess.run([sys.executable, test_script], capture_output=True, text=True)
            if res.returncode == 0:
                print(">> Verification Test suite: PASSED.")
            else:
                print(">> WARNING: Verification Test suite reported issues:")
                print(res.stdout)
                print(res.stderr)
        except Exception as e:
            print(f">> Failed to execute validation script: {str(e)}")
    else:
        print(">> Validation script not found. Skipping validation.")

    # 3. Open Browser dynamically after delay
    print("\n[Step 3] Launching enterprise dashboard...")
    url = "http://127.0.0.1:8000"
    
    # Simple delay open thread
    def open_browser():
        time.sleep(2.0)
        print(f"\n>> Opening connection link: {url}")
        webbrowser.open(url)
        
    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # 4. Boot Uvicorn FastAPI
    print("\n[Step 4] Starting FastAPI Uvicorn Server on port 8000...")
    try:
        import uvicorn
        uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\n>> Server shutdown requested by user. Terminating processes.")
    except Exception as e:
        print(f"\n>> CRITICAL: Server crashed: {str(e)}")
        print(">> Verify no other application is listening on port 8000.")

if __name__ == "__main__":
    main()
