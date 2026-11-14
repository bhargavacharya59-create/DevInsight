# DevInsight AI

**AI-powered observability and incident investigation platform for ShopSphere.**

DevInsight AI monitors the ShopSphere e-commerce platform, detects anomalies using machine learning, performs evidence-based root cause analysis, and generates AI-powered explanations via the Gemini API.

---

## Architecture Overview

```
ShopSphere (e-commerce)
    │
    ▼ OpenTelemetry Collector
    ├── Prometheus (metrics)
    ├── Loki (logs)
    └── Tempo/OTel (traces)
            │
            ▼ DevInsight AI Backend (FastAPI + Python)
            ├── Isolation Forest Anomaly Detection
            ├── Evidence-Based RCA Engine
            ├── Gemini AI Explanation
            └── PostgreSQL (incident persistence)
                    │
                    ▼ DevInsight AI Dashboard (React + TypeScript)
```

---

## Features

| Feature | Status |
|---|---|
| Demo Mode with 8 synthetic failure scenarios | ✅ |
| Isolation Forest anomaly detection (real ML) | ✅ |
| Evidence-based RCA engine (deterministic) | ✅ |
| Gemini AI incident explanation | ✅ (needs API key) |
| Incident management + deduplication | ✅ |
| PostgreSQL persistence | ✅ |
| Prometheus integration | ✅ (live mode) |
| Loki integration | ✅ (live mode) |
| OpenTelemetry integration | ✅ (live mode) |
| Interactive dashboard | ✅ |
| Service map | ✅ |
| Metrics explorer | ✅ |
| Logs explorer | ✅ |
| AI assistant chatbot | ✅ |
| Docker Compose deployment | ✅ |

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+ (3.14 supported)
- Node.js 18+
- PostgreSQL 14+ (or Docker)

### 1. Backend

```bash
cd backend

# Copy and configure environment
cp .env.example .env
# Edit .env — set GEMINI_API_KEY if you have one

# Install dependencies
pip install -r requirements.txt
pip install aiosqlite  # for local SQLite dev

# Start the backend
uvicorn app.main:app --reload --port 8000
```

The backend starts in **Demo Mode** by default using SQLite.  
Visit http://localhost:8000/docs for the interactive API docs.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173

---

## Docker Compose (DevInsight + ShopSphere)

The two repositories run as separate Compose projects but share one Docker network for metrics, error events, and OTLP traffic. Start DevInsight first.

### 1. Prepare DevInsight

```bash
cp .env.example .env
cp backend/.env.example backend/.env
```

Generate one strong shared key (run once):

```bash
openssl rand -hex 32
```

Put that value in `INGEST_API_KEY` in the root `.env` files of **both** repositories. Do not commit either `.env` file.

Create the shared network and start DevInsight:

```bash
docker network create observability-net
docker compose up -d --build
```

### 2. Start ShopSphere

