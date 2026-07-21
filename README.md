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

- [x] **Level 2: Orchestration & Networking** - Docker Compose environment, multiple replicas, Nginx reverse-proxy and load balancing.

- [ ] **Level 3: State & Scheduling** - PostgreSQL integration, background tasks worker, periodic service uptime checks history.

- [ ] **Level 4: Observability Stack** - Prometheus metrics export, Grafana dashboard visualization, application logging structure.

## Design Decisions: Infrastructure & Security

### 1. Reverse Proxy & Network Isolation (Level 2)
* **Decision:** The FastAPI application is completely isolated from the host network. The `ports` directive is removed from the `app` service in `docker-compose.yml`.
* **Rationale:** Security best practice. Only the Nginx container exposes port `80` to the outside world. All traffic to the application must pass through the proxy, eliminating direct scanning or bypassing of security controls.

### 2. Rate Limiting Configuration (Level 2)
* **Configuration:** `rate=5r/s`, `burst=3 nodelay`, `status=429`.
* **Rationale:** 
  * `rate=5r/s`: Protects the application threads from being overwhelmed by automated brute-force checking or DDoS loops.
  * `burst=3 nodelay`: Allows legitimate clients to execute a burst of up to 3 concurrent requests (e.g., when a dashboard UI requests status for multiple endpoints at once) without artificial latency (`nodelay`), but tightly drops any excessive spam.
  * `status=429`: Provides standard, semantically correct HTTP telemetry (`Too Many Requests`) instead of generic server errors (`503`).

### 3. Proxy Timeouts (Level 2)
* **Configuration:** `proxy_connect_timeout 3s;`, `proxy_read_timeout 3s;`.
* **Rationale:** If the internal Python application hangs or deadlocks due to an unhandled upstream network event, Nginx will wait no longer than 3 seconds before severing the connection and releasing worker threads. This prevents cascading failures across the proxy layer.

### 4. Environment Configuration & Templating (Level 2)
* **Decision:** Extracted all configurable runtime parameters (`NGINX_PORT`, `APP_PORT`, `RATE_LIMIT_RPS`, `RATE_LIMIT_BURST`) into a `.env` file (`.env.example` committed as a reference). Nginx dynamically renders `nginx.conf` at startup from `nginx.conf.template` via explicit `envsubst` in the Compose command.
* **Rationale:** 
  * Establishes a single source of truth for ports and rate-limiting across both Docker Compose orchestration and Nginx proxy configs.
  * Explicitly restricts `envsubst` to specified custom variables (`$RATE_LIMIT_RPS`, `$RATE_LIMIT_BURST`, `$APP_PORT`), avoiding corruption of Nginx internal directives (`$host`, `$remote_addr`).
  * Bypasses implicit Docker entrypoint script quirks, ensuring robust, deterministic configuration rendering at startup.

### 4. Database Persistence via Named Volume (Level 3)
* **Configuration:** `postgres_data:/var/lib/postgresql/data` (Docker Named Volume instead of a Bind Mount).

* **Rationale:** PostgreSQL requires strict POSIX file permissions (`chmod 700`, owner `postgres`) and high I/O throughput. Named Volumes are managed natively inside the Docker VM's Linux filesystem (ext4), bypassing the slow cross-OS filesystem translation layer (9p/virtiofs in WSL2) and eliminating FATAL: data directory has wrong ownership permission issues common with bind mounts on Windows hosts.