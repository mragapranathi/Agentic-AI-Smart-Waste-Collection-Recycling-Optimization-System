# Agentic AI Smart Waste Collection & Recycling Optimization System

An intelligent, multi-agent AI system for municipal waste management — featuring real-time bin monitoring, AI-driven route optimization, automated approval workflows, demand forecasting, and comprehensive operational reporting.

---

## 🚀 Live Deployment

| Service | Platform | URL |
|---------|----------|-----|
| Frontend | Vercel | https://frontend-five-lime-80.vercel.app |
| Backend API | Render | https://smartwaste-backend-gb09.onrender.com |

---

## 🏗️ Architecture

```
BrightConeAI/
├── backend/          # FastAPI + LangGraph 8-agent pipeline
│   └── app/
│       ├── api/      # REST endpoints
│       ├── models/   # SQLAlchemy ORM models
│       ├── services/ # Business logic (KPI, reports, forecasting)
│       └── workflows/# LangGraph multi-agent graph
├── frontend/         # Vite + React + TypeScript + Tailwind
│   └── src/
│       ├── pages/    # Dashboard, Forecasting, Workflows, Reports...
│       └── components/
├── ml/               # ML model training artifacts
├── data/             # Generated reports
├── render.yaml       # Render backend deployment
└── requirements.txt  # Python dependencies
```

---

## ⚙️ Local Development

### Backend
```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate      # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run backend
$env:PYTHONPATH="E:\BrightConeAI"
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local: set VITE_API_URL=http://localhost:8000/api
npm run dev
```

---

## 🌐 Deployment

### Backend → Render
1. Connect GitHub repo on [render.com](https://render.com)
2. Select `render.yaml` (infrastructure as code)
3. Set `GEMINI_API_KEY` in Render environment variables
4. Deploy — Render auto-provisions a PostgreSQL database

### Frontend → Vercel
1. Connect GitHub repo on [vercel.com](https://vercel.com)
2. Set **Root Directory** → `frontend`
3. Set environment variable: `VITE_API_URL=https://<your-render-url>/api`
4. Deploy

---

## 🤖 AI Agent Pipeline

The system uses **LangGraph** to orchestrate 8 specialized agents:

1. **Data Collection Agent** — sensor data ingestion
2. **Waste Analysis Agent** — overflow & anomaly detection
3. **Route Optimization Agent** — vehicle routing algorithms
4. **Scheduling Agent** — collection scheduling
5. **Predictive Maintenance Agent** — fleet health monitoring
6. **Compliance & Reporting Agent** — regulatory reporting
7. **Action Planning Agent** — operational decision making
8. **Reviewer & Critic Agent** — quality assurance & approval

---

## 📊 Key Features

- **Real-time Dashboard** — 12 KPI cards with live sensor data
- **AI Forecasting** — Random Forest ML model for waste demand prediction
- **Workflow Automation** — Human-in-the-loop approval system
- **Smart Routing** — Distance-optimized vehicle dispatch
- **PDF Reports** — Comprehensive operations reports (12 sections)
- **Alert Management** — Priority-based bin overflow alerts

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Python 3.11+ |
| AI Agents | LangGraph, Google Gemini |
| ML | Scikit-learn (Random Forest) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy |
| Reports | ReportLab |
| Deployment | Vercel + Render |
