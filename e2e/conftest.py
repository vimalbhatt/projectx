import subprocess
import time
import socket
import pytest
import os

# Add project root to path so Streamlit can find modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import Page
from playwright_config import BASE_URL, STREAMLIT_PORT, STREAMLIT_STARTUP_TIMEOUT, DEFAULT_TIMEOUT


def _port_open(port, host="localhost"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


@pytest.fixture(scope="session")
def streamlit_server():
    """Start Streamlit server once for the entire test session."""
    # Remove stale DB so tests start clean
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chat.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", str(STREAMLIT_PORT),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for server to be ready
    deadline = time.time() + STREAMLIT_STARTUP_TIMEOUT
    while time.time() < deadline:
        if _port_open(STREAMLIT_PORT):
            # Give Streamlit a moment to fully initialize
            time.sleep(1)
            break
        time.sleep(0.5)
    else:
        proc.kill()
        raise RuntimeError(f"Streamlit server did not start within {STREAMLIT_STARTUP_TIMEOUT}s")

    yield proc

    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture()
def app_page(streamlit_server, page: Page):
    """Provide a Playwright page pointed at the running app with clean DB state."""
    page.set_default_timeout(DEFAULT_TIMEOUT)
    # Ensure DB tables exist and clear messages between tests
    import db as _db
    _db.init_db()
    _db.clear_chat()
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    return page
