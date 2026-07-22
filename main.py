from datetime import datetime
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED, EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
import sys
import socket
import time
from fastapi import FastAPI, Request
import httpx
import psycopg
import os

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

MONITORED_URLS = [
    url.strip() for url in os.getenv("MONITORED_URLS", "").split(",") if url.strip()
]


START_TIME = time.time()


def init_db():
    """Creates the necessary database tables when the application starts."""
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS url_checks (
                    id SERIAL PRIMARY KEY,
                    url TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    response_time_ms INTEGER NOT NULL,
                    is_up BOOLEAN NOT NULL,
                    checked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()


def monitor_task():
    """A background task that polls all sites from the list and writes the results to the database."""
    if not MONITORED_URLS:
        print("Scheduler warning: MONITORED_URLS list is empty.")
        return

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                with httpx.Client(timeout=5.0, follow_redirects=True) as client:
                    for url in MONITORED_URLS:
                        start = time.perf_counter()
                        try:
                            response = client.get(url)
                            elapsed_ms = int((time.perf_counter() - start) * 1000)
                            status_code = response.status_code
                            is_up = status_code < 400
                        except (httpx.HTTPError, httpx.InvalidURL):
                            elapsed_ms = 0
                            status_code = 0
                            is_up = False

                        cur.execute(
                            """
                            INSERT INTO url_checks (url, status_code, response_time_ms, is_up)
                            VALUES (%s, %s, %s, %s);
                        """,
                            (url, status_code, elapsed_ms, is_up),
                        )

                conn.commit()
                print(
                    f"Scheduler success: {len(MONITORED_URLS)} URLs checked and saved."
                )
    except Exception as e:
        print(f"Scheduler critical database error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = BackgroundScheduler()

    def job_listener(event):
        if event.exception:
            print(f"Job crashed: {event.exception}")
        elif event.code == EVENT_JOB_MISSED:
            print(f"Job missed at {event.scheduled_run_time}")
        else:
            print(f"Job executed successfully at {datetime.now()}")

    scheduler.add_listener(
        job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
    )
    scheduler.add_job(
        monitor_task,
        "interval",
        seconds=60,
        id="url_monitor_job",
        misfire_grace_time=30,
    )
    scheduler.start()
    print("Scheduler successfully started.")
    monitor_task()
    yield
    scheduler.shutdown()
    print("Scheduler successfully stopped.")


app = FastAPI(lifespan=lifespan)


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


@app.get("/history")
def get_history(url: str, limit: int = 20):
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, url, status_code, response_time_ms, is_up, checked_at 
                    FROM url_checks
                    WHERE url = %s 
                    ORDER BY checked_at DESC 
                    LIMIT %s;
                """,
                    (url, limit),
                )

                rows = cur.fetchall()

                history = []
                for row in rows:
                    history.append(
                        {
                            "id": row[0],
                            "url": row[1],
                            "status_code": row[2],
                            "response_time_ms": row[3],
                            "is_up": row[4],
                            "checked_at": row[5].isoformat() if row[5] else None,
                        }
                    )

                return {"success": True, "url": url, "count": len(history), "history": history}

    except psycopg.Error as e:
        return {"success": False, "error": str(e)}
