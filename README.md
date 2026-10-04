# Agentic AI Smart Waste Collection & Recycling Optimization System

## Project Overview
A fully autonomous municipal waste‑management decision‑support platform that orchestrates **eight specialized AI agents** to ingest real‑time smart‑bin telemetry, forecast waste accumulation, prioritize collection, allocate vehicles, optimise routes, enforce recycling rules, and provide human‑in‑the‑loop approval. The system is built with FastAPI, LangGraph, Google OR‑Tools, React/TypeScript, and deployed on Render (backend) and Vercel (frontend).

## Problem Statement
Municipalities face rising waste volumes, inefficient collection routes, and poor recycling compliance. Manual scheduling leads to missed pickups, overloaded bins, and unnecessary fuel consumption. Our solution automates the end‑to‑end workflow, reducing collection costs, improving recycling rates, and ensuring timely service.

---

## System Architecture
![System Architecture](docs/architecture.png)

The architecture is layered:
1. **IoT Telemetry & Ingestion** – Smart bin sensors stream fill level, weight, temperature.
2. **Data Validation & Auditing** – Agent 1 validates sensor data, flags anomalies.
3. **Predictive Intelligence** – Agent 2 forecasts 24‑hour fill using a Random‑Forest model.
4. **Collection Prioritisation** – Agent 3 scores bins (critical, high, medium, low).
5. **Fleet Allocation & Routing** – Agents 4‑5 allocate vehicles and solve a CVRP with OR‑Tools.
6. **Governance & Human Approval** – Agents 6‑8 handle recycling checks and human‑in‑the‑loop approval.
7. **Execution, Re‑planning & Reporting** – Dynamic replanning on surge events and PDF audit report generation.

---

## Multi‑Agent Architecture
| Agent # | Name | Primary Role | Outputs |
|---|---|---|---|
| 1 | Smart Bin Monitoring Agent | Ingest telemetry, detect sensor drift, validate physical bounds. | Validated bin states, alerts |
| 2 | Waste Generation Forecasting Agent | Predict fill levels 24 h ahead (RandomForestRegressor). | Forecasted fill percentages |
| 3 | Collection Priority Agent | Compute deterministic priority scores (0‑100). | Priority tier (CRITICAL, HIGH, …) |
| 4 | Vehicle & Capacity Agent | Filter fleet based on capacity, waste‑type compatibility. | Qualified vehicle list |
| 5 | Route Optimisation Agent | Solve CVRP via Google OR‑Tools. | Optimised routes, travel‑distance metrics |
| 6 | Recycling & Segregation Agent | Audit cross‑stream contamination, compute recycling rates. | Segregation scorecard |
| 7 | Waste Operations & Action Planning Agent | Build unified dispatch plan (ETAs, driver shifts). | Dispatch blueprint |
| 8 | Operations Reviewer / Critic Agent | Independent audit, human‑approval gating. | APPROVED or REPLAN decision |

---

## Agent Prompts & Communication
Each agent is driven by a LangGraph node that receives a **prompt template** (see `backend/app/prompts/`). Communication occurs via **shared workflow state** (a Pydantic model) stored in the graph context. Agents read/write keys such as `sensor_data`, `forecast`, `priority_scores`, `vehicle_pool`, `routes`, and `approval`. The critic agent can raise a `replan` flag that loops back to the routing node.

---

## Shared Workflow State
```json
{
  "sensor_data": {...},
  "validated_bins": [...],
  "forecast": {...},
  "priority_scores": {...},
  "vehicle_pool": [...],
  "routes": [...],
  "recycling_audit": {...},
  "approval": "PENDING|APPROVED|REJECTED"
}
```
All agents read/write this single source of truth, guaranteeing deterministic execution.

---

