import sys
import socket
import time
from fastapi import FastAPI
import httpx

app = FastAPI()


START_TIME = time.time()


@app.get("/health")
def read_health():
    return {"status": "ok"}


@app.get("/info")
def read_info():
    current_uptime = time.time() - START_TIME
    return {
        "hostname": socket.gethostname(),
        "python_version": sys.version,
        "uptime_seconds": int(current_uptime),
    }


@app.get("/check")
def check_url(url: str):
    start = time.perf_counter()
    try:
        response = httpx.get(url, timeout=5.0, follow_redirects=True)
        end = time.perf_counter()
        elapsed_ms = int((end - start) * 1000)
        return {
            "url": url,
            "status_code": response.status_code,
            "response_time_ms": elapsed_ms,
            "is_up": response.status_code < 400,
        }
    except (httpx.HTTPError, httpx.InvalidURL):
        return {"url": url, "status_code": 0, "response_time_ms": 0, "is_up": False}
