"""
Pipeline Routes
===============
Endpoints for triggering pipeline runs and checking execution status.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from authorised_capital_changes.pipeline.edges.routing import build_pipeline_graph
from authorised_capital_changes.schemas.pipeline_state import PipelineState
from authorised_capital_changes.api.store import runs_store

router = APIRouter(prefix="/api/v1/pipeline", tags=["Pipeline Execution"])

class RunPipelineRequest(BaseModel):
    input_folder: str
    run_id: Optional[str] = None


def run_pipeline_task(run_id: str, input_folder: str):
    """Background task to run the LangGraph pipeline."""
    state: PipelineState = {
        "run_id": run_id,
        "input_folder": input_folder,
        "raw_files": [],
        "classified_docs": [],
        "sh7_documents": [],
        "non_sh7_documents": [],
        "unclassified_documents": [],
        "document_groups": [],
        "unmatched_attachment_refs": {},
        "attachment_bundles": [],
        "extracted_sh7s": [],
        "sh7_extraction_errors": [],
        "validation_reports": [],
        "sh7s_blocked_by_validation": [],
        "sh7s_passed_validation": [],
        "capital_table_rows": [],
        "final_table_rows": [],
        "discrepancy_report": None,
        "pipeline_errors": [],
        "completed_stages": []
    }
    runs_store[run_id] = state
    
    graph = build_pipeline_graph()
    try:
        final_state = graph.invoke(state)
        runs_store[run_id] = final_state
    except Exception as e:
        state["pipeline_errors"].append({"stage": "orchestrator", "error": str(e), "filename": "N/A"})
        runs_store[run_id] = state


@router.post("/run")
async def run_pipeline(request: RunPipelineRequest, background_tasks: BackgroundTasks):
    run_id = request.run_id or str(uuid.uuid4())
    background_tasks.add_task(run_pipeline_task, run_id, request.input_folder)
    return {
        "run_id": run_id,
        "status": "started",
        "started_at": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/status/{run_id}")
async def get_status(run_id: str):
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail="Run not found")
        
    state = runs_store[run_id]
    completed = state.get("completed_stages") or []
    errors = state.get("pipeline_errors") or []
    
    status = "running"
    if "narrative_generator" in completed:
        status = "completed"
    if errors and not completed:
        status = "failed"
    elif errors:
        status = "partial"
        
    return {
        "status": status,
        "completed_stages": completed,
        "pipeline_errors": errors
    }
