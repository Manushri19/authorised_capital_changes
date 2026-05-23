"""
FastAPI Entry Point
===================
Initializes the FastAPI application and binds the routing modules.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from authorised_capital_changes.api.routes import pipeline, results

app = FastAPI(
    title="Nexus Capital Intelligence API",
    description="API for managing capital intelligence pipeline runs via LangGraph.",
    version="1.0.0"
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