## Smart‑Bin Data Model
| Table | Fields |
|---|---|
| `bins` | `id`, `location (lat, lng)`, `capacity_liters`, `waste_type`, `last_fill_percent`, `last_update_ts` |
| `forecasts` | `bin_id`, `predicted_fill_percent`, `prediction_ts` |
| `vehicles` | `id`, `capacity_liters`, `compatible_waste_types`, `current_location` |
| `routes` | `vehicle_id`, `ordered_bin_ids`, `total_distance_km`, `eta_minutes` |
| `reports` | `id`, `generated_at`, `pdf_path` |

---

## IoT Simulation
A lightweight FastAPI endpoint (`/simulate`) streams synthetic sensor payloads generated from a configurable stochastic model (daily cycles, random spikes, sensor noise). The simulator is used for local development and CI testing.

---

## Sensor‑Data Ingestion
- **REST endpoint**: `POST /api/sensors` receives JSON payloads.
- **Kafka‑like queue** (in‑process) decouples ingestion from validation.
- **Bulk loader** (`scripts/seed_database.py`) populates initial historic data.

---

## Sensor Validation
Agent 1 applies:
- Physical bounds (0‑100 % fill, temperature range).
- Rate‑of‑change checks (reject > 30 %/min spikes).
- Staleness detection (no update > 2 h → `SENSOR_STALE`).
Alerts are persisted in `alerts` table and surfaced on the UI.

---

## Forecasting Dataset & Feature Engineering
The model is trained on three years of synthetic plus real‑world data. Features include:
- `current_fill_percent`
- `prev_fill_percent`
- `fill_change`
- `hour_of_day`
- `day_of_week`
- `waste_type` (one‑hot)
- `capacity_liters`
- `time_since_last_collection`
- `historical_growth_rate`
All features are scaled with `StandardScaler` before training.

---

## Forecasting Model
**RandomForestRegressor** – 100 trees, `max_depth=12`. Trained with `sklearn` and serialized via `joblib`. Evaluation metrics are stored in `model_metrics.json`.

---

## Model Evaluation
| Metric | Value |
|---|---|
| MAE | 1.64 % |
| RMSE | 2.10 % |
| MAPE | 3.17 % |

Cross‑validation (5‑fold) shows stable performance across waste types.

---

## Collection‑Priority Methodology
A weighted scoring function:
```
score = 0.5*fill_percent + 0.3*forecasted_increase + 0.2*waste_hazard_factor
```
Thresholds define tiers (CRITICAL ≥ 85 %, HIGH ≥ 65 %, …). Predictive overflow adds +25 points.

---

## Vehicle‑Management Logic
- Vehicles are filtered by **capacity** and **waste‑type compatibility**.
- Remaining capacity is tracked per route; over‑assignment raises `RouteValidator` errors.
- Fleet availability updates in real‑time from GPS stream (future extension).

---

## Route‑Optimization Problem Formulation
**Capacitated Vehicle Routing Problem (CVRP)**
- Objective: minimise total travel distance.
- Constraints: vehicle capacity, time windows (optional), mandatory service of all high‑priority bins.
- Solver: Google OR‑Tools `RoutingModel` with `AddDimension` for capacity.

---

## Optimization Algorithm
OR‑Tools uses a **guided local‑search** (meta‑heuristic) with **Tabu Search** and **Cheapest‑Insertion** heuristics as initial solution. Parameters are tuned for < 5 s solution time on typical city‑scale datasets (≈ 200 bins, 10 vehicles).

---

## Dynamic Re‑planning
During route execution, the system monitors:
- Unexpected surge events (new critical bin).
- Traffic delays (simulated via `traffic_factor`).
If a trigger fires, the **Re‑planning Service** re‑invokes the routing node and pushes the updated plan to the driver app.

---

## GIS Implementation
Geospatial calculations (distance matrix) use **Haversine formula** via the `geopy` library. The distance matrix is cached per‑day to speed up routing.

---

## Waste‑Segregation Rules & Recycling Calculations
- Each bin is labelled with a waste stream (General, Organic, Recyclable).
- The Recycling Agent checks that only compatible streams are loaded onto a vehicle.
- Post‑collection, `recycling_rate = recycled_volume / total_collected_volume` is stored and displayed in the dashboard.

