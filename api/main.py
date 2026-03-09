"""
Ahmad Al Zahidi Painting LLC — AI Agent System
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import os

from database.session import init_db
from api.routers import leads, agents, outreach, dashboard, webhooks
from api.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Ahmad Al Zahidi Painting AI Agent System")
    os.makedirs("data", exist_ok=True)
    await init_db()
    start_scheduler()
    logger.info("✅ System ready")
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="Ahmad Al Zahidi Painting — AI Lead Agent",
    description="AI-powered client acquisition system for Dubai painting services",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(leads.router, prefix="/api/leads", tags=["Leads"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(outreach.router, prefix="/api/outreach", tags=["Outreach"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

# Serve dashboard
if os.path.exists("dashboard"):
    app.mount("/", StaticFiles(directory="dashboard", html=True), name="dashboard")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Ahmad Al Zahidi Painting AI Agent"}
