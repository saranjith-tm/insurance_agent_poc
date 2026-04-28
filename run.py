"""
Master launcher for the Insurance Underwriting POC.

Starts all three services:
  1. Sales Agent App      → http://localhost:5001
  2. Underwriting App     → http://localhost:5002
  3. Streamlit Dashboard  → http://localhost:8501

Usage:
  python run.py              # Start all services
  python run.py --sales      # Sales agent only
  python run.py --uw         # Underwriting app only
  python run.py --dashboard  # Dashboard only
  python run.py --no-browser # Skip auto-opening browser
"""

import sys
import os
import time
import signal
import argparse
import subprocess
import threading
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_flask_app(app_path: str, port: int, name: str) -> subprocess.Popen:
    """Start a Flask app as a subprocess."""
    env = os.environ.copy()
    env["PYTHONPATH"] = BASE_DIR
    env["FLASK_ENV"] = "development"
    env["PYTHONUNBUFFERED"] = "1"

    proc = subprocess.Popen(
        [sys.executable, app_path],
        env=env,
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    def _stream_output():
        for line in iter(proc.stdout.readline, ""):
            print(f"[{name}] {line}", end="")

    thread = threading.Thread(target=_stream_output, daemon=True)
    thread.start()
    return proc


def run_streamlit(dashboard_path: str, port: int, name: str) -> subprocess.Popen:
    """Start the Streamlit dashboard as a subprocess."""
    env = os.environ.copy()
    env["PYTHONPATH"] = BASE_DIR
    env["PYTHONUNBUFFERED"] = "1"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            dashboard_path,
            f"--server.port={port}",
            "--server.address=localhost",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
            "--theme.base=light",
            "--theme.primaryColor=#3f51b5",
        ],
        env=env,
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    def _stream_output():
        for line in iter(proc.stdout.readline, ""):
            print(f"[{name}] {line}", end="")

    thread = threading.Thread(target=_stream_output, daemon=True)
    thread.start()
    return proc


def wait_for_service(url: str, timeout: int = 30, name: str = "") -> bool:
    """Poll a URL until it responds or timeout."""
    import urllib.request
    import urllib.error

    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(1)
    print(f"  ⚠️  {name} did not start in {timeout}s")
    return False


def main():
    parser = argparse.ArgumentParser(description="Insurance UW POC Launcher")
    parser.add_argument(
        "--sales", action="store_true", help="Start sales agent app only"
    )
    parser.add_argument("--uw", action="store_true", help="Start underwriting app only")
    parser.add_argument("--dashboard", action="store_true", help="Start dashboard only")
    parser.add_argument(
        "--no-browser", action="store_true", help="Don't open browser automatically"
    )
    args = parser.parse_args()

    run_all = not (args.sales or args.uw or args.dashboard)

    print("\n" + "=" * 60)
    print("🤖 INSURANCE UNDERWRITING AUTOMATION POC")
    print("=" * 60)

    processes = []

    # Start Sales Agent App
    if run_all or args.sales:
        print("\n▶ Starting Sales Agent App (port 5001)...")
        sales_path = os.path.join(BASE_DIR, "apps", "sales_agent", "app.py")
        proc = run_flask_app(sales_path, 5001, "SALES")
        processes.append(("Sales Agent", proc, 5001))

    # Start Underwriting App
    if run_all or args.uw:
        print("▶ Starting Underwriting Checklist App (port 5002)...")
        uw_path = os.path.join(BASE_DIR, "apps", "underwriting", "app.py")
        proc = run_flask_app(uw_path, 5002, "UW_APP")
        processes.append(("Underwriting App", proc, 5002))

    # Brief pause for Flask apps to bind ports
    time.sleep(2)

    # Start Streamlit Dashboard
    if run_all or args.dashboard:
        print("▶ Starting Streamlit Dashboard (port 8501)...")
        dashboard_path = os.path.join(BASE_DIR, "dashboard", "Home.py")
        proc = run_streamlit(dashboard_path, 8501, "DASHBOARD")
        processes.append(("Dashboard", proc, 8501))

    print("\n⏳ Waiting for services to start...")
    time.sleep(4)

    # Print URLs
    print("\n" + "=" * 60)
    print("✅ SERVICES RUNNING:")
    print("=" * 60)
    if run_all or args.sales:
        print("  📋 Sales Agent App:      http://localhost:5001")
    if run_all or args.uw:
        print("  ✅ Underwriting App:     http://localhost:5002")
    if run_all or args.dashboard:
        print("  🤖 Automation Dashboard: http://localhost:8501")
    print("\nPress Ctrl+C to stop all services")
    print("=" * 60 + "\n")

    # Open browser
    if not args.no_browser and (run_all or args.dashboard):
        time.sleep(2)
        print("🌐 Opening dashboard in browser...")
        webbrowser.open("http://localhost:8501")

    # Handle Ctrl+C gracefully
    def _shutdown(sig, frame):
        print("\n\n⛔ Shutting down all services...")
        for name, proc, port in processes:
            try:
                proc.terminate()
                print(f"  ✅ {name} stopped")
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Keep alive - monitor processes
    while True:
        time.sleep(5)
        for name, proc, port in processes:
            if proc.poll() is not None:
                print(f"  ⚠️  {name} (port {port}) exited with code {proc.returncode}")


if __name__ == "__main__":
    main()
