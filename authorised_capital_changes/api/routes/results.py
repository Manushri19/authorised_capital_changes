"""
Results Routes
==============
Endpoints for retrieving the parsed results of a pipeline execution.
"""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from authorised_capital_changes.api.store import runs_store

router = APIRouter(prefix="/api/v1/results", tags=["Pipeline Results"])

@router.get("/{run_id}/table")
async def get_table(run_id: str):
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail="Run not found")
        
    state = runs_store[run_id]
    if not state.get("final_table_rows"):
        raise HTTPException(status_code=400, detail="Table not yet generated for this run")
        
    report = state.get("discrepancy_report")
    flags = report.flags if report else []
    
    return {
        "capital_table": state["final_table_rows"],
        "flags": flags
    }


@router.get("/{run_id}/discrepancy-report")
async def get_discrepancy_report(run_id: str):
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail="Run not found")
        
    state = runs_store[run_id]
    report = state.get("discrepancy_report")
    if not report:
        raise HTTPException(status_code=400, detail="Discrepancy report not yet generated")
        
    return {
        "discrepancy_report": report
    }


@router.get("/{run_id}/html", response_class=HTMLResponse)
async def get_html(run_id: str):
    # Depending on how the pipeline is structured, HTML output might be written to disk.
    out_dir = os.path.join(os.getcwd(), "data", "outputs")
    html_path = os.path.join(out_dir, "capital_table.html")
    
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="HTML report not found on disk")
        
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()
