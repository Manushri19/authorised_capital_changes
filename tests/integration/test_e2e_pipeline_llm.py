import os
import shutil
import json
import logging
from pprint import pprint
from authorised_capital_changes.pipeline.edges.routing import build_pipeline_graph

logging.basicConfig(level=logging.INFO)

def create_dummy_data(folder_path: str):
    """Creates minimal but complete markdown files to trigger a full E2E LLM run."""
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    os.makedirs(folder_path)

    # 1. The Core SH-7 Form
    sh7_content = """# Form SH-7
Notice to Registrar of any alteration of share capital
CIN: U12345MH2024PTC123456
Company Name: MINIMAL DUMMY CORP
Date of meeting: 2024-01-15
Resolution type: Special

Brief particulars of change:
Authorized capital increased from ₹1,00,000 to ₹5,00,000.
Addition of 40,000 Equity Shares of ₹10 each.

Attachments:
1. Copy of resolution passed at EGM
2. Altered Memorandum of Association
"""
    with open(os.path.join(folder_path, "sh7_minimal.md"), "w", encoding="utf-8") as f:
        f.write(sh7_content)

    # 2. The Altered MOA
    moa_content = """# Memorandum of Association
Company: MINIMAL DUMMY CORP
Clause V: The Authorized Share Capital of the company is ₹5,00,000 divided into 50,000 Equity Shares of ₹10 each.
Date: 2024-01-15
"""
    with open(os.path.join(folder_path, "moa_minimal.md"), "w", encoding="utf-8") as f:
        f.write(moa_content)

    # 3. The Resolution / EGM
    egm_content = """# Extraordinary General Meeting
Company: MINIMAL DUMMY CORP
Date of Meeting: 2024-01-15
Resolution: To increase authorized share capital from ₹1,00,000 (10,000 Equity Shares of ₹10 each) to ₹5,00,000 by issuing 40,000 new Equity Shares of ₹10 each.
Passed unanimously.
"""
    with open(os.path.join(folder_path, "egm_minimal.md"), "w", encoding="utf-8") as f:
        f.write(egm_content)


def run_e2e_test():
    input_folder = os.path.join(os.getcwd(), "data", "dummy_e2e_input")
    create_dummy_data(input_folder)

    print(f"\n--- Starting Full E2E Pipeline with LLM ---")
    print(f"Reading from: {input_folder}")

    graph = build_pipeline_graph()
    
    initial_state = {
        "run_id": "test_e2e_minimal",
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

    # Execute the graph
    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        print("\n!!! PIPELINE FAILED !!!")
        print(f"Exception: {e}")
        # Graph raises on unhandled ValueError in a node. The state isn't returned natively by invoke if it crashes.
        # But we can see what was logged.
        return

    print("\n--- Pipeline Execution Complete ---")
    
    if final_state.get("pipeline_errors"):
        print("PIPELINE ERRORS:")
        pprint(final_state["pipeline_errors"])
        return

    print("\nFINAL CAPITAL TABLE ROWS:")
    rows = final_state.get("final_table_rows", [])
    for idx, row in enumerate(rows):
        print(f"Row {idx}: {row.meeting_date.value} | {row.authorised_from.value} -> {row.authorised_to.value}")

    print("\nOUTPUT FILES GENERATED:")
    outputs_dir = os.path.join(os.getcwd(), "data", "outputs")
    if os.path.exists(outputs_dir):
        for fname in os.listdir(outputs_dir):
            print(f"- {fname}")

    # Display report snippet
    report = final_state.get("discrepancy_report")
    if report:
        print("\nDISCREPANCY FLAGS:")
        for flag in report.flags:
            print(f"[{flag.flag_code}] Row {flag.row_number} - {flag.field_name}: {flag.flag_message}")
    
    print("\nSuccessfully ran the E2E Pipeline using LLMs.")

if __name__ == "__main__":
    run_e2e_test()
