# backend/api/main.py

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from backend.api.routes import initiatives, campaigns, content, metrics
from backend.api.middleware.auth import verify_token
from backend.api.middleware.tenant import get_tenant_id
from backend.config.settings import settings

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    # Shutdown
    print("Shutting down...")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    initiatives.router,
    prefix="/api/initiatives",
    tags=["initiatives"]
)

app.include_router(
    campaigns.router,
    prefix="/api/campaigns",
    tags=["campaigns"]
)

app.include_router(
    content.router,
    prefix="/api/content",
    tags=["content"]
)

app.include_router(
    metrics.router,
    prefix="/api/metrics",
    tags=["metrics"]
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "debug": settings.DEBUG
    }