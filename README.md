# Uptime Checker API

A minimal uptime-checker API built as a hands-on learning project to master professional Docker, container orchestration, and observability practices. The project follows an evolutionary path — going from a single isolated container to a complete production-like stack.

## Current Architecture Status
* **Backend:** FastAPI, HTTPX (resilient network exception handling)
* **Docker Best Practices:** Multi-stage builds (`python:3.12-slim`), `non-root` user security execution, build context optimization via `.dockerignore`.

---

## API Endpoints

* `GET /health` — Simple health check endpoint (returns `{"status": "ok"}`).
* `GET /info` — Container metadata (returns runtime process uptime, python version, and internal container `hostname`).
* `GET /check?url=<url>` — Performs a synchronous HTTP request to the target URL, measures response time in milliseconds, and handles connection/DNS errors gracefully without dropping the application.

---

## Quick Start

To build and run the application inside the secure container locally, execute:

```bash
# 1. Build the multi-stage image
docker build -t uptime-checker .

# 2. Run the container in interactive mode (ports mapped to 8000)
docker run -p 8000:8000 uptime-checker

# Once started, test it via curl:
curl "http://localhost:8000/check?url=https://google.com"
```
---

## Project Roadmap

- [x] **Level 1: Containerization Basics** - Single container setup, multi-stage build optimization, non-root user execution, layer trimming.

- [ ] **Level 2: Orchestration & Networking** - Docker Compose environment, multiple replicas, Nginx reverse-proxy and load balancing.

- [ ] **Level 3: State & Scheduling** - PostgreSQL integration, background tasks worker, periodic service uptime checks history.

- [ ] **Level 4: Observability Stack** - Prometheus metrics export, Grafana dashboard visualization, application logging structure.