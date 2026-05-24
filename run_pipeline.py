import os
import logging
from authorised_capital_changes.pipeline.edges.routing import build_pipeline_graph
from authorised_capital_changes.schemas.pipeline_state import PipelineState
from authorised_capital_changes.logging_config import configure_logging

configure_logging()

def main():
    input_folder = os.path.join(os.getcwd(), "authorised_capital_changes", "data", "raw")
    
    run_id = "test_run_001"
    configure_logging(run_id=run_id)   # injects run_id into every log record

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
        "human_review_queue": [],
        "human_review_resolved": [],
        "human_review_required": False,
        "pipeline_errors": [],
        "completed_stages": []
    }
    
    graph = build_pipeline_graph()
    
    print("Running pipeline...")
    final_state = graph.invoke(state)
    print("Pipeline finished.")
    if final_state.get("pipeline_errors"):
        print("Errors encountered:", final_state["pipeline_errors"])
    else:
        print("HTML successfully generated at:", os.path.join(os.getcwd(), "data", "outputs", "capital_table.html"))
    
if __name__ == "__main__":
    main()