---

## Human‑Approval Mechanism
After route generation, the **Operations Reviewer** presents a summary (total distance, fuel estimate, recycling compliance) in the UI. A human can **Approve** or **Reject → Re‑plan**. The decision is recorded in `approval_logs`.

---

## Database Design
Implemented with **SQLAlchemy** + **PostgreSQL** (Render). Key tables: `bins`, `vehicles`, `forecasts`, `routes`, `alerts`, `reports`, `approval_logs`. Alembic migrations manage schema evolution (`alembic/versions`).

---

## API Documentation
FastAPI automatically provides OpenAPI docs at `/docs`. Important endpoints:
- `POST /api/sensors` – ingest telemetry
- `GET /api/forecasts/{bin_id}` – retrieve forecast
- `GET /api/routes` – current routing plan
- `GET /api/reports/{report_id}` – download PDF audit report

---

## Environment Variables
| Variable | Description |
|---|---|
| `POSTGRES_URL` | PostgreSQL connection string |
| `VITE_API_URL` | Frontend API base URL |
| `MODEL_PATH` | Path to serialized RandomForest model |
| `SECRET_KEY` | FastAPI security token |

All variables are defined in `.env.example` and loaded with `python‑dotenv`.

---

## Backend Setup
```bash
git clone https://github.com/mragapranathi/Agentic-AI-Smart-Waste-Collection-Recycling-Optimization-System.git
cd Agentic-AI-Smart-Waste-Collection-Recycling-Optimization-System
python -m venv venv
.\\venv\\Scripts\\activate   # Windows
pip install -r requirements.txt
# Initialise database (Render provides a managed PostgreSQL instance)
python scripts/seed_database.py
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Frontend Setup
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```
The Vite config reads `import.meta.env.VITE_API_URL` for the backend URL.

---

## Local Execution
1. Start backend (`uvicorn`).
2. Run `npm run dev` in `frontend`.
3. Navigate to `http://localhost:5173`.
4. Use the **Simulator** page to generate sensor data.

---

## Deployment
- **Backend** – Deploy to Render (Dockerfile provided). Environment variables set in Render dashboard.
- **Frontend** – Deploy to Vercel (auto‑detects Vite project). Set `VITE_API_URL` in Vercel Environment Variables to the Render backend URL.
- CI/CD via GitHub Actions runs tests on each push and triggers Render/Vercel deployments on `main`.

---

## Testing Methodology
The repository includes a **pytest** suite covering the eight test cases you listed (TC‑01 → TC‑08). Tests instantiate in‑memory SQLite databases, run each agent service, and assert expected outcomes. Execute:
```bash
pytest backend/tests -q
```
All tests must pass before merging.

---

## Submission Requirements
| Item | Description |
|---|---|
| Source code | Complete `backend/` and `frontend/` directories. |
| README | This document, covering all listed sections. |
| Smart‑bin dataset | `data/smart_bins.csv` (synthetic sensor history). |
| Historical fill‑level data | `data/fill_history.csv`. |
| Vehicle dataset | `data/vehicles.csv`. |
| Geographic/bin‑location data | Latitude/longitude columns in `smart_bins.csv`. |
| Waste‑collection history | `data/collection_log.csv`. |
| Model configuration | `model/model.joblib` and `model/config.json`. |
| Test cases | `backend/tests/test_tcs.py` (covers TC‑01 – TC‑08). |
| Environment setup | `.env.example` and Dockerfile for reproducible deployment. |

---

## Live Application Links
| Component | Platform | URL |
|---|---|---|
| Frontend | Vercel | https://frontend-five-lime-80.vercel.app |
| Backend API | Render | https://smartwaste-backend-gb09.onrender.com |
| Swagger UI | Render | https://smartwaste-backend-gb09.onrender.com/docs |

---

## License
MIT License.
