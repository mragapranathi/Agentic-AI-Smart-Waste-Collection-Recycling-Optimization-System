from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.session import engine, Base
import backend.app.models.entities  # Ensure all models are registered

# Import API Routers
from backend.app.api.bins import router as bins_router
from backend.app.api.sensors import router as sensors_router
from backend.app.api.forecasts import router as forecasts_router
from backend.app.api.priorities import router as priorities_router
from backend.app.api.vehicles import router as vehicles_router
from backend.app.api.routes import router as routes_router
from backend.app.api.collections import router as collections_router
from backend.app.api.recycling import router as recycling_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.workflows import router as workflows_router
from backend.app.api.agent_runs import router as agent_runs_router
from backend.app.api.approvals import router as approvals_router
from backend.app.api.reports import router as reports_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schemas...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schemas initialized.")
    yield
    logger.info("Shutting down Smart Waste backend application.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Agentic AI Smart Waste Collection & Recycling Optimization System API",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check Endpoint
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "demo_mode": settings.DEMO_MODE,
        "environment": settings.ENVIRONMENT
    }

# Register API Routers
app.include_router(bins_router, prefix=settings.API_V1_STR)
app.include_router(sensors_router, prefix=settings.API_V1_STR)
app.include_router(forecasts_router, prefix=settings.API_V1_STR)
app.include_router(priorities_router, prefix=settings.API_V1_STR)
app.include_router(vehicles_router, prefix=settings.API_V1_STR)
app.include_router(routes_router, prefix=settings.API_V1_STR)
app.include_router(collections_router, prefix=settings.API_V1_STR)
app.include_router(recycling_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(workflows_router, prefix=settings.API_V1_STR)
app.include_router(agent_runs_router, prefix=settings.API_V1_STR)
app.include_router(approvals_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
