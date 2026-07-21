import sys
import socket
import time
from fastapi import FastAPI, Request
import httpx
import psycopg
import os

app = FastAPI()

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

START_TIME = time.time()


@app.get("/health")
def read_health():
    return {"status": "ok"}


@app.get("/info")
def read_info(request: Request):
    current_uptime = time.time() - START_TIME
    return {
        "hostname": socket.gethostname(),
        "python_version": sys.version,
        "uptime_seconds": int(current_uptime),
        "headers": dict(request.headers),
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


@app.get("/db-check")
def check_db():
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return {"db_connected": True}
    except psycopg.Error as e:
        return {"db_connected": False, "error": str(e)}