In the ShopSphere repository root:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
# Set the SAME INGEST_API_KEY in this repository's root .env
docker compose up -d --build
```

### 3. Local URLs

| Component | URL |
|---|---|
| DevInsight dashboard | http://localhost:3000 |
| DevInsight API docs | http://localhost:8000/docs |
| ShopSphere storefront | http://localhost:3002 |
| ShopSphere API docs | http://localhost:8001/docs |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |
| Loki | http://localhost:3100 |
| Tempo trace API | http://localhost:3200 |

ShopSphere host ports are shifted to avoid collisions: API `8001`, frontend `3002`, PostgreSQL `5433`. Internal container traffic uses port `8000`. Prometheus scrapes `shopsphere-backend:8000/metrics`; ShopSphere forwards HTTP 5xx events to DevInsight using the shared API key and sends OTLP traces to the DevInsight collector. The collector exports traces to Tempo, and DevInsight queries Tempo on port `3200`.

To stop either stack, run `docker compose down` in that repository. Keep the shared `observability-net` while the other stack is running.

---

## Monitoring Modes

### Demo Mode (default)
All telemetry is **synthetic and clearly labeled**. No ShopSphere connection required.

- Select a scenario in the Live Monitoring page
- Watch telemetry change in real-time
- See anomaly detection trigger
- View the RCA investigation
- Read the AI explanation

### Live Mode
Set `MONITORING_MODE=live` in `.env` and configure:
```env
PROMETHEUS_URL=http://your-prometheus:9090
LOKI_URL=http://your-loki:3100
OTEL_COLLECTOR_URL=http://localhost:3200  # Tempo trace-query API
```

---

## Demo Scenarios

| Scenario | Category | What it simulates |
|---|---|---|
| Normal Operation | baseline | Healthy baseline traffic |
| Database Latency Spike | database | 8× DB latency, cascading failures |
| HTTP 500 Error Spike | api | 15× error rate in ShopSphere API |
| Payment Failures | payment | 12× payment error rate |
| CPU Spike | infrastructure | CPU at ~90% on API host |
| Memory Leak | infrastructure | Steadily rising memory |
| Bad Deployment | deployment | Post-deploy regression |
| DB Connection Failures | database | Connection pool exhausted |

---

## Anomaly Detection

Uses **Isolation Forest** (scikit-learn) — not random scores.

**Features:**
- Request rate, Error rate, Response latency
- CPU utilization, Memory utilization
- Database query latency, Service error count

The model is trained on synthetic normal-operation data on startup.  
In live mode, it trains on actual telemetry history.

---

## RCA Engine

The RCA engine is **deterministic** — it scores candidates based on evidence:

1. **Metric signals** — latency increase, error rate spike, CPU/memory saturation
2. **Log patterns** — connection timeouts, exceptions, circuit breakers
3. **Trace signals** — error rate, slow spans by service
4. **Deployment correlation** — deployment timing vs. incident onset

Gemini AI provides the *explanation* on top of the deterministic results.

---

## Gemini AI Integration

Configure in `.env`:
```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash
```

The app works fully without a Gemini key — all RCA results are available via the deterministic engine. The AI provides natural-language explanation and additional context.

---

## API Documentation

Interactive docs at: http://localhost:8000/docs

Key endpoints:
```
GET  /health
GET  /api/dashboard/overview
GET  /api/incidents
GET  /api/incidents/{id}
POST /api/incidents/{id}/acknowledge
POST /api/incidents/{id}/resolve
GET  /api/incidents/{id}/rca
POST /api/rca/investigate
POST /api/anomaly/detect
GET  /api/metrics
GET  /api/logs
GET  /api/traces
GET  /api/services
GET  /api/services/map
GET  /api/demo/scenarios
POST /api/demo/scenarios/{id}/start
POST /api/demo/scenarios/{id}/stop
POST /api/demo/reset
POST /api/ai/explain
POST /api/ai/ask
```

---

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

Tests cover:
- Isolation Forest anomaly detection (7 tests)
- RCA engine (6 tests)
- Demo telemetry generator (7 tests)
- Gemini fallback behavior (3 tests)

---

## Project Structure

```
devinsight-ai/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   ├── core/         # Config, logging
│   │   ├── db/           # SQLAlchemy engine
│   │   ├── ml/           # Isolation Forest detector
│   │   ├── models/       # ORM models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   └── telemetry/    # Prometheus/Loki/OTel clients
│   └── tests/
├── frontend/
│   └── src/
│       ├── api/          # Axios client
│       ├── components/   # Reusable components
│       ├── pages/        # Route pages
│       ├── types/        # TypeScript types
│       └── utils/        # Formatters
├── infra/
│   ├── prometheus/       # prometheus.yml
│   ├── loki/             # loki-config.yaml
│   ├── otel/             # otel-collector-config.yaml
│   └── grafana/          # Datasource provisioning
└── docker-compose.yml
```
