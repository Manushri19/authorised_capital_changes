import os
from pprint import pprint
from authorised_capital_changes.pipeline.edges.routing import build_pipeline_graph

def run_all_raw_test():
    raw_folder = os.path.join(os.getcwd(), "authorised_capital_changes", "data", "raw")
    
    print(f"\n--- Starting Full E2E Pipeline with ALL RAW DATA (Ollama) ---")
    
    graph = build_pipeline_graph()
    initial_state = {
        "run_id": "test_all_raw",
        "input_folder": raw_folder,
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
        
    report = final_state.get("discrepancy_report")
    if report:
        print("\nDISCREPANCY FLAGS:")
        for flag in report.flags:
            print(f"[{flag.flag_code}] Row {flag.row_number} - {flag.field_name}: {flag.flag_message}")

if __name__ == "__main__":
    run_all_raw_test()
