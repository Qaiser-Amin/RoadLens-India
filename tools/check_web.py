"""Run the actual production browser journey against an owned temporary server."""

import argparse
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--browser", choices=["chromium", "firefox", "webkit"], default="chromium"
    )
    args = parser.parse_args()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryFile() as log:
        server = subprocess.Popen(
            [sys.executable, str(ROOT / "server.py"), "--port", str(port)],
            cwd=ROOT,
            stdout=log,
            stderr=log,
        )
        try:
            url = f"http://127.0.0.1:{port}"
            for attempt in range(100):
                if server.poll() is not None:
                    raise RuntimeError("Production server exited during startup")
                try:
                    with urllib.request.urlopen(url + "/health", timeout=2) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Production server did not become ready")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tests/browser_smoke.py"),
                    "--url",
                    url,
                    "--browser",
                    args.browser,
                ],
                cwd=ROOT,
                check=False,
            )
            return result.returncode
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            if sys.exc_info()[0]:
                log.seek(0)
                print(log.read().decode(errors="replace"), file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
