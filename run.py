"""
One-Click Launcher for GitScrum AI
Verifies dependencies, finds an available socket port, opens the web browser, and starts the FastAPI server.
"""

import socket
import sys
import threading
import time
import webbrowser

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def check_dependencies():
    missing = []
    for pkg in ["fastapi", "uvicorn", "httpx", "pydantic"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("\n" + "=" * 60)
        print(" [!] THIEU THU VIEN CAN THIET:")
        print(f"     Cac goi sau chua duoc cai dat: {', '.join(missing)}")
        print("\n [*] Vui long chay lenh sau de cai dat:")
        print("     pip install -r requirements.txt")
        print("=" * 60 + "\n")
        sys.exit(1)


def find_available_port(preferred_port=8080, candidates=(8080, 8001, 8002, 8050, 5000, 8888, 8000)):
    """Find the first available TCP port that does not throw WinError 10013 / permission denied."""
    ports_to_try = [preferred_port] + [p for p in candidates if p != preferred_port]
    for port in ports_to_try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    # Fallback to letting the OS assign an available port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def open_browser(port):
    time.sleep(1.2)
    url = f"http://127.0.0.1:{port}"
    print(f"\n[*] Dang tu dong mo GitScrum AI Web Dashboard tai: {url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    check_dependencies()
    import uvicorn

    port = find_available_port(preferred_port=8080)

    print("=" * 65)
    print(" [*] GITSCRUM AI - GitHub Activity Scanner & Agile Reporting Engine")
    print("=" * 65)
    print(f" [*] May chu FastAPI khoi dong tai: http://127.0.0.1:{port}")
    print(f" [*] Giao dien Web Dashboard:       http://127.0.0.1:{port}")
    print(" [*] Nhan Ctrl + C de dung may chu.")
    print("=" * 65)

    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
