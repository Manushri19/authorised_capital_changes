"""
FastAPI Entry Point
===================
Initializes the FastAPI application and binds the routing modules.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from authorised_capital_changes.api.routes import pipeline, results
from authorised_capital_changes.logging_config import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure logging once when the server starts."""
    configure_logging()
    yield   # server runs here


app = FastAPI(
    title="Nexus Capital Intelligence API",
    description="API for managing capital intelligence pipeline runs via LangGraph.",
    version="1.0.0",
    lifespan=lifespan,
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(pipeline.router)
app.include_router(results.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
