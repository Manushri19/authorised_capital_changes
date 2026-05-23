import os
import shutil
from pprint import pprint
from authorised_capital_changes.pipeline.edges.routing import build_pipeline_graph

def run_full_test():
    raw_folder = os.path.join(os.getcwd(), "authorised_capital_changes", "data", "raw")
    test_folder = os.path.join(os.getcwd(), "authorised_capital_changes", "data", "test_2018")
    
    if os.path.exists(test_folder):
        shutil.rmtree(test_folder)
    os.makedirs(test_folder)
    
    # Copy exactly the 3 requested files
    files_to_copy = ["SH7_Event1_2018.md", "MOA_Event1_2018.md", "EGM_Event1_2018.md"]
    for fname in files_to_copy:
        src = os.path.join(raw_folder, fname)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(test_folder, fname))
        else:
            print(f"Warning: {fname} not found in raw folder: {src}")
    
    print(f"\n--- Starting E2E Pipeline with 2018 Event (Ollama) ---")
    
    graph = build_pipeline_graph()
    initial_state = {
        "run_id": "test_2018_event",
        "input_folder": test_folder,
        "raw_files": [], "classified_docs": [], "sh7_documents": [], "non_sh7_documents": [],
        "unclassified_documents": [], "document_groups": [], "unmatched_attachment_refs": {},
        "attachment_bundles": [], "extracted_sh7s": [], "sh7_extraction_errors": [],
        "validation_reports": [], "sh7s_blocked_by_validation": [], "sh7s_passed_validation": [],
        "capital_table_rows": [], "final_table_rows": [], "discrepancy_report": None,
        "human_review_queue": [], "human_review_resolved": [], "human_review_required": False,
        "pipeline_errors": [], "completed_stages": []
    }
    
    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        print(f"\n!!! PIPELINE FAILED !!!\nException: {e}")
        return

    print("\n--- Pipeline Execution Complete ---")
    if final_state.get("pipeline_errors"):
        print("PIPELINE ERRORS:")
        pprint(final_state["pipeline_errors"])
    
    print("\nFINAL CAPITAL TABLE ROWS:")
    rows = final_state.get("final_table_rows", [])
    for idx, row in enumerate(rows):
        safe_from = str(row.authorised_from.value).replace('₹', 'Rs.') if row.authorised_from else 'None'
        safe_to = str(row.authorised_to.value).replace('₹', 'Rs.') if row.authorised_to else 'None'
        print(f"Row {idx}: {row.meeting_date.value} | {safe_from} -> {safe_to}")

if __name__ == "__main__":
    run_full_test()
