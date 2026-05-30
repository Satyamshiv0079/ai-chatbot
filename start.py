import subprocess
import sys
import os
import time
import threading

def stream_output(process, prefix, color_code):
    """Streams output from a subprocess line-by-line with a colored, CP1252-safe prefix."""
    reset = "\033[0m"
    prefix_colored = f"\033[{color_code}m{prefix}{reset}"
    
    try:
        for line in iter(process.stdout.readline, b''):
            # Decode to unicode with fallback
            decoded = line.decode('utf-8', errors='replace').rstrip()
            # Replace non-ASCII characters with '?' to ensure safe printing on Windows CP1252 terminals
            safe_text = decoded.encode('ascii', errors='replace').decode('ascii')
            print(f"{prefix_colored} {safe_text}")
    except Exception as e:
        print(f"{prefix_colored} Error reading stream: {e}")

def main():
    print("\033[94m==================================================\033[0m")
    print("\033[94m[*]             NovaMind Orchestrator            [*]\033[0m")
    print("\033[94m==================================================\033[0m")
    
    workspace_root = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(workspace_root, "backend")
    frontend_dir = os.path.join(workspace_root, "frontend")
    
    # Resolve paths
    python_exe = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable  # Fallback to current python interpreter
        
    app_py = os.path.join(backend_dir, "api", "app.py")
    
    print(f"[*] Booting Backend REST API on port 8000...")
    # Run with -u (unbuffered) to capture output immediately
    backend_proc = subprocess.Popen(
        [python_exe, "-u", app_py],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=backend_dir
    )
    
    # Spawn thread to log backend output
    backend_thread = threading.Thread(
        target=stream_output, 
        args=(backend_proc, "[Backend]", "95"), 
        daemon=True
    )
    backend_thread.start()
    
    # Wait briefly for backend to warm up
    time.sleep(2)
    
    print(f"[*] Booting Frontend Vite server on port 5000...")
    # On Windows, we run npm dev server via cmd.exe to bypass PowerShell script execution restrictions
    frontend_cmd = ["cmd", "/c", "npm", "run", "dev"]
    
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=frontend_dir
    )
    
    # Spawn thread to log frontend output
    frontend_thread = threading.Thread(
        target=stream_output, 
        args=(frontend_proc, "[Frontend]", "96"), 
        daemon=True
    )
    frontend_thread.start()
    
    print("\033[92m[+] Both systems started! Press Ctrl+C to terminate both servers.\033[0m\n")
    
    try:
        # Keep orchestrator running and check status of children
        while True:
            # Check if backend crashed
            if backend_proc.poll() is not None:
                print("\033[91m[-] Backend process stopped unexpectedly!\033[0m")
                break
            # Check if frontend crashed
            if frontend_proc.poll() is not None:
                print("\033[91m[-] Frontend process stopped unexpectedly!\033[0m")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\033[93m[!] Shutdown signal received. Cleaning up processes...\033[0m")
    finally:
        # Terminate processes gracefully
        try:
            print("[*] Terminating backend...")
            backend_proc.terminate()
            backend_proc.wait(timeout=2)
        except Exception:
            backend_proc.kill()
            
        try:
            print("[*] Terminating frontend...")
            frontend_proc.terminate()
            frontend_proc.wait(timeout=2)
        except Exception:
            frontend_proc.kill()
            
        print("\033[92m[+] Orchestrator shutdown complete.\033[0m")

if __name__ == "__main__":
    # Enable colors in Windows cmd/powershell
    os.system("")
    main()
